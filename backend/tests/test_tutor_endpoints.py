"""The tutor's two endpoints: what a turn costs, what it refuses, and what it cannot touch.

Three things are on trial here and they carry the feature's risk.

The first is that a failed turn leaves NOTHING behind, the learner's own message included.
"Save the question, then ask" is the natural implementation, and it fails in the way that
is hardest to notice afterwards: the transcript holds a question with nothing under it,
and there is no record saying whether the answer was lost or never written.

The second is the daily budget, which has to be counted one way. Remedial practice nearly
shipped a bug because its POST and its GET each derived the session separately, and
practice_facts was the fix. tutor.turn_counts is that shape here, and the tests below
drive both endpoints against the same seeded rows so a second arithmetic would show up as
two different answers about one day.

The third is what a conversation must not do. It is not a retrieval test, so a full
exchange has to leave review_cards, review_logs and attempts exactly as it found them, and
leave every progress figure the Today screen prints reading the same before and after. A
tutor that could move a schedule would let a learner talk their way to a longer interval.

Every LLM call goes through a stub provider. Nothing here reaches a real API.

Written as mutation tests where it matters. These were confirmed by making the change and
watching the right test go red:
  - write the learner row before the call -> the two zero-rows tests fail
  - swap the day and concept cap checks   -> the precedence test fails
  - drop the tutor branch of _unattributed_group -> the usage tests in
    test_usage_attribution.py fail (that half lives there, beside the other groups)
"""

import inspect
import json
import re
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect

from app import days, fsrs, main, metering, models, review, tutor
from app.concepts import normalize_concept
from app.db import Base, SessionLocal, init_db
from app.llm.base import LLMResult
from app.llm.fake_provider import FakeProvider

LESSON_CONTENT = (
    "# Stability\n\nStability is the number of days until recall of a concept drops to "
    "ninety percent. It is the quantity the scheduler grows on every successful review."
)


@pytest.fixture(autouse=True)
def _clear_todays_turns():
    """Delete this study day's tutor messages before each test in this file.

    The day-wide cap counts every learner row written today across every concept, and the
    whole suite shares one SQLite file. Without this, each successful turn in this file
    would push the next test closer to a cap it never asked to be near, and the file would
    start failing on nothing but its own length.

    Scoped to today's window rather than to the whole table, because test_tutor_context.py
    seeds rows at fixed dates in order to prove where the day boundary falls, and those are
    exactly the rows a blanket delete would take.
    """
    init_db()
    day_start, day_end = days.day_bounds()
    session = SessionLocal()
    try:
        session.query(models.TutorMessage).filter(
            models.TutorMessage.created_at >= day_start
        ).filter(models.TutorMessage.created_at < day_end).delete()
        session.commit()
    finally:
        session.close()


# --------------------------------------------------------------------------
# Stub providers
# --------------------------------------------------------------------------


class TutorProvider:
    """A well-formed tutor reply, with exact token counts and no price.

    `payload` is the raw dict the model is pretending to return, so a test can hand back a
    reply with an over-long aside or no answer at all without a second class per case.
    """

    name = "fake"
    model = "tutor-model"
    is_paid = False

    def __init__(self, payload: dict | None = None):
        self.calls = 0
        self.prompts: list[str] = []
        self.payload = payload if payload is not None else {
            "answer": "Grounded answer from your course.",
            "beyond": "A short aside your course does not cover.",
            "check": "What does it take in?",
        }

    def generate(self, system: str, prompt: str, max_tokens: int = 64000):
        self.calls += 1
        self.prompts.append(prompt)
        return LLMResult(text=json.dumps(self.payload), input_tokens=90, output_tokens=40)


class PaidTutorProvider(TutorProvider):
    """Same reply, but priced, so the spend cap has something to refuse."""

    name = "anthropic"
    model = "claude-opus-5"
    is_paid = True


