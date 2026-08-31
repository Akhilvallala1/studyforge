"""Remedial practice: a short bounded run at a concept, and what it must not touch.

Practice is a study event, not an assessment. It calls no model, writes no review log,
and changes no column of the card, so almost every test here is about something that
must NOT have moved. The interesting failures are all quiet ones: a session that
re-serves a question the learner just answered, a remedial answer that locks the same
item out of the next real review, or an elapsed time that leaks into the estimate for
how long a review session takes.

The other half is the attempts table, which nine readers share. Practice adds a new
source to it, and every one of those readers has an opinion about which sources it
counts; a test below pins each of them.

Every timestamp is built from days.day_bounds() rather than from datetime.now(), and
the study timezone is pinned. A test that subtracts an hour from "now" passes all day
and fails between midnight and 04:00 local, which on a UTC CI box is a real four hour
window in which the study day boundary sits between the two.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from test_remediation import _card_state, _notes, _seed_concept

from app import days, fsrs, models, remediation, review
from app.attempts import (
    GRADER,
    LESSON_QUIZ_SOURCE,
    _attempt_state,
    _attempts_for_item,
    _record_attempt,
    iso_utc,
)
from app.db import SessionLocal

PRACTICE = remediation.REMEDIAL_PRACTICE_SOURCE
WRONG = "not the answer"


@pytest.fixture(autouse=True)
def pinned_timezone(monkeypatch):
    """One study timezone for every test here, so 04:00 is the same instant everywhere.

    UTC rather than a real zone on purpose: days.local_tz falls back to UTC with a
    warning wherever tzdata is missing, so a test written around a non-UTC zone would
    mean one thing on a developer's machine and another in CI.
    """
    monkeypatch.setenv("STUDYFORGE_TIMEZONE", "UTC")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _practice_card(ratings=(fsrs.AGAIN, fsrs.AGAIN), item_count=1, **kwargs):
    """A card whose concept has an active note and `item_count` quiz items.

    The note is written directly rather than generated, because most of these tests
    are about what happens with no provider in the picture at all.
    """
    card_id, key, label = _seed_concept(list(ratings), item_count=item_count, **kwargs)
    session = SessionLocal()
    try:
        moment = review.now_utc()
        session.add(
            models.RemediationNote(
                card_id=card_id,
                concept_key=key,
                concept_label=label,
                content="## In simpler terms\n\nA shorter explanation.",
                source="llm",
                model="test-model",
                run_id=uuid4().hex,
                triggered_by=[],
                status=remediation.ACTIVE,
                cleared_at=None,
                cooldown_until=moment + timedelta(days=remediation.COOLDOWN_DAYS),
                created_at=moment,
            )
        )
        session.commit()
    finally:
        session.close()
    return card_id, key, label


def _items(concept_key):
    """(id, question, answer) for every quiz item testing the concept, lowest id first."""
    session = SessionLocal()
    try:
        items = review.concept_item_index(session).get(concept_key, [])
        return sorted((item.id, item.question, item.answer) for item in items)
    finally:
        session.close()


def _lesson_id(concept_key):
    session = SessionLocal()
    try:
        return review.concept_item_index(session)[concept_key][0].lesson_id
    finally:
        session.close()


def _attempts(concept_key, source=None):
    session = SessionLocal()
    try:
        query = session.query(models.Attempt).filter(models.Attempt.concept_key == concept_key)
        if source is not None:
            query = query.filter(models.Attempt.source == source)
        return query.order_by(models.Attempt.id).all()
    finally:
        session.close()


def _card_row(card_id):
    """Every column of the card, not a chosen few. The AC asks for the whole row."""
    session = SessionLocal()
    try:
        row = session.get(models.ReviewCard, card_id)
        return {attr.key: getattr(row, attr.key) for attr in inspect(models.ReviewCard).column_attrs}
    finally:
        session.close()


def _counts():
    session = SessionLocal()
    try:
        return {
            "review_logs": session.query(models.ReviewLog).count(),
            "llm_calls": session.query(models.LlmCall).count(),
        }
    finally:
        session.close()


def _card_logs(card_id):
    session = SessionLocal()
    try:
        return (
            session.query(models.ReviewLog).filter(models.ReviewLog.card_id == card_id).count()
        )
    finally:
        session.close()


def _state(client, card_id):
    response = client.get(f"/review/cards/{card_id}/remediation/practice")
    assert response.status_code == 200, response.text
    return response.json()


def _answer(client, card_id, item_id, answer, elapsed_ms=None):
    return client.post(
        f"/review/cards/{card_id}/remediation/practice",
        json={"item_id": item_id, "answer": answer, "elapsed_ms": elapsed_ms},
    )


def _walk(client, card_id, correct):
    """Answer whatever is served until the session ends. Returns the item ids served.

    `correct` decides whether each answer is the expected one, which is what picks
    which stop condition the session reaches.
    """
    concept_key = _state(client, card_id)["concept_key"]
    answers = {item_id: expected for item_id, _, expected in _items(concept_key)}
    served = []
    while True:
        state = _state(client, card_id)
        if state["item"] is None:
            return served
        item_id = state["item"]["id"]
        served.append(item_id)
        response = _answer(client, card_id, item_id, answers[item_id] if correct else WRONG)
        assert response.status_code == 200, response.text


def _clear_note(card_id):
    """Retire the note the way clear_resolved would, from outside the session."""
    session = SessionLocal()
    try:
        note = remediation.active_note(session, card_id)
        note.status = remediation.CLEARED
        note.cleared_at = review.now_utc()
        session.commit()
    finally:
        session.close()


def _move_practice_to(concept_key, moment):
    """Restamp today's practice rows, for testing the study day boundary."""
    session = SessionLocal()
    try:
        rows = (
            session.query(models.Attempt)
            .filter(models.Attempt.concept_key == concept_key)
            .filter(models.Attempt.source == PRACTICE)
            .all()
        )
        for row in rows:
            row.created_at = moment
        session.commit()
        return len(rows)
    finally:
        session.close()


