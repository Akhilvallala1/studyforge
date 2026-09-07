"""B5: reading a course's sources back, and serving one's original PDF bytes.

The list endpoint is a plain read and is tested mostly for shape. The file endpoint is
the security-sensitive one: THE CROSS-COURSE CASE IS THE ASSERTION THIS FILE IS FOR,
because a source_id that resolves but belongs to someone else's course is exactly the
shape of an IDOR, and it is worth naming as its own test rather than folding it into a
generic 404 check that a lazier implementation (session.get(CourseSource, source_id)
alone, with no course_id filter) would still pass.
"""

from urllib.parse import unquote
from uuid import uuid4

import h11
from sqlalchemy import event

from app import models
from app.db import SessionLocal, engine


def _course(title="Course"):
    session = SessionLocal()
    try:
        course = models.Course(title=title, description="")
        module = models.Module(title="M", position=0)
        lesson = models.Lesson(title="L", position=0, content="# L")
        module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.commit()
        return course.id
    finally:
        session.close()


def _add_source(
    course_id,
    position=0,
    kind="pdf",
    ref="notes.pdf",
    title="notes.pdf",
    locator="",
    char_count=10,
    byte_size=None,
    blob: bytes | None = None,
):
    session = SessionLocal()
    try:
        source = models.CourseSource(
            course_id=course_id,
            position=position,
            kind=kind,
            ref=ref,
            title=title,
            locator=locator,
            char_count=char_count,
            byte_size=byte_size if byte_size is not None else (len(blob) if blob else None),
        )
        session.add(source)
        session.flush()
        if blob is not None:
            session.add(models.CourseSourceBlob(source_id=source.id, data=blob))
        session.commit()
        return source.id
    finally:
        session.close()


def _key(prefix):
    return f"{prefix}-{uuid4().hex[:10]}"


def test_list_sources_is_404_for_an_unknown_course(client):
    resp = client.get("/courses/987654/sources")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Course not found"


def test_list_sources_returns_them_in_position_order_with_the_documented_fields(client):
    course_id = _course(_key("list"))
    second = _add_source(course_id, position=1, ref="b.pdf", title="b.pdf", blob=b"%PDF-b")
    first = _add_source(course_id, position=0, ref="a.pdf", title="a.pdf", blob=b"%PDF-a")

    resp = client.get(f"/courses/{course_id}/sources")
    assert resp.status_code == 200
    rows = resp.json()

    assert [row["id"] for row in rows] == [first, second]
    assert [row["position"] for row in rows] == [0, 1]
    row = rows[0]
    assert set(row) == {
        "id",
        "position",
        "kind",
        "ref",
        "title",
        "locator",
        "char_count",
        "byte_size",
        "has_file",
    }
    assert row["kind"] == "pdf"
    assert row["ref"] == "a.pdf"
    assert row["has_file"] is True
    assert "data" not in row and "blob" not in row


def test_list_sources_never_returns_blob_bytes_even_as_a_stray_key(client):
    course_id = _course(_key("nobytes"))
    _add_source(course_id, blob=b"%PDF-1.4 some real bytes here")

    body = client.get(f"/courses/{course_id}/sources").json()
    dumped = str(body)
    assert "some real bytes here" not in dumped


def test_list_sources_reports_a_source_with_no_blob_as_has_file_false(client):
    course_id = _course(_key("noblob"))
    _add_source(course_id, kind="text", ref="pasted", title="pasted", byte_size=None)

    row = client.get(f"/courses/{course_id}/sources").json()[0]
    assert row["has_file"] is False
    assert row["byte_size"] is None


def test_list_sources_never_loads_the_blob_data_column(client):
    """has_file must be answered from existence, not from row.blob is not None, which
    lazy-loads the whole CourseSourceBlob row (data column included) per source.
    """
    course_id = _course(_key("noload"))
    _add_source(course_id, blob=b"%PDF-1.4 " + b"x" * 10_000)

    statements = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _record)
    try:
        resp = client.get(f"/courses/{course_id}/sources")
    finally:
        event.remove(engine, "before_cursor_execute", _record)

    assert resp.status_code == 200
    assert resp.json()[0]["has_file"] is True
    assert not any("course_source_blobs.data" in s for s in statements), statements


def test_list_sources_reports_a_valid_youtube_locator_as_is(client):
    course_id = _course(_key("yt"))
    _add_source(course_id, kind="url", ref="https://youtu.be/dQw4w9WgXcQ", locator="dQw4w9WgXcQ")

    row = client.get(f"/courses/{course_id}/sources").json()[0]
    assert row["locator"] == "dQw4w9WgXcQ"


