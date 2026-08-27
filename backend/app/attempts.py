"""Recording and summarizing quiz attempts.

Lifted verbatim out of main.py. Review sessions have to write attempt rows through
exactly the same grading, duplicate-guard, and ordinal logic the lesson quiz uses,
and a router importing main.py would close an import cycle. Nothing here changed in
the move: the behavior is main.py's, only the address is new.
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.concepts import normalize_concept

LESSON_QUIZ_SOURCE = "lesson_quiz"
# Grading policy identifier, stored on every attempt. Bump it if the comparison
# below changes, so old rows stay interpretable under the rules they were graded by.
GRADER = "exact_ci"
MAX_ELAPSED_MS = 86_400_000
# A second click on the submit button is one answer, not two.
DOUBLE_SUBMIT_WINDOW = timedelta(seconds=2)


def iso_utc(value: datetime | None) -> str | None:
    """Serialize a stored timestamp with an explicit UTC offset.

    SQLite drops tzinfo on write, so every datetime read back is naive. Without the
    offset, clients parse the timestamp as local time and show it shifted.
    """
    return None if value is None else value.replace(tzinfo=UTC).isoformat()


def _normalized_answer(text: str) -> str:
    return text.strip().lower()


def _grade(submitted: str, expected: str) -> bool:
    return _normalized_answer(submitted) == _normalized_answer(expected)


def _attempt_state(attempts: list[models.Attempt]) -> dict:
    """Summarize one quiz item's history, from its attempts ordered by attempt_no.

    attempts/first_attempt_correct/latest_quiz_attempt describe the lesson quiz only,
    so a later review session cannot rewrite how the item went the first time.
    ever_correct counts every source: recalling it in review is still evidence of
    knowing it.

    latest_quiz_attempt is named for its scope on purpose. Once review attempts exist
    it is no longer "most recent activity" on the item, and a caller treating it as
    "last practiced" would be wrong in a way nothing would flag.
    """
    quiz_attempts = [a for a in attempts if a.source == LESSON_QUIZ_SOURCE]
    latest = quiz_attempts[-1] if quiz_attempts else None
    return {
        "attempts": len(quiz_attempts),
        "first_attempt_correct": quiz_attempts[0].correct if quiz_attempts else None,
        "ever_correct": any(a.correct for a in attempts),
        "latest_quiz_attempt": None
        if latest is None
        else {
            # expected rides inside this object, which exists only once the learner
            # has answered. That is what keeps unattempted questions from leaking the key.
            "answer": latest.submitted_answer,
            "correct": latest.correct,
            "expected": latest.expected_answer,
            "created_at": iso_utc(latest.created_at),
        },
    }


def _attempts_for_item(session: Session, quiz_item_id: int) -> list[models.Attempt]:
    return (
        session.query(models.Attempt)
        .filter(models.Attempt.quiz_item_id == quiz_item_id)
        .order_by(models.Attempt.attempt_no)
        .all()
    )


def _attempts_by_item(session: Session, lesson_id: int) -> dict[int, list[models.Attempt]]:
    """Every attempt in the lesson in one query, grouped in Python (no per-item N+1)."""
    rows = (
        session.query(models.Attempt)
        .filter(models.Attempt.lesson_id == lesson_id)
        .order_by(models.Attempt.quiz_item_id, models.Attempt.attempt_no)
        .all()
    )
    grouped: dict[int, list[models.Attempt]] = defaultdict(list)
    for row in rows:
        grouped[row.quiz_item_id].append(row)
    return grouped


def _sanitize_elapsed_ms(value: int | None) -> int | None:
    """Drop an implausible client-reported duration instead of rejecting the answer.

    elapsed_ms is a soft signal for future scheduling; a bad clock or a tab left
    open overnight must never cost the learner a real answer.
    """
    if value is None or not 0 <= value <= MAX_ELAPSED_MS:
        return None
    return value


def _recent_duplicate(
    session: Session, quiz_item_id: int, submitted: str, source: str = LESSON_QUIZ_SOURCE
) -> models.Attempt | None:
    """Best-effort double-click guard: catches a resubmit that arrives after the first
    one committed. Truly simultaneous submits both read no prior row and both insert.

    Scoped to one source so a review attempt can never swallow a lesson-quiz submission
    and hand the caller back a row of the wrong kind.
    """
    newest = (
        session.query(models.Attempt)
        .filter(models.Attempt.quiz_item_id == quiz_item_id)
        .filter(models.Attempt.source == source)
        .order_by(models.Attempt.attempt_no.desc())
        .first()
    )
    if newest is None:
        return None
    if _normalized_answer(newest.submitted_answer) != _normalized_answer(submitted):
        return None
    age = datetime.now(UTC) - newest.created_at.replace(tzinfo=UTC)
    return newest if abs(age) <= DOUBLE_SUBMIT_WINDOW else None


def _record_attempt(
    session: Session,
    item: models.QuizItem,
    submitted: str,
    correct: bool,
    elapsed_ms: int | None,
    source: str = LESSON_QUIZ_SOURCE,
) -> models.Attempt:
    """Append one attempt row. Attempts are never updated: the history is the data.

    Everything but the submitted answer and the elapsed time comes off the quiz item
    server-side, so a client cannot claim a different lesson, concept, or answer key.
    """
    duplicate = _recent_duplicate(session, item.id, submitted)
    if duplicate is not None:
        return duplicate

    # count+1 is safe only while attempts are never removed. If pruning or archival
    # is ever added, a gap makes every recount collide on the same taken ordinal and
    # this wedges permanently at 409; switch to max(attempt_no)+1 at that point.
    for _ in range(2):
        prior = (
            session.query(func.count(models.Attempt.id))
            .filter(models.Attempt.quiz_item_id == item.id)
            .scalar()
            or 0
        )
        row = models.Attempt(
            quiz_item_id=item.id,
            lesson_id=item.lesson_id,
            concept_key=normalize_concept(item.concept),
            concept_label=item.concept or "",
            submitted_answer=submitted,
            expected_answer=item.answer,
            correct=correct,
            attempt_no=prior + 1,
            source=source,
            grader=GRADER,
            elapsed_ms=elapsed_ms,
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            # Another request took this attempt_no between the count and the insert.
            # Re-count and try once more before giving up.
            session.rollback()
            continue
        session.refresh(row)
        return row

    raise HTTPException(409, "That answer collided with another submission. Try again.")
