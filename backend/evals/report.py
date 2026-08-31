"""Rendering: the full generated course as readable markdown, a metrics summary,
and a before/after comparison between two saved result files."""

import json
from pathlib import Path

from evals.metrics import NOVEL_RATE_LIMIT

# Headline numbers a prompt change is expected to move. Kept as one list so the
# summary table and the comparison never drift apart.
HEADLINE_METRICS = (
    ("structure.lessons", "Lessons"),
    ("structure.quiz_items", "Quiz items"),
    ("structure.problem_count", "Structure problems"),
    ("parse.strict_json_first_try_rate", "Strict JSON first try"),
    ("parse.hard_parse_failures", "Hard parse failures"),
    ("grounding.supported_rate", "Grounded, all items (old metric)"),
    ("grounding.extractive_supported_rate", "Grounded, extractive items only"),
    ("grounding.unsupported_items", "Ungrounded items, all"),
    ("grounding.extractive_unsupported_items", "Ungrounded extractive items"),
    ("grounding.hallucination_candidates", "Hallucination candidates"),
    ("grounding.mean_window_recall", "Mean grounding recall"),
    ("answerability.answerable_rate", "Answerable from lesson"),
    ("answerability.unanswerable_items", "Unanswerable items"),
    ("answerability.giveaway_mcqs", "Giveaway MCQs"),
    ("coverage.chunk_coverage_rate", "Source chunks covered"),
    ("coverage.max_chunk_share", "Largest single-chunk share (old metric)"),
    ("coverage.max_concentration_ratio", "Concentration vs chunk length"),
    ("source_coverage.mean_chunk_recall", "Source recall, mean chunk"),
    ("source_coverage.min_chunk_recall", "Source recall, worst chunk"),
    ("cost.cost_usd", "Cost USD"),
    ("cost.wall_clock_s", "Wall clock s"),
)


def headline(result: dict) -> dict:
    """Flatten one result into the comparable numbers named above.

    Keys absent from an older bundle come back as 0. A result file written before a
    metric existed cannot be made to report it here; rescore the saved course with
    `--rescore` to get a real number instead of a zero.
    """
    metrics = result.get("metrics") or {}
    structure = metrics.get("structure", {})
    grounding = metrics.get("grounding", {})
    answerability = metrics.get("answerability", {})
    coverage = metrics.get("coverage", {})
    source_cov = metrics.get("source_coverage", {})
    parse = result.get("parse_reliability", {})
    cost = result.get("cost_latency", {})
    calls = parse.get("total_calls") or 0
    return {
        "structure.lessons": structure.get("lessons", 0),
        "structure.quiz_items": structure.get("quiz_items", 0),
        "structure.problem_count": len(structure.get("problems", [])),
        "parse.strict_json_first_try_rate": (
            parse.get("strict_json_first_try", 0) / calls if calls else 0.0
        ),
        "parse.hard_parse_failures": parse.get("hard_parse_failures", 0),
        "grounding.supported_rate": grounding.get("supported_rate", 0.0),
        "grounding.extractive_supported_rate": grounding.get("extractive_supported_rate", 0.0),
        "grounding.unsupported_items": grounding.get("unsupported_items", 0),
        "grounding.extractive_unsupported_items": grounding.get(
            "extractive_unsupported_items", 0
        ),
        "grounding.hallucination_candidates": grounding.get("hallucination_candidates", 0),
        "grounding.mean_window_recall": grounding.get("mean_window_recall", 0.0),
        "answerability.answerable_rate": answerability.get("answerable_rate", 0.0),
        "answerability.unanswerable_items": answerability.get("unanswerable_items", 0),
        "answerability.giveaway_mcqs": answerability.get("giveaway_mcqs", 0),
        "coverage.chunk_coverage_rate": coverage.get("chunk_coverage_rate", 0.0),
        "coverage.max_chunk_share": coverage.get("max_chunk_share", 0.0),
        "coverage.max_concentration_ratio": coverage.get("max_concentration_ratio", 0.0),
        "source_coverage.mean_chunk_recall": source_cov.get("mean_chunk_recall", 0.0),
        "source_coverage.min_chunk_recall": source_cov.get("min_chunk_recall", 0.0),
        "cost.cost_usd": cost.get("cost_usd", 0.0),
        "cost.wall_clock_s": result.get("wall_clock_s", 0.0),
    }