# --------------------------------------------------------------------------
# The ordering, extracted from pick_items
# --------------------------------------------------------------------------


class _FakeItem:
    def __init__(self, item_id):
        self.id = item_id


def test_order_items_puts_never_asked_first_by_id():
    """Unseen items are partitioned out, not sorted against a sentinel date.

    A datetime.min sentinel would order the never-asked items among themselves by an
    invented timestamp instead of by id, which is a silent change to which question a
    learner is asked first.
    """
    day_start, _ = days.day_bounds()
    items = [_FakeItem(3), _FakeItem(1), _FakeItem(2)]
    last_seen = {1: day_start, 3: day_start - timedelta(days=2)}

    ordered = review.order_items(items, last_seen)

    assert [item.id for item in ordered] == [2, 3, 1]


def test_order_items_breaks_ties_on_id():
    day_start, _ = days.day_bounds()
    items = [_FakeItem(9), _FakeItem(4)]
    last_seen = {9: day_start, 4: day_start}

    assert [item.id for item in review.order_items(items, last_seen)] == [4, 9]


def test_pick_items_still_chooses_what_it_always_did(client):
    """pick_items delegates its preference now, and must answer exactly as before."""
    _, key, _ = _practice_card(item_count=3)
    items = _items(key)

    session = SessionLocal()
    try:
        assert review.pick_items(session, [key])[key].id == items[0][0]
        # Asking the lowest id rotates it to the back, so the next unseen one is chosen.
        _record_attempt(
            session, session.get(models.QuizItem, items[0][0]), WRONG, False, None, source=PRACTICE
        )
        assert review.pick_items(session, [key])[key].id == items[1][0]
        # A concept with no items at all is absent from the mapping rather than None.
        assert review.pick_items(session, ["no-such-concept"]) == {}
    finally:
        session.close()


# --------------------------------------------------------------------------
# The session state
# --------------------------------------------------------------------------


def test_a_card_with_a_note_and_items_is_ready(client):
    card_id, key, label = _practice_card(item_count=2)

    state = _state(client, card_id)

    assert set(state) == {
        "card_id",
        "concept_key",
        "concept_label",
        "status",
        "reason",
        "answered",
        "correct",
        "target_correct",
        "max_answers",
        "item",
        "results",
        "resets_at",
    }
    assert (state["status"], state["reason"]) == ("ready", None)
    assert (state["card_id"], state["concept_key"], state["concept_label"]) == (card_id, key, label)
    assert (state["answered"], state["correct"]) == (0, 0)
    assert (state["target_correct"], state["max_answers"]) == (2, 3)
    assert state["results"] == []
    assert state["resets_at"] is None
    # The question and nothing that gives its answer away.
    assert set(state["item"]) == {"id", "question", "kind", "options"}
    assert state["item"]["id"] == _items(key)[0][0]


