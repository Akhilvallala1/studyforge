"""CLI entrypoint for the generation eval. This is the only file in the tree that
spends real money, and it is run by hand, never from pytest.

    cd backend
    export STUDYFORGE_DB=/tmp/eval.sqlite3
    export STUDYFORGE_COST_LIMIT_USD=3.00
    export STUDYFORGE_COST_ALERT_USD=1.00
    python -m evals.run_eval --dry-run          # ingest + cost projection, no LLM call
    python -m evals.run_eval --label baseline   # the real thing

The preflight refuses to start against the developer's own database, or with a
paid provider and no hard cap configured, because the failure mode of getting
either wrong is measured in dollars and lost data rather than a stack trace.
"""

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import ingest
from app.costs import estimate_cost
from app.llm import get_provider
from evals import report, sources
from evals.harness import run_course_eval

DEFAULT_OUT_DIR = BACKEND_DIR / "evals" / "output"
DATA_DIR = BACKEND_DIR / "evals" / "data"

# The document under test. PEP 8 is real, dense, structured technical prose with
# section-level topics spread evenly through it, which is exactly what the concept
# coverage metric needs in order to distinguish "read the whole document" from
# "read the first page".
TECHNICAL_URL = "https://peps.python.org/pep-0008/"

# Rough tokens-per-character for the pre-run projection. Only used to warn a human
# before spending; the reported numbers always come from the provider's own counts.
CHARS_PER_TOKEN = 4.0
# Projection assumptions, from the midpoint of what OUTLINE_SYSTEM asks for.
PROJECTED_LESSONS = 9
PROJECTED_OUTPUT_TOKENS_PER_CALL = 2000


def available_sources() -> dict:
    """Source key -> zero-argument loader. Lazy so --dry-run of one source does not
    fetch the other."""
    return {
        "pep8-url": lambda: sources.from_url("pep8-url", TECHNICAL_URL),
        "prose-text": lambda: sources.from_text(
            "prose-text",
            "darwin-origin-excerpt",
            (DATA_DIR / "prose-darwin.txt").read_text(encoding="utf-8"),
        ),
    }


def preflight(require_cap: bool = True) -> dict:
    """Fail loudly before any money is spent, rather than after."""
    problems = []
    db_path = os.environ.get("STUDYFORGE_DB")
    if not db_path:
        problems.append(
            "STUDYFORGE_DB is unset; the eval would write into the default "
            "studyforge.sqlite3. Point it at a scratch file."
        )
    elif Path(db_path).resolve() == (BACKEND_DIR / "studyforge.sqlite3").resolve():
        problems.append(f"STUDYFORGE_DB points at the real database ({db_path}). Use a scratch file.")

    provider = get_provider()
    limit = os.environ.get("STUDYFORGE_COST_LIMIT_USD")
    if provider.is_paid and require_cap and not limit:
        problems.append(
            "Provider is paid and STUDYFORGE_COST_LIMIT_USD is unset, so nothing would "
            "stop a runaway run. Set a cap."
        )
    if problems:
        for problem in problems:
            print(f"REFUSING TO RUN: {problem}", file=sys.stderr)
        raise SystemExit(2)
    return {
        "provider": provider.name,
        "model": provider.model,
        "is_paid": provider.is_paid,
        "db": db_path,
        "cost_limit_usd": float(limit) if limit else None,
        "cost_alert_usd": os.environ.get("STUDYFORGE_COST_ALERT_USD"),
    }


def project_cost(model: str, text: str, lessons: int = PROJECTED_LESSONS) -> dict:
    """Order-of-magnitude cost projection for one course, before running it.

    Deliberately pessimistic in the way the pipeline actually is: `generate_course`
    re-sends every chunk of the document with every single lesson call, so input
    cost scales with lessons x whole document, not with the document once.
    """
    doc_tokens = int(len(text) / CHARS_PER_TOKEN)
    calls = lessons + 1
    input_tokens = doc_tokens * calls
    output_tokens = PROJECTED_OUTPUT_TOKENS_PER_CALL * calls
    cost, approximate = estimate_cost(model, input_tokens, output_tokens)
    return {
        "doc_tokens": doc_tokens,
        "assumed_lessons": lessons,
        "assumed_calls": calls,
        "projected_input_tokens": input_tokens,
        "projected_output_tokens": output_tokens,
        "projected_cost_usd": round(cost, 4),
        "approximate_pricing": approximate,
    }


