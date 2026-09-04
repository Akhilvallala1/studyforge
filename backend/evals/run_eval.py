"""CLI entrypoint for the generation eval. This is the only file in the tree that
spends real money, and it is run by hand, never from pytest.

    cd backend
    export STUDYFORGE_DB=/tmp/eval.sqlite3
    export STUDYFORGE_COST_LIMIT_USD=3.00
    export STUDYFORGE_COST_ALERT_USD=1.00
    python -m evals.run_eval --dry-run          # ingest + cost projection, no LLM call
    python -m evals.run_eval --label my-run     # the real thing

The preflight refuses to start against the developer's own database, or with a
paid provider and no hard cap configured, because the failure mode of getting
either wrong is measured in dollars and lost data rather than a stack trace.

Everything about money here is conditional on the provider actually charging for
the run. Against a free provider (ollama, fake) the runner quotes no price and
asks for no spending confirmation: there is no price to quote, and a confirmation
that appears on every run is one nobody reads on the run where it counts.
"""

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import generation, ingest
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


# How much of PEP 8 the multi-source corpus takes. Enough to be a real second document
# with its own vocabulary and structure, small enough that the whole corpus stays close
# to prose-text in size, so a multi-source run costs about what the existing single
# source run costs and can therefore be repeated. Repetition is not optional here: see
# evals/trials.py on why one run of each arm proves nothing.
MULTI_PEP8_CHARS = 3000


def _multi_documents() -> list[tuple[str, str]]:
    """The multi-source corpus: two genuinely unrelated documents.

    UNRELATED IS THE REQUIREMENT, not a detail. The failure this feature exists to
    prevent is a model reading two documents as one continuous work, and two excerpts of
    the same book cannot exhibit it: a lesson bridging them would be correct. Darwin and
    a Python style guide share no vocabulary, no structure and no subject, so a lesson
    that reads across the seam is visibly wrong rather than arguably fine.

    THE CHUNK ARITHMETIC IS THE POINT of these two sizes. Routing switches on at
    SEGMENT_ROUTING_MIN_CHUNKS, which is 3, and chunks are up to 8,000 characters, so two
    short documents make two chunks and stay UNROUTED. Darwin's full text is 2 chunks and
    the PEP 8 excerpt is 1, giving exactly 3: the smallest corpus that is genuinely
    multi-source AND routed, which is the configuration this feature turns on and the
    only one worth measuring.
    """
    darwin = (DATA_DIR / "prose-darwin.txt").read_text(encoding="utf-8")
    pep8 = ingest.extract_url(TECHNICAL_URL)[:MULTI_PEP8_CHARS]
    return [("darwin-origin", ingest.clean_text(darwin)), ("pep8-style-guide", pep8)]


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
        # A 2,500-char excerpt of the same text, for prompt trials. One course costs
        # roughly a third of the full source, which is what makes running the same
        # variant several times affordable, and repeated runs are the only way to tell
        # a real difference from the spread between two runs of one prompt.
        "prose-short": lambda: sources.from_text(
            "prose-short",
            "darwin-origin-short",
            (DATA_DIR / "prose-darwin-short.txt").read_text(encoding="utf-8"),
        ),
        # The multi-source arm. Loaded as one Source whose text is the whole corpus, so
        # every existing metric scores it unchanged; the document boundaries travel
        # separately, through MULTI_SOURCE_KEYS below, and only generation sees them.
        # Deliberately NOT a new Source field: the type is shared with app code and is
        # being lifted into app/ingest.py by another change, and a corpus is not a source.
        "multi-darwin-pep8": lambda: sources.from_text(
            "multi-darwin-pep8",
            "darwin-origin + pep8-style-guide",
            "\n\n".join(text for _, text in _multi_documents()),
        ),
    }


# Source keys whose corpus is several documents, mapped to their loader. The registry
# above hands back one Source so the metrics and the cost projection need no special
# case; this is the only place that knows the corpus has seams in it.
MULTI_SOURCE_KEYS = {"multi-darwin-pep8": _multi_documents}


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