def test_a_card_with_no_note_is_unavailable(client):
    """AC5: refused for a missing note, and refused before any item is chosen."""
    card_id, key, _ = _seed_concept([fsrs.AGAIN, fsrs.AGAIN], item_count=2)

    state = _state(client, card_id)

    assert (state["status"], state["reason"]) == ("unavailable", "no_note")
    assert state["item"] is None
    assert _items(key), "the concept does have items: the note is the only thing missing"


def test_a_concept_with_no_items_is_unavailable_for_a_different_reason(client):
    """AC6: distinct from the missing-note reason, even though a note could exist here."""
    card_id, key, _ = _practice_card(item_count=0)

    state = _state(client, card_id)

    assert (state["status"], state["reason"]) == ("unavailable", "no_items")
    assert state["reason"] != "no_note"
    assert state["item"] is None
    session = SessionLocal()
    try:
        # The lesson text is still there, so this is not "nothing to re-teach from".
        assert remediation.teaching_lessons(session, key)
    finally:
        session.close()


def test_an_unknown_card_is_a_404(client):
    assert client.get("/review/cards/999999/remediation/practice").status_code == 404
    assert _answer(client, 999999, 1, "x").status_code == 404


# --------------------------------------------------------------------------
# Answering
# --------------------------------------------------------------------------


def test_answering_writes_exactly_one_remedial_attempt(client):
    """AC3, plus the answer_review field names the feedback UI already binds to."""
    card_id, key, _ = _practice_card(item_count=2)
    item_id, _, expected = _items(key)[0]

    response = _answer(client, card_id, item_id, expected.upper(), elapsed_ms=4200)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["correct"] is True
    assert body["expected"] == expected
    assert body["submitted"] == expected.upper()

    rows = _attempts(key)
    assert len(rows) == 1
    row = rows[0]
    assert row.id == body["attempt_id"]
    assert row.source == "remedial_practice"
    assert row.concept_key == key
    assert row.expected_answer == expected
    assert row.grader == GRADER == "exact_ci"
    assert row.elapsed_ms == 4200


def test_the_post_state_is_the_get_state(client):
    """One function, two call sites: no second code path that can drift."""
    card_id, key, _ = _practice_card(item_count=3)
    item_id, _, expected = _items(key)[0]

    body = _answer(client, card_id, item_id, expected).json()

    assert body["state"] == _state(client, card_id)
    assert body["state"]["status"] == "in_progress"
    assert (body["state"]["answered"], body["state"]["correct"]) == (1, 1)
    assert body["state"]["item"]["id"] != item_id, "state.item is the NEXT question"
    assert body["state"]["results"] == [
        {
            "item_id": item_id,
            "question": _items(key)[0][1],
            "submitted": expected,
            "expected": expected,
            "correct": True,
            "created_at": body["state"]["results"][0]["created_at"],
        }
    ]
    assert body["state"]["results"][0]["created_at"].endswith("+00:00")


def test_an_item_from_another_concept_is_refused(client):
    card_id, _, _ = _practice_card(item_count=1)
    _, other_key, _ = _practice_card(item_count=1)
    other_item_id = _items(other_key)[0][0]

    response = _answer(client, card_id, other_item_id, "anything")

    assert response.status_code == 400
    assert response.json()["detail"] == "That quiz item does not test this concept"


def test_an_empty_answer_is_refused(client):
    card_id, key, _ = _practice_card(item_count=1)

    response = _answer(client, card_id, _items(key)[0][0], "   ")

    assert response.status_code == 400
    assert _attempts(key) == []


def test_an_unknown_item_is_a_404(client):
    card_id, _, _ = _practice_card(item_count=1)

    assert _answer(client, card_id, 999999, "anything").status_code == 404


# --------------------------------------------------------------------------
# Which question, and how many
# --------------------------------------------------------------------------