class ExplodingProvider:
    """A provider that never answers at all: the transport half of the 502."""

    name = "fake"
    model = "exploding-model"
    is_paid = False

    def __init__(self):
        self.calls = 0

    def generate(self, system: str, prompt: str, max_tokens: int = 64000):
        self.calls += 1
        raise RuntimeError("provider exploded")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _seed(item_count: int = 2, content: str = LESSON_CONTENT) -> tuple[str, str, int]:
    """A course teaching one fresh concept. Returns (key, label, course_id).

    The label is unique per call because concept keys are global and the test database is
    shared across the suite: a fixed label would let one test's conversation decide another
    test's limits.
    """
    label = f"Tutor {uuid4().hex[:8]}"
    key = normalize_concept(label)
    session = SessionLocal()
    try:
        course = models.Course(title=f"Course on {label}", description="")
        module = models.Module(title="Module 1", position=0)
        lesson = models.Lesson(
            title=f"Lesson on {label}", position=0, content=content, concepts=[label]
        )
        for position in range(item_count):
            lesson.quiz_items.append(
                models.QuizItem(
                    question=f"Question {position} about {label}?",
                    kind="short",
                    options=[],
                    answer=f"expected-answer-{position}-{key}",
                    concept=label,
                )
            )
        module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.commit()
        return key, label, course.id
    finally:
        session.close()


def _seed_turns(key: str, count: int, when=None) -> None:
    """`count` learner turns already spent on this concept at `when`."""
    moment = days.day_bounds()[0] + timedelta(hours=1) if when is None else when
    session = SessionLocal()
    try:
        for index in range(count):
            session.add(
                models.TutorMessage(
                    concept_key=key,
                    concept_label=key,
                    role=tutor.LEARNER_ROLE,
                    content=f"seeded question {index}",
                    beyond="",
                    check_question="",
                    run_id="",
                    model="",
                    created_at=moment,
                )
            )
        session.commit()
    finally:
        session.close()


def _ask(client, key: str, message: str = "I do not understand this"):
    return client.post("/tutor/messages", json={"concept_key": key, "message": message})


def _rows(key: str) -> list[models.TutorMessage]:
    session = SessionLocal()
    try:
        return tutor.conversation(session, key)
    finally:
        session.close()


def _message_count() -> int:
    session = SessionLocal()
    try:
        return session.query(func.count(models.TutorMessage.id)).scalar() or 0
    finally:
        session.close()


def _tutor_call_count() -> int:
    session = SessionLocal()
    try:
        return (
            session.query(func.count(models.LlmCall.id))
            .filter(models.LlmCall.stage == tutor.TUTOR_STAGE)
            .scalar()
            or 0
        )
    finally:
        session.close()


def _newest_tutor_call() -> models.LlmCall | None:
    session = SessionLocal()
    try:
        return (
            session.query(models.LlmCall)
            .filter(models.LlmCall.stage == tutor.TUTOR_STAGE)
            .order_by(models.LlmCall.id.desc())
            .first()
        )
    finally:
        session.close()


def _table_counts() -> dict[str, int]:
    """One row count per table in the schema, for asking what a request actually wrote."""
    session = SessionLocal()
    try:
        return {
            table.name: session.execute(select(func.count()).select_from(table)).scalar()
            for table in Base.metadata.sorted_tables
        }
    finally:
        session.close()


# --------------------------------------------------------------------------
# A turn, end to end
# --------------------------------------------------------------------------


def test_a_question_the_material_answers_comes_back_grounded_with_no_aside(client, monkeypatch):
    """AC 1, through the offline fixture rather than a stub written to pass it.

    The fixture reads the real prompt, so this is also the check that the tutor stage
    reaches the provider recognizably: a prompt that stopped matching TUTOR_MARKER would
    fall through to the lesson branch and fail to parse here.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    key, label, _ = _seed()

    answered = _ask(client, key, "I do not understand this")

    assert answered.status_code == 200, answered.json()
    body = answered.json()
    assert body["concept_key"] == key
    assert body["concept_label"] == label
    assert body["reply"]["answer"].strip()
    assert body["reply"]["beyond"] is None
    assert "does not cover" not in body["reply"]["answer"]


def test_a_question_the_material_does_not_cover_says_so_and_puts_the_rest_beyond(
    client, monkeypatch
):
    """AC 2. Both halves matter, and the second is the one that can be got wrong quietly.

    A reply that adds an aside while its answer carries on explaining from the course is
    two registers contradicting each other, and the learner is only shown the split, not
    the contradiction. So this asserts that the answer says where the course stops AND
    that the ungrounded part is non-empty.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    key, _, _ = _seed()

    answered = _ask(client, key, "What lies beyond what this lesson taught?")

    assert answered.status_code == 200, answered.json()
    reply = answered.json()["reply"]
    assert reply["beyond"].strip()
    assert "does not cover" in reply["answer"]


