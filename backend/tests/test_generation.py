import json

import pytest

from app.generation import generate_course, parse_json_response


class FakeProvider:
    """Returns canned outline then lesson responses, mimicking the two-stage pipeline."""

    def __init__(self):
        self.calls = 0

    def generate(self, system: str, prompt: str, max_tokens: int = 64000) -> str:
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


def test_generate_course_pipeline():
    provider = FakeProvider()
    course = generate_course(provider, ["some source text"])
    assert course["title"] == "Test Course"
    assert len(course["modules"]) == 1
    lessons = course["modules"][0]["lessons"]
    assert [lesson["title"] for lesson in lessons] == ["Lesson A", "Lesson B"]
    assert lessons[0]["quiz"][0]["answer"] == "2"
    # 1 outline call + 2 lesson calls
    assert provider.calls == 3
