"""Unit tests for the eval harness itself.

The harness exists to produce numbers a human will trust, so the matcher and the
metric aggregation need the same scrutiny as app code. Nothing here touches a
provider: the one file that can spend money (`evals/run_eval.py`) is only imported
for its preflight guard, which is tested precisely because it is what stands
between a typo and the user's credit card.
"""

import json

import pytest

from evals import report
from evals.harness import RecordingMeter, parse_reliability, prompt_fingerprint
from evals.metrics import (
    CLASS_EXTRACTIVE,
    CLASS_ODD_ONE_OUT,
    CLASS_RESTATEMENT,
    TIER_EXACT,
    TIER_UNSUPPORTED,
    ReferenceText,
    answerability,
    concept_coverage,
    evaluate,
    grounding,
    scoring_class,
    source_coverage,
    structure,
)
from evals.textmatch import (
    best_window_recall,
    contains_phrase,
    content_tokens,
    global_recall,
    is_trivial_answer,
    normalize,
    novel_tokens,
    stem,
    stem_vocab,
    tokenize,
)

SOURCE = (
    "Photosynthesis converts light energy into chemical energy stored in glucose. "
    "The light-dependent reactions occur in the thylakoid membrane and produce ATP."
)


def make_item(question="What is stored?", kind="mcq", options=None, answer="glucose",
              concept="photosynthesis"):
    if options is None and kind == "mcq":
        options = ["glucose", "starch", "cellulose", "lactose"]
    return {
        "question": question,
        "kind": kind,
        "options": options or [],
        "answer": answer,
        "concept": concept,
    }


def make_lesson(title="Lesson", content=SOURCE, concepts=None, quiz=None):
    # Default questions are distinct per lesson: duplicate_question is tracked
    # course-wide, so a fixture that repeated one question would make every
    # "clean course" assertion fail for reasons unrelated to what it tests.
    default_quiz = [make_item(question=f"{title} q{i}") for i in range(3)]
    return {
        "title": title,
        "content": content,
        "concepts": concepts if concepts is not None else ["photosynthesis", "ATP"],
        "quiz": quiz if quiz is not None else default_quiz,
    }


def make_course(modules=2, lessons=2, **lesson_kwargs):
    return {
        "title": "Course",
        "description": "A course",
        "modules": [
            {
                "title": f"Module {m + 1}",
                "lessons": [
                    make_lesson(title=f"Lesson {m + 1}.{i + 1}", **lesson_kwargs)
                    for i in range(lessons)
                ],
            }
            for m in range(modules)
        ],
    }


# --- textmatch -------------------------------------------------------------


def test_normalize_folds_case_and_punctuation():
    assert normalize("Thylakoid-Membrane, ATP!") == "thylakoid membrane atp"


def test_normalize_empty_is_empty():
    assert normalize("") == ""


def test_content_tokens_drops_stopwords():
    assert content_tokens("the cat is on the mat") == ["cat", "mat"]


def test_content_tokens_falls_back_when_all_stopwords():
    # "it is" is entirely function words; returning [] would make every metric
    # score it a vacuous 0, so the raw tokens stand in instead.
    assert content_tokens("it is") == ["it", "is"]


def test_contains_phrase_requires_whole_tokens():
    haystack = normalize("the thylakoid membrane")
    assert contains_phrase(haystack, "thylakoid membrane")
    # "lakoid" is a substring of "thylakoid" but not a token: a naive `in` test
    # would call this a match and inflate the grounding score.
    assert not contains_phrase(haystack, "lakoid")


def test_contains_phrase_empty_needle_is_false():
    assert not contains_phrase(normalize(SOURCE), "")


def test_window_recall_requires_locality():
    """The whole point of window recall: scattered words are not evidence."""
    haystack = ["alpha"] + ["filler"] * 500 + ["omega"]
    needle = ["alpha", "omega"]
    recall, _ = best_window_recall(needle, haystack)
    assert recall == 0.5
    # Global recall cannot tell the difference, which is why both are reported.
    assert global_recall(needle, set(haystack)) == 1.0


def test_window_recall_finds_adjacent_terms():
    haystack = tokenize("stored in glucose molecules")
    recall, _ = best_window_recall(["stored", "glucose"], haystack)
    assert recall == 1.0


def test_window_recall_empty_inputs():
    assert best_window_recall([], ["a"]) == (0.0, 0)
    assert best_window_recall(["a"], []) == (0.0, 0)


@pytest.mark.parametrize("answer", ["True", "  false ", "All of the above"])
def test_trivial_answers_detected(answer):
    assert is_trivial_answer(answer)


def test_non_trivial_answer():
    assert not is_trivial_answer("glucose")


# --- ReferenceText ---------------------------------------------------------


