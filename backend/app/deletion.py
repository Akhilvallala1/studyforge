"""Deleting a course, and the one thing that does not go with it.

WHAT THE ORM ALREADY DOES, so that nobody writes it again: session.delete(course)
removes the course's modules, its lessons, their quiz items and their attempts, through
four chained delete-orphan relationships. That fourth level is worth saying out loud
because it is the biggest thing this feature destroys: EVERY ANSWER THE LEARNER EVER GAVE
in that course, which is the table the whole mastery signal is derived from. Deleting a
course is not tidying a list, and the preview exists so the learner sees that before they
agree to it.

WHAT DOES NOT CASCADE IS THE FEATURE. ReviewCard is keyed on concept_key GLOBALLY with no
course_id, deliberately, so that a learner who meets gradient descent in two courses has
one memory of it rather than two. That is right, and it means a card outlives the course
that created it while the quiz items it would be asked from do not. Measured, deleting a
course with one genuinely due card:

    before:  due_cards 1, of those askable 1
    after:   due_cards 1, of those askable 0

Today then says a concept is due, renders the button, and the session serves nothing. The
review screen filters unaskable cards defensively so it fails quietly rather than loudly,
and the card STAYS DUE FOREVER, permanently inflating due_today, due_this_week and the
session estimate with no action the learner can take to clear it. This is not a
pre-existing hole: every card has always had an item behind it, because the only way to
create one is grade_lesson on a lesson that still exists. Deletion is the first path that
can break that invariant, and it breaks it in bulk.

So a card whose concept NO SURVIVING COURSE NAMES is retired in the same transaction.

THE SHARING GUARD IS THE POINT AND IT IS NOT OPTIONAL. A concept another course still
teaches keeps its card, its logs and its notes, entirely untouched. Getting this wrong
deletes the learner's memory of a concept because they tidied up one of the two courses
that happened to mention it, and the learner has no way to know that is what happened.

REMEDIATION NOTES MUST BE DELETED BY HAND. ReviewCard declares a relationship to its logs,
so those cascade, and declares NOTHING for RemediationNote, which holds a plain
ForeignKey("review_cards.id"). SQLite runs with PRAGMA foreign_keys off in this project, so
deleting a card leaves its notes pointing at a row that no longer exists, silently, with no
error at any layer. They are deleted explicitly below and asserted explicitly in the tests.

WHAT DELIBERATELY SURVIVES: LlmCall. Its course_id is a plain nullable integer with no
ForeignKey, and its class docstring says why in as many words, "so usage history survives
course deletion". Spend is money that was really spent; the /usage page keeps the row and
loses the name, falling back to the id it still carries. Nothing here touches it.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app import models
from app.concepts import normalize_concept
from app.review import course_lessons

# SQLite's parameter limit is 999, and a learner's concept vocabulary is unbounded in
# principle. Chunked for the reason review.course_concepts chunks its card lookups.
_CHUNK = 500


def concept_keys(lessons: list[models.Lesson]) -> set[str]:
    """Every concept key a set of lessons names, from lesson.concepts and their quiz items.

    Both sources, because they can disagree: a lesson lists the concepts it teaches and its
    quiz items each name the one they test, and a course that names a concept in either
    place is a course that teaches it. Missing one source would retire a card that a
    surviving course still asks about, which is the sharing bug wearing a different hat.

    normalize_concept rather than any local folding. There is exactly one normalization in
    this project on purpose: a second one that drifted would split a concept's history in
    two, and here it would mean comparing this course's keys against another course's keys
    under different rules and getting the sharing answer wrong.
    """
    keys: set[str] = set()
    for lesson in lessons:
        # lesson.concepts is a JSON column, so it can hold anything a model wrote into it.
        for raw in lesson.concepts or []:
            if isinstance(raw, str):
                key = normalize_concept(raw)
                if key:
                    keys.add(key)
        for item in lesson.quiz_items:
            key = normalize_concept(item.concept)
            if key:
                keys.add(key)
    return keys


def keys_named_elsewhere(session: Session, course: models.Course) -> set[str]:
    """Every concept key named by a course OTHER than this one.

    One query for the lessons plus one eager load for their quiz items, rather than a walk
    per course. The comparison is a set difference at the end, so this deliberately does
    not care which other course names a key, only that one does.
    """
    others = (
        session.query(models.Lesson)
        .join(models.Module)
        .filter(models.Module.course_id != course.id)
        .options(selectinload(models.Lesson.quiz_items))
        .all()
    )
    return concept_keys(others)


def _attempt_count(session: Session, course: models.Course) -> int:
    """Answers recorded in this course, counted through the join rather than by id list.

    A join instead of Attempt.lesson_id.in_(ids) because the id list is unbounded and would
    hit SQLite's 999 parameter limit on a large course, which is a failure that would only
    ever appear on somebody's real library and never in a test.
    """
    return (
        session.query(func.count(models.Attempt.id))
        .join(models.Lesson, models.Attempt.lesson_id == models.Lesson.id)
        .join(models.Module, models.Lesson.module_id == models.Module.id)
        .filter(models.Module.course_id == course.id)
        .scalar()
        or 0
    )


def _summary(session: Session, course: models.Course) -> tuple[dict, set[str]]:
    """The payload, and the concept keys whose cards this deletion would retire.

    ONE function behind both the preview and the delete, which is what makes "the preview
    told the truth" a property of the code rather than a claim two implementations have to
    keep agreeing on. delete_course computes this BEFORE it removes anything, so the body
    it returns describes the same database the preview would have described.
    """
    lessons = course_lessons(session, course)
    mine = concept_keys(lessons)
    elsewhere = keys_named_elsewhere(session, course)
    retired = mine - elsewhere
    kept = mine & elsewhere

    spend = (
        session.query(func.sum(models.LlmCall.estimated_cost_usd))
        .filter(models.LlmCall.course_id == course.id)
        .scalar()
        or 0.0
    )

    payload = {
        "course_id": course.id,
        "title": course.title,
        "lessons": len(lessons),
        "lessons_completed": sum(1 for lesson in lessons if lesson.completed_at is not None),
        # course_lessons eager-loads quiz items, so this is free rather than a query.
        "quiz_items": sum(len(lesson.quiz_items) for lesson in lessons),
        "attempts": _attempt_count(session, course),
        # Concepts are counted at the CONCEPT level, not the card level, so
        # retired + kept == total always holds. A concept the learner never studied has
        # no card to delete, and is still a concept this course was the last to name.
        "concepts_total": len(mine),
        "concepts_retired": len(retired),
        "concepts_kept": len(kept),
        "spend_usd": float(spend),
    }
    return payload, retired


def deletion_preview(session: Session, course: models.Course) -> dict:
    """What deleting this course would destroy. Writes nothing.

    Same shape as the delete's own answer, because the learner is being asked to consent to
    a specific thing and then told what happened, and two shapes would let those drift.
    """
    payload, _ = _summary(session, course)
    return payload


def _retire_cards(session: Session, retired: set[str]) -> None:
    """Remove the scheduling state for concepts no surviving course names.

    Notes first, then the card. With foreign keys enforced the order would matter; with
    them off, as SQLite runs here, nothing complains either way, which is exactly why the
    order is written down rather than left to chance. Logs are not touched explicitly
    because ReviewCard.logs cascades them; notes have no such relationship and would
    otherwise be left pointing at a card that no longer exists.
    """
    if not retired:
        return
    keys = sorted(retired)
    for start in range(0, len(keys), _CHUNK):
        cards = (
            session.query(models.ReviewCard)
            .filter(models.ReviewCard.concept_key.in_(keys[start : start + _CHUNK]))
            .all()
        )
        for card in cards:
            session.query(models.RemediationNote).filter(
                models.RemediationNote.card_id == card.id
            ).delete(synchronize_session=False)
            session.delete(card)


def delete_course(session: Session, course: models.Course) -> dict:
    """Delete a course and retire the scheduling state it was the last to justify.

    ONE TRANSACTION, committed here. The card retirement and the course removal have to
    land together: a crash between them would leave either cards for a course that is gone
    or a course whose concepts have no schedule, and both are states nothing in this system
    knows how to repair.

    The summary is computed FIRST, against the database as it still stands, because
    afterwards there is nothing left to count.
    """
    payload, retired = _summary(session, course)
    _retire_cards(session, retired)
    session.delete(course)
    session.commit()
    return payload
