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
from conftest import clear_todays_tutor_turns
from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect

from app import days, fsrs, main, metering, models, review, tutor
from app.concepts import normalize_concept
from app.db import Base, SessionLocal
from app.llm.base import LLMResult
from app.llm.fake_provider import FakeProvider

LESSON_CONTENT = (
    "# Stability\n\nStability is the number of days until recall of a concept drops to "
    "ninety percent. It is the quantity the scheduler grows on every successful review."
)


@pytest.fixture(autouse=True)
def _clear_todays_turns():
    """Every test in this file is about the tutor, so the day clears before each of them.

    Autouse is right HERE and wrong in test_usage_attribution.py: see
    clear_todays_tutor_turns in conftest.py for the rule and for why its two callers couple
    it differently.
    """
    clear_todays_tutor_turns()


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
        # Every system prompt this provider was handed, in order. The mode a turn was
        # SERVED in is not visible in the reply, so this is the only place a test can see
        # which of the two prompts the endpoint actually chose.
        self.systems: list[str] = []
        self.payload = payload if payload is not None else {
            "answer": "Grounded answer from your course.",
            "beyond": "A short aside your course does not cover.",
            "check": "What does it take in?",
        }

    def generate(self, system: str, prompt: str, max_tokens: int = 64000):
        self.calls += 1
        self.prompts.append(prompt)
        self.systems.append(system)
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


def _ask(client, key: str, message: str = "I do not understand this", mode=None):
    """One turn. `mode` OMITTED from the body entirely when it is None, not sent as
    "answer", because the default on the wire is what a client predating guided mode
    relies on and sending the value explicitly would never exercise it."""
    body = {"concept_key": key, "message": message}
    if mode is not None:
        body["mode"] = mode
    return client.post("/tutor/messages", json=body)


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

    keys = {"id", "role", "content", "answer", "beyond", "check", "ask", "model", "created_at"}
    assert set(body["learner"]) == keys
    assert set(body["reply"]) == keys

    learner = body["learner"]
    assert learner["role"] == "learner"
    assert learner["content"] == "why does this work"
    assert learner["answer"] is None
    assert learner["beyond"] is None
    assert learner["check"] is None
    assert learner["ask"] is None
    assert learner["model"] is None

    reply = body["reply"]
    assert reply["role"] == "tutor"
    assert reply["content"] is None
    assert reply["answer"] == "Grounded answer from your course."
    assert reply["beyond"] == "A short aside your course does not cover."
    assert reply["check"] == "What does it take in?"
    # Null on an ANSWER-MODE tutor row, not "". The panel draws a heading over this, and
    # an empty string there would ask the learner to finish a reply that is complete.
    assert reply["ask"] is None
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


class ProgrammingErrorProvider:
    """A provider that raises the way a BUG raises, rather than the way a network does."""

    name = "fake"
    model = "buggy-model"
    is_paid = False

    def __init__(self):
        self.calls = 0

    def generate(self, system: str, prompt: str, max_tokens: int = 64000):
        self.calls += 1
        raise TypeError("parse_reply() missing 1 required positional argument: 'mode'")


