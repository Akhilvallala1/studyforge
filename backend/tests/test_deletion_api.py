"""The two deletion endpoints, and the contract decisions that are easy to undo by accident.

Four of the assertions here exist to pin choices rather than to catch bugs: the 404 detail
is a bare string, the success is 200 with a body rather than 204, a second delete is a 404
rather than a success, and there is no refusal code at all. Each is a decision somebody
could reasonably make the other way, so each says why.
"""

from uuid import uuid4

import pytest

from app import fsrs, models, review
from app.db import SessionLocal

PAYLOAD_KEYS = {
    "course_id",
    "title",
    "lessons",
    "lessons_completed",
    "quiz_items",
    "attempts",
    "concepts_total",
    "concepts_retired",
    "concepts_kept",
    "spend_usd",
}


def _key(prefix):
    return f"{prefix}-{uuid4().hex[:10]}"


def _spend(course_id, amount):
    """Attribute one recorded provider call to a course."""
    session = SessionLocal()
    try:
        session.add(
            models.LlmCall(
                run_id=uuid4().hex[:16],
                course_id=course_id,
                provider="anthropic",
                model="claude-opus-5",
                stage="outline",
                input_tokens=10,
                output_tokens=5,
                estimated_cost_usd=amount,
            )
        )
        session.commit()
    finally:
        session.close()


def _make_course(concepts, title="Course"):
    session = SessionLocal()
    try:
        course = models.Course(title=title, description="")
        module = models.Module(title="M", position=0)
        for index, concept in enumerate(concepts):
            lesson = models.Lesson(
                title=f"L{index}", position=index, content="# L", concepts=[concept]
            )
            lesson.quiz_items.append(
                models.QuizItem(
                    question="Q?", kind="short", options=[], answer="a", concept=concept
                )
            )
            module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.commit()
        return course.id
    finally:
        session.close()


def test_deleting_a_course_answers_200_with_a_body(client):
    """200 AND A BODY, never 204. api.ts's request() ends in `return res.json()`
    unconditionally, so a 204 throws in the client on the success path, which is the worst
    place to put a throw. Both existing DELETE routes already return bodies."""
    course_id = _make_course([_key("api")], title="Doomed")

    response = client.delete(f"/courses/{course_id}")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PAYLOAD_KEYS
    assert body["course_id"] == course_id
    assert body["title"] == "Doomed"
    assert body["lessons"] == 1


def test_the_preview_answers_the_same_shape_without_deleting(client):
    """Same keys, because the learner consents to one and is then shown the other."""
    course_id = _make_course([_key("api"), _key("api")], title="Preview Me")

    preview = client.get(f"/courses/{course_id}/deletion-preview")

    assert preview.status_code == 200
    assert set(preview.json()) == PAYLOAD_KEYS
    assert preview.json()["lessons"] == 2
    assert client.get(f"/courses/{course_id}").status_code == 200

    # And the two agree, over HTTP and not only in the module.
    assert client.delete(f"/courses/{course_id}").json() == preview.json()


def test_a_missing_course_is_404_with_a_bare_string_detail(client):
    """A BARE STRING, matching the other course routes, and asserted as a string rather
    than merely as "not a coded object". A client writes two branches here on purpose:
    one for the shapeless 404s that mean the thing is not there, one for the coded 422s
    that mean the request was wrong. Giving this a code would quietly move it between
    them."""
    for response in (
        client.delete("/courses/987654"),
        client.get("/courses/987654/deletion-preview"),
    ):
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert isinstance(detail, str)
        assert detail == "Course not found"