def test_reference_text_exact_match_beats_overlap():
    ref = ReferenceText([SOURCE])
    support = ref.support("chemical energy")
    assert support.tier == TIER_EXACT
    assert support.exact
    assert support.evidence


def test_reference_text_unsupported_answer():
    ref = ReferenceText([SOURCE])
    support = ref.support("mitochondrial matrix oxidation")
    assert support.tier == TIER_UNSUPPORTED
    assert support.window_recall < 0.5


def test_reference_text_reports_best_chunk():
    ref = ReferenceText(["nothing relevant here", SOURCE])
    assert ref.support("thylakoid membrane").best_chunk == 1


# --- grounding -------------------------------------------------------------


def test_grounding_counts_supported_and_excludes_trivial():
    course = make_course(
        modules=2,
        lessons=2,
        quiz=[
            make_item(answer="glucose"),
            make_item(answer="True", kind="short", options=[]),
            make_item(answer="mitochondrial matrix oxidation"),
        ],
    )
    result = grounding(course, [SOURCE])
    assert result["total_items"] == 12  # 2 modules x 2 lessons x 3 items
    assert result["trivial_answers_excluded"] == 4
    assert result["scored_items"] == 8
    assert result["unsupported_items"] == 4
    assert result["supported_items"] == 4
    assert result["supported_rate"] == 0.5


def test_grounding_failures_carry_question_and_evidence():
    course = make_course(
        modules=2, lessons=2, quiz=[make_item(question="Where?", answer="quantum tunnelling flux")]
    )
    result = grounding(course, [SOURCE])
    assert result["failures"]
    failure = result["failures"][0]
    assert failure["question"] == "Where?"
    assert failure["answer"] == "quantum tunnelling flux"
    assert "location" in failure


def test_grounding_of_empty_course_does_not_divide_by_zero():
    result = grounding({"modules": []}, [SOURCE])
    assert result["scored_items"] == 0
    assert result["supported_rate"] == 0.0


# --- scoring classes and the corrected grounding number --------------------


@pytest.mark.parametrize(
    "question",
    [
        "Which of these is NOT one of the premises?",
        "Which of the following is not among the stated limits?",
        "All of the following are true EXCEPT which one?",
        "Which option is least likely to apply?",
    ],
)
def test_odd_one_out_questions_are_classified(question):
    assert scoring_class("mcq", question, "some false claim") == CLASS_ODD_ONE_OUT


@pytest.mark.parametrize(
    "question",
    [
        # "except" and "least" inside a quotation from the source, not an enumeration.
        "Darwin says nature cares nothing for appearances, except where useful. Why?",
        "What happens when variation is in the least degree injurious?",
        "Which molecule stores the energy?",
    ],
)
def test_ordinary_questions_are_not_mistaken_for_odd_one_out(question):
    """A false positive here would excuse a genuinely ungrounded answer."""
    assert scoring_class("mcq", question, "glucose") != CLASS_ODD_ONE_OUT


def test_restatement_questions_are_classified():
    assert scoring_class("short", "Explain in your own words why ATP matters.", "a") == (
        CLASS_RESTATEMENT
    )
    assert scoring_class("short", "Name the membrane involved.", "thylakoid") == (
        CLASS_EXTRACTIVE
    )


def test_odd_one_out_answer_does_not_count_against_grounding():
    """The whole point: its answer is meant to be absent from the source.

    Scored the old way this item reads as a hallucination. Scored on its
    distractors, which are the claims the source does make, it reads as sound.
    """
    item = {
        "question": "Which of these is NOT stated in the passage?",
        "kind": "mcq",
        "options": [
            "Photosynthesis is powered by sound waves",
            "light energy",
            "chemical energy",
            "thylakoid membrane",
        ],
        "answer": "Photosynthesis is powered by sound waves",
        "concept": "photosynthesis",
    }
    result = grounding(make_course(modules=1, lessons=1, quiz=[item]), [SOURCE])
    assert result["class_counts"][CLASS_ODD_ONE_OUT] == 1
    assert result["extractive_items"] == 0
    # Unscored by the old number, which still counts it as unsupported.
    assert result["unsupported_items"] == 1
    assert result["extractive_unsupported_items"] == 0
    assert result["odd_one_out_mean_distractor_rate"] == 1.0