def test_a_programming_error_is_not_reported_as_a_provider_failure(client, monkeypatch):
    """The broad `except Exception` around the provider call used to swallow this.

    It answered 502 and logged "the provider call failed", which sends whoever reads it to
    the network for a bug three lines above. That is not hypothetical: parse_reply takes
    `mode` with NO DEFAULT precisely so a call site that forgets it fails loudly, and the
    TypeError that produces is raised inside that try block. The mechanism worked in the
    test suite, where the caller's own tests went red, and degraded to a misleading 502 in
    production, which is the half nobody would have seen.

    TypeError, AttributeError and NameError are re-raised now, so the error reaches the
    framework with its traceback. TestClient re-raises server exceptions, so this asserts
    the exception rather than a status code, which IS the behaviour under test.

    Nothing has been added to the session at that point, so "a failed turn writes nothing"
    is unaffected by which of the two paths a failure takes; the row counts below say so.
    """
    provider = ProgrammingErrorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()
    before = _message_count()

    with pytest.raises(TypeError):
        _ask(client, key)

    assert provider.calls == 1
    assert _message_count() == before
    assert _rows(key) == []


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
    # The message and the key set are pinned because all three metered surfaces render
    # this payload through one formatter on the way to the learner. A site that drifted
    # would not raise anywhere: it would print the wrong sentence about their own money.
    # See test_usage_api.py for the generation and re-teaching halves of the same claim.
    assert detail["message"] == "LLM spend limit reached"
    assert set(detail) == {"error", "message", "limit_usd", "spent_usd"}
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
    # And the other half of the distinction: here there ARE other concepts to go to, so
    # the sentence must say so. See the day-cap test for why this is asserted as a phrase.
    assert "Other concepts still have" in detail["message"]
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
    # The sentence has to say the day is gone. A phrase rather than the whole string, so
    # a copy edit does not break the test but exchanging the two bodies does: told
    # "other concepts still have questions left" here, the learner goes to another
    # concept to be refused there too, which is what the split exists to prevent.
    assert "across every concept" in detail["message"]
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
    # The code AND the sentence, because this is the case where a learner who is out for
    # the day is most likely to be handed the concept sentence and sent looking.
    assert "across every concept" in detail["message"]
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


# --------------------------------------------------------------------------
# Guided mode: the run, the fade, and the one place the mode is decided
# --------------------------------------------------------------------------
#
# WHAT IS ON TRIAL HERE. Guided mode is a partial answer with the last move withheld, and
# every way it can be got wrong is silent. A reply prompted to withhold but parsed in
# answer mode drops `ask` and hands the learner a finished answer, which renders perfectly.
# A run counted as "guided replies today" rather than as CONSECUTIVE ones caps the wrong
# thing and nothing raises. A guided-state block computed before the insert is off by one
# for exactly the request the learner is about to make. None of the three has a symptom
# that a person looking at the panel would recognise as a bug.
#
# Written as mutation tests where it matters. Confirmed by making the change and watching
# the right test go red:
#   - count non-consecutive guided replies -> test_an_answered_turn_in_the_middle_...
#   - decide the mode a second time from body.mode instead of threading the one value ->
#     both halves of test_every_consumer_follows_the_one_mode_decision
#   - compute the guided block before the insert -> test_the_guided_block_is_computed_...

GUIDED_REPLY = {
    "answer": "Everything your course gives you, carried up to the last move.",
    "ask": "What is the last move?",
}


def _guided_run(key: str) -> int:
    session = SessionLocal()
    try:
        return tutor.guided_run(session, key)
    finally:
        session.close()


def _seed_reply(key: str, ask: str, when=None) -> None:
    """One tutor row with (or without) a withheld move, at `when`.

    A tutor row rather than a learner one, because the run is counted off replies. Seeded
    directly so a test can put a run BEFORE the study-day boundary, which no sequence of
    requests can do.
    """
    moment = days.day_bounds()[0] + timedelta(hours=1) if when is None else when
    session = SessionLocal()
    try:
        session.add(
            models.TutorMessage(
                concept_key=key,
                concept_label=key,
                role=tutor.TUTOR_ROLE,
                content="a grounded answer",
                beyond="",
                check_question="" if ask else "what does it take in?",
                ask=ask,
                run_id="",
                model="",
                created_at=moment,
            )
        )
        session.commit()
    finally:
        session.close()


def test_the_run_cap_is_the_number_of_rungs():
    """One fact written twice, pinned together. A third rung added to the fade with
    GUIDED_RUN_MAX left at 2 would stop the fade one rung short of itself, and nothing
    else in the suite compares the two."""
    assert tutor.GUIDED_RUN_MAX == len(tutor.GUIDED_RUNGS)


def test_a_request_with_no_mode_is_answered_exactly_as_it_was_before(client, monkeypatch):
    """AC 12, and the compatibility promise this whole feature rests on.

    A client written before guided mode existed sends no `mode` key at all. It has to get
    the behaviour it already had: an answer-mode prompt, a `check` question, no `ask`, and
    a response that says so. Sending "answer" explicitly would not test this, which is why
    _ask omits the key entirely when it is not asked for.
    """
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    body = _ask(client, key).json()

    assert body["mode"] == tutor.MODE_ANSWER
    assert body["reply"]["check"] == "What does it take in?"
    assert body["reply"]["ask"] is None
    assert provider.systems[-1] == tutor.TUTOR_SYSTEM