def test_items_are_served_in_pick_items_order(client):
    """AC7: least recently asked, and the one just answered goes to the back."""
    card_id, key, _ = _practice_card(item_count=3)
    first, second, third = (item_id for item_id, _, _ in _items(key))
    day_start, _unused = days.day_bounds()

    session = SessionLocal()
    try:
        # `third` was asked a while ago and `first` more recently, both in an earlier
        # review session so neither counts against today's practice; `second` is unseen.
        # The timestamps are explicit rather than two calls a millisecond apart, which
        # is a tie the clock decides and the assertion below would then be guessing at.
        for item_id, moment in ((third, day_start - timedelta(days=2)), (first, day_start)):
            item = session.get(models.QuizItem, item_id)
            session.add(
                models.Attempt(
                    quiz_item_id=item.id,
                    lesson_id=item.lesson_id,
                    concept_key=key,
                    concept_label=item.concept,
                    submitted_answer=WRONG,
                    expected_answer=item.answer,
                    correct=False,
                    attempt_no=1,
                    source=review.REVIEW_SESSION_SOURCE,
                    grader=GRADER,
                    created_at=moment,
                )
            )
        session.commit()
    finally:
        session.close()

    served = _walk(client, card_id, correct=False)

    assert served == [second, third, first]


def test_no_item_is_served_twice_in_one_day(client):
    """AC8, and its 409: a question already answered is refused, with the next one."""
    card_id, key, _ = _practice_card(item_count=3)
    served = []

    state = _state(client, card_id)
    served.append(state["item"]["id"])
    assert _answer(client, card_id, served[0], WRONG).status_code == 200

    repeat = _answer(client, card_id, served[0], "a different wrong answer")
    assert repeat.status_code == 409
    detail = repeat.json()["detail"]
    assert detail["error"] == "item_already_answered"
    # The invariant: this refusal always carries the question to ask instead.
    assert detail["state"]["item"] is not None
    assert detail["state"]["item"]["id"] != served[0]
    # And it wrote nothing: the duplicate guard matches on answer text and would have
    # let this second, different answer through.
    assert len(_attempts(key, PRACTICE)) == 1

    served += _walk(client, card_id, correct=False)
    assert len(set(served)) == 3


def test_two_correct_answers_end_the_session(client):
    """AC9: the target, with a question still left in the pool."""
    card_id, _, _ = _practice_card(item_count=3)

    served = _walk(client, card_id, correct=True)

    state = _state(client, card_id)
    assert len(served) == 2
    assert (state["status"], state["reason"]) == ("done", "target_reached")
    assert (state["answered"], state["correct"]) == (2, 2)
    assert state["item"] is None
    assert state["resets_at"] == iso_utc(days.day_bounds()[1])
    assert len(state["results"]) == 2
    assert all(result["correct"] for result in state["results"])


def test_three_answers_end_the_session_with_the_pool_still_stocked(client):
    """AC9: the answer ceiling outranks a pool that still has questions in it."""
    card_id, key, _ = _practice_card(item_count=4)

    served = _walk(client, card_id, correct=False)

    state = _state(client, card_id)
    assert len(served) == 3
    assert (state["status"], state["reason"]) == ("done", "attempts_spent")
    assert (state["answered"], state["correct"]) == (3, 0)
    assert len(_items(key)) == 4, "a fourth question exists and is deliberately not served"


def test_a_one_item_concept_exhausts_its_pool_and_never_reaches_the_target(client):
    """AC9, and the reason no_items and pool_exhausted must not be confused.

    Both compute from an empty list and both serve no item. This one had a question,
    the learner answered it, and there is no second one: two correct answers were never
    reachable here, so reporting target_reached would be a claim about work never done.
    """
    card_id, key, _ = _practice_card(item_count=1)
    item_id, _, expected = _items(key)[0]

    assert _answer(client, card_id, item_id, expected).status_code == 200

    state = _state(client, card_id)
    assert (state["status"], state["reason"]) == ("done", "pool_exhausted")
    assert (state["answered"], state["correct"]) == (1, 1)
    assert state["correct"] < state["target_correct"]


def test_the_finished_state_survives_a_restart(client):
    """AC9: nothing is held in memory, so a fresh session reads the same session back."""
    card_id, _, _ = _practice_card(item_count=3)
    _walk(client, card_id, correct=True)

    session = SessionLocal()
    try:
        card = session.get(models.ReviewCard, card_id)
        state = remediation.practice_state(session, card)
    finally:
        session.close()

    assert (state["status"], state["reason"]) == ("done", "target_reached")
    assert state == _state(client, card_id)