def test_a_check_question_carries_at_most_one_question(client, monkeypatch):
    """AC 5. Its job is to interrupt the nod of recognition, and two questions is a quiz.

    Asserted against the fixture's reply and against the instruction that asks for it,
    because the second is the only half a live model reads.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    key, _, _ = _seed()

    reply = _ask(client, key).json()["reply"]

    assert reply["check"].count("?") == 1
    assert 'ask ONE short recall question in "check"' in tutor.TUTOR_SYSTEM


def test_a_long_aside_is_truncated_at_a_sentence_boundary_and_not_rejected(client, monkeypatch):
    """AC 4. The grounded answer is the part the learner asked for, and an aside that ran
    long is no reason to throw it away."""
    monkeypatch.setattr(
        main,
        "get_provider",
        lambda: TutorProvider(
            {"answer": "The grounded half.", "beyond": ("x" * 150 + ". ") * 4}
        ),
    )
    key, _, _ = _seed()

    answered = _ask(client, key)

    assert answered.status_code == 200, answered.json()
    reply = answered.json()["reply"]
    assert reply["answer"] == "The grounded half."
    assert len(reply["beyond"]) <= tutor.BEYOND_MAX_CHARS
    # A sentence boundary, not a hard cut: the ellipsis is what _hard_cut leaves behind.
    assert reply["beyond"].endswith(".")
    assert not reply["beyond"].endswith("...")


def test_the_two_rows_come_back_in_the_one_shape_both_endpoints_render(client, monkeypatch):
    """One shape, discriminated on role, with the register split present on every row.

    A learner row carries its text under `content` and a tutor row under `answer`, never
    both: they are the same column, and a payload carrying it twice is a second copy that
    can disagree with the first.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _, _ = _seed()

    body = _ask(client, key, "why does this work").json()

    keys = {"id", "role", "content", "answer", "beyond", "check", "model", "created_at"}
    assert set(body["learner"]) == keys
    assert set(body["reply"]) == keys

    learner = body["learner"]
    assert learner["role"] == "learner"
    assert learner["content"] == "why does this work"
    assert learner["answer"] is None
    assert learner["beyond"] is None
    assert learner["check"] is None
    assert learner["model"] is None

    reply = body["reply"]
    assert reply["role"] == "tutor"
    assert reply["content"] is None
    assert reply["answer"] == "Grounded answer from your course."
    assert reply["beyond"] == "A short aside your course does not cover."
    assert reply["check"] == "What does it take in?"
    assert reply["model"] == "tutor-model"
    assert learner["id"] < reply["id"]


def test_the_limits_are_recomputed_after_the_insert(client, monkeypatch):
    """The turn just spent is already counted, so the learner is never shown a budget the
    next request will disagree with."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _, _ = _seed()
    _seed_turns(key, 3)

    limits = _ask(client, key).json()["limits"]

    assert limits["concept_used"] == 4
    assert limits["day_used"] == 4
    assert limits["concept_limit"] == tutor.CONCEPT_TURNS_PER_DAY
    assert limits["day_limit"] == tutor.DAY_TURNS
    assert limits["resets_at"] is not None


def test_a_concept_with_no_review_card_is_answered_rather_than_404ed(client, monkeypatch):
    """A concept met on the concept map and never quizzed on has no card, and refusing it
    would be a 404 for something that plainly exists."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _, _ = _seed()

    session = SessionLocal()
    try:
        assert review.get_card(session, key) is None
    finally:
        session.close()

    assert _ask(client, key).status_code == 200