def usage_snapshot() -> dict:
    """The app's own GET /usage, in-process against the scratch database.

    Read through the API rather than the ORM on purpose: it is the number the user
    would see in the product, so if metering and the endpoint disagree, that is a
    bug worth catching here.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/usage")
        response.raise_for_status()
        return response.json()


def load_sources(keys: list[str]) -> list:
    registry = available_sources()
    unknown = [k for k in keys if k not in registry]
    if unknown:
        raise SystemExit(f"Unknown source(s): {unknown}. Known: {sorted(registry)}")
    loaded = []
    for key in keys:
        print(f"Ingesting {key} ...", flush=True)
        source = registry[key]()
        chunks = ingest.chunk_text(source.text)
        print(f"  {len(source.text):,} chars -> {len(chunks)} chunks")
        loaded.append(source)
    return loaded


def rescore(bundle_path: Path, out_dir: Path, label: str) -> Path:
    """Recompute today's metrics over a saved bundle's courses. Costs nothing.

    Needed because a metric that did not exist when a run was saved cannot be read
    back out of the file. Comparing a corrected metric on the new run against a zero
    on the old one would not be a comparison, so the old course is re-measured with
    the same code before any before/after table is drawn.
    """
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    from evals.metrics import evaluate

    registry = available_sources()
    rescored = []
    for result in bundle.get("runs", []):
        course = result.get("course")
        key = result.get("name")
        if not course or key not in registry:
            print(f"  {key}: no course to rescore, kept as is")
            rescored.append(result)
            continue
        chunks = ingest.chunk_text(registry[key]().text)
        if len(chunks) != result.get("source", {}).get("chunks"):
            print(
                f"  {key}: WARNING source now splits into {len(chunks)} chunks, "
                f"was {result['source']['chunks']}; rescoring against today's text"
            )
        result = {**result, "metrics": evaluate(course, chunks), "rescored": True}
        print(f"  {key}: rescored over {len(chunks)} chunks")
        rescored.append(result)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = report.write_outputs(out_dir, label, rescored)
    return written["results"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="baseline", help="names the output files")
    parser.add_argument(
        "--source",
        action="append",
        dest="source_keys",
        help="repeatable; defaults to every registered source",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ingest and project cost without calling the model",
    )
    parser.add_argument("--yes", action="store_true", help="skip the spend confirmation prompt")
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("BEFORE.json", "AFTER.json"),
        help="render a before/after table from two saved result bundles and exit",
    )
    parser.add_argument(
        "--rescore",
        type=Path,
        metavar="RESULTS.json",
        help=(
            "recompute today's metrics over a saved bundle's courses and write it "
            "under --label. No model calls, no cost."
        ),
    )
    args = parser.parse_args(argv)

    if args.rescore:
        path = rescore(args.rescore, args.out, args.label)
        print(f"Wrote {path}")
        return 0

    if args.compare:
        before = json.loads(Path(args.compare[0]).read_text(encoding="utf-8"))
        after = json.loads(Path(args.compare[1]).read_text(encoding="utf-8"))
        text = report.compare_markdown(before, after)
        out_path = args.out / f"compare-{args.label}.md"
        args.out.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(text)
        print(f"\nWrote {out_path}")
        return 0

    env = preflight(require_cap=not args.dry_run)
    print(f"Provider: {env['provider']} / {env['model']} (paid={env['is_paid']})")
    print(f"Database: {env['db']}")
    print(f"Cost cap: {env['cost_limit_usd']}, alert at {env['cost_alert_usd']}")

    keys = args.source_keys or list(available_sources())
    loaded = load_sources(keys)

    total_projected = 0.0
    for source in loaded:
        projection = project_cost(env["model"], source.text)
        total_projected += projection["projected_cost_usd"]
        print(
            f"  {source.key}: ~{projection['doc_tokens']:,} tokens/doc, "
            f"projected ${projection['projected_cost_usd']:.2f} "
            f"({projection['assumed_calls']} calls)"
        )
    print(f"Projected total: ~${total_projected:.2f} (cap ${env['cost_limit_usd']})")

    if args.dry_run:
        print("Dry run: no model calls made.")
        return 0

    if not args.yes:
        answer = input("Spend real money on this run? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return 1

    from app.db import init_db

    init_db()

    results = []
    for source in loaded:
        print(f"\nGenerating course from {source.key} ...", flush=True)
        result = run_course_eval(source.key, source.text, source.meta())
        results.append(result)
        cost = result.get("cost_latency", {})
        status = "ok" if result["ok"] else f"FAILED: {result['error']}"
        print(
            f"  {status} | {cost.get('calls', 0)} calls | "
            f"${cost.get('cost_usd', 0):.4f} | {result['wall_clock_s']:.0f}s"
        )
        # Persist after every course: a later failure must not throw away the
        # measurements a completed course already paid for.
        written = report.write_outputs(args.out, args.label, results)

    usage = usage_snapshot()
    usage_path = args.out / f"usage-{args.label}.json"
    usage_path.write_text(json.dumps(usage, indent=2), encoding="utf-8")

    print("\nWrote:")
    for name, path in written.items():
        print(f"  {name}: {path}")
    print(f"  usage: {usage_path}")
    totals = usage.get("totals", usage)
    print(f"\nGET /usage totals: {json.dumps(totals)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