def test_paraphrase_answer_scores_low_on_overlap_but_low_on_novelty_too():
    """The separation the old metric could not make.

    Both answers score badly on window recall. Only one introduces vocabulary the
    source never used, and only that one is a hallucination candidate.
    """
    paraphrase = make_item(
        question="Explain in your own words what the reactions produce.",
        kind="short",
        options=[],
        answer="The reactions of light produce ATP inside a membrane of the thylakoid",
    )
    invented = make_item(
        question="Name the enzyme involved.",
        kind="short",
        options=[],
        answer="Rubisco carboxylase catalyses mitochondrial fermentation",
    )
    result = grounding(
        make_course(modules=1, lessons=1, quiz=[paraphrase, invented]), [SOURCE]
    )
    by_location = {i["question"]: i for i in result["items"]}
    assert by_location[paraphrase["question"]]["hallucination_candidate"] is False
    assert by_location[invented["question"]]["hallucination_candidate"] is True
    assert result["hallucination_candidates"] == 1


def test_stem_folds_inflections_both_directions():
    assert stem("survival") == stem("surviving")
    assert stem("generations") == stem("generation")
    assert stem("go") == "go", "too short to fold"


def test_novel_tokens_ignores_inflection_and_pedagogical_filler():
    vocab = stem_vocab(tokenize("many generations of surviving organisms"))
    # "of", not "across": the point is that inflections fold, and "across" is
    # genuinely a word the source never used, so asserting it is not novel would be
    # asking the function for the wrong answer.
    assert novel_tokens("survival of generations", vocab) == []
    assert novel_tokens("mitochondrial fermentation", vocab) == [
        "mitochondrial",
        "fermentation",
    ]


# --- answerability ---------------------------------------------------------


def test_answerability_flags_item_taught_nowhere_in_its_lesson():
    course = make_course(
        modules=2,
        lessons=2,
        content="This lesson only discusses the Calvin cycle in general terms.",
        quiz=[make_item(answer="thylakoid membrane")],
    )
    result = answerability(course)
    assert result["unanswerable_items"] == 4
    assert result["answerable_rate"] == 0.0


def test_answerability_detects_giveaway_mcq():
    """Correct option quoted from the lesson, no distractor is: string-matchable."""
    course = make_course(
        modules=2,
        lessons=2,
        quiz=[make_item(options=["glucose", "zzz alpha", "zzz beta", "zzz gamma"])],
    )
    result = answerability(course)
    assert result["giveaway_mcqs"] == 4
    assert result["items"][0]["answer_verbatim_in_lesson"]
    assert result["items"][0]["distractors_verbatim_in_lesson"] == 0


def test_answerability_not_giveaway_when_distractors_also_appear():
    course = make_course(
        modules=2,
        lessons=2,
        content=SOURCE + " Distractors: starch and cellulose and lactose.",
        quiz=[make_item()],
    )
    result = answerability(course)
    assert result["giveaway_mcqs"] == 0


# --- coverage --------------------------------------------------------------


def test_coverage_flags_chunks_no_concept_touches():
    chunks = [SOURCE, "Plate tectonics describes the motion of lithospheric plates."]
    course = make_course(modules=2, lessons=2, concepts=["photosynthesis", "thylakoid membrane"])
    result = concept_coverage(course, chunks)
    assert result["source_chunks"] == 2
    assert result["chunks_with_a_concept"] == 1
    assert result["uncovered_chunk_indexes"] == [1]
    assert result["chunk_coverage_rate"] == 0.5
    assert result["max_chunk_share"] == 1.0


def test_coverage_counts_unanchored_concepts():
    course = make_course(modules=2, lessons=2, concepts=["utterly unrelated notion", "ATP"])
    result = concept_coverage(course, [SOURCE])
    assert result["unanchored_concepts"] == 4
    assert result["anchored_concepts"] == 4


# --- structure -------------------------------------------------------------


def test_source_coverage_is_not_fooled_by_chunk_length():
    """The regression that started this work.

    A course covering both chunks equally well must read as covering both. The old
    concept_coverage histogram anchored each concept to its best-matching chunk, so a
    much longer chunk offered proportionally more candidate windows and won the
    argmax whatever the course actually said. On the first real run that bias alone
    reported 92% of concepts concentrated in one chunk of two, and it was read as the
    pipeline ignoring the back half of the document. It was not.
    """
    long_chunk = " ".join(
        f"Sentence {i} describes the thylakoid membrane and its role in ATP synthesis."
        for i in range(12)
    )
    short_chunk = "Carbon fixation happens in the stroma during the Calvin cycle."

    # A course that genuinely says both things.
    course = make_course(
        modules=1,
        lessons=1,
        content=f"{long_chunk} {short_chunk}",
    )
    result = source_coverage(course, [long_chunk, short_chunk])

    recalls = [chunk["recall"] for chunk in result["per_chunk"]]
    assert all(recall > 0.8 for recall in recalls), result["per_chunk"]
    # The short chunk must not be reported as neglected just for being short.
    assert abs(recalls[0] - recalls[1]) < 0.25