@pytest.mark.parametrize("mode", ["socratic", "", "ANSWER", "guided ", "hint"])
def test_a_mode_nobody_answers_in_is_refused_before_the_provider_is_called(
    client, monkeypatch, mode
):
    """Hand rolled rather than a Pydantic Literal, so the detail shape matches the other
    tutor errors. A Literal would answer 422 too, with a list of validation objects under
    `detail`, and a client parsing this route's errors would meet two unrelated shapes."""
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    answered = _ask(client, key, mode=mode)

    assert answered.status_code == 422
    detail = answered.json()["detail"]
    assert detail["error"] == "invalid_mode"
    assert detail["message"] == main.INVALID_MODE_MESSAGE
    assert set(detail) == {"error", "message"}
    assert provider.calls == 0
    assert _rows(key) == []


def _post_mode(client, key: str, mode):
    """POST with `mode` PRESENT and set to exactly this JSON value, whatever its type.

    Not _ask, which omits the key when mode is None. Omission and an explicit null are
    different requests and this file has to be able to send both.
    """
    return client.post(
        "/tutor/messages",
        json={"concept_key": key, "message": "I do not understand this", "mode": mode},
    )


# A mode of the wrong TYPE. Several types rather than one, because the interesting
# implementations of this fix are the ones that handle SOME of them: an annotation widened
# to str | int passes the integer case and fails every other row here, and that is exactly
# the mutation a single-case test would wave through. Containers and null are in for the
# same reason, since a hand-rolled isinstance check is easy to write for scalars alone.
_WRONG_TYPE_MODES = [7, None, [], {}, True, 1.5, ["guided"], {"mode": "guided"}]


def test_the_published_schema_declares_the_mode_type_and_its_legal_values():
    """What /docs tells a client, pinned, because it has already been lost once silently.

    Widening the annotation to Any to fix the refusal shape dropped `type` from the
    generated OpenAPI property, and nothing said so: the endpoint behaved correctly, every
    test passed, and the only casualty was the documentation. json_schema_extra puts it
    back and adds the legal VALUES, which no version of this field has ever advertised.

    THE LAST ASSERTION IS THE LOAD-BEARING ONE. The enum here DOCUMENTS and does not
    VALIDATE: pydantic hands `mode` through untouched, and app/main.py's hand-rolled check
    is still the only thing that refuses anything. Someone reading `enum` in the schema
    would reasonably assume otherwise and reach for a real Literal, which would restore
    exactly the bug this branch fixed, since pydantic would then reject a wrong value with
    its own validation array instead of invalid_mode. So the passthrough is asserted right
    here, next to the enum, rather than left to the endpoint tests to imply.

    The enum is compared against TUTOR_MODES rather than a literal list, so the docs cannot
    drift from the values the server actually accepts.
    """
    prop = main.TutorQuestion.model_json_schema()["properties"]["mode"]

    assert prop["type"] == "string"
    assert prop["enum"] == list(tutor.TUTOR_MODES)
    assert prop["default"] == tutor.MODE_ANSWER

    assert main.TutorQuestion(concept_key="k", message="m", mode=7).mode == 7, (
        "the schema enum has started validating, so a wrong mode is now rejected before "
        "the endpoint's own check runs and comes back in the framework's shape again"
    )


@pytest.mark.parametrize("mode", _WRONG_TYPE_MODES, ids=repr)
def test_a_mode_of_the_wrong_type_is_refused_exactly_like_one_of_the_wrong_value(
    client, monkeypatch, mode
):
    """QA's finding, and the assertion is the EQUIVALENCE rather than the status code.

    A wrong type and a wrong value are the same mistake from the caller's side, so the two
    refusals are compared body to body rather than each being checked against a shape.
    That is the property the fix is for: before it, a `mode` of the wrong type never
    reached this endpoint's code at all, because pydantic rejected it first, and the
    learner would have been shown "Input should be a valid string" out of a raw array of
    validation objects.

    A shape check alone would pass against a fix that produced a DIFFERENT well-formed
    error for the type case, which would still leave a client with two paths to write.
    """
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    wrong_type = _post_mode(client, key, mode)
    wrong_value = _post_mode(client, key, "socratic")

    assert wrong_type.status_code == wrong_value.status_code == 422
    assert wrong_type.json() == wrong_value.json()
    detail = wrong_type.json()["detail"]
    assert detail == {"error": "invalid_mode", "message": main.INVALID_MODE_MESSAGE}
    assert provider.calls == 0
    assert _rows(key) == []


