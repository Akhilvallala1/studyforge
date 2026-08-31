"""Course generation pipeline: source chunks -> outline -> authored lessons with quizzes."""

import json
import logging
import re
from typing import Protocol

logger = logging.getLogger("studyforge.generation")

# Below this many segments the whole document is small enough to hand to every
# lesson call, so routing buys no cost saving and only risks withholding context.
SEGMENT_ROUTING_MIN_CHUNKS = 3

_OUTLINE_BASE = """You are a curriculum designer. Given source material, produce a course \
outline as JSON. Respond with ONLY a JSON object, no prose, matching:
{
  "title": str,
  "description": str,
  "modules": [{"title": str, "lessons": [{"title": str, "summary": str%(segments_field)s}]}]
}
Aim for 2-5 modules with 2-4 lessons each, scaled to how much material there is. \
%(segments_rules)sEvery lesson must be grounded in the source material - do not invent topics \
it doesn't cover."""

_SEGMENTS_FIELD = ', "segments": [int]'

_SEGMENTS_RULES = """The material is split into numbered segments. "segments" lists the \
numbers of the segments a lesson is drawn from, normally one or two. Cover the whole document: \
every segment number must appear in at least one lesson's "segments", and roughly longer \
segments deserve roughly more lessons. Material near the end is not an appendix: work through \
the segments in order and keep going to the last one. """


def outline_system(chunk_count: int) -> str:
    """The outline instructions, asking for segment routing only where it is used.

    Routing earns its keep on a long document: it makes coverage structural rather
    than hoped for, and stops every lesson call re-sending the whole text. On a short
    one it is dead weight, and asking for it anyway measurably hurt. On a two-chunk
    source the segment instructions halved the lesson count (12 to 6) and dragged
    answerability from 43% to 12%, because a handful of dense lessons range further
    from the material any single question is drawn from. So the instruction now
    appears exactly where lesson_segments will act on it.
    """
    routed = chunk_count >= SEGMENT_ROUTING_MIN_CHUNKS
    return _OUTLINE_BASE % {
        "segments_field": _SEGMENTS_FIELD if routed else "",
        "segments_rules": _SEGMENTS_RULES if routed else "",
    }


# Kept for callers and tests that want the routed wording without a chunk count.
OUTLINE_SYSTEM = outline_system(SEGMENT_ROUTING_MIN_CHUNKS)

LESSON_SYSTEM = """You are a teacher writing one lesson of a course. Given the lesson title, \
its summary, and the relevant source material, respond with ONLY a JSON object matching:
{
  "content": str,            # the lesson itself, in markdown: explanations, examples
  "concepts": [str],         # 2-5 key concepts this lesson teaches
  "quiz": [
    {"question": str, "kind": "mcq" | "short", "options": [str], "answer": str, "concept": str}
  ]
}
Output format: the JSON object is the entire reply. Do not put a ``` fence around it and do not \
write anything before or after it. Code examples belong inside the "content" string as ordinary \
markdown, fences and all, escaped the way JSON requires; a code example is never a reason to \
stop emitting JSON.

Quiz rules:
- Write 3-6 items. For "mcq" give exactly 4 options and set "answer" to the correct option's \
text. For "short" leave "options" empty.
- Every answer must be traceable to the source material: a reader should be able to point at \
the passage it comes from. Do not ask about anything the source does not actually say, and do \
not require knowledge the source assumes but never states.
- Teach a thing in "content" before asking about it, so the lesson alone is enough to answer.
- Write all four MCQ options in the same voice, at similar length and specificity. Never lift \
the correct option word for word from a sentence in the content while inventing the other three: \
that makes the item solvable by spotting the familiar phrase. Each wrong option should be a \
claim a reader who half-understood the lesson could genuinely believe."""
# Chosen by measurement, not taste. See evals/output/trials-report.md: over four runs each on a
# short source, this wording scored 59.7% answerable and 50.4% grounded against 21.2% and 16.8%
# for the previous wording, with non-overlapping ranges, and held at 48.5% and 46.9% over two
# runs of the full source. The sentence doing the work is the first one: anchoring answers to a
# passage in the SOURCE, rather than merely to the lesson, also dropped hallucination candidates
# from 30 per course to 6.5. Change it only against a fresh run of the same trial.