def test_source_coverage_catches_a_course_that_really_stopped_early():
    """The metric still has to fail when coverage is genuinely bad, or replacing the
    old one just swaps a false alarm for a blind spot."""
    covered = "The thylakoid membrane hosts the light dependent reactions of photosynthesis."
    ignored = "Mycorrhizal fungi exchange phosphorus with plant roots in a symbiosis."

    course = make_course(modules=1, lessons=1, content=covered)
    result = source_coverage(course, [covered, ignored])

    per_chunk = result["per_chunk"]
    assert per_chunk[0]["recall"] > 0.8
    assert per_chunk[1]["recall"] == 0.0
    assert result["min_chunk_recall"] == 0.0


def test_source_coverage_reports_routed_segments_when_the_outline_assigned_them():
    lesson = make_lesson(title="Routed")
    lesson["segments"] = [1]
    course = {"title": "C", "description": "d", "modules": [{"title": "M", "lessons": [lesson]}]}

    result = source_coverage(course, ["chunk zero text", "chunk one text"])
    assert result["lessons_per_segment"] == [0, 1]
    # Segment 0 got no lesson, and with routing in play that is a real finding.
    assert result["segments_with_no_lesson"] == [0]


def test_source_coverage_says_nothing_was_routed_rather_than_guessing():
    """Below the routing threshold the outline assigns no segments at all, so every
    segment trivially has no lesson. Reporting that as a coverage gap would be the
    same false alarm in a new costume, so the metric returns None instead."""
    course = make_course(modules=1, lessons=1)
    result = source_coverage(course, ["one chunk only"])
    assert result["lessons_per_segment"] == [0]
    assert result["segments_with_no_lesson"] is None


def test_structure_clean_course_has_no_problems():
    result = structure(make_course())
    assert result["clean"], result["problems"]
    assert result["modules"] == 2
    assert result["lessons"] == 4
    assert result["quiz_items"] == 12


def test_structure_flags_mcq_answer_missing_from_options():
    """The one that makes an item literally impossible to answer correctly."""
    course = make_course(
        modules=2,
        lessons=2,
        quiz=[
            make_item(answer="sucrose"),
            make_item(question="q2"),
            make_item(question="q3"),
        ],
    )
    result = structure(course)
    assert result["problem_counts"]["mcq_answer_not_in_options"] == 4


def test_structure_flags_duplicate_options_and_wrong_option_count():
    course = make_course(
        modules=2,
        lessons=2,
        quiz=[
            make_item(options=["glucose", "glucose", "starch"]),
            make_item(question="q2"),
            make_item(question="q3"),
        ],
    )
    result = structure(course)
    assert result["problem_counts"]["duplicate_mcq_options"] == 4
    assert result["problem_counts"]["mcq_option_count"] == 4


def test_structure_flags_empty_content_and_counts_out_of_range():
    course = make_course(modules=1, lessons=1, content="   ", quiz=[make_item()], concepts=[])
    result = structure(course)
    counts = result["problem_counts"]
    assert counts["module_count_out_of_range"] == 1
    assert counts["lesson_count_out_of_range"] == 1
    assert counts["empty_lesson_content"] == 1
    assert counts["concept_count_out_of_range"] == 1
    assert counts["quiz_count_out_of_range"] == 1


def test_structure_flags_duplicate_questions():
    course = make_course(modules=2, lessons=2, quiz=[make_item(), make_item(), make_item()])
    result = structure(course)
    # Duplicates are counted course-wide, not per lesson: 12 identical questions
    # means one original and 11 repeats. A learner meeting the same question in
    # four different lessons is the failure this is meant to catch.
    assert result["problem_counts"]["duplicate_question"] == 11


def test_structure_flags_short_item_carrying_options():
    course = make_course(
        modules=2,
        lessons=2,
        quiz=[
            make_item(kind="short", options=["a", "b", "c", "d"]),
            make_item(question="q2"),
            make_item(question="q3"),
        ],
    )
    assert structure(course)["problem_counts"]["short_item_has_options"] == 4


# --- harness ---------------------------------------------------------------


class StubMeter:
    """Stands in for MeteredLLM. Returns canned text; never calls a provider."""

    def __init__(self, responses):
        self.responses = list(responses)

    def generate(self, stage, system, prompt, max_tokens=64000):
        return self.responses.pop(0)


OUTLINE_JSON = json.dumps({"title": "T", "description": "d", "modules": [{"title": "M"}]})
LESSON_JSON = json.dumps({"content": "c", "concepts": ["x"], "quiz": []})


def test_recording_meter_classifies_clean_json():
    meter = RecordingMeter(StubMeter([OUTLINE_JSON]))
    meter.generate("outline", "sys", "prompt")
    record = meter.records[0]
    assert record.strict_json
    assert record.tolerant_json
    assert record.schema_ok
    assert not record.used_code_fence
    assert not record.used_prose_trim