def test_omitting_mode_and_sending_null_are_different_requests(client, monkeypatch):
    """The third case, and the one where treating null as absent would be wrong.

    Omission is a client that predates guided mode, and it has to keep working untouched:
    answer mode, a complete reply, no withheld move. An explicit null is a client that
    meant to say something and said nothing, which is a bug in the caller worth reporting
    rather than a request to be quietly defaulted. Coercing null to "answer" would make
    that bug invisible for exactly as long as it took to ship.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    key, _, _ = _seed()

    omitted = _ask(client, key)
    explicit_null = _post_mode(client, key, None)

    assert omitted.status_code == 200, omitted.json()
    assert omitted.json()["mode"] == tutor.MODE_ANSWER
    assert omitted.json()["reply"]["ask"] is None

    assert explicit_null.status_code == 422
    assert explicit_null.json()["detail"] == {
        "error": "invalid_mode",
        "message": main.INVALID_MODE_MESSAGE,
    }


@pytest.mark.parametrize("field", ["concept_key", "message"])
def test_other_fields_answer_a_wrong_type_in_the_one_shape_too(client, monkeypatch, field):
    """THE BOUNDARY TEST THAT USED TO BE HERE HAS BEEN RETIRED, AND THIS REPLACES IT.

    It asserted the OPPOSITE: that concept_key and message still answered a wrong type
    with the framework's raw array, because at the time only `mode` had been widened. It
    was not there to defend that behaviour. It was there so that changing it would have to
    be somebody's decision rather than a diff nobody noticed, and it said so.

    That decision has now been taken. app/main.py carries a RequestValidationError handler
    that puts every framework 422 in the {error, message} shape, on every route, so the
    old assertion pins exactly the thing that was deliberately changed and would now be a
    test defending a retired design. Its replacement makes the same two fields prove the
    new invariant instead, at the same place in the file, so the history is legible from
    the diff.

    See test_error_shape.py for the app-wide version of this claim, which is where it
    belongs: an invariant that holds across three request bodies should not be asserted
    only on the tutor's.
    """
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()
    body = {"concept_key": key, "message": "I do not understand this"}
    body[field] = 7

    answered = client.post("/tutor/messages", json=body)

    assert answered.status_code == 422
    detail = answered.json()["detail"]
    assert set(detail) == {"error", "message"}, "a framework 422 escaped the shared shape"
    assert detail["error"] == main.INVALID_REQUEST_ERROR
    assert field in detail["message"], "the message has to say which field was wrong"
    assert provider.calls == 0


def test_the_mode_check_sits_third_in_the_precedence_and_not_first(client, monkeypatch):
    """The order the endpoint fixes, at the two boundaries the new entry created.

    An empty message and an over-long one are both wrong about the MESSAGE, and they are
    decided first because they are cheaper and because a client that sent both a bad mode
    and no message needs to hear about the message. A concept with no material is decided
    AFTER, because that takes a read, and a request naming a mode this server does not
    have is malformed whatever the concept turns out to hold.
    """
    provider = TutorProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    empty = _ask(client, key, "  ", mode="socratic").json()["detail"]
    too_long = _ask(client, key, "q" * (tutor.MAX_MESSAGE_CHARS + 1), mode="socratic")
    untaught = _ask(client, normalize_concept(f"Untaught {uuid4().hex[:8]}"), mode="socratic")

    assert empty["error"] == "message_empty"
    assert too_long.json()["detail"]["error"] == "message_too_long"
    assert untaught.json()["detail"]["error"] == "invalid_mode"
    assert provider.calls == 0


def test_a_guided_turn_withholds_a_move_and_carries_no_check(client, monkeypatch):
    """AC 1 and AC 2 on the served path: the answer is non-empty, `ask` is populated, and
    `check` is empty because parse_reply blanks it in this mode rather than because the
    prompt asked nicely. The provider sends both."""
    provider = TutorProvider({**GUIDED_REPLY, "check": "a recall question"})
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    body = _ask(client, key, "walk me through it", mode=tutor.MODE_GUIDED).json()

    assert body["mode"] == tutor.MODE_GUIDED
    reply = body["reply"]
    assert reply["answer"] == GUIDED_REPLY["answer"]
    assert reply["ask"] == GUIDED_REPLY["ask"]
    assert reply["check"] is None
    # And the model was actually prompted to withhold, rather than the field being
    # accepted off an answer-mode reply.
    assert "GIVE EVERYTHING BUT THE LAST MOVE" in provider.systems[-1]


def test_a_guided_reply_with_no_answer_is_a_502_that_writes_no_rows(client, monkeypatch):
    """AC 1's other half. A guided reply that is ONLY a question is the thing this whole
    feature must not become, so a reply carrying `ask` and no `answer` is refused exactly
    as an answer-mode reply with no answer is, and the learner's message is not left in
    the transcript with nothing under it."""
    provider = TutorProvider({"ask": "what is the last move?"})
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()
    before = _message_count()

    answered = _ask(client, key, mode=tutor.MODE_GUIDED)

    assert answered.status_code == 502
    assert provider.calls == 1
    assert _message_count() == before
    assert _rows(key) == []


def test_an_answer_mode_reply_never_carries_a_withheld_move(client, monkeypatch):
    """AC 2 mirrored, and the off-diagonal cell that matters here. A model that sends
    `ask` in answer mode is handing a withheld move to a learner who was just given the
    complete answer, and the server drops it rather than rendering a non sequitur."""
    provider = TutorProvider({"answer": "The whole answer.", "ask": "and the last move?"})
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    body = _ask(client, key, mode=tutor.MODE_ANSWER).json()

    assert body["mode"] == tutor.MODE_ANSWER
    assert body["reply"]["ask"] is None
    assert _rows(key)[-1].ask == ""


def test_the_run_grows_by_one_a_turn_and_the_third_request_is_answered(client, monkeypatch):
    """AC 3, end to end, which is the acceptance criterion this section exists for.

    The third guided request on the same concept in the same day is a 200 carrying a
    complete answer and mode "answer", NOT a refusal. The learner asked for help and gets
    help; below rung 2 there is nothing left to withhold that is still worth asking for.
    """
    provider = TutorProvider(GUIDED_REPLY)
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()
    assert _guided_run(key) == 0

    first = _ask(client, key, "one", mode=tutor.MODE_GUIDED).json()
    assert first["mode"] == tutor.MODE_GUIDED
    assert _guided_run(key) == 1

    second = _ask(client, key, "two", mode=tutor.MODE_GUIDED).json()
    assert second["mode"] == tutor.MODE_GUIDED
    assert _guided_run(key) == 2

    third_response = _ask(client, key, "three", mode=tutor.MODE_GUIDED)
    third = third_response.json()

    assert third_response.status_code == 200, third
    assert third["mode"] == tutor.MODE_ANSWER
    assert third["reply"]["ask"] is None
    assert third["reply"]["answer"]
    # The forced answer was prompted in answer mode, not merely parsed in it.
    assert "GIVE EVERYTHING BUT THE LAST MOVE" not in provider.systems[-1]
    # And it breaks the run, so the next guided request starts a fresh fade.
    assert _guided_run(key) == 0


def test_the_fade_advances_a_rung_per_turn(client, monkeypatch):
    """The two rungs are a fade, and serving rung 1 twice would be invisible in the reply.

    Rung 2 states the method for the final move outright and withholds only what it
    produces, so the two prompts differ by exactly one sentence and only the system prompt
    the provider was handed can say which one was sent.
    """
    provider = TutorProvider(GUIDED_REPLY)
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    _ask(client, key, "one", mode=tutor.MODE_GUIDED)
    _ask(client, key, "two", mode=tutor.MODE_GUIDED)

    assert provider.systems[0] == tutor.guided_system(1)
    assert provider.systems[1] == tutor.guided_system(2)
    assert provider.systems[0] != provider.systems[1]


def test_an_answered_turn_in_the_middle_resets_the_run(client, monkeypatch):
    """MUTATION TARGET. Count guided replies today rather than CONSECUTIVE ones and this
    is the test that goes red.

    Two guided turns with an answer-mode turn between them is a run of ONE, not two, and
    the difference is the whole definition. The naive count would put the learner on rung
    2 for a fade they restarted, and would cap them after two guided turns spread across
    an afternoon of ordinary questions.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider(GUIDED_REPLY))
    key, _, _ = _seed()

    _ask(client, key, "one", mode=tutor.MODE_GUIDED)
    assert _guided_run(key) == 1

    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    _ask(client, key, "just tell me", mode=tutor.MODE_ANSWER)
    assert _guided_run(key) == 0, "an answer-mode reply has an empty ask, so it ends a run"

    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider(GUIDED_REPLY))
    resumed = _ask(client, key, "three", mode=tutor.MODE_GUIDED).json()

    assert resumed["mode"] == tutor.MODE_GUIDED
    assert _guided_run(key) == 1
    assert resumed["guided"]["run"] == 1


