"""Questions-only generation: no lesson prose, content filled from source chunks.

Four acceptance criteria are on trial here. A source-mode lesson's content is
non-empty and a verbatim substring of the ingested source (proving the model did
not write it), every lesson still carries at least one concept (review cards key
on concept_key and need one to exist), the review-card path builds a card from a
source-mode course exactly like it does from a lessons-mode one, and a tutor turn
on a source-mode concept receives a non-empty, grounded material block.
"""

import json
from uuid import uuid4

from conftest import StubPaidProvider

from app import generation, ingest, models, review, tutor
from app.concepts import normalize_concept
from app.db import SessionLocal, init_db
from app.generation import (
    LESSON_SYSTEM,
    QUESTIONS_SYSTEM,
    generate_questions,
    generate_questions_course,
    source_excerpt,
)
from app.metering import MeteredLLM

SOURCE_TEXT = (
    "Photosynthesis converts light energy into chemical energy stored in glucose.\n\n"
    "Chlorophyll in the chloroplast absorbs light, mostly red and blue wavelengths, "
    "and reflects green light, which is why leaves look green.\n\n"
    "The light-dependent reactions split water and release oxygen as a byproduct, "
    "while the Calvin cycle fixes carbon dioxide into sugar using that captured energy.\n\n"
    "NADPH and ATP produced by the light reactions power the Calvin cycle, which runs "
    "in the stroma rather than on the thylakoid membrane."
)


class FakeQuestionsMeter:
    """Canned outline, then a questions-shaped reply for every lesson call.

    Mirrors test_generation.py's FakeMeter, dispatching on QUESTIONS_SYSTEM's own
    phrase instead of falling through to a lesson shape, so a caller that
    accidentally invoked generate_lesson here would get a KeyError, not a pass.
    """

    def __init__(self):
        self.calls = 0
        self.stages = []

    def generate(self, stage: str, system: str, prompt: str, max_tokens: int = 64000) -> str:
        self.calls += 1
        self.stages.append(stage)
        if "curriculum designer" in system:
            return json.dumps(
                {
                    "title": "Plant Biology",
                    "description": "A course",
                    "modules": [
                        {
                            "title": "Module 1",
                            "lessons": [
                                {"title": "Lesson A", "summary": "first", "segments": [0, 1]},
                                {"title": "Lesson B", "summary": "second", "segments": [2, 3]},
                            ],
                        }
                    ],
                }
            )
        assert "without writing the lesson itself" in system
        return json.dumps(
            {
                "concepts": ["chlorophyll"],
                "quiz": [
                    {
                        "question": "What does chlorophyll absorb?",
                        "kind": "short",
                        "options": [],
                        "answer": "light",
                        "concept": "chlorophyll",
                    }
                ],
            }
        )


def test_stub_paid_provider_answers_the_questions_stage_from_its_own_branch():
    """Pins conftest.StubPaidProvider's questions branch: without it, this falls
    through to the lesson shape below, whose "concepts"/"quiz" also parse, so a
    caller expecting this stage to fail loudly would get a course instead. The
    values here (stub-concept/stub-answer) are distinct from that fallback's
    (concept-1/a) precisely so this test tells the two branches apart.
    """
    init_db()
    meter = MeteredLLM(StubPaidProvider(), uuid4().hex)
    result = generate_questions(meter, "Lesson", "summary", ["A chunk of source text."])
    assert result["concepts"] == ["stub-concept"]
    assert result["quiz"][0]["answer"] == "stub-answer"


def test_generate_questions_returns_only_concepts_and_quiz():
    """No "content" key: the caller fills that field locally, never the model."""
    meter = FakeQuestionsMeter()
    result = generate_questions(meter, "Lesson A", "summary", ["chunk zero", "chunk one"])
    assert set(result.keys()) == {"concepts", "quiz"}
    assert result["concepts"] == ["chlorophyll"]


