"""Source-anchored storage: the two new tables and what a course generation writes to them.

Phase B1/B3 add course_sources and course_source_blobs and plumb ingest.Source through
_save_course, with no endpoint yet choosing "source" mode. Two things matter most here: the
default "lessons" path must behave exactly as before (that is the whole risk of touching
_save_course at all), and a course's sources must not outlive the course except in the one
place (llm_calls) that is supposed to survive deletion.
"""

from uuid import uuid4

from app import deletion, ingest, main, models
from app.db import SessionLocal
from app.llm.fake_provider import FakeProvider


def _key(prefix):
    return f"{prefix}-{uuid4().hex[:10]}"


def test_default_lessons_mode_writes_no_blobs_and_every_lesson_stays_lesson_kind(
    client, monkeypatch
):
    """A real generation run, through the actual PDF endpoint, in the untouched default
    mode. This is the regression test the task calls for: _save_course changed shape and
    the one path every existing caller uses (mode="lessons") must be indistinguishable
    from before it did.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    monkeypatch.setattr(ingest, "extract_pdf", lambda data: data.decode())
    pdf_bytes = f"Gradient descent walks downhill. {_key('body')} " * 30
    pdf_bytes = pdf_bytes.encode()

    response = client.post(
        "/courses/generate/pdf",
        files={"file": ("notes.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200, response.text
    course_id = response.json()["id"]

    session = SessionLocal()
    try:
        course = session.get(models.Course, course_id)
        lessons = [lesson for module in course.modules for lesson in module.lessons]
        assert lessons, "the fake provider always produces at least one lesson"
        for lesson in lessons:
            assert lesson.content_kind == "lesson"
            assert lesson.source_id is None

        sources = (
            session.query(models.CourseSource)
            .filter(models.CourseSource.course_id == course_id)
            .all()
        )
        assert len(sources) == 1
        assert sources[0].kind == "pdf"
        assert sources[0].byte_size == len(pdf_bytes)

        blobs = (
            session.query(models.CourseSourceBlob)
            .filter(models.CourseSourceBlob.source_id == sources[0].id)
            .all()
        )
        assert blobs == [], "lessons mode must never write the original bytes to a blob"
    finally:
        session.close()


def _save_source_mode_course():
    """One course saved directly through _save_course in mode="source", bypassing the
    provider entirely: no endpoint chooses this mode yet, so this is the only way to
    exercise it before B4/B5 exist.
    """
    course = {
        "title": "Anchored Course",
        "description": "",
        "modules": [{"title": "Module 1", "lessons": [{"title": "The Source", "content": ""}]}],
    }
    sources = [
        ingest.Source(
            key="",
            kind="pdf",
            ref="notes.pdf",
            text="Gradient descent walks downhill.",
            locator="",
            raw=b"%PDF-1.4 fake bytes",
        )
    ]
    session = SessionLocal()
    try:
        row = main._save_course(session, course, sources, mode="source")
        return row.id
    finally:
        session.close()


def test_source_mode_writes_a_blob_and_tags_the_lesson():
    """The other half of the same change: mode="source" is the one existing tests cannot
    reach through any endpoint, so it is pinned directly against _save_course.
    """
    course_id = _save_source_mode_course()

    session = SessionLocal()
    try:
        course = session.get(models.Course, course_id)
        lesson = course.modules[0].lessons[0]
        source = (
            session.query(models.CourseSource)
            .filter(models.CourseSource.course_id == course_id)
            .one()
        )
        assert lesson.content_kind == "source"
        assert lesson.source_id == source.id

        blob = (
            session.query(models.CourseSourceBlob)
            .filter(models.CourseSourceBlob.source_id == source.id)
            .one()
        )
        assert blob.data == b"%PDF-1.4 fake bytes"
    finally:
        session.close()


def test_deleting_a_course_removes_its_sources_and_blobs_but_spend_survives_stamped():
    """The load-bearing survival behaviour: llm_calls is untouched by the cascade and
    still resolvable through course_title_at_deletion after the course, its sources and
    its blob are all gone.
    """
    course_id = _save_source_mode_course()
    run_id = uuid4().hex[:16]

    session = SessionLocal()
    try:
        source_ids = [
            row.id
            for row in session.query(models.CourseSource).filter(
                models.CourseSource.course_id == course_id
            )
        ]
        assert source_ids, "fixture must have created at least one source"
        assert (
            session.query(models.CourseSourceBlob)
            .filter(models.CourseSourceBlob.source_id.in_(source_ids))
            .count()
            == 1
        )

        session.add(
            models.LlmCall(
                run_id=run_id,
                course_id=course_id,
                provider="anthropic",
                model="claude-opus-5",
                stage="outline",
                input_tokens=10,
                output_tokens=5,
                estimated_cost_usd=0.02,
            )
        )
        session.commit()

        course = session.get(models.Course, course_id)
        deletion.delete_course(session, course)

        assert session.get(models.Course, course_id) is None
        assert (
            session.query(models.CourseSource)
            .filter(models.CourseSource.course_id == course_id)
            .count()
            == 0
        )
        assert (
            session.query(models.CourseSourceBlob)
            .filter(models.CourseSourceBlob.source_id.in_(source_ids))
            .count()
            == 0
        )

        call = session.query(models.LlmCall).filter(models.LlmCall.run_id == run_id).one()
        assert call.course_title_at_deletion == "Anchored Course"
    finally:
        session.close()