def test_a_guided_turn_the_model_answered_outright_ends_the_run(client, monkeypatch):
    """AC 5. The run is counted off what was WRITTEN, not off what was requested.

    The guided prompt tells the model to leave `ask` out when the course does not cover
    the question, because withholding a step of something never taught is a riddle. The
    reply that comes back is an ordinary answer, so it ends the run, and a run counted off
    the requested mode would have charged the learner a rung for a turn that withheld
    nothing.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider(GUIDED_REPLY))
    key, _, _ = _seed()
    _ask(client, key, "one", mode=tutor.MODE_GUIDED)
    assert _guided_run(key) == 1

    monkeypatch.setattr(
        main,
        "get_provider",
        lambda: TutorProvider({"answer": "Your course does not cover that.", "beyond": "An aside."}),
    )
    body = _ask(client, key, "two", mode=tutor.MODE_GUIDED).json()

    assert body["mode"] == tutor.MODE_GUIDED, "the turn was still SERVED guided"
    assert body["reply"]["ask"] is None
    assert _guided_run(key) == 0
    assert body["guided"]["run"] == 0


def test_a_run_that_ended_before_the_study_day_boundary_does_not_count(client, monkeypatch):
    """AC 4. The fade does not survive the night, and 04:00 is where the night ends.

    A learner resuming mid-withholding on a concept they last saw yesterday would be asked
    for a move whose supporting explanation is a day and a scroll away. Seeded rather than
    driven through requests, because no sequence of requests can put rows before the
    boundary.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider(GUIDED_REPLY))
    day_start, _ = days.day_bounds()
    key, _, _ = _seed()

    _seed_reply(key, ask="yesterday's withheld move", when=day_start - timedelta(seconds=1))
    _seed_reply(key, ask="and another", when=day_start - timedelta(hours=2))

    assert _guided_run(key) == 0
    body = _ask(client, key, "today", mode=tutor.MODE_GUIDED).json()

    assert body["mode"] == tutor.MODE_GUIDED
    assert body["guided"]["run"] == 1


