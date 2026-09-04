"""One course from URLs, pasted text and PDFs combined in one multipart request.

test_multi_source.py already proves the shared machinery: every outcome reported, nothing
generated if anything failed, caps checked before any provider call. This file is scoped to
what is genuinely new about /courses/generate/multipart:

  1. `sources` and `file` combine into ONE course, in COMBINED SENT ORDER, and that order is
     what `index` in a refusal counts from.
  2. The route always answers with the dict refusal shape, never the legacy bare string,
     because there is no caller of this route the bare-string seam has to protect.
  3. `sources` is a hand-parsed JSON string riding in a form field, so malformed JSON, the
     wrong JSON shape, and an invalid element all have to be caught here rather than by
     FastAPI's own body parsing.
  4. MAX_UPLOAD_BYTES, checked on UploadFile.size before any file is read, which
     /courses/generate/pdf does not have.
  5. GET /meta/limits, read from the same constants ingest.load_sources enforces.

`extract_pdf` is monkeypatched to decode its own input rather than parsing real PDF bytes,
and `extract_url` is monkeypatched to skip the network fetch but keeps calling the real
`_check_host` guard first, so a private-address URL still fails the way it does in
production and a public one still succeeds. Good URLs in this file are public IP literals
(93.184.216.34, one of example.com's own addresses) rather than domain names, so
`_check_host`'s own address lookup resolves them without a DNS query. Real fetching and
real PDF parsing are exercised elsewhere (test_ingest.py, TestFriendlyGenerationErrors);
this file is about what happens to several sources of different kinds once each has been
read.
"""

import asyncio
import io
import json

import fastapi
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from app import ingest, main
from app.llm.fake_provider import FakeProvider
from tests.test_multi_source import NeverCalledProvider

GOOD_TEXT = "Gradient descent walks downhill by following the slope. " * 30


GOOD_URL_HOST = "93.184.216.34"  # a public address of example.com; see module docstring
PRIVATE_URL = "http://127.0.0.1/wiki"

# The one refusal body a present-but-empty `sources` field must produce, whichever of "" or
# whitespace-only it was spelled, alone or with a file attached. The agreement is the
# property under test, so every case below is asserted against this single constant rather
# than each writing out its own copy that could quietly diverge.
_EMPTY_SOURCES_DETAIL = {
    "error": main.INVALID_REQUEST_ERROR,
    "message": f"{main.INVALID_REQUEST_MESSAGE} 'sources' must not be empty.",
}


def _fake_extract_url(url: str) -> str:
    """The real host guard, then canned text instead of a real fetch.

    Calling ingest._check_host directly means a private-address URL still raises
    UnsafeURLError exactly as it does in production, so "bad URL" in this file is the
    same failure the app actually produces rather than a fixture's opinion of one.
    """
    ingest._check_host(url)
    return f"{url}. {GOOD_TEXT}"


@pytest.fixture(autouse=True)
def _fake_reads(monkeypatch):
    """Every URL and PDF in this file reads back its own identifying text.

    A URL's "content" is the URL itself, repeated to clear ingest's per-source length
    floor; a PDF's "content" is whatever bytes the test uploaded, decoded. Neither touches
    the network or a real PDF parser, so a source is good or bad by construction rather
    than by chance.
    """
    monkeypatch.setattr(ingest, "extract_url", _fake_extract_url)
    monkeypatch.setattr(ingest, "extract_pdf", lambda data: data.decode())


def _seen_prompts(monkeypatch) -> list[str]:
    seen: list[str] = []

    class Recorder(FakeProvider):
        def generate(self, system: str, prompt: str, max_tokens: int = 64000):
            seen.append(prompt)
            return super().generate(system, prompt, max_tokens)

    monkeypatch.setattr(main, "get_provider", lambda: Recorder())
    return seen


def _sources_part(specs: list[dict]) -> dict:
    return {"sources": (None, json.dumps(specs), "text/plain")}


def _pdf_part(label: str) -> tuple:
    """One uploaded "PDF", whose bytes decode straight back to its own label.

    Not a byte-valid PDF: extract_pdf is faked in this file, so what matters is that these
    bytes round-trip through UploadFile untouched, not that pypdf can parse them.
    """
    return (f"{label}.pdf", f"{label} content: {GOOD_TEXT}".encode(), "application/pdf")


def _generate(client, *, sources: list[dict] | None = None, files: list[tuple] | None = None):
    data = {"sources": json.dumps(sources)} if sources is not None else {}
    upload_files = [("file", pdf) for pdf in (files or [])]
    return client.post("/courses/generate/multipart", data=data, files=upload_files or None)