APPROXIMATE_COST_NOTE = (
    "Approximate: at least one metered call is missing an exact token count, or used a "
    "model with no entry in the pricing table and was costed at the configured fallback "
    "rate (STUDYFORGE_PRICE_DEFAULT_IN_USD / _OUT_USD)."
)


def cost_note(cost: dict) -> str | None:
    """The qualifier a cost figure needs, when it needs one.

    harness.latency_and_cost already works `any_approximate` out from the metered
    rows and puts it in the saved bundle. Nothing rendered it, so a paid provider on
    a model missing from costs.PRICING printed a confident dollar figure built from
    the fallback rates with nothing saying the price was a guess. /usage grew a
    notice for exactly that state; this file is the artifact a human reads to judge
    a run, so it says it too.

    The harness records one boolean for two causes and, unlike main.py, has no
    session to separate them from. Naming both is the honest form of what the flag
    actually knows, and it covers the token columns beside the cost as well.
    """
    return APPROXIMATE_COST_NOTE if cost.get("any_approximate") else None


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".") if abs(value) < 1000 else f"{value:.2f}"
    return str(value)


def course_markdown(result: dict) -> str:
    """The full generated course, nothing summarized away.

    This is the artifact a human reads to judge quality for themselves, so every
    lesson's complete content and every quiz item's expected answer is included.
    """
    course = result.get("course")
    if not course:
        return f"# {result.get('name')}\n\nGeneration failed: {result.get('error')}\n"
    source = result.get("source", {})
    cost = result.get("cost_latency", {})
    lines = [
        f"# {course.get('title', 'Untitled')}",
        "",
        f"> {course.get('description', '')}",
        "",
        "## How this was generated",
        "",
        f"- Eval run: `{result.get('name')}` (run id `{result.get('run_id')}`)",
        (f"- Source: {source.get('kind')} `{source.get('ref')}`, "
        f"{source.get('chars', 0):,} characters in {source.get('chunks', 0)} chunks"),
        f"- Provider/model: {cost.get('provider')} / `{cost.get('model')}`",
        (f"- {cost.get('calls', 0)} LLM calls, {cost.get('input_tokens', 0):,} input tokens, "
        f"{cost.get('output_tokens', 0):,} output tokens, "
        f"${cost.get('cost_usd', 0):.4f}, {result.get('wall_clock_s', 0):.0f}s wall clock"),
        *([f"- {note}"] if (note := cost_note(cost)) else []),
        (f"- Prompt fingerprint: outline `{result.get('prompts', {}).get('outline_system')}`, "
        f"lesson `{result.get('prompts', {}).get('lesson_system')}`"),
        "",
        ("Quiz answers are shown inline on purpose: this file exists so a human can "
        "check whether the answers are actually supported by the source."),
        "",
        "---",
        "",
    ]
    for m_index, module in enumerate(course.get("modules", []), start=1):
        lines += [f"## Module {m_index}: {module.get('title', '')}", ""]
        for l_index, lesson in enumerate(module.get("lessons", []), start=1):
            lines += [f"### Lesson {m_index}.{l_index}: {lesson.get('title', '')}", ""]
            concepts = lesson.get("concepts", []) or []
            segments = lesson.get("segments")
            lines += [
                "**Concepts:** " + (", ".join(concepts) if concepts else "(none)"),
                "",
                ("**Written from source segments:** "
                f"{segments if segments is not None else 'whole document'}"),
                "",
                "#### Lesson content",
                "",
                lesson.get("content", "") or "(empty)",
                "",
                "#### Quiz",
                "",
            ]
            quiz = lesson.get("quiz", []) or []
            if not quiz:
                lines += ["(no quiz items)", ""]
            for q_index, item in enumerate(quiz, start=1):
                lines += [
                    f"{q_index}. **{item.get('question', '')}**  ",
                    (f"   kind: `{item.get('kind', '')}` | concept: "
                    f"`{item.get('concept', '')}`  "),
                ]
                for option in item.get("options", []) or []:
                    marker = "x" if option == item.get("answer") else " "
                    lines.append(f"   - [{marker}] {option}")
                lines += [f"   **Expected answer:** {item.get('answer', '')}", ""]
            lines += ["---", ""]
    return "\n".join(lines)