def test_list_sources_reports_an_invalid_stored_locator_as_absent_not_echoed(client):
    """A locator that no longer fullmatches WATCH_ID (corrupted, truncated, or carrying a
    trailing newline the fixed .match() bug used to let through) must not reach a client
    unchanged: this asserts the "" fallback, not merely that the request succeeds.
    """
    course_id = _course(_key("badyt"))
    _add_source(course_id, kind="url", ref="https://youtu.be/x", locator="dQw4w9WgXcQ\n")

    row = client.get(f"/courses/{course_id}/sources").json()[0]
    assert row["locator"] == ""


def test_file_endpoint_is_404_for_an_unknown_course(client):
    course_id = _course(_key("filecourse"))
    source_id = _add_source(course_id, blob=b"%PDF-1.4")

    resp = client.get(f"/courses/987654/sources/{source_id}/file")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Course not found"


def test_file_endpoint_is_404_when_the_source_belongs_to_a_different_course(client):
    """THE SECURITY-RELEVANT CASE. source_id is a real, existing row, just not one that
    belongs to course_id: an implementation that looked the source up by id alone would
    serve it anyway, silently letting one course's request read another course's PDF.
    """
    owner_course = _course(_key("owner"))
    other_course = _course(_key("other"))
    source_id = _add_source(owner_course, blob=b"%PDF-1.4 belongs to owner")

    resp = client.get(f"/courses/{other_course}/sources/{source_id}/file")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Source not found"

    # And the legitimate owner can still read it: this is not a blanket regression.
    ok = client.get(f"/courses/{owner_course}/sources/{source_id}/file")
    assert ok.status_code == 200


def test_file_endpoint_is_404_when_the_source_has_no_blob(client):
    course_id = _course(_key("noblobfile"))
    source_id = _add_source(course_id, kind="pdf", blob=None)

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Source has no file"


def test_file_endpoint_refuses_a_non_pdf_source_even_if_it_somehow_has_a_blob(client):
    """kind="pdf" is the only source that should ever carry a blob (see _save_course),
    but this endpoint checks kind rather than trusting that invariant held, so a stray
    blob on a non-pdf row (a bad migration, a bug) is still refused.
    """
    course_id = _course(_key("nonpdf"))
    source_id = _add_source(course_id, kind="text", ref="pasted", blob=b"not really a pdf")

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Source has no file"


def test_file_endpoint_serves_the_exact_stored_bytes_with_all_five_required_headers(client):
    course_id = _course(_key("headers"))
    pdf_bytes = b"%PDF-1.4\n%mock pdf content\n"
    source_id = _add_source(course_id, ref="my notes.pdf", title="my notes.pdf", blob=pdf_bytes)

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")

    assert resp.status_code == 200
    assert resp.content == pdf_bytes
    assert resp.headers["Content-Type"] == "application/pdf"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert (
        resp.headers["Content-Disposition"]
        == 'inline; filename="my notes.pdf"; filename*=UTF-8\'\'my%20notes.pdf'
    )
    assert resp.headers["Content-Security-Policy"] == "default-src 'none'; sandbox"
    assert resp.headers["Cache-Control"] == "private, no-store"


def test_file_endpoint_ignores_the_stored_media_type_column(client):
    """The Content-Type sent is the fixed literal, never CourseSourceBlob.media_type.
    Nothing in this codebase sets that column from upload data today, so this test sets
    it directly to prove the endpoint would still ignore it even if something did.
    """
    course_id = _course(_key("mediatype"))
    session = SessionLocal()
    try:
        source = models.CourseSource(
            course_id=course_id, position=0, kind="pdf", ref="x.pdf", title="x.pdf"
        )
        session.add(source)
        session.flush()
        session.add(
            models.CourseSourceBlob(
                source_id=source.id, data=b"%PDF-1.4", media_type="text/html"
            )
        )
        session.commit()
        source_id = source.id
    finally:
        session.close()

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"


def test_file_endpoint_sanitizes_a_double_quote_in_ref_out_of_the_filename_header(client):
    course_id = _course(_key("quote"))
    source_id = _add_source(
        course_id, ref='evil".pdf', title='evil".pdf', blob=b"%PDF-1.4"
    )

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 200
    disposition = resp.headers["Content-Disposition"]
    quoted_name = disposition.split(";")[1].split("=", 1)[1].strip()
    assert '"' not in quoted_name[1:-1]
    # Exactly one filename= parameter: no second one smuggled in via the unescaped quote.
    # (filename*= is the separate RFC 5987 parameter this endpoint always adds.)
    assert disposition.count("filename=") == 1


def test_file_endpoint_sanitizes_a_newline_in_ref_out_of_the_filename_header(client):
    """Header injection through Content-Disposition: a raw CR or LF in the filename
    parameter would let `ref` terminate the header and start writing a new one.
    """
    course_id = _course(_key("crlf"))
    source_id = _add_source(
        course_id,
        ref="evil.pdf\r\nX-Injected: yes",
        title="evil.pdf\r\nX-Injected: yes",
        blob=b"%PDF-1.4",
    )

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 200
    disposition = resp.headers["Content-Disposition"]
    assert "\r" not in disposition and "\n" not in disposition
    assert "X-Injected" not in resp.headers