def test_deleting_twice_is_a_404_and_not_a_success(client):
    """NOT IDEMPOTENT, deliberately unlike DELETE /plan/days-off/{day}.

    A day off is set membership, so removing an absent one leaves the learner in exactly
    the state they asked for and a 200 is honest. A course is an entity: the second call
    names something that does not exist, and answering 200 would tell a client its delete
    worked when there was nothing to delete, which hides a bug in the caller rather than
    the caller's own.
    """
    course_id = _make_course([_key("twice")], title="Once")

    assert client.delete(f"/courses/{course_id}").status_code == 200
    second = client.delete(f"/courses/{course_id}")
    assert second.status_code == 404
    assert second.json()["detail"] == "Course not found"


def test_the_course_disappears_from_the_list(client):
    course_id = _make_course([_key("listed")], title="Listed")
    assert any(row["id"] == course_id for row in client.get("/courses").json())

    client.delete(f"/courses/{course_id}")

    assert not any(row["id"] == course_id for row in client.get("/courses").json())
    assert client.get(f"/courses/{course_id}").status_code == 404


def test_a_shared_concept_still_answers_over_http(client):
    """The guard, through the endpoint rather than the module, because the endpoint is
    what the learner actually reaches. concepts_kept is asserted first so this cannot pass
    with a survivor that does not really name the concept."""
    shared = _key("httpshared")
    session = SessionLocal()
    try:
        review.record_review(session, shared, shared, fsrs.GOOD)
        session.commit()
    finally:
        session.close()

    doomed = _make_course([shared], title="Doomed")
    _make_course([shared], title="Survivor")

    body = client.delete(f"/courses/{doomed}").json()
    assert body["concepts_kept"] == 1
    assert body["concepts_retired"] == 0

    session = SessionLocal()
    try:
        assert (
            session.query(models.ReviewCard)
            .filter(models.ReviewCard.concept_key == shared)
            .count()
            == 1
        )
    finally:
        session.close()


def test_usage_still_answers_and_still_reports_the_deleted_courses_spend(client):
    """Spend outlives the course, and /usage was already built for it.

    The row keeps its money and its NAME, because deletion stamps the title onto it.
    `title` stays None, which is still how a client asks whether the course exists; the
    stamp shows up in `label`, which is what the learner reads.
    """
    course_id = _make_course([_key("usage")], title="Costly")
    session = SessionLocal()
    try:
        session.add(
            models.LlmCall(
                run_id=uuid4().hex[:16],
                course_id=course_id,
                provider="anthropic",
                model="claude-opus-5",
                stage="outline",
                input_tokens=10,
                output_tokens=5,
                estimated_cost_usd=0.5,
            )
        )
        session.commit()
    finally:
        session.close()

    before = client.get("/usage").json()
    assert before["totals"]["estimated_cost_usd"] >= 0.5

    client.delete(f"/courses/{course_id}")

    after = client.get("/usage")
    assert after.status_code == 200
    body = after.json()

    # The money is still in the total.
    assert body["totals"]["estimated_cost_usd"] == before["totals"]["estimated_cost_usd"]

    orphaned = [row for row in body["per_course"] if row["course_id"] == course_id]
    assert len(orphaned) == 1
    row = orphaned[0]
    assert row["estimated_cost_usd"] == 0.5
    assert row["title"] is None
    assert row["label"] == "Costly"


