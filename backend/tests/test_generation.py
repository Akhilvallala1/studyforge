import json

import pytest

from app.generation import (
    REPAIR_INSTRUCTION,
    generate_course,
    generate_json,
    generate_lesson,
    lesson_segments,
    parse_json_response,
)

OUTLINE = {
    "title": "Test Course",
    "description": "A course",
    "modules": [
        {
            "title": "Module 1",
            "lessons": [
                {"title": "Lesson A", "summary": "first", "segments": [0]},
                {"title": "Lesson B", "summary": "second", "segments": [2]},
            ],
        }
    ],
}
LESSON = {
    "content": "# Lesson\nSome content",
    "concepts": ["concept-1"],
    "quiz": [
        {
            "question": "What is 1+1?",
            "kind": "mcq",
            "options": ["1", "2", "3", "4"],
            "answer": "2",
            "concept": "concept-1",
        }
    ],
}


class ScriptedMeter:
    """Replays a fixed list of responses and remembers the prompts it was given."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []
        self.stages = []

    def generate(self, stage: str, system: str, prompt: str, max_tokens: int = 64000) -> str:
        self.prompts.append(prompt)
        self.stages.append(stage)
        return self.responses.pop(0)


class FakeMeter:
    """Returns canned outline then lesson responses, mimicking the two-stage pipeline.

    Mimics the MeteredLLM.generate(stage, system, prompt, max_tokens) -> str contract
    that generation.py's Meter protocol expects.
    """

    def __init__(self):
        self.calls = 0

    def generate(self, stage: str, system: str, prompt: str, max_tokens: int = 64000) -> str:
        self.calls += 1
        if "curriculum designer" in system:
            return json.dumps(
                {
                    "title": "Test Course",
                    "description": "A course",
                    "modules": [
                        {
                            "title": "Module 1",
                            "lessons": [
                                {"title": "Lesson A", "summary": "first"},
                                {"title": "Lesson B", "summary": "second"},
                            ],
                        }
                    ],
                }
            )
        return json.dumps(
            {
                "content": "# Lesson\nSome content",
                "concepts": ["concept-1"],
                "quiz": [
                    {
                        "question": "What is 1+1?",
                        "kind": "mcq",
                        "options": ["1", "2", "3", "4"],
                        "answer": "2",
                        "concept": "concept-1",
                    }
                ],
            }
        )


def test_parse_json_response_plain():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_json_response_code_fence():
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_response_with_prose():
    assert parse_json_response('Here you go:\n{"a": 1}') == {"a": 1}


def test_parse_json_response_no_json():
    with pytest.raises(ValueError):
        parse_json_response("no json here")


def test_parse_json_response_prefers_the_object_over_an_inner_code_fence():
    """A lesson about code is valid JSON containing a ```python fence in a string."""
    response = json.dumps({"content": "```python\nx = 1\n```", "concepts": ["a"]})
    assert parse_json_response(response)["concepts"] == ["a"]


def test_parse_json_response_finds_the_object_after_prose_and_a_stray_fence():
    response = (
        "Here is your lesson.\n\n"
        "```python\ndef helper():\n    return {}\n```\n\n"
        + json.dumps({"content": "body", "concepts": ["b"], "quiz": []})
    )
    assert parse_json_response(response)["concepts"] == ["b"]


def test_parse_json_response_picks_the_outermost_object():
    """Prose that quotes a fragment before the real object must not win on order."""
    response = '{"note": 1}\n\n' + json.dumps({"content": "c", "concepts": ["x"], "quiz": []})
    assert parse_json_response(response)["concepts"] == ["x"]


def test_parse_json_response_ignores_braces_inside_strings():
    response = json.dumps({"content": "use {} for a dict", "concepts": ["c"]})
    assert parse_json_response(response)["concepts"] == ["c"]


def test_parse_json_response_rejects_a_truncated_object():
    with pytest.raises(ValueError, match="No JSON object"):
        parse_json_response('{"content": "cut off here')


def test_generate_json_retries_once_with_a_corrective_instruction():
    meter = ScriptedMeter(["I cannot do that.", json.dumps(LESSON)])
    result = generate_json(meter, "lesson", "sys", "original prompt")
    assert result["concepts"] == ["concept-1"]
    assert len(meter.prompts) == 2
    assert meter.prompts[0] == "original prompt"
    assert REPAIR_INSTRUCTION in meter.prompts[1]


def test_generate_json_gives_up_after_one_retry():
    meter = ScriptedMeter(["nope", "still nope"])
    with pytest.raises(ValueError, match="No JSON object"):
        generate_json(meter, "lesson", "sys", "p")
    assert len(meter.prompts) == 2


def test_a_quiz_item_that_is_not_an_object_is_dropped():
    """From a real paid run: the model returned a bare string where the schema asks
    for an object. It reached _save_course, which calls .get on every item, and became
    a 500 after the course had already been generated and paid for."""
    lesson = dict(LESSON)
    lesson["quiz"] = ["Just a question with no answer", {"question": "Real?", "answer": "yes"}]
    meter = ScriptedMeter([json.dumps(lesson)])

    result = generate_lesson(meter, "T", "S", ["chunk"])

    assert len(result["quiz"]) == 1
    assert result["quiz"][0]["question"] == "Real?"
    # Every surviving item carries the keys _save_course reads, so nothing downstream
    # has to guess.
    assert set(result["quiz"][0]) == {"question", "kind", "options", "answer", "concept"}


def test_a_quiz_item_missing_its_answer_is_dropped_not_invented():
    """A question with no answer cannot be graded, and filling one in would put words
    in the model's mouth."""
    lesson = dict(LESSON)
    lesson["quiz"] = [
        {"question": "What is it?", "answer": "   "},
        {"question": "", "answer": "orphan"},
    ]
    meter = ScriptedMeter([json.dumps(lesson)])
    assert generate_lesson(meter, "T", "S", ["chunk"])["quiz"] == []


def test_malformed_concepts_do_not_reach_the_lesson():
    lesson = dict(LESSON)
    lesson["concepts"] = ["fine", 42, None, "  spaced  ", ""]
    meter = ScriptedMeter([json.dumps(lesson)])
    assert generate_lesson(meter, "T", "S", ["chunk"])["concepts"] == ["fine", "spaced"]


def test_generate_course_keeps_the_lessons_that_parsed():
    """One unrecoverable lesson costs that lesson, not the course and its spend."""
    meter = ScriptedMeter(
        [json.dumps(OUTLINE), json.dumps(LESSON), "garbage", "garbage again"]
    )
    course = generate_course(meter, ["one", "two", "three"])
    lessons = course["modules"][0]["lessons"]
    assert [lesson["title"] for lesson in lessons] == ["Lesson A"]
    assert course["dropped_lessons"] == [
        {"lesson": "Lesson B", "error": course["dropped_lessons"][0]["error"]}
    ]
    assert "No JSON object" in course["dropped_lessons"][0]["error"]


def test_generate_course_raises_when_every_lesson_fails():
    meter = ScriptedMeter([json.dumps(OUTLINE)] + ["garbage"] * 4)
    with pytest.raises(ValueError, match="No lesson could be generated"):
        generate_course(meter, ["one", "two", "three"])


def test_lesson_segments_routes_on_a_long_document():
    assert lesson_segments({"segments": [2, 0, 2]}, 5) == [0, 2]


def test_lesson_segments_ignores_out_of_range_and_junk():
    assert lesson_segments({"segments": [1, 99, -1, "x", None]}, 4) == [1]


def test_lesson_segments_falls_back_to_the_whole_document():
    """A model that omits or mangles the field keeps its old, full context."""
    assert lesson_segments({}, 5) == [0, 1, 2, 3, 4]
    assert lesson_segments({"segments": []}, 5) == [0, 1, 2, 3, 4]
    assert lesson_segments({"segments": ["nonsense"]}, 5) == [0, 1, 2, 3, 4]


def test_short_documents_skip_routing_entirely():
    """With two segments there is nothing to save and context to lose."""
    assert lesson_segments({"segments": [0]}, 2) == [0, 1]


def test_generate_course_sends_only_the_routed_segments():
    meter = ScriptedMeter([json.dumps(OUTLINE), json.dumps(LESSON), json.dumps(LESSON)])
    course = generate_course(meter, ["alpha text", "beta text", "gamma text"])
    lesson_a, lesson_b = meter.prompts[1], meter.prompts[2]
    assert "alpha text" in lesson_a and "gamma text" not in lesson_a
    assert "gamma text" in lesson_b and "alpha text" not in lesson_b
    assert course["modules"][0]["lessons"][1]["segments"] == [2]


def test_outline_prompt_numbers_every_segment():
    meter = ScriptedMeter([json.dumps(OUTLINE), json.dumps(LESSON), json.dumps(LESSON)])
    generate_course(meter, ["alpha", "beta", "gamma"])
    outline_prompt = meter.prompts[0]
    assert "has 3 segments" in outline_prompt
    for index in range(3):
        assert f"[segment {index}]" in outline_prompt


def test_generate_course_pipeline():
    meter = FakeMeter()
    course = generate_course(meter, ["some source text"])
    assert course["title"] == "Test Course"
    assert len(course["modules"]) == 1
    lessons = course["modules"][0]["lessons"]
    assert [lesson["title"] for lesson in lessons] == ["Lesson A", "Lesson B"]
    assert lessons[0]["quiz"][0]["answer"] == "2"
    # 1 outline call + 2 lesson calls
    assert meter.calls == 3
