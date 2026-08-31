"""Grading a concept that more than one lesson teaches.

Every lesson-quiz answer has to be counted exactly once. Not zero times, which is
what happened while the exposure window was a timestamp comparison and a sibling
lesson had been completed first, and not twice, which would inflate a card's
strength just as wrongly as dropping an answer deflates it. Both halves are
asserted here, because a change that fixes either one alone is easy to write and
wrong.
"""

import pytest

from app import fsrs, models, review
from app.concepts import normalize_concept
from app.db import SessionLocal

SHARED = "Quorum Reads"
SHARED_KEY = normalize_concept(SHARED)


def _shared_concept_course():
    """Two lessons in one course, each with one quiz item on the same concept.

    Returns (lesson_id, quiz_item_id, answer) per lesson, in course order.
    """
    session = SessionLocal()
    try:
        course = models.Course(title="Distributed Systems", description="")
        module = models.Module(title="Module 1", position=0)
        for position, title in enumerate(("Replication", "Consensus")):
            lesson = models.Lesson(
                title=title, position=position, content=f"# {title}", concepts=[SHARED]
            )
            lesson.quiz_items.append(
                models.QuizItem(
                    question=f"{title}: when can a quorum read be stale?",
                    kind="short",
                    options=[],
                    answer=f"answer-{position}",
                    concept=SHARED,
                )
            )
            module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.commit()
        ordered = sorted(module.lessons, key=lambda row: row.position)
        return [
            (lesson.id, lesson.quiz_items[0].id, lesson.quiz_items[0].answer)
            for lesson in ordered
        ]
    finally:
        session.close()


def _card_state():
    """The shared concept's card as plain values, safe to hold across sessions."""
    session = SessionLocal()
    try:
        row = review.get_card(session, SHARED_KEY)
        if row is None:
            return None
        return {
            "state": row.state,
            "stability": row.stability,
            "lapses": row.lapses,
            "reps": row.reps,
            "due": row.due,
        }
    finally:
        session.close()


def _logs():
    """Every rating on the shared concept's card, oldest first."""
    session = SessionLocal()
    try:
        row = review.get_card(session, SHARED_KEY)
        if row is None:
            return []
        return (
            session.query(models.ReviewLog)
            .filter(models.ReviewLog.card_id == row.id)
            .order_by(models.ReviewLog.id)
            .all()
        )
    finally:
        session.close()


def _answer(client, item_id, text):
    return client.post(f"/quiz/{item_id}/answer", json={"answer": text}).json()["attempt_id"]


@pytest.fixture(autouse=True)
def clean_schedule(client):
    """Empty the scheduling tables before each test, as test_review.py does.

    The suite shares one SQLite file with no per-test reset, and this module asserts
    on the entire history of one card, so a card left behind by another module would
    change the answer. Courses and attempts are deliberately untouched.
    """
    session = SessionLocal()
    try:
        session.query(models.ReviewLog).delete()
        session.query(models.ReviewCard).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture
def shared(client):
    """Takes client so init_db() has run and the scheduling tables exist."""
    return _shared_concept_course()


def test_the_second_lesson_grades_the_shared_concept(client, shared):
    """The reproduction: both answers given first, then both lessons completed.

    The second completion used to record nothing at all. Its attempt was older than
    the last_review that the first completion had just written, so the filter whose
    job is to stop an answer being graded twice threw away an answer that had never
    been graded once.
    """
    (a_lesson, a_item, a_answer), (b_lesson, b_item, b_answer) = shared
    a_attempt = _answer(client, a_item, a_answer)
    b_attempt = _answer(client, b_item, b_answer)

    first = client.post(f"/lessons/{a_lesson}/complete").json()
    second = client.post(f"/lessons/{b_lesson}/complete").json()

    assert first["scheduled_concepts"] == 1
    assert second["scheduled_concepts"] == 1
    # Two ratings, each naming the answer it was derived from and neither naming the
    # other's: the evidence is split across the completions, not duplicated.
    assert [log.attempt_ids for log in _logs()] == [[a_attempt], [b_attempt]]
    assert _card_state()["reps"] == 2


def test_a_miss_in_the_second_lesson_reaches_the_card(client, shared):
    """The recovered answer has to move the card, not merely show up in a log.

    A correct repeat on the same day leaves stability exactly where it is, because
    FSRS clamps the short-term increase to 1.0, so the schedule is asserted on the
    case where the discarded evidence provably changed it: a miss in the second
    lesson drops the card into relearning and counts the lapse the bug hid.
    """
    (a_lesson, a_item, a_answer), (b_lesson, b_item, _) = shared
    _answer(client, a_item, a_answer)
    _answer(client, b_item, "not the answer")

    client.post(f"/lessons/{a_lesson}/complete")
    before = _card_state()
    assert before["state"] == fsrs.REVIEW
    assert before["lapses"] == 0

    client.post(f"/lessons/{b_lesson}/complete")
    after = _card_state()

    assert _logs()[-1].rating == fsrs.AGAIN
    assert after["state"] == fsrs.RELEARNING
    assert after["lapses"] == 1
    assert after["stability"] < before["stability"]
    assert after["due"] < before["due"]


def test_completing_the_same_lesson_twice_does_not_grade_twice(client, shared):
    """The guard the fix had to keep: one attempt, at most one rating.

    A repeat POST is not a second retrieval. Rating it again would inflate the card
    exactly as wrongly as dropping the sibling lesson's answer deflated it, which is
    why the fix distinguishes "already counted" from "older than something counted"
    rather than dropping the check.
    """
    (a_lesson, a_item, a_answer), _ = shared
    _answer(client, a_item, a_answer)

    client.post(f"/lessons/{a_lesson}/complete")
    repeat = client.post(f"/lessons/{a_lesson}/complete").json()

    assert repeat["scheduled_concepts"] == 0
    assert len(_logs()) == 1
    assert _card_state()["reps"] == 1


def test_redoing_a_lesson_grades_only_the_new_answer(client, shared):
    """Reopening a lesson and answering again is new evidence, and only that."""
    (a_lesson, a_item, a_answer), _ = shared
    missed = _answer(client, a_item, "not the answer")
    client.post(f"/lessons/{a_lesson}/complete")

    client.delete(f"/lessons/{a_lesson}/complete")
    retried = _answer(client, a_item, a_answer)
    client.post(f"/lessons/{a_lesson}/complete")

    logs = _logs()
    assert [log.attempt_ids for log in logs] == [[missed], [retried]]
    assert logs[0].rating == fsrs.AGAIN
    assert logs[1].rating > fsrs.AGAIN