def test_the_run_is_scoped_to_its_concept(client, monkeypatch):
    """A fade on one concept says nothing about another. The learner is not two rungs
    into an idea they have not asked about yet."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider(GUIDED_REPLY))
    first, _, _ = _seed()
    second, _, _ = _seed()

    _ask(client, first, "one", mode=tutor.MODE_GUIDED)
    _ask(client, first, "two", mode=tutor.MODE_GUIDED)

    assert _guided_run(first) == tutor.GUIDED_RUN_MAX
    assert _guided_run(second) == 0
    assert _ask(client, second, "one", mode=tutor.MODE_GUIDED).json()["mode"] == tutor.MODE_GUIDED


def test_learner_rows_between_replies_do_not_break_the_run(client, monkeypatch):
    """A conversation alternates learner and tutor, so a run counted over EVERY row rather
    than over tutor rows would cap at one and rung 2 would be unreachable."""
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider(GUIDED_REPLY))
    key, _, _ = _seed()

    _ask(client, key, "one", mode=tutor.MODE_GUIDED)
    _ask(client, key, "two", mode=tutor.MODE_GUIDED)

    roles = [row.role for row in _rows(key)]
    assert roles == ["learner", "tutor", "learner", "tutor"]
    assert _guided_run(key) == 2


def test_every_consumer_follows_the_one_mode_decision(client, monkeypatch):
    """MUTATION TARGET, and the structural claim this design is for.

    tutor.effective_mode is stubbed to DISAGREE with the request, in both directions. Every
    consumer has to follow the stub: the system prompt sent, the field parse_reply keeps,
    the row written, and the mode reported. A second computation anywhere, reading
    body.mode or re-deriving the run, would follow the REQUEST instead and this fails.

    That is what makes "enforced in one place but not the other" structurally unavailable
    rather than something review has to notice. The specific failure it forecloses: the
    model is prompted to withhold, the parser is told to expect a complete answer, `ask` is
    dropped from a reply written around it, and the row that lands renders perfectly.
    """
    provider = TutorProvider({**GUIDED_REPLY, "check": "a recall question"})
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    monkeypatch.setattr(tutor, "effective_mode", lambda *a, **k: tutor.MODE_GUIDED)
    key, _, _ = _seed()

    # Asked for ANSWER, decided GUIDED.
    forced_guided = _ask(client, key, "one", mode=tutor.MODE_ANSWER).json()

    assert forced_guided["mode"] == tutor.MODE_GUIDED
    assert forced_guided["reply"]["ask"] == GUIDED_REPLY["ask"]
    assert forced_guided["reply"]["check"] is None
    assert "GIVE EVERYTHING BUT THE LAST MOVE" in provider.systems[-1]
    assert _rows(key)[-1].ask == GUIDED_REPLY["ask"]

    # Asked for GUIDED, decided ANSWER.
    monkeypatch.setattr(tutor, "effective_mode", lambda *a, **k: tutor.MODE_ANSWER)
    forced_answer = _ask(client, key, "two", mode=tutor.MODE_GUIDED).json()

    assert forced_answer["mode"] == tutor.MODE_ANSWER
    assert forced_answer["reply"]["ask"] is None
    assert forced_answer["reply"]["check"] == "a recall question"
    assert "GIVE EVERYTHING BUT THE LAST MOVE" not in provider.systems[-1]
    assert _rows(key)[-1].ask == ""


def test_the_withheld_move_replays_under_the_grounded_label(client, monkeypatch):
    """AC 6. Both halves, and each is a different mistake.

    Dropped from the replay, the learner's next message is their attempt at a question the
    model can no longer see, and it answers a question nobody asked. Replayed under the
    BEYOND label, the model is told on the next turn that its own grounded reasoning was
    an aside its course does not support, which is the one confusion in this conversation
    that nothing downstream can detect.
    """
    provider = TutorProvider(GUIDED_REPLY)
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    key, _, _ = _seed()

    _ask(client, key, "one", mode=tutor.MODE_GUIDED)
    _ask(client, key, "I think it is four", mode=tutor.MODE_GUIDED)

    replay = provider.prompts[-1]
    assert GUIDED_REPLY["ask"] in replay
    grounded = f"{tutor.GROUNDED_LABEL} {GUIDED_REPLY['answer']}\n{GUIDED_REPLY['ask']}"
    assert grounded in replay
    assert f"{tutor.BEYOND_LABEL} {GUIDED_REPLY['ask']}" not in replay


def test_the_guided_block_is_computed_after_the_insert(client, monkeypatch):
    """AC 7. MUTATION TARGET: read the run before the insert and this goes red.

    The turn just written is part of the run now, so the block the learner is shown has to
    be what their NEXT request will be measured against. Computed before the insert it is
    off by one for exactly the request they are about to make, and a panel would offer a
    third guided turn the server has already decided to answer outright.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider(GUIDED_REPLY))
    key, _, _ = _seed()

    first = _ask(client, key, "one", mode=tutor.MODE_GUIDED).json()["guided"]
    assert first == {"run": 1, "run_max": tutor.GUIDED_RUN_MAX, "available": True}

    second = _ask(client, key, "two", mode=tutor.MODE_GUIDED).json()["guided"]
    assert second == {"run": 2, "run_max": tutor.GUIDED_RUN_MAX, "available": False}

    # And "available: False" is exactly the prediction the next request confirms.
    third = _ask(client, key, "three", mode=tutor.MODE_GUIDED).json()
    assert third["mode"] == tutor.MODE_ANSWER