def test_recording_meter_classifies_code_fence():
    meter = RecordingMeter(StubMeter([f"```json\n{OUTLINE_JSON}\n```"]))
    meter.generate("outline", "sys", "prompt")
    record = meter.records[0]
    assert not record.strict_json
    assert record.used_code_fence
    assert record.tolerant_json


def test_recording_meter_classifies_prose_wrapper():
    meter = RecordingMeter(StubMeter([f"Sure, here you go:\n{OUTLINE_JSON}\nHope that helps!"]))
    meter.generate("outline", "sys", "prompt")
    record = meter.records[0]
    assert not record.strict_json
    assert record.used_prose_trim
    assert record.tolerant_json


def test_recording_meter_records_hard_parse_failure():
    meter = RecordingMeter(StubMeter(["I cannot help with that."]))
    meter.generate("outline", "sys", "prompt")
    record = meter.records[0]
    assert not record.tolerant_json
    assert record.error and record.error.startswith("parse:")


def test_recording_meter_flags_missing_schema_keys():
    meter = RecordingMeter(StubMeter(['{"title": "T"}']))
    meter.generate("outline", "sys", "prompt")
    assert meter.records[0].tolerant_json
    assert not meter.records[0].schema_ok


def test_recording_meter_records_then_reraises_provider_error():
    class Boom:
        def generate(self, *args, **kwargs):
            raise RuntimeError("provider exploded")

    meter = RecordingMeter(Boom())
    with pytest.raises(RuntimeError):
        meter.generate("lesson", "sys", "prompt")
    # The record must survive the exception: a paid call that failed still cost money.
    assert len(meter.records) == 1
    assert "provider exploded" in meter.records[0].error


def test_parse_reliability_aggregates_per_stage():
    meter = RecordingMeter(StubMeter([OUTLINE_JSON, LESSON_JSON, "not json"]))
    meter.generate("outline", "s", "p")
    meter.generate("lesson", "s", "p")
    meter.generate("lesson", "s", "p")
    summary = parse_reliability(meter.records)
    assert summary["total_calls"] == 3
    assert summary["strict_json_first_try"] == 2
    assert summary["hard_parse_failures"] == 1
    assert summary["per_stage"]["lesson"]["calls"] == 2
    assert summary["per_stage"]["lesson"]["hard_parse_failures"] == 1
    assert summary["retry_path_exists"] is True


def test_prompt_fingerprint_is_stable_and_short():
    first, second = prompt_fingerprint(), prompt_fingerprint()
    assert first == second
    assert len(first["outline_system"]) == 12


# --- the parse hazard this eval found on a real document -------------------


def test_fenced_code_inside_lesson_content_parses():
    """Regression test for the bug the first real-provider run found.

    The old parser stripped the FIRST ``` fence anywhere in the response. A valid
    JSON lesson whose markdown `content` contains a code example matched that regex
    on the example, so the whole response was replaced by the code and the course
    died with an HTTP 502. The real PEP 8 run failed exactly here, on:
        No JSON object in model response: 'python\\ndef processRecord(rec):\\n ...'

    The parser now tries the reply verbatim before it considers any fence.
    """
    from app.generation import parse_json_response

    response = json.dumps(
        {
            "content": "Use snake_case:\n\n```python\ndef process_record(rec):\n    ...\n```\n",
            "concepts": ["naming"],
            "quiz": [],
        }
    )
    assert json.loads(response)["concepts"] == ["naming"], "the response itself is valid JSON"
    assert parse_json_response(response)["concepts"] == ["naming"]


def test_fenced_code_survives_prose_around_the_object():
    """The same lesson, with the model narrating before and after it.

    Now neither the verbatim parse nor a json-labelled fence can help, so recovery
    depends on the balanced-brace scan finding the object with a ```python fence
    sitting inside one of its strings.
    """
    from app.generation import parse_json_response

    obj = json.dumps(
        {
            "content": "Indent with 4 spaces:\n\n```python\nif x:\n    pass\n```\n",
            "concepts": ["indentation"],
            "quiz": [],
        }
    )
    response = f"Sure! Here is the lesson.\n\n{obj}\n\nLet me know if you want changes."
    assert parse_json_response(response)["concepts"] == ["indentation"]


def test_parser_handles_a_lesson_with_no_code_fence():
    """The same lesson without a code block parses fine, isolating the cause."""
    from app.generation import parse_json_response

    response = json.dumps({"content": "Use snake_case.", "concepts": ["naming"], "quiz": []})
    assert parse_json_response(response)["concepts"] == ["naming"]


# --- report ----------------------------------------------------------------