def _course_shape(client, course_id: int) -> tuple[str, list[str]]:
    body = client.get(f"/courses/{course_id}").json()
    lessons = [lesson["title"] for module in body["modules"] for lesson in module["lessons"]]
    return body["title"], lessons


# --------------------------------------------------------------------------
# One course, several kinds of source, in combined order
# --------------------------------------------------------------------------


def test_urls_and_pdfs_combine_into_one_course(client, monkeypatch):
    """Acceptance 1: 2 URLs plus 2 PDFs, one course, every mark reaches the outline."""
    seen = _seen_prompts(monkeypatch)

    response = _generate(
        client,
        sources=[
            {"kind": "url", "value": f"http://{GOOD_URL_HOST}/UNIQUEMARK0"},
            {"kind": "url", "value": f"http://{GOOD_URL_HOST}/UNIQUEMARK1"},
        ],
        files=[_pdf_part("UNIQUEMARK2"), _pdf_part("UNIQUEMARK3")],
    )

    assert response.status_code == 200, response.text
    outline_prompt = seen[0]
    for index in range(4):
        assert f"UNIQUEMARK{index}" in outline_prompt, f"UNIQUEMARK{index} never reached the outline"


def test_files_only_matches_the_pdf_only_route_shape(client, monkeypatch):
    """Acceptance 2: files-only multipart produces the same course shape as /courses/generate/pdf."""
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    pdf_bytes = f"Shared PDF content. {GOOD_TEXT}".encode()

    multipart = client.post(
        "/courses/generate/multipart",
        data={},
        files=[("file", ("notes.pdf", pdf_bytes, "application/pdf"))],
    )
    pdf_only = client.post(
        "/courses/generate/pdf",
        files={"file": ("notes.pdf", pdf_bytes, "application/pdf")},
    )

    assert multipart.status_code == 200, multipart.text
    assert pdf_only.status_code == 200, pdf_only.text
    assert _course_shape(client, multipart.json()["id"]) == _course_shape(
        client, pdf_only.json()["id"]
    )


def test_sources_only_with_no_files_works(client, monkeypatch):
    """Acceptance 3: `sources` alone, with no `file` part at all, still generates."""
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())

    response = client.post(
        "/courses/generate/multipart",
        data={"sources": json.dumps([{"kind": "text", "value": GOOD_TEXT}])},
    )

    assert response.status_code == 200, response.text


# --------------------------------------------------------------------------
# What gets refused, before any provider is touched
# --------------------------------------------------------------------------


def test_neither_part_present_is_the_shared_no_source_shape(client):
    """Acceptance 4: no `sources`, no `file`, the same 400 shape /courses/generate uses."""
    response = client.post("/courses/generate/multipart")

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == {"error": "no_source", "message": main.NO_SOURCE_MESSAGE}