def test_a_finished_session_refuses_a_further_answer(client):
    card_id, key, _ = _practice_card(item_count=4)
    served = _walk(client, card_id, correct=False)
    spare = next(item_id for item_id, _, _ in _items(key) if item_id not in served)

    response = _answer(client, card_id, spare, WRONG)

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "session_complete"
    assert detail["state"]["item"] is None
    assert len(_attempts(key, PRACTICE)) == 3


def test_the_last_question_ends_the_session_rather_than_repeating_itself(client):
    """The invariant behind item_already_answered: it always has a next question.

    With one item and one answer there is nothing left to offer, so re-answering that
    item is a finished session rather than "here is the next one", which would be a
    409 promising a question that does not exist.
    """
    card_id, key, _ = _practice_card(item_count=1)
    item_id, _, expected = _items(key)[0]
    assert _answer(client, card_id, item_id, expected).status_code == 200

    response = _answer(client, card_id, item_id, expected)

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "session_complete"


def test_a_second_session_waits_for_the_next_study_day(client):
    """AC10, on the 04:00 boundary rather than on midnight."""
    card_id, key, _ = _practice_card(item_count=4)
    _walk(client, card_id, correct=False)
    assert _state(client, card_id)["status"] == "done"

    day_start, _ = days.day_bounds()
    # One second before the boundary is the previous study day: today is clean again.
    assert _move_practice_to(key, day_start - timedelta(seconds=1)) == 3
    fresh = _state(client, card_id)
    assert (fresh["status"], fresh["answered"]) == ("ready", 0)
    assert fresh["results"] == []

    # The window is half open at the start, so 04:00 itself belongs to today.
    _move_practice_to(key, day_start)
    assert _state(client, card_id)["answered"] == 3
    assert _state(client, card_id)["reason"] == "attempts_spent"


# --------------------------------------------------------------------------
# What practice must not touch
# --------------------------------------------------------------------------


def test_the_card_is_untouched_by_practice(client):
    """AC1: every column, before and after, including a fully correct session."""
    card_id, _, _ = _practice_card(item_count=3)
    before = _card_row(card_id)
    assert _card_state(card_id)["lapses"] == before["lapses"]

    _walk(client, card_id, correct=True)

    assert _card_row(card_id) == before


def test_practice_writes_no_review_log_and_calls_no_model(client, failing_provider):
    """AC2 and AC4: the provider here raises on any call, and a full session runs."""
    card_id, _, _ = _practice_card(item_count=3)
    before = _counts() | {"card_logs": _card_logs(card_id)}

    served = _walk(client, card_id, correct=True)

    assert len(served) == 2
    assert _counts() | {"card_logs": _card_logs(card_id)} == before


def test_the_note_keeps_its_status_and_its_cooldown(client):
    """AC16: practicing does not clear, shorten, or reset anything about the note."""
    card_id, _, _ = _practice_card(item_count=3)
    before = [(n.id, n.status, n.cooldown_until, n.cleared_at) for n in _notes(card_id)]

    _walk(client, card_id, correct=True)

    assert [(n.id, n.status, n.cooldown_until, n.cleared_at) for n in _notes(card_id)] == before
    assert before[0][1] == remediation.ACTIVE


def test_needs_attention_is_unchanged_by_a_perfect_session(client):
    """AC11: the trigger reads ratings, and practice writes none."""
    card_id, key, _ = _practice_card([fsrs.AGAIN, fsrs.GOOD, fsrs.AGAIN], item_count=3)
    moment = review.now_utc()
    session = SessionLocal()
    try:
        before = review.needs_attention(session, moment)
    finally:
        session.close()
    assert any(entry["concept_key"] == key for entry in before)

    _walk(client, card_id, correct=True)

    session = SessionLocal()
    try:
        assert review.needs_attention(session, moment) == before
    finally:
        session.close()


def test_the_dashboard_numbers_are_unchanged_by_a_perfect_session(client):
    """AC12: retention, mastery, the weakest concept, and the streak all hold still."""
    card_id, key, label = _practice_card([fsrs.AGAIN, fsrs.GOOD, fsrs.AGAIN], item_count=3)
    moment = review.now_utc()

    def snapshot():
        session = SessionLocal()
        try:
            course = (
                session.query(models.Course)
                .filter(models.Course.title == f"Course {label}")
                .one()
            )
            concepts = review.course_concepts(session, course, moment)
            return {
                "retention": review.retention(session, moment),
                "day_streak": review.day_streak(session, moment),
                "bucket": review.mastery_bucket(review.get_card(session, key), moment),
                "weakest": review.weakest_concept(concepts),
            }
        finally:
            session.close()

    before = snapshot()

    _walk(client, card_id, correct=True)

    assert snapshot() == before


