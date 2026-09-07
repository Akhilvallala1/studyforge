"""B4b/B4a end to end: `mode` is reachable on the two generate endpoints that take it,
and a real generation run tags every lesson with the source that actually wrote it.

test_course_sources.py already pins the mapping logic (_lesson_source_position and
_save_course) directly. This file is scoped to what is genuinely new here: the endpoints
route to generate_questions_course when asked, and a real multi-lesson, one-source run
comes out anchored correctly through the whole pipeline, not just through a hand-built
course dict.
"""

import io

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app import ingest, main, models
from app.db import SessionLocal
from app.llm.fake_provider import FakeProvider
from tests.test_multi_source import NeverCalledProvider

# Long enough, and paragraph-shaped enough, to be chunked into several pieces by
# ingest.chunk_text (MAX_CHUNK_CHARS=8000), so the fake outline's round-robin dealing
# spreads real segments across all four of its lesson slots instead of dumping
# everything into lesson one.
WIDE_SOURCE = "\n\n".join(f"Paragraph {i} about gradient descent walks downhill." * 80 for i in range(8))


def _lessons(client, course_id):
    course = client.get(f"/courses/{course_id}").json()
    return [
        client.get(f"/lessons/{stub['id']}").json()
        for module in course["modules"]
        for stub in module["lessons"]
    ]


def test_json_route_mode_source_tags_every_lesson_source_kind_with_content_from_the_text(
    client, monkeypatch
):
    """GET /lessons/{id} does not surface content_kind or source_id (out of scope for
    this task; nothing in B4/B5/B6 asks for it), so those two are checked against the
    row directly. `content` is already on the read response, so that half is checked
    through the real API the way a client would.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())

    resp = client.post("/courses/generate", json={"text": WIDE_SOURCE, "mode": "source"})
    assert resp.status_code == 200, resp.text
    course_id = resp.json()["id"]

    lessons = _lessons(client, course_id)
    assert len(lessons) > 1, "fixture must produce more than one lesson to be a real test"
    cleaned = ingest.clean_text(WIDE_SOURCE)
    for lesson in lessons:
        assert lesson["content"], "source-mode content must not be empty"
        assert lesson["content"] in cleaned, "content must be verbatim source text"

    session = SessionLocal()
    try:
        course = session.get(models.Course, course_id)
        for lesson in (lesson for module in course.modules for lesson in module.lessons):
            assert lesson.content_kind == "source"
    finally:
        session.close()


def test_json_route_mode_source_anchors_every_lesson_to_the_one_source_it_came_from(
    client, monkeypatch
):
    """The exact case the Nth-lesson-to-Nth-source placeholder got wrong, run through
    the real endpoint rather than through a hand-built course dict.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())

    resp = client.post("/courses/generate", json={"text": WIDE_SOURCE, "mode": "source"})
    assert resp.status_code == 200, resp.text
    course_id = resp.json()["id"]

    session = SessionLocal()
    try:
        course = session.get(models.Course, course_id)
        assert len(course.sources) == 1
        source_id = course.sources[0].id
        lessons = [lesson for module in course.modules for lesson in module.lessons]
        assert len(lessons) > 1
        assert all(lesson.source_id == source_id for lesson in lessons)
    finally:
        session.close()