def _result_fixture():
    course = make_course(modules=2, lessons=2)
    chunks = [SOURCE]
    return {
        "name": "demo",
        "ok": True,
        "error": None,
        "run_id": "abc123",
        "prompts": prompt_fingerprint(),
        "source": {"key": "demo", "kind": "text", "ref": "demo", "chars": 100, "chunks": 1},
        "wall_clock_s": 12.0,
        "parse_reliability": parse_reliability([]),
        "cost_latency": {"calls": 0, "per_stage": {}, "cost_usd": 0.0},
        "calls": [],
        "metrics": evaluate(course, chunks),
        "course": course,
    }


def test_course_markdown_includes_every_question_and_answer():
    markdown = report.course_markdown(_result_fixture())
    assert markdown.count("**Expected answer:**") == 12
    assert "Module 1" in markdown and "Lesson 2.2" in markdown
    assert "photosynthesis" in markdown


def test_course_markdown_marks_the_correct_option():
    markdown = report.course_markdown(_result_fixture())
    assert "- [x] glucose" in markdown
    assert "- [ ] starch" in markdown


def test_course_markdown_reports_a_failed_run():
    markdown = report.course_markdown({"name": "x", "error": "boom", "course": None})
    assert "Generation failed" in markdown


def test_headline_has_every_advertised_metric():
    head = report.headline(_result_fixture())
    for key, _label in report.HEADLINE_METRICS:
        assert key in head


def test_metrics_markdown_renders_without_crashing():
    markdown = report.metrics_markdown([_result_fixture()])
    assert "Headline metrics" in markdown
    assert "Grounding" in markdown


def test_compare_markdown_shows_deltas():
    before = {"label": "a", "runs": [_result_fixture()]}
    after = {"label": "b", "runs": [_result_fixture()]}
    after["runs"][0]["wall_clock_s"] = 20.0
    markdown = report.compare_markdown(before, after)
    assert "Delta" in markdown
    assert "Wall clock s" in markdown


def test_compare_markdown_with_no_shared_runs():
    before = {"label": "a", "runs": []}
    after = {"label": "b", "runs": [_result_fixture()]}
    assert "nothing to compare" in report.compare_markdown(before, after)


def test_write_outputs_creates_report_and_course_files(tmp_path):
    written = report.write_outputs(tmp_path, "unit", [_result_fixture()])
    assert (tmp_path / "results-unit.json").exists()
    assert (tmp_path / "report-unit.md").exists()
    assert (tmp_path / "course-demo.md").exists()
    bundle = json.loads((tmp_path / "results-unit.json").read_text(encoding="utf-8"))
    assert bundle["label"] == "unit"
    assert bundle["runs"][0]["name"] == "demo"
    assert written["results"].exists()


# --- run_eval preflight ----------------------------------------------------


def test_preflight_refuses_without_a_cost_cap(monkeypatch, tmp_path):
    """The guard that stands between a typo and an unbounded bill."""
    from evals import run_eval

    monkeypatch.setenv("STUDYFORGE_DB", str(tmp_path / "scratch.sqlite3"))
    monkeypatch.delenv("STUDYFORGE_COST_LIMIT_USD", raising=False)

    class Paid:
        name, model, is_paid = "anthropic", "claude-opus-5", True

    monkeypatch.setattr(run_eval, "get_provider", lambda: Paid())
    with pytest.raises(SystemExit) as excinfo:
        run_eval.preflight()
    assert excinfo.value.code == 2


def test_preflight_refuses_the_real_database(monkeypatch):
    from evals import run_eval

    monkeypatch.setenv("STUDYFORGE_DB", str(run_eval.BACKEND_DIR / "studyforge.sqlite3"))
    monkeypatch.setenv("STUDYFORGE_COST_LIMIT_USD", "3.00")

    class Paid:
        name, model, is_paid = "anthropic", "claude-opus-5", True

    monkeypatch.setattr(run_eval, "get_provider", lambda: Paid())
    with pytest.raises(SystemExit):
        run_eval.preflight()


def test_preflight_accepts_a_scratch_db_with_a_cap(monkeypatch, tmp_path):
    from evals import run_eval

    monkeypatch.setenv("STUDYFORGE_DB", str(tmp_path / "scratch.sqlite3"))
    monkeypatch.setenv("STUDYFORGE_COST_LIMIT_USD", "3.00")

    class Paid:
        name, model, is_paid = "anthropic", "claude-opus-5", True

    monkeypatch.setattr(run_eval, "get_provider", lambda: Paid())
    env = run_eval.preflight()
    assert env["cost_limit_usd"] == 3.00
    assert env["model"] == "claude-opus-5"