def test_the_get_reports_the_guided_state_the_post_serves(client, monkeypatch):
    """One arithmetic, read by both endpoints, for the reason `limits` is.

    A panel opening on an existing conversation has to know whether the work-it-out button
    will work before the learner presses it. Counting `ask` fields in the array it happens
    to hold would be a second definition of the run, living where it cannot be kept right.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider(GUIDED_REPLY))
    key, _, _ = _seed()
    _ask(client, key, "one", mode=tutor.MODE_GUIDED)
    posted = _ask(client, key, "two", mode=tutor.MODE_GUIDED).json()["guided"]

    described = _conversation(client, key).json()["guided"]

    assert described == posted
    assert described["available"] is False


def test_a_conversation_nobody_has_started_reports_guided_available(client):
    """The empty case, because a panel drawn on a concept nobody has asked about has to
    offer the button rather than hide it."""
    body = _conversation(client, normalize_concept(f"Never asked {uuid4().hex[:8]}")).json()

    assert body["guided"] == {"run": 0, "run_max": tutor.GUIDED_RUN_MAX, "available": True}


def test_just_tell_me_re_asks_in_answer_mode_and_the_transcript_keeps_both(client, monkeypatch):
    """AC 14, the server half.

    The learner asks the same question again in answer mode. THE DUPLICATE LEARNER ROW IS
    WRITTEN AND THE TURN IS SPENT, and both are accepted plainly rather than deduplicated:
    tutor_messages is append-only, the learner really did ask twice, and the second asking
    bought a model call that has to be visible on /usage. What the transcript shows
    afterwards is the guided reply AND the full answer, in order, which is the record of
    what actually happened.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider(GUIDED_REPLY))
    key, _, _ = _seed()
    question = "how do I finish this step"
    _ask(client, key, question, mode=tutor.MODE_GUIDED)

    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider())
    told = _ask(client, key, question, mode=tutor.MODE_ANSWER).json()

    assert told["mode"] == tutor.MODE_ANSWER
    assert told["limits"]["concept_used"] == 2, "the second asking spent a turn"
    rows = _rows(key)
    assert [row.role for row in rows] == ["learner", "tutor", "learner", "tutor"]
    assert rows[0].content == rows[2].content == question
    assert rows[1].ask == GUIDED_REPLY["ask"]
    assert rows[3].ask == ""
    assert rows[3].check_question