# Sent back with the original prompt when a reply cannot be parsed. Names the one
# failure mode worth naming: the model narrating around the object, or fencing it.
REPAIR_INSTRUCTION = """Your previous reply could not be parsed as JSON. Send the same content \
again as a single raw JSON object and nothing else: no explanation before or after it, and no \
``` fence around the object itself. Code examples inside string values are welcome; keep them \
escaped as valid JSON strings."""


class Meter(Protocol):
    def generate(self, stage: str, system: str, prompt: str, max_tokens: int = 64000) -> str: ...


# The stage names this pipeline records in llm_calls. /usage reads them: a row with
# one of these stages and no course id is a run that failed before its course could
# be saved, and the page says so in those words. Adding a stage here means checking
# that sentence is still true of it, or giving the new stage its own.
OUTLINE_STAGE = "outline"
LESSON_STAGE = "lesson"
STAGES = frozenset({OUTLINE_STAGE, LESSON_STAGE})


def _balanced_objects(text: str) -> list[str]:
    """Every top-level {...} span in `text`, longest first.

    Scans character by character tracking string literals and escapes, so braces
    inside a JSON string (a markdown code example, say) do not open or close a
    span. An unterminated object - a reply truncated at max_tokens - yields
    nothing rather than a broken prefix.
    """
    spans: list[str] = []
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for i, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                    spans.append(text[start : i + 1])
    return sorted(spans, key=len, reverse=True)


def _json_candidates(text: str) -> list[str]:
    """Substrings that might be the model's JSON object, best guess first."""
    stripped = text.strip()
    candidates = [stripped]
    # A fenced object, but only from a fence the model labelled json or left bare.
    # Matching any fence is what broke on real technical material: a lesson whose
    # markdown content contains a ```python example would hand back the example.
    for lang, body in re.findall(
        r"```([A-Za-z0-9_+-]*)[ \t]*\r?\n(.*?)```", stripped, flags=re.DOTALL
    ):
        if lang.lower() in ("", "json"):
            candidates.append(body.strip())
    candidates.extend(_balanced_objects(stripped))
    seen: set[str] = set()
    return [c for c in candidates if c and not (c in seen or seen.add(c))]


def parse_json_response(text: str) -> dict:
    """Extract the JSON object from a model response.

    Order matters. The reply is tried verbatim first, because a well-formed lesson
    about code is valid JSON that happens to contain ``` fences inside a string,
    and any eager fence-stripping returns the code example instead of the lesson.
    """
    for candidate in _json_candidates(text):
        try:
            parsed = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError(f"No JSON object in model response: {text[:200]!r}")


def generate_json(
    meter: Meter, stage: str, system: str, prompt: str, max_tokens: int = 64000
) -> dict:
    """One model call, parsed, with a single corrective retry if it will not parse.

    Worth one extra call: by the time a reply fails to parse the input tokens are
    already paid for, and abandoning the stage wastes them for certain.
    """
    try:
        return parse_json_response(meter.generate(stage, system, prompt, max_tokens))
    except ValueError as first_error:
        logger.warning("stage=%s: reply did not parse, retrying once (%s)", stage, first_error)
    retry_prompt = f"{prompt}\n\n{REPAIR_INSTRUCTION}"
    return parse_json_response(meter.generate(stage, system, retry_prompt, max_tokens))


def label_segments(chunks: list[str], indexes: list[int] | None = None) -> str:
    """Source material with each segment numbered, so the outline can refer to them."""
    picked = range(len(chunks)) if indexes is None else indexes
    return "\n\n".join(f"[segment {i}]\n{chunks[i]}" for i in picked)


def generate_outline(meter: Meter, chunks: list[str]) -> dict:
    routed = len(chunks) >= SEGMENT_ROUTING_MIN_CHUNKS
    if routed:
        material = label_segments(chunks)
        prompt = f"The source material has {len(chunks)} segments.\n\nSource material:\n\n{material}"
    else:
        # No segment numbering either: labels the model is told nothing about are
        # noise in the middle of the text it is meant to be reading.
        prompt = "Source material:\n\n" + "\n\n".join(chunks)
    outline = generate_json(meter, OUTLINE_STAGE, outline_system(len(chunks)), prompt)
    if not outline.get("modules"):
        raise ValueError("Outline has no modules")
    return outline