def _table(rows: list[list[str]], header: list[str]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines


def metrics_markdown(results: list[dict]) -> str:
    """Side-by-side summary of one or more runs, with every grounding failure quoted."""
    lines = ["# StudyForge generation eval", ""]
    names = [r["name"] for r in results]
    heads = [headline(r) for r in results]

    lines += ["## Headline metrics", ""]
    lines += _table(
        [[label] + [_fmt(h[key]) for h in heads] for key, label in HEADLINE_METRICS],
        ["Metric"] + names,
    )

    for result in results:
        lines += [f"## {result['name']}", ""]
        if not result.get("ok"):
            lines += [f"**Generation failed:** `{result.get('error')}`", ""]
        source = result.get("source", {})
        lines += [
            (f"Source: {source.get('kind')} `{source.get('ref')}`, "
            f"{source.get('chars', 0):,} chars, {source.get('chunks', 0)} chunks"),
            "",
        ]

        parse = result.get("parse_reliability", {})
        lines += ["### Parse reliability", ""]
        lines += _table(
            [
                [
                    stage,
                    str(s["calls"]),
                    str(s["strict_json_first_try"]),
                    str(s["needed_code_fence_strip"]),
                    str(s["needed_prose_trim"]),
                    str(s["tolerant_parse_ok"]),
                    str(s["schema_ok"]),
                    str(s["hard_parse_failures"]),
                ]
                for stage, s in parse.get("per_stage", {}).items()
            ],
            ["Stage", "Calls", "Strict JSON", "Fence strip", "Prose trim", "Parsed", "Schema ok",
             "Failures"],
        )

        cost = result.get("cost_latency", {})
        lines += ["### Cost and latency by stage", ""]
        lines += _table(
            [
                [
                    stage,
                    str(s["calls"]),
                    f"{s['input_tokens']:,}",
                    f"{s['output_tokens']:,}",
                    f"${s['cost_usd']:.4f}",
                    f"{s['mean_latency_s']:.1f}",
                    f"{s['max_latency_s']:.1f}",
                ]
                for stage, s in cost.get("per_stage", {}).items()
            ],
            ["Stage", "Calls", "In tokens", "Out tokens", "Cost", "Mean s", "Max s"],
        )
        if note := cost_note(cost):
            lines += ["", note, ""]

        metrics = result.get("metrics") or {}
        if not metrics:
            continue

        structure = metrics["structure"]
        lines += [
            "### Structure",
            "",
            (f"- {structure['modules']} modules, {structure['lessons']} lessons, "
            f"{structure['quiz_items']} quiz items"),
            f"- Quiz items per lesson: {structure['quiz_items_per_lesson']}",
            f"- Concepts per lesson: {structure['concepts_per_lesson']}",
            (f"- Lesson content chars: mean "
            f"{structure['mean_lesson_content_chars']:.0f}, min "
            f"{structure['min_lesson_content_chars']}"),
            f"- Item kinds: {structure['kinds']}",
            f"- Problems: {structure['problem_counts'] or 'none'}",
            "",
        ]
        for problem in structure["problems"]:
            lines.append(f"  - `{problem['problem']}` at {problem['location']}: {problem['detail']}")
        if structure["problems"]:
            lines.append("")

        grounding = metrics["grounding"]
        lines += [
            "### Grounding (answer vs source document)",
            "",
            "**Uncorrected, every non-trivial answer scored by token overlap:**",
            "",
            (f"- {grounding['supported_items']}/{grounding['scored_items']} answers supported "
            f"(exact or strong) = {grounding['supported_rate']:.1%}"),
            f"- Tiers: {grounding['tier_counts']}",
            f"- Mean best-window recall: {grounding['mean_window_recall']:.3f}",
            (f"- Trivial answers excluded from scoring: "
            f"{grounding['trivial_answers_excluded']}"),
            f"- Low-signal answers (under 2 content tokens): {grounding['low_signal_items']}",
            "",
        ]
        if "class_counts" in grounding:
            lines += [
                ("**Corrected.** Odd-one-out MCQs have deliberately false answers and "
                "restatement questions ask for a paraphrase, so neither can be scored by "
                "looking for its answer in the source. They are split out and scored on "
                "their own terms:"),
                "",
                f"- Item classes: {grounding['class_counts']}",
                (f"- Extractive items supported: "
                f"{grounding['extractive_supported_items']}/{grounding['extractive_items']} = "
                f"{grounding['extractive_supported_rate']:.1%} "
                f"(mean window recall {grounding['extractive_mean_window_recall']:.3f})"),
                (f"- Odd-one-out items: mean share of their distractors found in the source "
                f"= {grounding['odd_one_out_mean_distractor_rate']:.1%}"),
                (f"- Restatement items: mean share of answer words absent from the source "
                f"= {grounding['restatement_mean_novel_rate']:.1%}"),
                (f"- Hallucination candidates (low window recall AND over "
                f"{NOVEL_RATE_LIMIT:.0%} novel vocabulary): "
                f"{grounding['hallucination_candidates']}"),
                "",
            ]
            for flagged in grounding.get("flagged", []):
                lines += [
                    (
                        f"  - **{flagged['location']}** ({flagged['scoring_class']}) "
                        f"novel {flagged['novel_rate']:.0%}: {flagged['answer'][:160]}"
                    ),
                ]
            if grounding.get("flagged"):
                lines.append("")
        if grounding["failures"]:
            lines += ["#### Ungrounded extractive items", ""]
            for failure in grounding["failures"]:
                lines += [
                    f"- **{failure['location']}** ({failure['lesson_title']})",
                    f"  - Q: {failure['question']}",
                    f"  - Expected answer: `{failure['answer']}`",
                    (f"  - Best window recall {failure['window_recall']:.2f}, "
                    f"global token recall {failure['global_recall']:.2f}"),
                    f"  - Closest source text: `{failure['evidence'][:300]}`",
                    "",
                ]
        else:
            lines += ["No ungrounded items.", ""]

        answerability = metrics["answerability"]
        lines += [
            "### Answerability (answer vs its own lesson content)",
            "",
            (f"- {answerability['answerable_items']}/{answerability['scored_items']} answerable "
            f"from the lesson alone = {answerability['answerable_rate']:.1%}"),
            f"- Tiers: {answerability['tier_counts']}",
            (f"- Giveaway MCQs (correct option quoted verbatim, no distractor is): "
            f"{answerability['giveaway_mcqs']}"),
            "",
        ]
        if answerability["failures"]:
            lines += ["#### Items not answerable from their lesson", ""]
            for failure in answerability["failures"]:
                lines += [
                    f"- **{failure['location']}** ({failure['lesson_title']})",
                    f"  - Q: {failure['question']}",
                    f"  - Expected answer: `{failure['answer']}`",
                    f"  - Best window recall against lesson: {failure['window_recall']:.2f}",
                    "",
                ]

        coverage = metrics["coverage"]
        lines += [
            "### Concept coverage across the source",
            "",
            (f"- {coverage['anchored_concepts']}/{coverage['total_concepts']} concepts anchored "
            f"to a source chunk ({coverage['unanchored_concepts']} unanchored)"),
            (f"- Chunks containing at least one concept: "
            f"{coverage['chunks_with_a_concept']}/{coverage['source_chunks']} "
            f"({coverage['chunk_coverage_rate']:.1%})"),
            f"- Concepts per chunk: {coverage['concepts_per_chunk']}",
            f"- Lessons per chunk: {coverage['lessons_per_chunk']}",
            f"- Uncovered chunk indexes: {coverage['uncovered_chunk_indexes'] or 'none'}",
            f"- Largest share in one chunk: {coverage['max_chunk_share']:.1%}",
            "",
        ]
        if "share_vs_expected" in coverage:
            lines += [
                ("Raw shares are not comparable across chunks of different sizes. Actual "
                "share over expected share (by chunk length) is: 1.0 means balanced."),
                "",
                f"- Expected share per chunk: {coverage['expected_share_per_chunk']}",
                f"- Actual share per chunk: {coverage['actual_share_per_chunk']}",
                f"- Actual/expected: {coverage['share_vs_expected']}",
                f"- Worst concentration ratio: {coverage['max_concentration_ratio']:.2f}",
                "",
            ]

        source_cov = metrics.get("source_coverage")
        if source_cov:
            lines += [
                "### Source coverage (document sentences reaching the course)",
                "",
                ("Measured from the source side, so chunk length cancels out: what share "
                "of each chunk's substantial sentences is said anywhere in the course."),
                "",
                f"- Mean chunk recall: {source_cov['mean_chunk_recall']:.1%}",
                (f"- Worst chunk: {source_cov['worst_chunk']} at "
                f"{source_cov['min_chunk_recall']:.1%}"),
                f"- Chunks under 50% covered: {source_cov['chunks_below_half']}",
                f"- Lessons routed per segment: {source_cov['lessons_per_segment']}",
                (f"- Segments with no lesson: "
                f"{source_cov['segments_with_no_lesson'] if source_cov['segments_with_no_lesson'] is not None else 'n/a (routing off)'}"),
                "",
            ]
            lines += _table(
                [
                    [
                        str(c["chunk"]),
                        f"{c['chars']:,}",
                        str(c["sentences"]),
                        str(c["covered_sentences"]),
                        f"{c['recall']:.1%}",
                        f"{c['mean_sentence_recall']:.3f}",
                    ]
                    for c in source_cov["per_chunk"]
                ],
                ["Chunk", "Chars", "Sentences", "Covered", "Recall", "Mean sentence recall"],
            )
    return "\n".join(lines)


def compare_markdown(before: dict, after: dict) -> str:
    """Before/after table for a prompt change, over the headline metrics."""
    before_runs = {r["name"]: r for r in before.get("runs", [])}
    after_runs = {r["name"]: r for r in after.get("runs", [])}
    shared = [name for name in after_runs if name in before_runs]
    lines = [
        "# Eval comparison",
        "",
        (f"- Before: `{before.get('label', '?')}` prompts "
        f"{before.get('prompts')}"),
        f"- After: `{after.get('label', '?')}` prompts {after.get('prompts')}",
        "",
    ]
    if not shared:
        lines += ["No run names in common; nothing to compare.", ""]
        return "\n".join(lines)
    for name in shared:
        b_head = headline(before_runs[name])
        a_head = headline(after_runs[name])
        lines += [f"## {name}", ""]
        rows = []
        for key, label in HEADLINE_METRICS:
            b_val, a_val = b_head[key], a_head[key]
            delta = a_val - b_val if isinstance(b_val, int | float) else ""
            rows.append([label, _fmt(b_val), _fmt(a_val), _fmt(delta) if delta else "0"])
        lines += _table(rows, ["Metric", "Before", "After", "Delta"])
    return "\n".join(lines)


def write_outputs(out_dir: Path, label: str, results: list[dict]) -> dict:
    """Persist the machine-readable result bundle, the metrics report, and one
    markdown file per generated course."""
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "label": label,
        "prompts": results[0].get("prompts") if results else None,
        "runs": results,
    }
    written = {}
    results_path = out_dir / f"results-{label}.json"
    results_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    written["results"] = results_path

    report_path = out_dir / f"report-{label}.md"
    report_path.write_text(metrics_markdown(results), encoding="utf-8")
    written["report"] = report_path

    for result in results:
        if result.get("course"):
            course_path = out_dir / f"course-{result['name']}.md"
            course_path.write_text(course_markdown(result), encoding="utf-8")
            written[f"course:{result['name']}"] = course_path
    return written