def test_practice_time_never_enters_the_session_estimate(client):
    """AC13 and reader 3: seconds_per_card is review-session scoped, and stays so.

    Two hundred remedial rows, which is exactly the sample window, so if the source
    filter were dropped every sample would be a ten minute remedial answer and the
    median would move whatever else the test database happens to hold.
    """
    card_id, key, _ = _practice_card(item_count=3)
    before_minutes = client.get("/review/today").json()["estimated_minutes"]
    yesterday = days.day_bounds()[0] - timedelta(hours=1)
    session = SessionLocal()
    try:
        before = review.seconds_per_card(session)
        item = session.get(models.QuizItem, _items(key)[0][0])
        session.add_all(
            models.Attempt(
                quiz_item_id=item.id,
                lesson_id=item.lesson_id,
                concept_key=key,
                concept_label=item.concept,
                submitted_answer=WRONG,
                expected_answer=item.answer,
                correct=False,
                attempt_no=ordinal,
                source=PRACTICE,
                grader=GRADER,
                elapsed_ms=600_000,
                # Dated into an earlier study day, so they are a duration sample and
                # not two hundred answers against today's cap.
                created_at=yesterday,
            )
            for ordinal in range(1, review.DURATION_SAMPLE_SIZE + 1)
        )
        session.commit()
    finally:
        session.close()

    assert _answer(client, card_id, _items(key)[1][0], WRONG, elapsed_ms=600_000).status_code == 200

    session = SessionLocal()
    try:
        assert review.seconds_per_card(session) == before
    finally:
        session.close()
    assert client.get("/review/today").json()["estimated_minutes"] == before_minutes


# --------------------------------------------------------------------------
# The nine readers of attempts
# --------------------------------------------------------------------------


def test_a_remedial_answer_does_not_lock_the_item_out_of_review(client):
    """Reader 1, and the single most important test here.

    already_answered_this_exposure exists to stop a learner reading the answer key off
    a review response and resubmitting it. It is scoped to review_session attempts, and
    if it ever stops being, practicing a concept would silently disqualify its question
    from the review that practice was supposed to prepare for.
    """
    card_id, key, _ = _practice_card(item_count=1)
    item_id, _, expected = _items(key)[0]
    assert _answer(client, card_id, item_id, expected).status_code == 200

    session = SessionLocal()
    try:
        card = session.get(models.ReviewCard, card_id)
        item = session.get(models.QuizItem, item_id)
        assert review.already_answered_this_exposure(session, card, item) is False
    finally:
        session.close()

    response = client.post(
        f"/review/cards/{card_id}/answer", json={"item_id": item_id, "answer": expected}
    )

    assert response.status_code == 200, response.text
    assert response.json()["correct"] is True
    assert [row.source for row in _attempts(key)] == [PRACTICE, review.REVIEW_SESSION_SOURCE]


def test_grade_lesson_rates_nothing_from_a_remedial_attempt(client):
    """Reader 2 and AC15: the same lesson, practiced or not, schedules the same thing."""
    practiced_card, practiced_key, _ = _practice_card(item_count=1)
    _, plain_key, _ = _practice_card(item_count=1)

    practiced_item, _, practiced_expected = _items(practiced_key)[0]
    assert _answer(client, practiced_card, practiced_item, practiced_expected).status_code == 200
    remedial_ids = [row.id for row in _attempts(practiced_key, PRACTICE)]
    assert len(remedial_ids) == 1

    def finish(key):
        item_id, _, _ = _items(key)[0]
        lesson_id = _lesson_id(key)
        # Wrong on the quiz, right in practice: if the remedial row were counted the
        # two lessons could not possibly grade the same.
        assert client.post(f"/quiz/{item_id}/answer", json={"answer": WRONG}).status_code == 200
        completion = client.post(f"/lessons/{lesson_id}/complete")
        assert completion.status_code == 200
        session = SessionLocal()
        try:
            log = (
                session.query(models.ReviewLog)
                .filter(models.ReviewLog.card_id == review.get_card(session, key).id)
                .order_by(models.ReviewLog.id.desc())
                .first()
            )
            return completion.json()["scheduled_concepts"], (
                log.rating,
                log.rating_v,
                log.items_correct,
                log.items_total,
                len(log.attempt_ids or []),
            ), list(log.attempt_ids or [])
        finally:
            session.close()

    practiced_scheduled, practiced_log, practiced_ids = finish(practiced_key)
    plain_scheduled, plain_log, _ = finish(plain_key)

    assert practiced_scheduled == plain_scheduled == 1
    assert practiced_log == plain_log
    assert practiced_ids and not set(practiced_ids) & set(remedial_ids)

    session = SessionLocal()
    try:
        every_rated_id = set()
        for (attempt_ids,) in session.query(models.ReviewLog.attempt_ids).all():
            every_rated_id.update(attempt_ids or [])
    finally:
        session.close()
    assert not every_rated_id & set(remedial_ids)


