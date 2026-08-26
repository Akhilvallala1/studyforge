"""Course generation pipeline: source chunks -> outline -> authored lessons with quizzes."""

import json
import re
from typing import Protocol

OUTLINE_SYSTEM = """You are a curriculum designer. Given source material, produce a course \
outline as JSON. Respond with ONLY a JSON object, no prose, matching:
{
  "title": str,
  "description": str,
  "modules": [{"title": str, "lessons": [{"title": str, "summary": str}]}]
}
Aim for 2-5 modules with 2-4 lessons each, scaled to how much material there is. \
Every lesson must be grounded in the source material - do not invent topics it doesn't cover."""

LESSON_SYSTEM = """You are a teacher writing one lesson of a course. Given the lesson title, \
its summary, and the relevant source material, respond with ONLY a JSON object matching:
{
  "content": str,            # the lesson itself, in markdown: explanations, examples
  "concepts": [str],         # 2-5 key concepts this lesson teaches
  "quiz": [
    {"question": str, "kind": "mcq" | "short", "options": [str], "answer": str, "concept": str}
  ]
}
Write 3-6 quiz items. For "mcq" give exactly 4 options and set "answer" to the correct option's \
text. For "short" leave "options" empty. Every question must be answerable from the lesson \
content alone."""


class Meter(Protocol):
    def generate(self, stage: str, system: str, prompt: str, max_tokens: int = 64000) -> str: ...


def parse_json_response(text: str) -> dict:
    """Extract the first JSON object from a model response, tolerating code fences."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in model response: {text[:200]!r}")
    return json.loads(text[start : end + 1])


def generate_outline(meter: Meter, chunks: list[str]) -> dict:
    material = "\n\n---\n\n".join(chunks)
    response = meter.generate("outline", OUTLINE_SYSTEM, f"Source material:\n\n{material}")
    outline = parse_json_response(response)
    if not outline.get("modules"):
        raise ValueError("Outline has no modules")
    return outline


def generate_lesson(
    meter: Meter, lesson_title: str, lesson_summary: str, chunks: list[str]
) -> dict:
    material = "\n\n---\n\n".join(chunks)
    prompt = (
        f"Lesson title: {lesson_title}\n"
        f"Lesson summary: {lesson_summary}\n\n"
        f"Source material:\n\n{material}"
    )
    lesson = parse_json_response(meter.generate("lesson", LESSON_SYSTEM, prompt))
    lesson.setdefault("content", "")
    lesson.setdefault("concepts", [])
    lesson.setdefault("quiz", [])
    return lesson


def generate_course(meter: Meter, chunks: list[str]) -> dict:
    """Full pipeline. Returns {title, description, modules: [{title, lessons: [...]}]}
    where each lesson has title, content, concepts, and quiz."""
    outline = generate_outline(meter, chunks)
    course = {
        "title": outline.get("title", "Untitled course"),
        "description": outline.get("description", ""),
        "modules": [],
    }
    for module in outline["modules"]:
        built = {"title": module.get("title", "Module"), "lessons": []}
        for lesson_stub in module.get("lessons", []):
            title = lesson_stub.get("title", "Lesson")
            authored = generate_lesson(meter, title, lesson_stub.get("summary", ""), chunks)
            built["lessons"].append({"title": title, **authored})
        course["modules"].append(built)
    return course