def test_each_successful_turn_writes_exactly_one_llm_call_with_the_tutor_stage(
    client, monkeypatch
):
    """AC 22. One turn is one call: no corrective retry, and no second call for the aside."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _, _ = _seed()
    before = _tutor_call_count()

    assert _ask(client, key).status_code == 200

    assert _tutor_call_count() == before + 1
    call = _newest_tutor_call()
    assert call.stage == tutor.TUTOR_STAGE
    # The row is tied to the reply it paid for, which is what makes a transcript
    # traceable back to its cost.
    assert call.run_id == _rows(key)[-1].run_id


# --------------------------------------------------------------------------
# What a failed turn leaves behind, which is nothing
# --------------------------------------------------------------------------


def test_a_reply_with_no_answer_is_a_502_that_writes_no_rows_at_all(client, monkeypatch):
    """AC 3, and the reason both rows are built after the parse rather than around it.

    A reply carrying only an aside is a confident paragraph of general knowledge with the
    heading that would have said it was not from the course now standing over nothing. The
    turn is refused, and the learner's question is not left in the transcript unanswered.
    """
    provider = TutorProvider({"beyond": "general knowledge only", "check": "and?"})
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()
    messages_before = _message_count()
    calls_before = _tutor_call_count()

    answered = _ask(client, key)

    assert answered.status_code == 502
    assert provider.calls == 1
    assert _message_count() == messages_before
    assert _rows(key) == []
    # The tokens were spent, so the meter still records them, exactly as in
    # remediation.generate_note. That is what keeps a run of unparseable replies visible
    # on /usage instead of silently free.
    assert _tutor_call_count() == calls_before + 1


def test_a_provider_that_never_answers_writes_no_rows_either(client, monkeypatch):
    """The transport half of the same promise. Logged apart from the schema case, because
    the two need opposite fixes."""
    provider = ExplodingProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()
    messages_before = _message_count()

    answered = _ask(client, key)

    assert answered.status_code == 502
    assert provider.calls == 1
    assert _message_count() == messages_before


def test_a_failed_turn_does_not_spend_one(client, monkeypatch):
    """The corollary the learner actually feels: a turn that produced nothing is not
    charged against the twelve, so retrying is possible rather than punished."""
    monkeypatch.setattr(main, "get_provider", lambda: ExplodingProvider())
    key, _, _ = _seed()

    assert _ask(client, key).status_code == 502

    session = SessionLocal()
    try:
        assert tutor.turn_counts(session, key).concept_used == 0
    finally:
        session.close()


# --------------------------------------------------------------------------
# The requests that never reach a model
# --------------------------------------------------------------------------


@pytest.mark.parametrize("message", ["", "   ", "\n\t "])
def test_an_empty_message_is_refused_before_anything_else(client, monkeypatch, message):
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    answered = _ask(client, key, message)

    assert answered.status_code == 422
    assert answered.json()["detail"]["error"] == "message_empty"
    assert provider.calls == 0


def test_a_message_over_the_cap_is_refused_before_the_provider_is_called(client, monkeypatch):
    """AC 17. Past this length it is not a question, it is a document, and a document
    belongs in course generation where it is chunked and paid for deliberately."""
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    answered = _ask(client, key, "q" * (tutor.MAX_MESSAGE_CHARS + 1))

    assert answered.status_code == 422
    assert answered.json()["detail"]["error"] == "message_too_long"
    assert provider.calls == 0
    assert _rows(key) == []


def test_a_message_exactly_at_the_cap_is_accepted(client, monkeypatch):
    """The bound is inclusive. Without this the off-by-one above is invisible."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _, _ = _seed()

    assert _ask(client, key, "q" * tutor.MAX_MESSAGE_CHARS).status_code == 200


def test_a_concept_with_no_material_is_refused_with_the_shared_copy(client, monkeypatch):
    """Nothing was sent and nothing was spent, and answering it as a model failure would
    invite a retry that can only fail the same way."""
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)

    answered = _ask(client, normalize_concept(f"Untaught {uuid4().hex[:8]}"))

    assert answered.status_code == 422
    detail = answered.json()["detail"]
    assert detail["error"] == "no_material"
    assert detail["message"] == main.NO_MATERIAL_MESSAGE
    assert provider.calls == 0