def test_six_combined_sources_refuses_before_any_provider_call(client, monkeypatch):
    """Acceptance 5: the combined count, across both parts, is what the cap counts.

    ALSO PINS THAT THE GUARD IS EARLY, not merely that the count is enforced. The response
    body cannot tell the two guards apart: ingest.load_sources's own (identical) TooManySources
    check, one layer down, raises through the exact same too_many_sources_message() helper
    with the same count, so the status, error code and message text are byte-for-byte the
    same whichever guard catches it. Spying on ingest.extract_pdf does not discriminate them
    either, because load_sources's own count check runs before its own extraction loop, so
    extract_pdf is never called from either arm - it is a constant, not a discriminator.

    What the early guard actually buys, and the only thing distinguishing it, is that
    generate_multipart's spec-building loop below (`value=upload.file.read()`) runs BEFORE
    ingest.load_sources is ever called - so without the early guard, every uploaded file is
    still read fully into memory before the deep guard gets a chance to refuse. Spying on
    load_sources itself is what proves that: with the early guard in place, load_sources is
    never invoked at all for an over-cap request.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())
    load_sources_calls: list[int] = []
    original_load_sources = ingest.load_sources

    def _spy_load_sources(specs, *args, **kwargs):
        load_sources_calls.append(len(specs))
        return original_load_sources(specs, *args, **kwargs)

    monkeypatch.setattr(ingest, "load_sources", _spy_load_sources)
    over = ingest.MAX_SOURCES + 1
    text_sources = [{"kind": "text", "value": GOOD_TEXT} for _ in range(over - 2)]
    files = [_pdf_part(f"pdf{i}") for i in range(2)]

    response = _generate(client, sources=text_sources, files=files)

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "too_many_sources"
    assert str(over) in detail["message"]
    assert load_sources_calls == [], (
        "too_many_sources must refuse before load_sources is ever called, "
        "since reaching it means every uploaded file was already read into memory"
    )


def test_one_bad_url_and_one_good_pdf_reports_only_the_bad_one(client, monkeypatch):
    """Acceptance 6: mixed kinds, one failure, the good source absent from the report."""
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    response = _generate(
        client,
        sources=[{"kind": "url", "value": PRIVATE_URL}],
        files=[_pdf_part("good")],
    )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "source_failed"
    assert len(detail["sources"]) == 1
    assert detail["sources"][0]["kind"] == "url"


def test_index_is_the_sent_position_not_the_failure_position(client, monkeypatch):
    """Acceptance 7: [good, bad, good, bad] reports indices [1, 3], not [0, 1]."""
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    # Built directly rather than through the _generate helper, which cannot express a bad
    # file part: this is [good text, bad url, good pdf, bad pdf], sent in that order.
    response = client.post(
        "/courses/generate/multipart",
        data={
            "sources": json.dumps(
                [
                    {"kind": "text", "value": GOOD_TEXT},
                    {"kind": "url", "value": PRIVATE_URL},
                ]
            )
        },
        files=[
            ("file", _pdf_part("good")),
            ("file", ("bad.pdf", b"", "application/pdf")),
        ],
    )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "source_failed"
    indices = [entry["index"] for entry in detail["sources"]]
    assert indices == [1, 3], "index must count the sent position, not the failure position"


def test_a_single_file_request_gets_the_dict_shape_not_a_bare_string(client, monkeypatch):
    """Acceptance 8: a lone failing PDF on this route is the dict shape, unlike /generate/pdf."""
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    response = client.post(
        "/courses/generate/multipart",
        files=[("file", ("bad.pdf", b"", "application/pdf"))],
    )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert isinstance(detail, dict), "a single-file multipart request must not get the legacy string"
    assert detail["error"] == "source_failed"
    assert detail["sources"][0]["index"] == 0


@pytest.mark.parametrize(
    ("raw_sources", "expected_fragment"),
    [
        ("not json at all", "not valid JSON"),
        (json.dumps({"kind": "text", "value": "x"}), "must be a JSON array"),
        (json.dumps([{"kind": "carrier-pigeon", "value": "x"}]), "kind"),
    ],
    ids=["malformed-json", "object-not-array", "unknown-kind"],
)
def test_malformed_sources_is_invalid_request_before_any_fetch(
    client, monkeypatch, raw_sources, expected_fragment
):
    """Acceptance 9: malformed JSON, a non-array, and an unknown kind are all invalid_request."""
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    response = client.post("/courses/generate/multipart", data={"sources": raw_sources})

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["error"] == main.INVALID_REQUEST_ERROR
    assert expected_fragment in detail["message"]


def test_over_cap_uploads_are_refused_without_reading_any_file(client, monkeypatch):
    """Acceptance 11: MAX_UPLOAD_BYTES on the sum of file sizes, before the provider is touched.

    ALSO PINS THAT THIS RUNS BEFORE EXTRACTION, the same gap as the count guard above. The
    character cap in _ingest_or_refuse would refuse this request too, on the same error
    code, once both PDFs had been decoded to their (huge) text - which proves the cap
    exists, not that the byte check ran first and skipped reading them. extract_pdf being
    untouched is the property the "before reading" half of this test's name promises.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())
    pdf_reads: list[bytes] = []
    monkeypatch.setattr(ingest, "extract_pdf", lambda data: pdf_reads.append(data) or data.decode())
    each = ingest.MAX_UPLOAD_BYTES // 2 + 1

    response = client.post(
        "/courses/generate/multipart",
        files=[
            ("file", ("a.pdf", b"x" * each, "application/pdf")),
            ("file", ("b.pdf", b"x" * each, "application/pdf")),
        ],
    )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "source_too_large"
    assert str(ingest.MAX_UPLOAD_BYTES) in detail["message"].replace(",", "")
    assert pdf_reads == [], "the byte cap must refuse before any uploaded PDF is read"


class _NoSourcesRequest:
    """A minimal stand-in for fastapi.Request.

    generate_multipart only calls `request.form()`, and only to read `sources`, before the
    size guard this test targets ever runs. What this test pins does not depend on `sources`
    at all, so this returns an empty mapping (`sources` absent) rather than a real Request.
    """

    async def form(self):
        return {}