def test_a_reused_course_id_does_not_inherit_the_deleted_courses_spend(client):
    """THE DEFECT, reproduced exactly as it was found.

    courses.id is an INTEGER PRIMARY KEY with no AUTOINCREMENT, so SQLite reissues a
    deleted course's id to the next course created. Before the stamp, the surviving spend
    rows resolved to that new course and its bill silently absorbed the old one's.

    The id-reuse assertion is not decoration. If SQLite ever stopped reissuing the id this
    test would prove nothing at all, and it should say so rather than pass quietly.
    """
    doomed = _make_course([_key("reuse")], title="Old Course")
    _spend(doomed, 0.25)
    before_total = client.get("/usage").json()["totals"]["estimated_cost_usd"]

    client.delete(f"/courses/{doomed}")

    fresh = _make_course([_key("reuse")], title="New Course")
    assert fresh == doomed, (
        "this test needs the deleted id to actually be reissued; without that it cannot "
        "distinguish a working stamp from no stamp at all"
    )
    _spend(fresh, 0.10)

    body = client.get("/usage").json()
    rows = [row for row in body["per_course"] if row["course_id"] == doomed]

    # SEVERAL rows can share one id, one per course that has ever held it, and in the
    # shared suite database more than two usually do. That is the mechanism working: each
    # course's spend stays with the title it had. So this asserts on the two courses this
    # test created rather than on the total number of rows.
    assert len(rows) >= 2, [row["label"] for row in rows]
    by_label = {row["label"]: row for row in rows}
    assert "Old Course" in by_label and "New Course" in by_label
    assert by_label["Old Course"]["estimated_cost_usd"] == 0.25
    assert by_label["Old Course"]["title"] is None
    assert by_label["New Course"]["estimated_cost_usd"] == 0.10
    assert by_label["New Course"]["title"] == "New Course"

    # And nothing was lost or double counted along the way. approx because these are
    # floats and the suite-wide running total is rarely exactly representable.
    assert body["totals"]["estimated_cost_usd"] == pytest.approx(before_total + 0.10)


def test_a_reused_course_id_does_not_inherit_the_spend_in_the_preview_either(client):
    """THE SAME DEFECT ON THE CONSENT PATH, which is the half that matters more.

    /usage is a report somebody consults after the fact. The preview is the number on
    screen while a learner is being asked to agree to something irreversible, so it is the
    one place an inflated figure changes a decision rather than a reading.

    Mirrors test_a_reused_course_id_does_not_inherit_the_deleted_courses_spend, including
    asserting the id really was reissued: without that this cannot tell a working filter
    from no filter at all.
    """
    doomed = _make_course([_key("prev")], title="Old Course")
    _spend(doomed, 0.25)
    client.delete(f"/courses/{doomed}")

    fresh = _make_course([_key("prev")], title="New Course")
    assert fresh == doomed, (
        "this test needs the deleted id to actually be reissued; without that it cannot "
        "distinguish a working stamp filter from none"
    )
    _spend(fresh, 0.10)

    assert client.get(f"/courses/{fresh}/deletion-preview").json()["spend_usd"] == 0.10
    # And what the delete reports agrees with the preview the learner consented to.
    assert client.delete(f"/courses/{fresh}").json()["spend_usd"] == 0.10


def test_an_unstamped_row_still_resolves_the_old_way(client):
    """The upgrade path. Rows written before this column existed carry NULL, and NULL has
    to keep meaning "resolve my course_id", or an existing install would lose or relabel
    every historical attribution the moment it upgraded."""
    course_id = _make_course([_key("unstamped")], title="Still Alive")
    _spend(course_id, 0.05)

    row = next(
        row
        for row in client.get("/usage").json()["per_course"]
        if row["course_id"] == course_id
    )
    assert row["title"] == "Still Alive"
    assert row["label"] == "Still Alive"


def test_deleting_a_course_leaves_the_review_queue_answerable(client):
    """THE DEFECT THIS FEATURE EXISTS FOR, asserted end to end.

    Before the retirement step, a card whose only quiz items were deleted stayed due
    forever: Today counted it, the button rendered, and the session served nothing, with
    no action the learner could take to clear it. The queue and the due count now agree
    again after a delete.
    """
    concept = _key("queue")
    session = SessionLocal()
    try:
        review.record_review(session, concept, concept, fsrs.AGAIN)
        session.commit()
    finally:
        session.close()

    course_id = _make_course([concept], title="Sole Source")

    client.delete(f"/courses/{course_id}")

    queue = client.get("/review/queue").json()
    assert not any(card["concept_key"] == concept for card in queue["cards"])
    session = SessionLocal()
    try:
        assert (
            session.query(models.ReviewCard)
            .filter(models.ReviewCard.concept_key == concept)
            .count()
            == 0
        )
    finally:
        session.close()