def test_cost_projection_scales_with_lessons(monkeypatch):
    """The projection must reflect that every lesson call re-sends the whole document."""
    from evals import run_eval

    text = "word " * 4000
    small = run_eval.project_cost("claude-opus-5", text, lessons=2)
    large = run_eval.project_cost("claude-opus-5", text, lessons=20)
    assert large["projected_cost_usd"] > small["projected_cost_usd"] * 5
    assert not small["approximate_pricing"]


def test_dry_run_makes_no_provider_calls(monkeypatch, tmp_path):
    """End-to-end guard: --dry-run must never construct a real provider call."""
    from evals import run_eval

    monkeypatch.setenv("STUDYFORGE_DB", str(tmp_path / "scratch.sqlite3"))

    class Paid:
        name, model, is_paid = "anthropic", "claude-opus-5", True

        def generate(self, *args, **kwargs):
            raise AssertionError("dry run must not call the provider")

    monkeypatch.setattr(run_eval, "get_provider", lambda: Paid())
    monkeypatch.setattr(
        run_eval,
        "available_sources",
        lambda: {"stub": lambda: run_eval.sources.from_text("stub", "stub", SOURCE)},
    )
    assert run_eval.main(["--dry-run", "--out", str(tmp_path)]) == 0


# --- run_eval tells the truth about whichever provider it is pointed at ----
#
# Both defects below were found on a real Ollama run. The runner quoted "projected
# $0.53" for a provider that cannot charge anything, because project_cost looked
# "llama3.1:8b" up in the pricing table, missed, and fell back to the default rate.
# Then it asked "Spend real money on this run?" about that same free run. The second
# is the worse of the two: a confirmation that appears when there is nothing to
# confirm is a confirmation that gets waved through on the run where it matters.


class _Paid:
    name, model, is_paid = "anthropic", "claude-opus-5", True

    def generate(self, *args, **kwargs):
        raise AssertionError("these tests must not call a provider")


class _Free:
    name, model, is_paid = "ollama", "llama3.1:8b", False

    def generate(self, *args, **kwargs):
        raise AssertionError("these tests must not call a provider")


def _stubbed_run(monkeypatch, tmp_path, provider):
    """Wire main() up so it can run end to end without a provider or a real course."""
    from evals import run_eval

    monkeypatch.setenv("STUDYFORGE_DB", str(tmp_path / "scratch.sqlite3"))
    monkeypatch.setattr(run_eval, "get_provider", lambda: provider)
    monkeypatch.setattr(
        run_eval,
        "available_sources",
        lambda: {"stub": lambda: run_eval.sources.from_text("stub", "stub", SOURCE)},
    )
    monkeypatch.setattr(run_eval, "run_course_eval", lambda *a, **k: _result_fixture())
    monkeypatch.setattr(run_eval, "usage_snapshot", lambda: {"totals": {}})
    return run_eval


def _refuse_input(monkeypatch, why: str):
    def boom(*args, **kwargs):
        raise AssertionError(why)

    monkeypatch.setattr("builtins.input", boom)


def _record_input(monkeypatch, answer: str) -> list[str]:
    asked: list[str] = []

    def fake_input(prompt: str = "") -> str:
        asked.append(prompt)
        return answer

    monkeypatch.setattr("builtins.input", fake_input)
    return asked


# --- the projection ---


def test_free_provider_is_quoted_no_price(monkeypatch):
    """A dollar figure for a free run is invented, not estimated."""
    from evals import run_eval

    projection = run_eval.project_cost("llama3.1:8b", "word " * 4000, is_paid=False)
    assert projection["projected_cost_usd"] is None
    assert projection["priced"] is False
    # The tokens are still real, and still worth reporting.
    assert projection["projected_input_tokens"] > 0
    assert projection["assumed_calls"] == run_eval.PROJECTED_LESSONS + 1


def test_paid_provider_is_still_quoted_a_price(monkeypatch):
    from evals import run_eval

    projection = run_eval.project_cost("claude-opus-5", "word " * 4000, is_paid=True)
    assert projection["projected_cost_usd"] > 0
    assert projection["priced"] is True
    assert projection["approximate_pricing"] is False


def test_projection_defaults_to_pricing_when_nobody_says(monkeypatch):
    """Forgetting the flag must over-warn, not under-warn."""
    from evals import run_eval

    assert run_eval.project_cost("claude-opus-5", "word " * 100)["projected_cost_usd"] > 0


