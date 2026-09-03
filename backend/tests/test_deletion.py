"""Deleting a course: what goes, what stays, and the one thing that must not go.

The cascade itself is SQLAlchemy's and is not worth re-testing in the abstract, so the
tests that exercise it assert the rows are gone rather than that the relationship is
configured. What IS worth testing, at length, is the part the ORM does not do: a
ReviewCard has no course_id and survives its course, so this module decides which cards
have lost their last reason to exist.

THE SHARING GUARD IS THE ASSERTION THIS FILE IS FOR, and the way it fails is by passing
vacuously. A test where the surviving course does not really name the shared concept
proves nothing at all, so every sharing test here asserts concepts_kept is non-zero BEFORE
it asserts the card survived. Without that, an implementation that ignored other courses
entirely would pass, which is exactly the mutation this file has to catch.
"""

from uuid import uuid4

import pytest

from app import deletion, fsrs, models, review
from app.db import SessionLocal, init_db


@pytest.fixture(autouse=True)
def _schema():
    """Create the tables. conftest points STUDYFORGE_DB at a fresh temp file and nothing
    builds the schema until something asks for it.

    The API tests in test_deletion_api.py get this for free, because the client fixture
    boots the app and its startup handler calls init_db. A file that only reaches for
    SessionLocal has no startup handler, so it says so here rather than depending on an API
    test having run first, which would work today and break the moment this file is run on
    its own.
    """
    init_db()


def _key(prefix):
    """A concept nobody else's test can collide with.

    review_cards is keyed on concept_key globally with a unique constraint and the whole
    suite shares one SQLite file, so a fixed label here would collide with another test's
    card and this file would fail for a reason that has nothing to do with deletion.
    """
    return f"{prefix}-{uuid4().hex[:10]}"


def _make_course(concepts, title="Course", completed=0, attempts=0):
    """A one-module course naming `concepts`, one lesson per concept.

    Each lesson lists its concept AND carries a quiz item naming it, because
    deletion.concept_keys reads both and a fixture using only one would not notice if the
    implementation stopped reading the other.
    """
    session = SessionLocal()
    try:
        course = models.Course(title=title, description="")
        module = models.Module(title="Module 1", position=0)
        for index, concept in enumerate(concepts):
            lesson = models.Lesson(
                title=f"Lesson {index}",
                position=index,
                content="# L",
                concepts=[concept],
            )
            lesson.quiz_items.append(
                models.QuizItem(
                    question=f"Q{index}?",
                    kind="short",
                    options=[],
                    answer="a",
                    concept=concept,
                )
            )
            module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.commit()

        for lesson in module.lessons[:completed]:
            lesson.completed_at = models.utcnow()
        for lesson in module.lessons[:attempts]:
            session.add(
                models.Attempt(
                    quiz_item_id=lesson.quiz_items[0].id,
                    lesson_id=lesson.id,
                    concept_key=lesson.concepts[0],
                    concept_label=lesson.concepts[0],
                    submitted_answer="a",
                    expected_answer="a",
                    correct=True,
                    attempt_no=1,
                )
            )
        session.commit()
        return course.id
    finally:
        session.close()


def _schedule(concept, with_note=False):
    """Give a concept a real card, a real log, and optionally a remediation note."""
    session = SessionLocal()
    try:
        review.record_review(session, concept, concept, fsrs.GOOD)
        session.commit()
        card = (
            session.query(models.ReviewCard)
            .filter(models.ReviewCard.concept_key == concept)
            .one()
        )
        if with_note:
            session.add(
                models.RemediationNote(
                    card_id=card.id,
                    concept_key=concept,
                    concept_label=concept,
                    content="Try it this way instead.",
                )
            )
            session.commit()
        return card.id
    finally:
        session.close()


def _counts(concept, card_id):
    session = SessionLocal()
    try:
        return {
            "cards": session.query(models.ReviewCard)
            .filter(models.ReviewCard.concept_key == concept)
            .count(),
            "logs": session.query(models.ReviewLog)
            .filter(models.ReviewLog.card_id == card_id)
            .count(),
            "notes": session.query(models.RemediationNote)
            .filter(models.RemediationNote.card_id == card_id)
            .count(),
        }
    finally:
        session.close()


def _delete(course_id):
    session = SessionLocal()
    try:
        return deletion.delete_course(session, session.get(models.Course, course_id))
    finally:
        session.close()


def _preview(course_id):
    session = SessionLocal()
    try:
        return deletion.deletion_preview(session, session.get(models.Course, course_id))
    finally:
        session.close()


# --------------------------------------------------------------------------
# The sharing guard
# --------------------------------------------------------------------------