def project_cost(
    model: str, text: str, lessons: int = PROJECTED_LESSONS, is_paid: bool = True
) -> dict:
    """Order-of-magnitude cost projection for one course, before running it.

    Deliberately pessimistic in the way the pipeline actually is: `generate_course`
    re-sends every chunk of the document with every single lesson call, so input
    cost scales with lessons x whole document, not with the document once.

    A free provider is quoted no price at all. estimate_cost falls back to the
    configured default rates for any model id it does not recognize, and no local
    model is in the pricing table, so asking it about "llama3.1:8b" cheerfully
    returns a dollar figure for a run that cannot cost anything. projected_cost_usd
    is None in that case and the caller reports tokens instead. is_paid defaults to
    True so that a caller who forgets over-warns rather than under-warns.
    """
    doc_tokens = int(len(text) / CHARS_PER_TOKEN)
    calls = lessons + 1
    input_tokens = doc_tokens * calls
    output_tokens = PROJECTED_OUTPUT_TOKENS_PER_CALL * calls
    projection = {
        "doc_tokens": doc_tokens,
        "assumed_lessons": lessons,
        "assumed_calls": calls,
        "projected_input_tokens": input_tokens,
        "projected_output_tokens": output_tokens,
        "priced": is_paid,
    }
    if not is_paid:
        # None rather than 0.0: a zero would be true, but it would read as a price,
        # and the whole point is that there is no price here to be right or wrong.
        return {**projection, "projected_cost_usd": None, "approximate_pricing": None}
    cost, approximate = estimate_cost(model, input_tokens, output_tokens)
    return {
        **projection,
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
        # Chunked the way GENERATION will chunk it, which for a multi-source corpus is
        # per document rather than over the concatenation. The two disagree, and the
        # disagreement is not cosmetic: chunk_text packs paragraphs up to 8,000
        # characters, so this corpus concatenated is 2 chunks and the same corpus
        # chunked per document is 3. Routing switches on at 3. Printing the
        # concatenated count told the operator the run was unrouted while generation
        # routed it, and routing is the one thing this eval is about.
        if key in MULTI_SOURCE_KEYS:
            documents = MULTI_SOURCE_KEYS[key]()
            chunks, _owners = ingest.chunk_sources(
                [ingest.from_text("", label, text) for label, text in documents]
            )
            print(
                f"  {len(source.text):,} chars over {len(documents)} documents "
                f"-> {len(chunks)} chunks "
                f"(routing {'ON' if len(chunks) >= generation.SEGMENT_ROUTING_MIN_CHUNKS else 'off'})"
            )
        else:
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


# What --label falls back to, and an OCCUPIED name: evals/output holds the
# reference run's committed report-baseline.md, results-baseline.json and
# usage-baseline.json. See check_overwrite for why that matters.
DEFAULT_LABEL = "baseline"


def existing_outputs(out_dir: Path, label: str) -> list[Path]:
    """Files a run under `label` would overwrite, found before anything is written.

    These patterns have to stay in step with what is actually written, here and in
    report.write_outputs, and an artifact type this misses is a file the guard would
    let a run destroy in silence. So the drift is tested rather than trusted:
    test_the_guard_sees_every_artifact_a_run_writes performs a real run and asserts
    this function finds every file it produced.

    The course pattern over-matches, and deliberately. course-<label>-<source>.md
    cannot be split by filename alone once either half contains a hyphen, so
    "baseline" also matches course-baseline-rescored-demo.md, which belongs to the
    label "baseline-rescored". The two errors are not symmetric: over-matching costs
    a --label or a --force, under-matching costs a committed file. So this errs
    wide, and the refusal below says these files MATCH the label rather than
    claiming a run would certainly overwrite each one.
    """
    patterns = (
        f"results-{label}.json",
        f"report-{label}.md",
        f"usage-{label}.json",
        f"compare-{label}.md",
        f"course-{label}-*.md",
    )
    found: set[Path] = set()
    for pattern in patterns:
        found.update(out_dir.glob(pattern))
    return sorted(found)


def check_overwrite(out_dir: Path, label: str, explicit: bool, force: bool) -> None:
    """Refuse to destroy a previous run's output that nobody asked to replace.

    The trap is the default, not reusing a label. --label falls back to "baseline"
    and --out falls back to the committed evals/output, and "baseline" is where the
    reference run's artifacts already live, so the command you get by typing nothing
    overwrites four committed files. "baseline" also READS like a name reserved for
    that reference, which makes overwriting it feel safe when it is the opposite.

    An explicitly passed --label is left alone, and not merely warned about either.
    Rerunning a label you named is the documented behaviour (evals/README: a label
    is the run's name) and it is the ordinary loop while iterating on a prompt.
    Warning on every iteration of the common case is the crying-wolf failure, and
    the cost of it is that people stop reading the line that does matter.
    """
    if explicit or force:
        return
    clashes = existing_outputs(out_dir, label)
    if not clashes:
        return
    print(
        f"REFUSING TO RUN: no --label was given, so it defaults to {label!r}, and "
        f"{out_dir} already holds {len(clashes)} file(s) whose names match it:",
        file=sys.stderr,
    )
    for path in clashes:
        print(f"  {path.name}", file=sys.stderr)
    print(
        "Pass --label <name> to write a new run, or --force to overwrite these.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--label",
        default=None,
        help=f"names the output files (default: {DEFAULT_LABEL})",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="source_keys",
        help="repeatable; defaults to every registered source",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--variant",
        help="named prompt variant from evals/variants.py; omit to use what app code ships",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ingest and project cost without calling the model",
    )
    parser.add_argument("--yes", action="store_true", help="skip the spend confirmation prompt")
    parser.add_argument(
        "--no-source-tags",
        action="store_true",
        help=(
            "multi-source runs only: withhold the document tags, reproducing the "
            "pre-feature prompt exactly. This is the BEFORE arm of the outline A/B."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing output written under the default label",
    )
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
    label = DEFAULT_LABEL if args.label is None else args.label
    # Every path below this writes under `label` except --dry-run, which makes no
    # calls and writes nothing, so refusing it over an occupied name would be a
    # false alarm on the one command that is always safe to run.
    if not args.dry_run:
        check_overwrite(args.out, label, explicit=args.label is not None, force=args.force)

    if args.rescore:
        path = rescore(args.rescore, args.out, label)
        print(f"Wrote {path}")
        return 0

    if args.compare:
        before = json.loads(Path(args.compare[0]).read_text(encoding="utf-8"))
        after = json.loads(Path(args.compare[1]).read_text(encoding="utf-8"))
        text = report.compare_markdown(before, after)
        out_path = args.out / f"compare-{label}.md"
        args.out.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(text)
        print(f"\nWrote {out_path}")
        return 0

    env = preflight(require_cap=not args.dry_run)
    print(f"Provider: {env['provider']} / {env['model']} (paid={env['is_paid']})")
    print(f"Database: {env['db']}")
    if env["is_paid"]:
        print(f"Cost cap: {env['cost_limit_usd']}, alert at {env['cost_alert_usd']}")
    else:
        print(f"Cost: none. {env['provider']} is a free provider, so the spend cap and the "
              f"cost alert do not apply to this run.")

    keys = args.source_keys or list(available_sources())
    loaded = load_sources(keys)
    projections = [
        (source, project_cost(env["model"], source.text, is_paid=env["is_paid"]))
        for source in loaded
    ]

    if env["is_paid"]:
        total_projected = 0.0
        guessed_price = False
        for source, projection in projections:
            total_projected += projection["projected_cost_usd"]
            guessed_price = guessed_price or projection["approximate_pricing"]
            print(
                f"  {source.key}: ~{projection['doc_tokens']:,} tokens/doc, "
                f"projected ${projection['projected_cost_usd']:.2f} "
                f"({projection['assumed_calls']} calls)"
            )
        print(f"Projected total: ~${total_projected:.2f} (cap ${env['cost_limit_usd']})")
        if guessed_price:
            # The same state /usage grew a notice for: exact token counts against a
            # price nobody has. Saying it here costs one line and stops a confident
            # figure being read as a quote.
            print(
                f"  NOTE: {env['model']} has no entry in the pricing table, so that figure "
                f"uses the STUDYFORGE_PRICE_DEFAULT_IN_USD / _OUT_USD fallback rates. The "
                f"token estimate is the usual one; the price is a guess."
            )
    else:
        # Tokens and calls are real numbers about a free run. A dollar figure is not.
        total_calls = 0
        total_tokens = 0
        for source, projection in projections:
            total_calls += projection["assumed_calls"]
            total_tokens += (
                projection["projected_input_tokens"] + projection["projected_output_tokens"]
            )
            print(
                f"  {source.key}: ~{projection['doc_tokens']:,} tokens/doc, "
                f"~{projection['projected_input_tokens']:,} in + "
                f"~{projection['projected_output_tokens']:,} out "
                f"({projection['assumed_calls']} calls)"
            )
        print(
            f"Projected total: ~{total_tokens:,} tokens over {total_calls} calls. "
            f"No cost: {env['provider']} is free."
        )

    if args.dry_run:
        print("Dry run: no model calls made.")
        return 0

    # Only a paid provider is asked to consent. Asking on a free run trains the
    # answer to a question that matters, and there is nothing to consent to.
    if env["is_paid"] and not args.yes:
        answer = input("Spend real money on this run? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return 1

    from app.db import init_db

    init_db()

    if args.variant:
        from evals import variants

        chosen = variants.apply(args.variant)
        print(f"Prompt variant: {chosen.key} ({chosen.note})")

    results = []
    for source in loaded:
        documents = MULTI_SOURCE_KEYS[source.key]() if source.key in MULTI_SOURCE_KEYS else None
        if documents:
            tagged = "untagged (pre-feature prompt)" if args.no_source_tags else "tagged"
            print(
                f"\n{source.key} is {len(documents)} documents: "
                f"{', '.join(label for label, _ in documents)} [{tagged}]"
            )
        elif args.no_source_tags:
            # Silently ignoring the flag would let a whole arm of the A/B be run with
            # the wrong prompt and reported as the right one.
            print(f"  NOTE: --no-source-tags does nothing for single-source {source.key}.")
        print(f"\nGenerating course from {source.key} ...", flush=True)
        result = run_course_eval(
            source.key,
            source.text,
            source.meta(),
            documents=documents,
            tag_sources=not args.no_source_tags,
        )
        results.append(result)
        cost = result.get("cost_latency", {})
        status = "ok" if result["ok"] else f"FAILED: {result['error']}"
        # This dollar figure stays on a free run, where the projection above does not,
        # and the difference is not an inconsistency. It is summed from real llm_calls
        # rows, so on an unpaid provider it is a MEASURED zero: metering wrote 0.0
        # because is_paid is False, and reporting what was measured is the point of
        # the line. The projection is suppressed because it was never a measurement of
        # anything, only estimate_cost guessing a rate for a model it did not know.
        # Do not "tidy" this to match the projection path; they say different things.
        print(
            f"  {status} | {cost.get('calls', 0)} calls | "
            f"${cost.get('cost_usd', 0):.4f} | {result['wall_clock_s']:.0f}s"
        )
        # Persist after every course: a later failure must not throw away the
        # measurements a completed course already paid for.
        written = report.write_outputs(args.out, label, results)

    usage = usage_snapshot()
    usage_path = args.out / f"usage-{label}.json"
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