def test_the_spend_cap_surfaces_as_402_with_both_figures(client, monkeypatch):
    """AC 18. The cap is checked before the call, so the refusal costs nothing either."""
    provider = PaidTutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    session = SessionLocal()
    try:
        spent = metering.total_spend(session)
    finally:
        session.close()
    # Already at the cap, whatever the rest of the suite has spent.
    monkeypatch.setenv("STUDYFORGE_COST_LIMIT_USD", str(spent))

    answered = _ask(client, key)

    assert answered.status_code == 402
    detail = answered.json()["detail"]
    assert detail["error"] == "cost_limit_exceeded"
    assert detail["limit_usd"] == pytest.approx(spent)
    assert detail["spent_usd"] == pytest.approx(spent)
    assert provider.calls == 0
    assert _rows(key) == []


# --------------------------------------------------------------------------
# The daily budget
# --------------------------------------------------------------------------


def test_the_thirteenth_turn_on_one_concept_is_refused_and_costs_nothing(client, monkeypatch):
    """AC 14. The per-concept cap stops one confusing idea from consuming the whole day."""
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()
    _seed_turns(key, tutor.CONCEPT_TURNS_PER_DAY)

    answered = _ask(client, key)

    assert answered.status_code == 409
    detail = answered.json()["detail"]
    assert detail["error"] == "concept_turn_limit"
    assert detail["limits"]["concept_used"] == tutor.CONCEPT_TURNS_PER_DAY
    assert detail["limits"]["resets_at"] is not None
    assert provider.calls == 0
    # The refusal wrote nothing either: the twelve seeded turns are all there is.
    assert len(_rows(key)) == tutor.CONCEPT_TURNS_PER_DAY