def test_a_remedially_answered_item_rotates_to_the_back_for_review(client):
    """Reader 4: pick_items reads every source, and that is intended.

    Practicing a question is a reason to ask a different one next time. The card is
    not touched, but which of its questions comes up is.
    """
    card_id, key, _ = _practice_card(item_count=2)
    first, second = (item_id for item_id, _, _ in _items(key))

    session = SessionLocal()
    try:
        assert review.pick_items(session, [key])[key].id == first
    finally:
        session.close()

    assert _answer(client, card_id, first, WRONG).status_code == 200

    session = SessionLocal()
    try:
        assert review.pick_items(session, [key])[key].id == second
    finally:
        session.close()


def test_a_correct_remedial_answer_moves_ever_correct_and_nothing_else(client):
    """Reader 5: both halves of _attempt_state, which splits its sources deliberately."""
    card_id, key, _ = _practice_card(item_count=1)
    item_id, _, expected = _items(key)[0]
    assert client.post(f"/quiz/{item_id}/answer", json={"answer": WRONG}).status_code == 200

    session = SessionLocal()
    try:
        before = _attempt_state(_attempts_for_item(session, item_id))
    finally:
        session.close()
    assert before["ever_correct"] is False

    assert _answer(client, card_id, item_id, expected).status_code == 200

    session = SessionLocal()
    try:
        after = _attempt_state(_attempts_for_item(session, item_id))
    finally:
        session.close()
    assert after["ever_correct"] is True
    assert after["attempts"] == before["attempts"] == 1
    assert after["first_attempt_correct"] is False
    assert after["latest_quiz_attempt"] == before["latest_quiz_attempt"]

    # And the lesson page says the same, since it renders exactly this state.
    quiz = client.get(f"/lessons/{_lesson_id(key)}").json()["quiz"]
    state = next(entry["attempt_state"] for entry in quiz if entry["id"] == item_id)
    assert state == after


def test_the_lesson_attempt_history_shows_remedial_rows(client):
    """Reader 6: /lessons/{id}/attempts is the full history and stays unfiltered.

    It already returns review_session rows and its docstring promises everything, so a
    remedial row belongs in it. This is a public response gaining a new source value.
    """
    card_id, key, _ = _practice_card(item_count=1)
    item_id, _, expected = _items(key)[0]
    assert client.post(f"/quiz/{item_id}/answer", json={"answer": WRONG}).status_code == 200
    assert _answer(client, card_id, item_id, expected).status_code == 200

    rows = client.get(f"/lessons/{_lesson_id(key)}/attempts").json()["attempts"]

    assert [row["source"] for row in rows] == [LESSON_QUIZ_SOURCE, PRACTICE]
    assert rows[1]["expected_answer"] == expected
    assert rows[1]["grader"] == GRADER


def test_the_duplicate_guard_is_scoped_to_the_practice_source(client):
    """Reader 8: practice passes its own source, so the guard self-scopes."""
    _, key, _ = _practice_card(item_count=1)
    item_id = _items(key)[0][0]

    session = SessionLocal()
    try:
        item = session.get(models.QuizItem, item_id)
        first = _record_attempt(session, item, "same words", False, None, source=PRACTICE)
        again = _record_attempt(session, item, "same words", False, None, source=PRACTICE)
        assert again.id == first.id
        # The same text from the lesson quiz is a different answer to a different
        # question being asked, and gets its own row.
        quiz = _record_attempt(session, item, "same words", False, None)
        assert quiz.id != first.id
        assert quiz.source == LESSON_QUIZ_SOURCE
    finally:
        session.close()


