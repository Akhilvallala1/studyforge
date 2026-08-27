"""Aggregate repeated eval runs, so a prompt comparison can be read honestly.

A single run tells you almost nothing. Generation is nondeterministic, so two runs of
one prompt differ, and the only way to know whether prompt A beats prompt B is to know
how far apart two runs of A already are. This module reports that spread alongside the
averages, and refuses to name a winner whose lead is inside it.

    python -m evals.trials evals/output --group noise-B --group trial-A
"""

import argparse
import json
import statistics
from pathlib import Path

# The metrics the maintainer chose to optimize, in the order they matter.
PRIMARY = [
    ("answerability.answerable_rate", "Answerable from lesson"),
    ("grounding.supported_rate", "Grounded answers"),
]
SECONDARY = [
    ("answerability.giveaway_mcqs", "Giveaway MCQs"),
    ("grounding.hallucination_candidates", "Hallucination candidates"),
    ("structure.quiz_items", "Quiz items"),
    ("structure.lessons", "Lessons"),
]


def dig(data: dict, dotted: str):
    for part in dotted.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


def load_group(out_dir: Path, prefix: str) -> list[dict]:
    """Every result file whose label starts with `prefix`, one entry per course."""
    runs = []
    for path in sorted(out_dir.glob(f"results-{prefix}*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for result in payload.get("runs", []):
            if result.get("ok") and result.get("metrics"):
                runs.append({"label": path.stem, "metrics": result["metrics"]})
    return runs


def summarize(runs: list[dict], key: str) -> dict | None:
    values = [dig(r["metrics"], key) for r in runs]
    values = [v for v in values if isinstance(v, int | float)]
    if not values:
        return None
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "min": min(values),
        "max": max(values),
        "spread": max(values) - min(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "values": values,
    }


def _fmt(value: float, key: str) -> str:
    return f"{value:.1%}" if "rate" in key else f"{value:.1f}"


def report(out_dir: Path, groups: list[str]) -> str:
    lines = ["# Prompt trials", ""]
    loaded = {g: load_group(out_dir, g) for g in groups}
    for group, runs in loaded.items():
        lines.append(f"- `{group}`: {len(runs)} run(s)")
    lines.append("")

    for key, title in PRIMARY + SECONDARY:
        lines += [f"## {title}", "", "| Variant | n | mean | range | spread |", "|---|---|---|---|---|"]
        for group, runs in loaded.items():
            stat = summarize(runs, key)
            if not stat:
                lines.append(f"| {group} | 0 | - | - | - |")
                continue
            lines.append(
                f"| {group} | {stat['n']} | {_fmt(stat['mean'], key)} | "
                f"{_fmt(stat['min'], key)} to {_fmt(stat['max'], key)} | "
                f"{_fmt(stat['spread'], key)} |"
            )
        lines.append("")

    # The honesty check: is any lead bigger than the noise it would have to beat?
    lines += ["## Is any difference real?", ""]
    for key, title in PRIMARY:
        stats = {g: summarize(r, key) for g, r in loaded.items()}
        stats = {g: s for g, s in stats.items() if s}
        if len(stats) < 2:
            continue
        widest = max(s["spread"] for s in stats.values())
        ranked = sorted(stats.items(), key=lambda kv: kv[1]["mean"], reverse=True)
        best, second = ranked[0], ranked[1]
        lead = best[1]["mean"] - second[1]["mean"]
        verdict = (
            f"lead {_fmt(lead, key)} vs widest within-prompt spread {_fmt(widest, key)}: "
            + (
                "larger than the noise, worth acting on"
                if lead > widest
                else "INSIDE the noise, not a result"
            )
        )
        lines.append(f"- **{title}**: {best[0]} leads {second[0]}, {verdict}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--group", action="append", dest="groups", required=True)
    parser.add_argument("--write", type=Path, help="also write the report here")
    args = parser.parse_args()

    text = report(args.out_dir, args.groups)
    print(text)
    if args.write:
        args.write.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