def test_free_run_prints_tokens_and_calls_instead_of_dollars(monkeypatch, tmp_path, capsys):
    run_eval = _stubbed_run(monkeypatch, tmp_path, _Free())
    assert run_eval.main(["--dry-run", "--out", str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "projected $" not in out
    assert "Projected total: ~$" not in out
    assert "cap $" not in out
    # No cap line either: a cap that cannot apply reads as a cap someone forgot.
    assert "Cost cap:" not in out
    # What it says instead: the numbers that are real about a free run.
    assert "tokens over" in out
    assert "calls" in out
    assert "ollama is free" in out


def test_paid_run_still_prints_the_dollar_projection(monkeypatch, tmp_path, capsys):
    run_eval = _stubbed_run(monkeypatch, tmp_path, _Paid())
    monkeypatch.setenv("STUDYFORGE_COST_LIMIT_USD", "3.00")
    assert run_eval.main(["--dry-run", "--out", str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "projected $" in out
    assert "Projected total: ~$" in out
    assert "(cap $3.0)" in out
    assert "Cost cap: 3.0" in out


def test_paid_run_on_an_unpriced_model_says_the_price_was_guessed(monkeypatch, tmp_path, capsys):
    """The other half of project_cost's silent fallback, on the paid side.

    /usage already grew a notice for exactly this state: a model with no entry in
    the pricing table gets exact token counts against a price nobody has. The
    runner printed the figure with no such qualifier.
    """

    class PaidUnpriced(_Paid):
        model = "claude-something-unreleased"

    run_eval = _stubbed_run(monkeypatch, tmp_path, PaidUnpriced())
    assert run_eval.main(["--dry-run", "--out", str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "projected $" in out
    assert "no entry in the pricing table" in out
    assert "STUDYFORGE_PRICE_DEFAULT_IN_USD" in out


def test_priced_model_gets_no_guessed_price_note(monkeypatch, tmp_path, capsys):
    run_eval = _stubbed_run(monkeypatch, tmp_path, _Paid())
    run_eval.main(["--dry-run", "--out", str(tmp_path)])
    assert "no entry in the pricing table" not in capsys.readouterr().out


# --- the consent prompt ---


def test_free_run_is_not_asked_to_approve_spending(monkeypatch, tmp_path, capsys):
    run_eval = _stubbed_run(monkeypatch, tmp_path, _Free())
    _refuse_input(monkeypatch, "a free provider must not be asked to approve spending")

    assert run_eval.main(["--out", str(tmp_path)]) == 0
    assert "Spend real money" not in capsys.readouterr().out


def test_paid_run_is_still_asked_to_approve_spending(monkeypatch, tmp_path):
    run_eval = _stubbed_run(monkeypatch, tmp_path, _Paid())
    monkeypatch.setenv("STUDYFORGE_COST_LIMIT_USD", "3.00")
    asked = _record_input(monkeypatch, "n")

    assert run_eval.main(["--out", str(tmp_path)]) == 1
    assert asked and "Spend real money" in asked[0]


def test_paid_run_declined_aborts_before_any_generation(monkeypatch, tmp_path, capsys):
    run_eval = _stubbed_run(monkeypatch, tmp_path, _Paid())
    monkeypatch.setenv("STUDYFORGE_COST_LIMIT_USD", "3.00")
    monkeypatch.setattr(
        run_eval,
        "run_course_eval",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("declined run must not generate")),
    )
    _record_input(monkeypatch, "n")

    assert run_eval.main(["--out", str(tmp_path)]) == 1
    assert "Aborted." in capsys.readouterr().out


def test_paid_run_with_yes_flag_still_skips_the_prompt(monkeypatch, tmp_path):
    run_eval = _stubbed_run(monkeypatch, tmp_path, _Paid())
    monkeypatch.setenv("STUDYFORGE_COST_LIMIT_USD", "3.00")
    _refuse_input(monkeypatch, "--yes must not prompt")

    assert run_eval.main(["--yes", "--out", str(tmp_path)]) == 0


# --- the cap guard, unweakened ---


def test_free_provider_does_not_need_a_cost_cap(monkeypatch, tmp_path):
    """The other side of test_preflight_refuses_without_a_cost_cap.

    A cap on a free provider would be a cap on nothing, and MeteredLLM does not
    apply one to an unpaid provider anyway. Pinned so that making the free path
    honest cannot drift into refusing to run it.
    """
    from evals import run_eval

    monkeypatch.setenv("STUDYFORGE_DB", str(tmp_path / "scratch.sqlite3"))
    monkeypatch.delenv("STUDYFORGE_COST_LIMIT_USD", raising=False)
    monkeypatch.setattr(run_eval, "get_provider", lambda: _Free())

    env = run_eval.preflight()
    assert env["is_paid"] is False
    assert env["cost_limit_usd"] is None


def test_free_run_without_a_cap_still_refuses_the_real_database(monkeypatch):
    """The database guard is not about money and must not follow the price out."""
    from evals import run_eval

    monkeypatch.setenv("STUDYFORGE_DB", str(run_eval.BACKEND_DIR / "studyforge.sqlite3"))
    monkeypatch.setattr(run_eval, "get_provider", lambda: _Free())
    with pytest.raises(SystemExit):
        run_eval.preflight()