def test_a_double_submitted_practice_answer_writes_one_row(client):
    """AC17: one answer, one row, whichever guard catches the second click."""
    card_id, key, _ = _practice_card(item_count=2)
    item_id, _, expected = _items(key)[0]

    first = _answer(client, card_id, item_id, expected)
    second = _answer(client, card_id, item_id, expected)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"]["error"] == "item_already_answered"
    assert len(_attempts(key, PRACTICE)) == 1


def test_attempt_ordinals_stay_monotone_across_sources(client):
    """Reader 9: attempt_no counts every touch of the item, on purpose."""
    card_id, key, _ = _practice_card(item_count=1)
    item_id, _, expected = _items(key)[0]

    assert _answer(client, card_id, item_id, expected).status_code == 200
    assert client.post(f"/quiz/{item_id}/answer", json={"answer": WRONG}).status_code == 200

    rows = _attempts(key)
    assert [(row.source, row.attempt_no) for row in rows] == [
        (PRACTICE, 1),
        (LESSON_QUIZ_SOURCE, 2),
    ]
    session = SessionLocal()
    try:
        # And the lesson-quiz count is still one, not two.
        assert _attempt_state(_attempts_for_item(session, item_id))["attempts"] == 1
    finally:
        session.close()


# --------------------------------------------------------------------------
# The note cleared underneath a session
# --------------------------------------------------------------------------


def test_an_answer_in_flight_is_still_graded_when_the_note_clears(client):
    """Terminating means no NEW question, not a discarded answer.

    Another tab can clear the note between this question and this answer, because the
    Today screen fans getRemediation out per concept. Throwing the answer away would be
    the discard-evidence mistake this project has already fixed once; the terminal
    state arrives on the response that carries the answer instead.
    """
    card_id, key, _ = _practice_card(item_count=3)
    served = _state(client, card_id)["item"]["id"]
    _clear_note(card_id)

    response = _answer(client, card_id, served, WRONG)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["expected"] == next(a for i, _, a in _items(key) if i == served)
    assert len(_attempts(key, PRACTICE)) == 1
    # The state that follows it is the terminal one, and it serves nothing new.
    assert (body["state"]["status"], body["state"]["reason"]) == ("unavailable", "no_note")
    assert body["state"]["item"] is None
    assert body["state"]["answered"] == 1


def test_a_card_that_never_had_a_note_refuses_every_answer(client):
    """The other half of that ruling: nothing was ever in the learner's hands here."""
    card_id, key, _ = _seed_concept([fsrs.AGAIN, fsrs.AGAIN], item_count=2)

    response = _answer(client, card_id, _items(key)[0][0], WRONG)

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "no_note"
    assert detail["state"]["item"] is None
    assert _attempts(key, PRACTICE) == []


def test_a_cleared_note_refuses_a_question_already_answered_today(client):
    """The day is consumed by answers, not by sessions, and a cleared note says so."""
    card_id, key, _ = _practice_card(item_count=3)
    served = _state(client, card_id)["item"]["id"]
    assert _answer(client, card_id, served, WRONG).status_code == 200
    _clear_note(card_id)

    response = _answer(client, card_id, served, "another wrong answer")

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "no_note"
    assert len(_attempts(key, PRACTICE)) == 1


def test_a_concept_with_no_items_refuses_the_answer_as_a_conflict(client):
    """no_items is a 409 rather than re-teaching's 422.

    The 422 there means "we could not do the work you asked for". This means "there is
    no work here to do", which is a fact about the concept, and the GET reports it as
    ordinary data rather than as a failure.
    """
    card_id, _, _ = _practice_card(item_count=0)
    _, other_key, _ = _practice_card(item_count=1)

    response = _answer(client, card_id, _items(other_key)[0][0], WRONG)

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "no_items"
    assert detail["state"]["status"] == "unavailable"
    assert detail["state"]["item"] is None


def test_practice_is_not_reachable_from_inside_a_review_session(client):
    """The queue serves questions and previews, and offers no way into practice.

    Practice belongs under the note on the Today screen, where the learner has just
    read an explanation. Offering it mid-review would put an untimed second try inside
    the retrieval test the card exists to run.
    """
    _practice_card(item_count=2)

    assert "practice" not in client.get("/review/queue").text
    assert "practice" not in client.get("/review/today").text