def test_a_concept_another_course_teaches_keeps_its_card_untouched():
    """THE GUARANTEE. Both courses exist, and the survivor really does name the concept.

    The concepts_kept assertion runs FIRST and is not decoration: it is what stops this
    test passing vacuously. If the surviving course did not name the shared concept, an
    implementation that ignored other courses entirely would delete the card and this test
    would still be green, which is the shape of failure this whole file is built against.
    """
    shared = _key("shared")
    only_mine = _key("mine")
    card_id = _schedule(shared, with_note=True)

    doomed = _make_course([shared, only_mine], title="Doomed")
    _make_course([shared], title="Survivor")

    preview = _preview(doomed)
    assert preview["concepts_total"] == 2
    assert preview["concepts_kept"] == 1, "vacuous: the survivor does not name the concept"
    assert preview["concepts_retired"] == 1

    _delete(doomed)

    after = _counts(shared, card_id)
    assert after["cards"] == 1
    assert after["logs"] >= 1
    assert after["notes"] == 1


def test_a_concept_only_the_deleted_course_taught_loses_card_logs_and_notes():
    """The other half. Notes are the ones that need saying: ReviewCard has no relationship
    to RemediationNote, only a bare ForeignKey, and SQLite here runs with foreign keys off,
    so a card deleted without touching them leaves rows pointing at nothing and no layer
    complains."""
    orphan = _key("orphan")
    card_id = _schedule(orphan, with_note=True)

    before = _counts(orphan, card_id)
    assert before == {"cards": 1, "logs": 1, "notes": 1}

    doomed = _make_course([orphan], title="Only Teacher")
    result = _delete(doomed)

    assert result["concepts_retired"] == 1
    assert result["concepts_kept"] == 0
    assert _counts(orphan, card_id) == {"cards": 0, "logs": 0, "notes": 0}


def test_sharing_is_decided_across_quiz_items_as_well_as_lesson_concepts():
    """A course can name a concept in either place, and both count as teaching it.

    Reading only lesson.concepts would retire a card that a surviving course still asks
    questions about, which is the sharing bug with a smaller blast radius.
    """
    shared = _key("viaquiz")
    card_id = _schedule(shared)

    doomed = _make_course([shared], title="Doomed")

    # A survivor that names the concept ONLY on a quiz item, with an unrelated lesson
    # concept list.
    session = SessionLocal()
    try:
        course = models.Course(title="Quiz Only Survivor", description="")
        module = models.Module(title="M", position=0)
        lesson = models.Lesson(title="L", position=0, content="# L", concepts=["something else"])
        lesson.quiz_items.append(
            models.QuizItem(
                question="Q?", kind="short", options=[], answer="a", concept=shared
            )
        )
        module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.commit()
    finally:
        session.close()

    assert _preview(doomed)["concepts_kept"] == 1
    _delete(doomed)
    assert _counts(shared, card_id)["cards"] == 1


def test_a_concept_is_shared_under_normalization_not_exact_text():
    """"Gradient Descent." and "gradient descent" are one concept, and the sharing check
    has to agree with the card key, which is normalized. A second local folding rule would
    make this the case where the two disagree."""
    shared = _key("normalized")
    card_id = _schedule(shared)

    doomed = _make_course([shared], title="Doomed")
    _make_course([f"  {shared.upper()}. "], title="Survivor Spelled Differently")

    assert _preview(doomed)["concepts_kept"] == 1
    _delete(doomed)
    assert _counts(shared, card_id)["cards"] == 1


# --------------------------------------------------------------------------
# The cascade, and the things that must not go with it
# --------------------------------------------------------------------------


def test_the_course_and_everything_under_it_is_gone():
    """Including every attempt, which is the biggest thing this destroys."""
    concept = _key("cascade")
    course_id = _make_course([concept, _key("other")], title="Doomed", completed=1, attempts=2)

    session = SessionLocal()
    try:
        course = session.get(models.Course, course_id)
        lesson_ids = [lesson.id for module in course.modules for lesson in module.lessons]
        item_ids = [
            item.id
            for module in course.modules
            for lesson in module.lessons
            for item in lesson.quiz_items
        ]
    finally:
        session.close()
    assert lesson_ids and item_ids

    _delete(course_id)

    session = SessionLocal()
    try:
        assert session.get(models.Course, course_id) is None
        assert (
            session.query(models.Lesson).filter(models.Lesson.id.in_(lesson_ids)).count() == 0
        )
        assert (
            session.query(models.QuizItem).filter(models.QuizItem.id.in_(item_ids)).count() == 0
        )
        assert (
            session.query(models.Attempt)
            .filter(models.Attempt.lesson_id.in_(lesson_ids))
            .count()
            == 0
        )
    finally:
        session.close()