def test_multipart_route_mode_source_writes_a_blob_and_tags_the_lesson(client, monkeypatch):
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    monkeypatch.setattr(ingest, "extract_pdf", lambda data: data.decode())

    pdf_bytes = ("Gradient descent walks downhill. " * 200).encode()
    resp = client.post(
        "/courses/generate/multipart",
        data={"mode": "source"},
        files={"file": ("notes.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    course_id = resp.json()["id"]

    session = SessionLocal()
    try:
        course = session.get(models.Course, course_id)
        assert len(course.sources) == 1
        source = course.sources[0]
        blob = (
            session.query(models.CourseSourceBlob)
            .filter(models.CourseSourceBlob.source_id == source.id)
            .one_or_none()
        )
        assert blob is not None
        assert blob.data == pdf_bytes

        lessons = [lesson for module in course.modules for lesson in module.lessons]
        assert lessons
        for lesson in lessons:
            assert lesson.content_kind == "source"
            assert lesson.source_id == source.id
    finally:
        session.close()


def test_multipart_route_mode_defaults_to_lessons_when_omitted(client, monkeypatch):
    """Every existing caller of this route never sends `mode` at all, so it must keep
    getting lesson-mode output exactly as before.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    monkeypatch.setattr(ingest, "extract_pdf", lambda data: data.decode())

    pdf_bytes = ("Gradient descent walks downhill. " * 200).encode()
    resp = client.post(
        "/courses/generate/multipart",
        files={"file": ("notes.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    course_id = resp.json()["id"]

    session = SessionLocal()
    try:
        course = session.get(models.Course, course_id)
        lessons = [lesson for module in course.modules for lesson in module.lessons]
        assert lessons
        for lesson in lessons:
            assert lesson.content_kind == "lesson"
            assert lesson.source_id is None

        blobs = (
            session.query(models.CourseSourceBlob)
            .filter(models.CourseSourceBlob.source_id == course.sources[0].id)
            .all()
        )
        assert blobs == [], "lessons mode must never write the original bytes to a blob"
    finally:
        session.close()


def test_pdf_route_mode_source_writes_a_blob_and_tags_the_lesson(client, monkeypatch):
    """The PDF-only route takes `mode` too, for API consistency with the multipart
    route, even though the web UI itself posts uploads to /courses/generate/multipart
    (frontend/src/lib/api.ts) rather than this one.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    monkeypatch.setattr(ingest, "extract_pdf", lambda data: data.decode())

    pdf_bytes = ("Gradient descent walks downhill. " * 200).encode()
    resp = client.post(
        "/courses/generate/pdf",
        data={"mode": "source"},
        files={"file": ("notes.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    course_id = resp.json()["id"]

    session = SessionLocal()
    try:
        course = session.get(models.Course, course_id)
        assert len(course.sources) == 1
        source = course.sources[0]
        blob = (
            session.query(models.CourseSourceBlob)
            .filter(models.CourseSourceBlob.source_id == source.id)
            .one_or_none()
        )
        assert blob is not None and blob.data == pdf_bytes

        lessons = [lesson for module in course.modules for lesson in module.lessons]
        assert lessons
        for lesson in lessons:
            assert lesson.content_kind == "source"
            assert lesson.source_id == source.id
    finally:
        session.close()


def test_pdf_route_mode_defaults_to_lessons_when_omitted(client, monkeypatch):
    """This route predates `mode` and has live callers that never send it."""
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    monkeypatch.setattr(ingest, "extract_pdf", lambda data: data.decode())

    pdf_bytes = ("Gradient descent walks downhill. " * 200).encode()
    resp = client.post(
        "/courses/generate/pdf",
        files={"file": ("notes.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200, resp.text

    session = SessionLocal()
    try:
        course = session.get(models.Course, resp.json()["id"])
        lessons = [lesson for module in course.modules for lesson in module.lessons]
        assert lessons
        for lesson in lessons:
            assert lesson.content_kind == "lesson"
            assert lesson.source_id is None

        blobs = (
            session.query(models.CourseSourceBlob)
            .filter(models.CourseSourceBlob.source_id == course.sources[0].id)
            .all()
        )
        assert blobs == [], "lessons mode must never write the original bytes to a blob"
    finally:
        session.close()


def test_pdf_route_over_cap_uploads_are_refused_without_reading_any_file(client, monkeypatch):
    """Finding 7: /courses/generate/pdf shares _check_upload_size with the multipart
    route (see test_generate_multipart.test_over_cap_uploads_are_refused_without_reading_any_file,
    the test this mirrors), so an over-budget batch is refused before extract_pdf runs.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())
    pdf_reads: list[bytes] = []
    monkeypatch.setattr(ingest, "extract_pdf", lambda data: pdf_reads.append(data) or data.decode())
    each = ingest.MAX_UPLOAD_BYTES // 2 + 1

    resp = client.post(
        "/courses/generate/pdf",
        files=[
            ("file", ("a.pdf", b"x" * each, "application/pdf")),
            ("file", ("b.pdf", b"x" * each, "application/pdf")),
        ],
    )

    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "source_too_large"
    assert str(ingest.MAX_UPLOAD_BYTES) in detail["message"].replace(",", "")
    assert pdf_reads == [], "the byte cap must refuse before any uploaded PDF is read"


def test_pdf_route_unknown_upload_size_is_refused_as_over_cap_not_under():
    """Finding 7's direct-call sibling of test_generate_multipart's own version: an
    UploadFile with no known size must be refused, not summed as zero, on this route too.
    """
    upload = UploadFile(file=io.BytesIO(b"x" * 10), size=None, filename="huge.pdf")

    with pytest.raises(HTTPException) as exc_info:
        main.generate_from_pdf(file=[upload], mode="lessons", session=None)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"] == "source_too_large"