def test_questions_system_carries_the_two_measured_bullets_verbatim():
    """The write-count and option-voice rules are the ones the trial measured; copy them."""
    write_count_bullet = (
        '- Write 3-6 items. For "mcq" give exactly 4 options and set "answer" to the correct '
        'option\'s text. For "short" leave "options" empty.'
    )
    option_voice_bullet = (
        "- Write all four MCQ options in the same voice, at similar length and specificity. "
        "Never lift the correct option word for word from a sentence in the content while "
        "inventing the other three: that makes the item solvable by spotting the familiar "
        "phrase. Each wrong option should be a claim a reader who half-understood the lesson "
        "could genuinely believe."
    )
    assert write_count_bullet in LESSON_SYSTEM
    assert write_count_bullet in QUESTIONS_SYSTEM
    assert option_voice_bullet in LESSON_SYSTEM
    assert option_voice_bullet in QUESTIONS_SYSTEM


def test_questions_system_drops_the_teach_before_ask_rule():
    """There is no "content" field in this mode, so the rule referring to it must not appear."""
    assert 'Teach a thing in "content"' in LESSON_SYSTEM
    assert 'Teach a thing in "content"' not in QUESTIONS_SYSTEM


def test_source_excerpt_spans_a_contiguous_window():
    chunks = ["para zero.", "para one.", "para two.", "para three."]
    assert source_excerpt(chunks, [1, 2]) == "para one.\n\npara two."
    assert source_excerpt(chunks, [0]) == "para zero."
    # A gap still yields one contiguous span, not the two named chunks alone.
    assert source_excerpt(chunks, [0, 2]) == "para zero.\n\npara one.\n\npara two."


def test_generate_questions_course_content_is_a_substring_of_the_source():
    """Proves the model did not write the content: it must appear in the raw source."""
    meter = FakeQuestionsMeter()
    chunks = ingest.chunk_text(ingest.clean_text(SOURCE_TEXT))
    course = generate_questions_course(meter, chunks)
    cleaned_source = ingest.clean_text(SOURCE_TEXT)
    for module in course["modules"]:
        for lesson in module["lessons"]:
            assert lesson["content"]
            assert lesson["content"] in cleaned_source
            assert lesson["content_kind"] == generation.SOURCE_CONTENT_KIND
            assert len(lesson["concepts"]) >= 1


def test_generate_questions_course_never_asks_the_model_for_content():
    meter = FakeQuestionsMeter()
    chunks = ingest.chunk_text(ingest.clean_text(SOURCE_TEXT))
    generate_questions_course(meter, chunks)
    assert meter.stages.count(generation.QUESTIONS_STAGE) == 2
    assert generation.LESSON_STAGE not in meter.stages


def _seed_source_lesson():
    """A course whose one lesson carries source-mode content, seeded directly.

    Bypasses generate_questions_course because the review-card and tutor paths key
    on concepts/quiz_items/content_kind alone, the same fields test_tutor_context's
    own _seed writes; this only adds content_kind="source" to that shape.
    """
    label = f"Chlorophyll {uuid4().hex[:8]}"
    key = normalize_concept(label)
    excerpt = source_excerpt(
        ["Chlorophyll absorbs red and blue light.", "It reflects green light."], [0, 1]
    )
    session = SessionLocal()
    try:
        course = models.Course(title=f"Course {label}", description="")
        module = models.Module(title="Module 1", position=0)
        lesson = models.Lesson(
            title=f"Lesson on {label}",
            position=0,
            content=excerpt,
            content_kind=generation.SOURCE_CONTENT_KIND,
            concepts=[label],
        )
        lesson.quiz_items.append(
            models.QuizItem(
                question=f"What does {label} absorb?",
                kind="short",
                options=[],
                answer="red and blue light",
                concept=label,
            )
        )
        module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.commit()
        return key, label, excerpt
    finally:
        session.close()


def test_review_card_is_created_from_a_source_mode_lesson():
    """The review-card path is indifferent to content_kind: it keys on concept_key alone."""
    init_db()
    key, label, _ = _seed_source_lesson()
    session = SessionLocal()
    try:
        review.record_review(session, key, label, rating=3)
        session.commit()
        card = review.get_card(session, key)
        assert card is not None
        assert card.concept_key == key
    finally:
        session.close()


def test_tutor_material_block_is_grounded_in_the_source_excerpt():
    """A tutor turn on a source-mode concept must see the excerpt, not an empty block."""
    init_db()
    key, _label, excerpt = _seed_source_lesson()
    session = SessionLocal()
    try:
        ctx = tutor.context(session, key)
        prompt = tutor.build_prompt(ctx, [], "What does it absorb?")
        assert excerpt in prompt
    finally:
        session.close()