def test_the_forty_first_turn_of_the_day_is_refused_whatever_the_concept(client, monkeypatch):
    """AC 15. Without a day-wide cap a learner could sit at the per-concept limit on
    twenty concepts at once, and the per-concept number would bound nothing."""
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    fresh, _, _ = _seed()
    # Spread across enough other concepts to pass the day cap while every one of them
    # sits at its own. The concept being asked about has spent nothing.
    for _ in range(tutor.DAY_TURNS // tutor.CONCEPT_TURNS_PER_DAY + 1):
        other, _, _ = _seed()
        _seed_turns(other, tutor.CONCEPT_TURNS_PER_DAY)

    answered = _ask(client, fresh)

    assert answered.status_code == 409
    detail = answered.json()["detail"]
    assert detail["error"] == "daily_turn_limit"
    assert detail["limits"]["day_used"] >= tutor.DAY_TURNS
    # This concept has spent nothing, so the concept cap cannot be what refused it.
    assert detail["limits"]["concept_used"] == 0
    assert provider.calls == 0


def test_the_day_cap_is_reported_even_when_the_concept_cap_is_also_reached(client, monkeypatch):
    """The precedence, and the reason for it.

    Both caps are over here. Naming the concept cap would be true and useless: it sends
    the learner to another concept to be refused there as well, having been told the
    problem was this one. The day is the wider fact, so it is the one reported.
    """
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()
    _seed_turns(key, tutor.DAY_TURNS)

    detail = _ask(client, key).json()["detail"]

    assert detail["error"] == "daily_turn_limit"
    assert detail["limits"]["concept_used"] >= tutor.CONCEPT_TURNS_PER_DAY
    assert provider.calls == 0


def test_a_cap_refusal_carries_the_limits_and_nothing_else(client, monkeypatch):
    """Unlike the practice and re-teaching 409s, this one sends back no conversation.

    The conversation is already on screen and this refusal did not change it, so a copy
    travelling with the error is a second copy that can disagree with the first. What
    changed is the limits.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _, _ = _seed()
    _seed_turns(key, tutor.CONCEPT_TURNS_PER_DAY)

    detail = _ask(client, key).json()["detail"]

    assert set(detail) == {"error", "message", "limits"}
    assert set(detail["limits"]) == {
        "concept_used",
        "concept_limit",
        "day_used",
        "day_limit",
        "resets_at",
    }


def test_the_caps_reset_at_the_study_day_boundary_and_not_at_midnight(client, monkeypatch):
    """AC 16. Someone who sits down at 23:30 and finishes at 00:40 did one study session,
    and a midnight reset would hand them a fresh set of turns halfway through it."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    day_start, _ = days.day_bounds()

    spent_today, _, _ = _seed()
    _seed_turns(spent_today, tutor.CONCEPT_TURNS_PER_DAY, when=day_start)
    assert _ask(client, spent_today).status_code == 409

    spent_yesterday, _, _ = _seed()
    _seed_turns(
        spent_yesterday,
        tutor.CONCEPT_TURNS_PER_DAY,
        when=day_start - timedelta(seconds=1),
    )
    answered = _ask(client, spent_yesterday)

    assert answered.status_code == 200, answered.json()
    assert answered.json()["limits"]["concept_used"] == 1
    # And what the learner is told about the reset says 04:00 rather than 00:00. Read as
    # an hour rather than compared against days.day_bounds(), which is the function the
    # endpoint already called: that comparison would hold against a midnight boundary too,
    # because both sides of it would have moved together.
    resets_at = datetime.fromisoformat(answered.json()["limits"]["resets_at"])
    assert resets_at.astimezone(days.local_tz()).hour == days.DAY_START_HOUR


# --------------------------------------------------------------------------
# Reading the conversation back
# --------------------------------------------------------------------------


def _conversation(client, key: str):
    return client.get("/tutor/conversation", params={"concept_key": key})


def test_the_conversation_reads_back_oldest_first_in_the_shape_the_post_returned(
    client, monkeypatch
):
    """The POST hands back two rows and the client appends them to this list, so the two
    have to render the same. A tutor message reloaded without its register split would be
    presented as course content it never was."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, label, _ = _seed()
    first = _ask(client, key, "first question").json()
    second = _ask(client, key, "second question").json()

    body = _conversation(client, key).json()

    assert body["concept_key"] == key
    assert body["concept_label"] == label
    assert [row["role"] for row in body["messages"]] == ["learner", "tutor", "learner", "tutor"]
    assert body["messages"][0] == first["learner"]
    assert body["messages"][1] == first["reply"]
    assert body["messages"][2] == second["learner"]
    assert body["messages"][3] == second["reply"]
    assert body["last_message_at"] == second["reply"]["created_at"]


def test_a_learner_row_read_back_still_carries_a_null_register_split(client, monkeypatch):
    """The half of "one shape" that a reader could otherwise construct wrongly."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _, _ = _seed()
    _ask(client, key)

    learner, reply = _conversation(client, key).json()["messages"]

    assert learner["beyond"] is None and learner["check"] is None
    assert reply["beyond"] and reply["check"]


def test_a_conversation_nobody_has_started_is_described_rather_than_refused(client):
    """Any concept_key answers 200, like get_remedial_practice. The Today screen fans this
    out per concept, and a 4xx per concept would make a page of ordinary answers look
    broken."""
    body = _conversation(client, normalize_concept(f"Never asked {uuid4().hex[:8]}")).json()

    assert body["messages"] == []
    assert body["last_message_at"] is None
    assert body["limits"]["concept_used"] == 0


def test_a_conversation_is_scoped_to_its_concept(client, monkeypatch):
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    first, _, _ = _seed()
    second, _, _ = _seed()
    _ask(client, first, "about the first")
    _ask(client, second, "about the second")

    body = _conversation(client, first).json()

    assert [row["content"] for row in body["messages"] if row["role"] == "learner"] == [
        "about the first"
    ]


def test_the_get_reports_the_limits_the_post_refuses_on(client, monkeypatch):
    """One arithmetic, read by both endpoints. Remedial practice nearly shipped a bug
    because its POST and its GET each derived the session separately."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _, _ = _seed()
    _seed_turns(key, tutor.CONCEPT_TURNS_PER_DAY)

    described = _conversation(client, key).json()["limits"]
    refused = _ask(client, key).json()["detail"]["limits"]

    assert described == refused
    assert described["concept_used"] == described["concept_limit"]


def test_the_conversation_names_its_concept_after_the_courseware_is_gone(client, monkeypatch):
    """TutorMessage.concept_label exists for this, so the label is read off the rows.

    Looking the name up in the courseware would mean reading every lesson on a request a
    panel makes on open, and it would come back empty here anyway.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, label, course_id = _seed()
    _ask(client, key)

    session = SessionLocal()
    try:
        session.delete(session.get(models.Course, course_id))
        session.commit()
    finally:
        session.close()

    assert _conversation(client, key).json()["concept_label"] == label


# --------------------------------------------------------------------------
# What a conversation must not touch
# --------------------------------------------------------------------------


def _card_columns(session, key: str) -> dict:
    card = review.get_card(session, key)
    return {
        column.key: getattr(card, column.key)
        for column in sa_inspect(models.ReviewCard).mapper.column_attrs
    }


def _seed_reviewed_concept() -> tuple[str, str]:
    """A concept with a card, a rating history, and enough lapses to be flagged.

    Flagged on purpose: needs_attention feeds tutor.context, so this is the shape where
    the tutor reads the most about the learner and therefore has the most to move.
    """
    key, label, _ = _seed()
    session = SessionLocal()
    try:
        moment = review.now_utc() - timedelta(days=4)
        for rating in (fsrs.AGAIN, fsrs.AGAIN, fsrs.GOOD):
            review.record_review(session, key, label, rating, now=moment)
            moment += timedelta(days=1)
        session.commit()
    finally:
        session.close()
    return key, label


def test_a_full_exchange_leaves_review_tables_byte_identical(client, monkeypatch):
    """AC 7. A conversation is not a retrieval test, and nothing about it is a rating.

    Row counts alone would pass against an endpoint that rewrote a card in place, so every
    column of the card is compared as well.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _ = _seed_reviewed_concept()

    session = SessionLocal()
    try:
        before_counts = {
            table: session.execute(select(func.count()).select_from(table)).scalar()
            for table in (
                models.ReviewCard.__table__,
                models.ReviewLog.__table__,
                models.Attempt.__table__,
            )
        }
        before_card = _card_columns(session, key)
    finally:
        session.close()

    assert _ask(client, key, "why do I keep missing this").status_code == 200

    session = SessionLocal()
    try:
        after_counts = {
            table: session.execute(select(func.count()).select_from(table)).scalar()
            for table in (
                models.ReviewCard.__table__,
                models.ReviewLog.__table__,
                models.Attempt.__table__,
            )
        }
        after_card = _card_columns(session, key)
    finally:
        session.close()

    assert after_counts == before_counts
    assert after_card == before_card


def test_a_full_exchange_moves_no_figure_the_learner_is_shown(client, monkeypatch):
    """AC 8. The tutor may READ the mastery bucket and the missed-of count, which is what
    lets it choose where to start. Reading them must not be able to change them."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _ = _seed_reviewed_concept()
    # A fixed instant, so a figure that genuinely depends on the clock (retrievability,
    # what is due) cannot drift between the two reads and be mistaken for a write.
    now = review.now_utc()

    def _figures():
        session = SessionLocal()
        try:
            return (
                review.needs_attention(session, now),
                review.mastery_bucket(review.get_card(session, key), now),
                review.retention(session, now),
                review.day_streak(session, now),
                review.due_counts(session, now),
            )
        finally:
            session.close()

    before = _figures()
    assert _ask(client, key).status_code == 200

    assert _figures() == before


def test_the_tutor_request_path_writes_only_tutor_messages(client, monkeypatch):
    """AC 9, end to end: every table in the schema counted before and after one turn.

    Two tutor_messages, one llm_calls row, and nothing else anywhere. The llm_calls row is
    the meter's, and it is not the tutor writing about the learner: it records what the
    call cost, which is the same row every other stage writes.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _ = _seed_reviewed_concept()
    before = _table_counts()

    assert _ask(client, key).status_code == 200

    after = _table_counts()
    moved = {name: after[name] - before[name] for name in after if after[name] != before[name]}
    assert moved == {"tutor_messages": 2, "llm_calls": 1}


def test_the_tutor_endpoint_builds_no_row_but_a_tutor_message(client):
    """The static half of AC 9, on the request path's own source.

    test_the_context_module_writes_nothing covers app/tutor.py, which is all reads. This
    is the endpoint, which is the only place in the feature that writes at all, and a
    reviewer reading a diff is the other thing that would have to catch a stray row.
    """
    source = inspect.getsource(main.post_tutor_message)

    assert re.findall(r"models\.(\w+)\(", source) == ["TutorMessage", "TutorMessage"]
    for grader in ("_record_attempt", "record_review", "grade_lesson", "_grade("):
        assert grader not in source, f"{grader} on the tutor request path"