def test_the_guided_path_writes_only_tutor_messages(client, monkeypatch):
    """AC 10, counted per table across a whole guided run.

    Nothing in this path writes an attempt, a review log, or any column of a review card.
    A withheld move is not a quiz question and the learner's next message is not an answer
    to one, so nothing here is a rating and nothing may reach a schedule. Every column of
    the card is compared too, because row counts alone would pass against an endpoint that
    rewrote one in place.
    """
    monkeypatch.setattr(main, "get_provider", lambda: TutorProvider(GUIDED_REPLY))
    key, _ = _seed_reviewed_concept()

    session = SessionLocal()
    try:
        before_card = _card_columns(session, key)
    finally:
        session.close()
    before = _table_counts()

    assert _ask(client, key, "one", mode=tutor.MODE_GUIDED).status_code == 200
    assert _ask(client, key, "I think it is four", mode=tutor.MODE_GUIDED).status_code == 200

    after = _table_counts()
    session = SessionLocal()
    try:
        after_card = _card_columns(session, key)
    finally:
        session.close()

    moved = {name: after[name] - before[name] for name in after if after[name] != before[name]}
    assert moved == {"tutor_messages": 4, "llm_calls": 2}
    assert after_card == before_card
    for table in ("attempts", "review_logs", "review_cards"):
        assert after[table] == before[table]


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