def lesson_segments(stub: dict, chunk_count: int) -> list[int]:
    """Which source segments one lesson is written from.

    Falls back to the whole document whenever the outline gave no usable answer,
    so a model that ignores the "segments" field (or a small local one that cannot
    manage it) degrades to the previous behaviour instead of losing its material.
    """
    if chunk_count < SEGMENT_ROUTING_MIN_CHUNKS:
        return list(range(chunk_count))
    picked = set()
    for raw in stub.get("segments") or []:
        try:
            index = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= index < chunk_count:
            picked.add(index)
    return sorted(picked) or list(range(chunk_count))


def _clean_concepts(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [c.strip() for c in raw if isinstance(c, str) and c.strip()]


def _clean_quiz(raw: object) -> list[dict]:
    """Keep only quiz items shaped the way the rest of the app expects.

    The schema asks for objects, and a real run returned a bare string instead. That
    reached _save_course, which calls .get on every item, and became a 500 after the
    course had already been paid for. Model output is untrusted input like any other,
    so it is normalized where it enters rather than trusted at every later use.

    A malformed item is dropped rather than repaired: a question with no answer is
    not a question, and inventing one would put words in the model's mouth.
    """
    if not isinstance(raw, list):
        return []
    clean: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            logger.warning("Dropping quiz item that is %s, not an object", type(item).__name__)
            continue
        question = item.get("question")
        answer = item.get("answer")
        if not isinstance(question, str) or not question.strip():
            continue
        if not isinstance(answer, str) or not answer.strip():
            continue
        options = item.get("options")
        kind = item.get("kind")
        concept = item.get("concept")
        clean.append(
            {
                "question": question.strip(),
                "kind": kind if kind in {"mcq", "short"} else "short",
                "options": [o for o in options if isinstance(o, str)]
                if isinstance(options, list)
                else [],
                "answer": answer.strip(),
                "concept": concept.strip() if isinstance(concept, str) else "",
            }
        )
    return clean


def generate_lesson(
    meter: Meter,
    lesson_title: str,
    lesson_summary: str,
    chunks: list[str],
    segments: list[int] | None = None,
) -> dict:
    indexes = list(range(len(chunks))) if segments is None else segments
    prompt = (
        f"Lesson title: {lesson_title}\n"
        f"Lesson summary: {lesson_summary}\n\n"
        f"Source material:\n\n{label_segments(chunks, indexes)}"
    )
    lesson = generate_json(meter, LESSON_STAGE, LESSON_SYSTEM, prompt)
    lesson["content"] = lesson.get("content") or ""
    lesson["concepts"] = _clean_concepts(lesson.get("concepts"))
    lesson["quiz"] = _clean_quiz(lesson.get("quiz"))
    return lesson


def generate_course(meter: Meter, chunks: list[str]) -> dict:
    """Full pipeline. Returns {title, description, modules: [{title, lessons: [...]}]}
    where each lesson has title, content, concepts, quiz, and the source segments it
    was written from.

    A lesson that will not parse even after its retry is dropped and the rest of the
    course is kept: one bad reply out of twelve should cost one lesson, not the whole
    run and everything already spent on it.
    """
    outline = generate_outline(meter, chunks)
    course = {
        "title": outline.get("title", "Untitled course"),
        "description": outline.get("description", ""),
        "modules": [],
    }
    failures: list[dict] = []
    for module in outline["modules"]:
        built = {"title": module.get("title", "Module"), "lessons": []}
        for lesson_stub in module.get("lessons", []):
            title = lesson_stub.get("title", "Lesson")
            segments = lesson_segments(lesson_stub, len(chunks))
            try:
                authored = generate_lesson(
                    meter, title, lesson_stub.get("summary", ""), chunks, segments
                )
            except ValueError as exc:
                logger.error("dropping lesson %r: %s", title, exc)
                failures.append({"lesson": title, "error": str(exc)})
                continue
            built["lessons"].append({"title": title, "segments": segments, **authored})
        # An empty module would render as a heading with nothing under it.
        if built["lessons"]:
            course["modules"].append(built)
    if not course["modules"]:
        raise ValueError(f"No lesson could be generated ({len(failures)} failed)")
    if failures:
        course["dropped_lessons"] = failures
    return course