def test_spend_survives_the_course_it_was_spent_on():
    """LlmCall.course_id is a plain nullable integer with no ForeignKey, and its docstring
    says why: usage history outlives the course. Money really was spent."""
    course_id = _make_course([_key("spend")], title="Expensive")

    session = SessionLocal()
    try:
        session.add(
            models.LlmCall(
                run_id=uuid4().hex[:16],
                course_id=course_id,
                provider="anthropic",
                model="claude-opus-5",
                stage="outline",
                input_tokens=1000,
                output_tokens=500,
                estimated_cost_usd=0.25,
            )
        )
        session.commit()
    finally:
        session.close()

    result = _delete(course_id)
    assert result["spend_usd"] == 0.25

    session = SessionLocal()
    try:
        surviving = (
            session.query(models.LlmCall).filter(models.LlmCall.course_id == course_id).all()
        )
        assert len(surviving) == 1
        assert surviving[0].estimated_cost_usd == 0.25
    finally:
        session.close()


def test_a_course_with_no_lessons_deletes_cleanly():
    """Nothing to count and nothing to retire, and no branch that divides by any of it.

    spend_usd is deliberately NOT asserted to be zero here. This test asserts that an empty
    course counts as empty, and a brand new course's spend is not actually guaranteed to be
    zero: courses.id is an INTEGER PRIMARY KEY with no AUTOINCREMENT, so SQLite hands a
    freed id to the next insert, and llm_calls rows carry a plain integer course_id with no
    ForeignKey and are deliberately left behind by deletion. A new course can therefore
    inherit a deleted one's spend. That is a real defect, measured and reported, and it is
    not this test's job either to enforce it away or to bless it: an assertion here would
    have been passing on the accident that no earlier test had freed an id.
    """
    course_id = _make_course([], title="Empty")

    result = _delete(course_id)

    assert result["lessons"] == 0
    assert result["quiz_items"] == 0
    assert result["attempts"] == 0
    assert result["concepts_total"] == 0
    assert result["concepts_retired"] == 0
    assert result["concepts_kept"] == 0

    session = SessionLocal()
    try:
        assert session.get(models.Course, course_id) is None
    finally:
        session.close()


def test_retiring_a_concept_nobody_ever_studied_is_not_an_error():
    """A concept with no card is still a concept this course was the last to name, so it
    counts as retired; there is simply nothing to delete for it."""
    never_studied = _key("unstudied")
    course_id = _make_course([never_studied], title="Never Opened")

    result = _delete(course_id)

    assert result["concepts_total"] == 1
    assert result["concepts_retired"] == 1

    session = SessionLocal()
    try:
        assert (
            session.query(models.ReviewCard)
            .filter(models.ReviewCard.concept_key == never_studied)
            .count()
            == 0
        )
    finally:
        session.close()


# --------------------------------------------------------------------------
# The preview told the truth
# --------------------------------------------------------------------------


def test_the_preview_equals_what_the_delete_actually_reports():
    """THE ACCEPTANCE CRITERION, run against one fixture rather than two similar ones.

    The learner consents to the preview and is then told what happened, so the two have to
    be the same numbers about the same database. Both come from one summary function, and
    delete_course computes it BEFORE removing anything, which is what makes this hold by
    construction rather than by two implementations staying in step.
    """
    shared = _key("both")
    unique = _key("solo")
    _schedule(shared)
    _schedule(unique)

    doomed = _make_course([shared, unique], title="Doomed", completed=1, attempts=2)
    _make_course([shared], title="Survivor")

    preview = _preview(doomed)
    result = _delete(doomed)

    assert preview == result
    # And it is not trivially equal because everything is zero.
    assert preview["lessons"] == 2
    assert preview["lessons_completed"] == 1
    assert preview["quiz_items"] == 2
    assert preview["attempts"] == 2
    assert preview["concepts_total"] == 2
    assert preview["concepts_kept"] == 1
    assert preview["concepts_retired"] == 1


def test_the_preview_writes_nothing():
    """It is shown on a confirmation screen the learner may well abandon."""
    concept = _key("previewonly")
    card_id = _schedule(concept, with_note=True)
    course_id = _make_course([concept], title="Still Here")

    _preview(course_id)
    _preview(course_id)

    session = SessionLocal()
    try:
        assert session.get(models.Course, course_id) is not None
    finally:
        session.close()
    assert _counts(concept, card_id) == {"cards": 1, "logs": 1, "notes": 1}
