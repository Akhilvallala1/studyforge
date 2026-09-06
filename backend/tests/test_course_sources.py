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
    provider entirely.

    The lesson carries "segments": [0], the real shape generate_questions_course
    produces, so this exercises the actual (post-B4a) segments-to-source mapping rather
    than the placeholder lesson-index pairing it replaced. `positions=[0]` says chunk 0
    came from source position 0, which is true here: the one source's text is short
    enough to be a single chunk.
    """
    course = {
        "title": "Anchored Course",
        "description": "",
        "modules": [
            {
                "title": "Module 1",
                "lessons": [{"title": "The Source", "content": "", "segments": [0]}],
            }
        ],
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
        row = main._save_course(session, course, sources, mode="source", positions=[0])
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


def test_lesson_source_position_picks_the_majority_source_breaking_ties_by_lowest_position():
    # A clear majority: three segments from source 1, one from source 0.
    assert main._lesson_source_position([0, 1, 1, 1], [0, 1, 1, 1]) == 1
    # A tie between sources 0 and 1: lowest position wins.
    assert main._lesson_source_position([0, 1], [0, 1]) == 0
    # Empty segments and segments indexing nothing both leave it unresolved.
    assert main._lesson_source_position([], [0, 1]) is None
    assert main._lesson_source_position([5, 6], [0, 1]) is None


def test_one_source_producing_many_lessons_anchors_each_to_that_one_source():
    """The exact case the Nth-lesson-to-Nth-source placeholder got wrong: one source
    that yields several chunks, each lesson using a different subset of them, must
    all resolve to that same single source rather than only the first N lessons.
    """
    course = {
        "title": "One Source, Many Lessons",
        "description": "",
        "modules": [
            {
                "title": "Module 1",
                "lessons": [
                    {"title": "Lesson 1", "content": "", "segments": [0]},
                    {"title": "Lesson 2", "content": "", "segments": [1]},
                    {"title": "Lesson 3", "content": "", "segments": [2]},
                ],
            }
        ],
    }
    sources = [
        ingest.Source(key="", kind="text", ref="wide.txt", text="alpha beta gamma", locator="")
    ]
    session = SessionLocal()
    try:
        row = main._save_course(session, course, sources, mode="source", positions=[0, 0, 0])
        session.refresh(row)
        source_id = row.sources[0].id
        lessons = [lesson for module in row.modules for lesson in module.lessons]
        assert len(lessons) == 3
        assert all(lesson.source_id == source_id for lesson in lessons)
    finally:
        session.close()


def test_a_lesson_spanning_two_sources_anchors_to_the_majority_one():
    course = {
        "title": "Split Lesson",
        "description": "",
        "modules": [
            {
                "title": "Module 1",
                "lessons": [
                    {"title": "Mostly Second", "content": "", "segments": [0, 1, 2]},
                ],
            }
        ],
    }
    sources = [
        ingest.Source(key="", kind="text", ref="first.txt", text="one", locator=""),
        ingest.Source(key="", kind="text", ref="second.txt", text="two three", locator=""),
    ]
    # chunk 0 came from source 0, chunks 1 and 2 came from source 1: majority is source 1.
    session = SessionLocal()
    try:
        row = main._save_course(session, course, sources, mode="source", positions=[0, 1, 1])
        session.refresh(row)
        lesson = row.modules[0].lessons[0]
        assert lesson.source_id == row.sources[1].id
    finally:
        session.close()


def test_two_sources_sharing_an_identical_ref_are_still_told_apart():
    """Two uploads named the same thing must not collide: the mapping keys on
    source POSITION (from `positions`), never on `ref`.
    """
    course = {
        "title": "Same Filename Twice",
        "description": "",
        "modules": [
            {
                "title": "Module 1",
                "lessons": [
                    {"title": "From First", "content": "", "segments": [0]},
                    {"title": "From Second", "content": "", "segments": [1]},
                ],
            }
        ],
    }
    sources = [
        ingest.Source(key="", kind="text", ref="notes.pdf", text="first copy", locator=""),
        ingest.Source(key="", kind="text", ref="notes.pdf", text="second copy", locator=""),
    ]
    session = SessionLocal()
    try:
        row = main._save_course(session, course, sources, mode="source", positions=[0, 1])
        session.refresh(row)
        lessons = row.modules[0].lessons
        assert lessons[0].source_id == row.sources[0].id
        assert lessons[1].source_id == row.sources[1].id
        assert lessons[0].source_id != lessons[1].source_id
    finally:
        session.close()


def test_a_lesson_with_no_valid_segments_leaves_source_id_null_instead_of_guessing():
    course = {
        "title": "No Segments",
        "description": "",
        "modules": [
            {"title": "Module 1", "lessons": [{"title": "Orphan", "content": ""}]},
        ],
    }
    sources = [ingest.Source(key="", kind="text", ref="a.txt", text="alpha", locator="")]
    session = SessionLocal()
    try:
        row = main._save_course(session, course, sources, mode="source", positions=[0])
        session.refresh(row)
        lesson = row.modules[0].lessons[0]
        assert lesson.content_kind == "source"
        assert lesson.source_id is None
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


def test_deletion_summary_reports_the_sources_and_bytes_the_cascade_is_about_to_free():
    """B6: _summary's two new keys, checked against real numbers rather than just shape.

    stored_bytes is asserted against the blob's own length rather than a hardcoded
    number, so this stays correct if the fixture's source text ever changes.
    """
    course_id = _save_source_mode_course()

    session = SessionLocal()
    try:
        source = session.query(models.CourseSource).filter(
            models.CourseSource.course_id == course_id
        ).one()
        blob = (
            session.query(models.CourseSourceBlob)
            .filter(models.CourseSourceBlob.source_id == source.id)
            .one()
        )

        preview = deletion.deletion_preview(session, session.get(models.Course, course_id))
        assert preview["sources"] == 1
        assert preview["stored_bytes"] == len(blob.data)

        course = session.get(models.Course, course_id)
        payload = deletion.delete_course(session, course)
        assert payload["sources"] == 1
        assert payload["stored_bytes"] == len(blob.data)
    finally:
        session.close()