def test_file_endpoint_strips_control_bytes_that_h11_would_reject(client):
    """A NUL is not an injection risk, it is a self-denial one: h11 refuses to serve any
    response whose header value holds one, so an upload named with a NUL byte would make
    its own download fail at the protocol layer rather than at any check of ours.
    """
    course_id = _course(_key("ctrl"))
    source_id = _add_source(
        course_id, ref="ev\x00il\x01.pdf", title="ev\x00il\x01.pdf", blob=b"%PDF-1.4"
    )

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 200
    disposition = resp.headers["Content-Disposition"]
    assert disposition == 'inline; filename="evil.pdf"; filename*=UTF-8\'\'evil.pdf'
    h11.Response(
        status_code=200, reason=b"OK", headers=[(b"Content-Disposition", disposition.encode())]
    )


def test_a_ref_of_nothing_but_unsafe_bytes_still_yields_a_usable_filename(client):
    """The fallback arm of the sanitizer, which nothing else reaches: strip every
    character and the name would be empty, which is not a filename.
    """
    course_id = _course(_key("empty"))
    source_id = _add_source(course_id, ref='"/\\', title='"/\\', blob=b"%PDF-1.4")

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 200
    assert (
        resp.headers["Content-Disposition"]
        == 'inline; filename="source.pdf"; filename*=UTF-8\'\'source.pdf'
    )


def test_file_endpoint_serves_a_cjk_ref_with_an_ascii_fallback_and_a_utf8_filename_star(client):
    """The bug this guards: Starlette encodes header values as latin-1, and a codepoint
    above U+00FF in a bare filename= raises UnicodeEncodeError there. filename="source.pdf"
    keeps the header encodable while filename* still carries the real name.
    """
    course_id = _course(_key("cjk"))
    source_id = _add_source(course_id, ref="研究.pdf", title="研究.pdf", blob=b"%PDF-1.4")

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 200
    disposition = resp.headers["Content-Disposition"]
    disposition.encode("latin-1")  # must not raise
    assert disposition == 'inline; filename="source.pdf"; filename*=UTF-8\'\'%E7%A0%94%E7%A9%B6.pdf'
    assert unquote(disposition.split("filename*=UTF-8''")[1]) == "研究.pdf"


def test_file_endpoint_serves_a_cyrillic_ref_with_an_ascii_fallback(client):
    course_id = _course(_key("cyrillic"))
    source_id = _add_source(
        course_id, ref="документ.pdf", title="документ.pdf", blob=b"%PDF-1.4"
    )

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 200
    disposition = resp.headers["Content-Disposition"]
    disposition.encode("latin-1")  # must not raise
    assert 'filename="source.pdf"' in disposition
    assert unquote(disposition.split("filename*=UTF-8''")[1]) == "документ.pdf"


def test_file_endpoint_serves_an_emoji_ref_keeping_the_surviving_ascii_base(client):
    """Unlike the CJK and Cyrillic cases, the ascii base here is not empty ("notes"
    survives once the emoji is stripped), so the ascii fallback need not be "source.pdf".
    """
    course_id = _course(_key("emoji"))
    source_id = _add_source(course_id, ref="📄notes.pdf", title="📄notes.pdf", blob=b"%PDF-1.4")

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 200
    disposition = resp.headers["Content-Disposition"]
    disposition.encode("latin-1")  # must not raise
    assert 'filename="notes.pdf"' in disposition
    assert unquote(disposition.split("filename*=UTF-8''")[1]) == "📄notes.pdf"


def test_file_endpoint_falls_back_to_source_pdf_for_a_ref_that_is_entirely_non_ascii(client):
    """No extension in the ref at all, so nothing ascii survives, including no ".pdf":
    the fallback arm of the ascii name, distinct from the fallback arm of the sanitizer
    that test_a_ref_of_nothing_but_unsafe_bytes_still_yields_a_usable_filename covers.
    """
    course_id = _course(_key("allnonascii"))
    source_id = _add_source(course_id, ref="研究", title="研究", blob=b"%PDF-1.4")

    resp = client.get(f"/courses/{course_id}/sources/{source_id}/file")
    assert resp.status_code == 200
    disposition = resp.headers["Content-Disposition"]
    disposition.encode("latin-1")  # must not raise
    assert disposition == 'inline; filename="source.pdf"; filename*=UTF-8\'\'%E7%A0%94%E7%A9%B6.pdf'
    assert unquote(disposition.split("filename*=UTF-8''")[1]) == "研究.pdf"