def test_unknown_upload_size_is_refused_as_over_cap_not_under():
    """Reviewer finding 1: an UploadFile whose size is unknown must be refused, not summed as 0.

    Called directly rather than through TestClient: Starlette 1.6.0's own multipart parser
    always sets UploadFile.size before a route ever sees it, so a None size is not reachable
    through a real request today. It is reachable if that ever changes, or if a caller
    constructs an UploadFile by hand the way this test does, so the route guards against it
    rather than trusting the library's current behavior to hold forever.

    The payload is 10 bytes, nowhere near MAX_UPLOAD_BYTES, so the only thing that can cause
    a source_too_large refusal here is the None-size rule itself, not the byte count.

    session=None is deliberate, not a shortcut: generate_multipart never touches `session`
    until after both size checks, so passing None and still getting the refusal is itself
    part of what this test pins - the refusal happens before any database access.
    """
    upload = UploadFile(file=io.BytesIO(b"x" * 10), size=None, filename="huge.pdf")

    async def _call():
        return await main.generate_multipart(
            request=_NoSourcesRequest(), sources=None, file=[upload], session=None
        )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_call())

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"] == "source_too_large"


@pytest.mark.parametrize("raw_sources", ["", "   "], ids=["empty-string", "whitespace-only"])
def test_present_but_empty_sources_is_invalid_request_alone(client, raw_sources):
    """Reviewer finding 2: `sources=""` and `sources="   "` are the same mistake, refused alike.

    Before this fix, `sources: str | None = Form(default=None)` was the route's only source
    of truth, and FastAPI's own Form() dependency resolution collapses "" to None before the
    route body ever runs (see test_form_field_collapses_empty_string_to_none below), so "" was
    silently treated as omitted while "   " reached _parse_multipart_sources and failed to
    parse as JSON - two different refusals for what is the same caller mistake. The route now
    reads `sources` from the raw form data instead, which keeps "" and "   " both non-None and
    both are decided by the identical `raw.strip()` check, so they are asserted here against
    the identical _EMPTY_SOURCES_DETAIL body, which is the property under test.
    """
    response = client.post("/courses/generate/multipart", data={"sources": raw_sources})

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == _EMPTY_SOURCES_DETAIL


@pytest.mark.parametrize("raw_sources", ["", "   "], ids=["empty-string", "whitespace-only"])
def test_present_but_empty_sources_is_invalid_request_with_a_file_attached(
    client, monkeypatch, raw_sources
):
    """Reviewer finding 2, sharper case: a real file must not paper over an empty `sources`.

    Before this fix, `sources=""` with a file attached collapsed to None at the Form()
    dependency layer and reached the provider on the file alone, silently ignoring that
    `sources` was sent and empty - the silent-partial failure mode this whole feature exists
    to avoid (a client with three URLs and one PDF whose serialization bug yields "" would get
    a course built from the PDF alone and believe the links are in it). NeverCalledProvider
    proves that no longer happens for either spelling: the refusal happens before the file is
    ever ingested.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    response = client.post(
        "/courses/generate/multipart",
        data={"sources": raw_sources},
        files=[("file", _pdf_part("irrelevant"))],
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == _EMPTY_SOURCES_DETAIL


def test_form_field_collapses_empty_string_to_none():
    """Pins the FastAPI assumption generate_multipart's raw-form-read workaround depends on.

    Verified against FastAPI 0.141.1: fastapi/dependencies/utils.py::_get_multidict_value
    replaces a present-but-empty ("") value for any `Form()`-declared field with that field's
    default before the route body ever runs, so `sources: str | None = Form(default=None)`
    can never itself distinguish "" from an omitted field. generate_multipart works around
    this by reading `sources` from the raw form data instead (see its docstring). If a future
    FastAPI stops collapsing "" this way, that workaround becomes unnecessary rather than
    wrong, but this test failing is what would tell us that has happened, instead of it going
    unnoticed.
    """
    probe = fastapi.FastAPI()

    @probe.post("/probe")
    def echo(sources: str | None = fastapi.Form(default=None)):
        return {"sources": sources, "is_none": sources is None}

    response = TestClient(probe).post("/probe", data={"sources": ""})

    assert response.json() == {"sources": None, "is_none": True}


# --------------------------------------------------------------------------
# GET /meta/limits
# --------------------------------------------------------------------------


def test_limits_are_read_from_the_ingest_constants(client):
    """Acceptance 10: asserted against the constants themselves, so it cannot go stale."""
    response = client.get("/meta/limits")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "max_sources": ingest.MAX_SOURCES,
        "max_total_chars": ingest.MAX_TOTAL_CHARS,
        "max_upload_bytes": ingest.MAX_UPLOAD_BYTES,
    }
