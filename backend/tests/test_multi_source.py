"""One course from several sources: what gets read, what gets refused, and what it costs.

THE CLAIM THIS FILE EXISTS FOR is that adding sources added no second code path. `text`,
`url` and `sources` are three spellings of one request, normalized in GenerateRequest
before anything downstream sees them, and
test_the_alias_and_the_canonical_form_produce_the_same_course is the assertion that says
so. If that test ever fails there are two paths again, whatever the docstrings claim.

The other three claims, in the order they cost money:

  1. EVERY outcome is reported, not the first failure. A caller with two bad URLs among
     five sources fixes both from one response, rather than learning about the second only
     after correcting the first.
  2. Nothing is generated if anything failed. Fail-closed is free here because the whole
     ingestion happens before the first token is bought, so refusing costs a resubmit while
     best-effort would cost a course built from three of five documents, paid in full.
  3. The caps refuse before any provider call at all, which is asserted with a provider
     that raises if it is touched rather than by counting rows afterwards.

Nothing here reaches the network. Bad URLs are private addresses, which app.ingest's own
host guard refuses from the resolved address without fetching anything, and that is also
the case worth testing: it is the guard that already existed, now reported per source.
"""

import pytest

from app import ingest, main, models
from app.db import SessionLocal
from app.llm.fake_provider import FakeProvider

GOOD_TEXT = "Gradient descent walks downhill by following the slope. " * 30

# Refused by ingest._check_host from the resolved address, with no request made. Loopback
# rather than a domain that fails to resolve, so the failure is the guard's and not DNS's.
PRIVATE_URL = "http://127.0.0.1/wiki"
OTHER_PRIVATE_URL = "http://10.0.0.5/notes"


class NeverCalledProvider:
    """A provider that fails the test if anything asks it to generate.

    The caps are supposed to refuse BEFORE any model call. Counting llm_calls rows
    afterwards would not prove that: a call that happened and was refused mid-flight still
    writes a row, and a call that happened and succeeded would leave the count looking
    reasonable. Raising on contact is the only version of this assertion that cannot be
    satisfied by a late refusal.
    """

    name = "never"
    model = "never"
    is_paid = False

    def generate(self, system: str, prompt: str, max_tokens: int = 64000):
        raise AssertionError("a provider was called before the caps refused the request")


def _text_source(value: str, ref: str | None = None) -> dict:
    source = {"kind": "text", "value": value}
    if ref is not None:
        source["ref"] = ref
    return source


def _outline_calls() -> int:
    session = SessionLocal()
    try:
        return session.query(models.LlmCall).filter(models.LlmCall.stage == "outline").count()
    finally:
        session.close()


def _generate(client, payload: dict):
    return client.post("/courses/generate", json=payload)


def _course_shape(client, course_id: int) -> tuple[str, list[str]]:
    """A course reduced to what two runs can be compared on.

    Titles rather than ids, because two runs of the same material produce two courses with
    different ids and the same content, and ids are the one field guaranteed to differ.
    """
    body = client.get(f"/courses/{course_id}").json()
    lessons = [lesson["title"] for module in body["modules"] for lesson in module["lessons"]]
    return body["title"], lessons


# --------------------------------------------------------------------------
# One path, three spellings
# --------------------------------------------------------------------------


def test_the_alias_and_the_canonical_form_produce_the_same_course(client, monkeypatch):
    """THE TEST THE WHOLE DESIGN RESTS ON.

    `{"text": ...}` and `{"sources": [{"kind": "text", "value": ...}]}` are the same request
    written twice, so they must produce the same course. They do because the aliases are
    folded into `sources` by GenerateRequest's validator and nothing past that line can
    tell them apart.

    This is what makes keeping the deprecated fields cheap rather than a liability. The rot
    in an alias is a second CODE PATH, and a spelling that collapses at the edge is not one.
    If this ever fails, the fold has been bypassed somewhere and there are two paths again.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())

    aliased = _generate(client, {"text": GOOD_TEXT})
    canonical = _generate(client, {"sources": [_text_source(GOOD_TEXT)]})

    assert aliased.status_code == 200, aliased.text
    assert canonical.status_code == 200, canonical.text
    assert _course_shape(client, aliased.json()["id"]) == _course_shape(
        client, canonical.json()["id"]
    )


def test_the_url_alias_folds_into_sources_too(client, monkeypatch):
    """The other alias, checked on the refusal rather than on a fetch.

    A URL alias cannot be exercised without either the network or a stub, so this asserts
    the fold at the point it is observable for free: a private URL sent as `url` and the
    same URL sent as a source both reach the same host guard and report the same message.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    aliased = _generate(client, {"url": PRIVATE_URL})
    canonical = _generate(client, {"sources": [{"kind": "url", "value": PRIVATE_URL}]})

    assert "private or local network" in aliased.json()["detail"]
    assert "private or local network" in canonical.json()["detail"]["sources"][0]["message"]


def test_sources_wins_when_a_request_carries_both_spellings(client, monkeypatch):
    """A confused request gets the canonical field, deterministically.

    Nothing produces this today. It is pinned because "whichever one the validator happens
    to check first" is the kind of behaviour that becomes load bearing by accident.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())

    response = _generate(client, {"text": "ignored " * 50, "sources": [_text_source(GOOD_TEXT)]})

    assert response.status_code == 200, response.text
    title, _ = _course_shape(client, response.json()["id"])
    assert "ignored" not in title


# --------------------------------------------------------------------------
# Several sources, one course
# --------------------------------------------------------------------------


def test_five_sources_make_exactly_one_outline_call(client, monkeypatch):
    """Several documents are ONE course, not several, and cost one outline.

    The lesson calls scale with what the outline invents and are not asserted here. The
    outline is the one call whose count is a fact about this feature: a loop that generated
    per source would produce five courses, or one course five times over, and either way
    this count would move.
    """
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    before = _outline_calls()

    response = _generate(
        client,
        {"sources": [_text_source(f"Topic {index}. {GOOD_TEXT}") for index in range(5)]},
    )

    assert response.status_code == 200, response.text
    assert _outline_calls() == before + 1


def test_every_source_reaches_the_material(client, monkeypatch):
    """All five texts are in the prompt, not just the first or the last.

    Chunked per source, so the assertion is that every source contributed at least one
    segment. A concatenation bug that dropped everything after the first would still return
    a course, which is why this looks at the prompt rather than at the response.
    """
    seen: list[str] = []

    class Recorder(FakeProvider):
        def generate(self, system: str, prompt: str, max_tokens: int = 64000):
            seen.append(prompt)
            return super().generate(system, prompt, max_tokens)

    monkeypatch.setattr(main, "get_provider", lambda: Recorder())

    marks = [f"UNIQUEMARK{index}" for index in range(5)]
    response = _generate(client, {"sources": [_text_source(f"{m}. {GOOD_TEXT}") for m in marks]})

    assert response.status_code == 200, response.text
    outline_prompt = seen[0]
    for mark in marks:
        assert mark in outline_prompt, f"{mark} never reached the outline"


# --------------------------------------------------------------------------
# What gets refused, and what it costs
# --------------------------------------------------------------------------


def test_no_source_is_unchanged_for_an_empty_list_too(client):
    """An empty `sources` is the same refusal as no field at all, with the same code."""
    for payload in ({}, {"sources": []}):
        response = _generate(client, payload)
        assert response.status_code == 400, response.text
        assert response.json()["detail"] == {
            "error": "no_source",
            "message": main.NO_SOURCE_MESSAGE,
        }


def test_too_many_sources_is_refused_without_touching_a_provider(client, monkeypatch):
    """The count cap, and it refuses before ANY fetching or any model call.

    Before the fetching matters as much as before the spend: six URLs over the limit should
    cost zero requests to other people's servers, not six. The provider raises on contact,
    so a late refusal fails rather than passes.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())
    count = ingest.MAX_SOURCES + 1

    response = _generate(client, {"sources": [_text_source(GOOD_TEXT) for _ in range(count)]})

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "too_many_sources"
    assert str(count) in detail["message"], "the message must name the count that was sent"
    assert str(ingest.MAX_SOURCES) in detail["message"], "and the cap it exceeded"


def test_the_cap_itself_is_accepted(client, monkeypatch):
    """The bound is inclusive. Without this the off-by-one above is invisible."""
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())

    response = _generate(
        client, {"sources": [_text_source(GOOD_TEXT) for _ in range(ingest.MAX_SOURCES)]}
    )

    assert response.status_code == 200, response.text


def test_sources_over_the_size_cap_are_refused_before_any_spend(client, monkeypatch):
    """The size cap, on TOTAL characters across sources rather than per source.

    Per source would be trivially defeated by splitting one document in two, and the thing
    being bounded is the outline prompt and the lesson count after it, both of which see
    the total. The provider raises on contact, so this also pins that the refusal happens
    before the first call rather than after the outline is paid for.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())
    each = ingest.MAX_TOTAL_CHARS // 2
    payload = {"sources": [_text_source("x" * each) for _ in range(3)]}

    response = _generate(client, payload)

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "source_too_large"
    assert str(ingest.MAX_TOTAL_CHARS) in detail["message"].replace(",", "")


# --------------------------------------------------------------------------
# Per-source failure, which is the only genuinely new shape
# --------------------------------------------------------------------------


def test_every_failure_is_reported_not_only_the_first(client, monkeypatch):
    """MUTATION TARGET, and the reason load_sources has no early exit.

    Two bad sources with a good one between them. A loop that stopped at the first failure
    returns a response that looks entirely correct: right status, right code, a populated
    list, one plausible row. The caller then fixes that source, resubmits, and is told about
    the second one, having learned nothing they could not have been told the first time.

    So the assertion is the COUNT and both refs, not that the list is non-empty. Make
    load_sources break on its first SourceError and this is the test that goes red.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    response = _generate(
        client,
        {
            "sources": [
                {"kind": "url", "value": PRIVATE_URL},
                _text_source(GOOD_TEXT),
                {"kind": "url", "value": OTHER_PRIVATE_URL},
            ]
        },
    )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "source_failed"
    refs = [entry["ref"] for entry in detail["sources"]]
    assert refs == [PRIVATE_URL, OTHER_PRIVATE_URL], (
        "both failures must be reported, in the order they were sent, so a client can line "
        "them up against the rows it drew"
    )
    for entry in detail["sources"]:
        assert set(entry) == {"kind", "ref", "error", "message"}
        assert entry["kind"] == "url"
        assert entry["error"] == ingest.UNSAFE_URL
        assert "private or local network" in entry["message"], (
            "the guard's own message, which names the host and how to allow it, rather "
            "than a generic one"
        )


def test_one_bad_source_among_good_ones_generates_nothing(client, monkeypatch):
    """FAIL CLOSED. Four readable sources and one that is not is not four fifths of a course.

    The provider raises on contact, so this asserts the stronger thing: not merely that no
    course was saved, but that nothing was ever asked of a model. Best-effort would have
    spent the whole generation budget and produced a course silently missing a document.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())
    before = len(client.get("/courses").json())

    response = _generate(
        client,
        {
            "sources": [
                *[_text_source(GOOD_TEXT) for _ in range(4)],
                {"kind": "url", "value": PRIVATE_URL},
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "source_failed"
    assert len(client.get("/courses").json()) == before, "a course was saved despite the refusal"


def test_a_source_with_no_usable_text_is_a_per_source_failure(client, monkeypatch):
    """Empty is a failure OF THAT SOURCE, reported like any other.

    A blank paste, a scanned PDF and a JavaScript-rendered page all arrive here. Before
    this feature an empty single source was a bare-string 400; it keeps that shape when it
    is the only source and joins the list when it is not.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    response = _generate(
        client, {"sources": [_text_source(GOOD_TEXT), _text_source("   ", ref="blank")]}
    )

    assert response.status_code == 422, response.text
    failures = response.json()["detail"]["sources"]
    assert [entry["ref"] for entry in failures] == ["blank"]
    assert failures[0]["error"] == ingest.NO_USABLE_TEXT


def test_a_text_source_is_named_by_position_when_it_has_no_ref(client, monkeypatch):
    """A wall of pasted prose needs a handle, and its own first characters are not one.

    Without this a client rendering the failure list has nothing to put in the row, or puts
    the document itself there. The URL case is different and tested above: a URL is already
    its own name.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    response = _generate(client, {"sources": [_text_source(GOOD_TEXT), _text_source("")]})

    failures = response.json()["detail"]["sources"]
    assert [entry["ref"] for entry in failures] == ["source 2"], (
        "the label must say WHICH source, counting from the request as sent"
    )


# --------------------------------------------------------------------------
# The seam that keeps every existing caller working
# --------------------------------------------------------------------------


def test_a_deprecated_single_source_keeps_its_original_refusal(client, monkeypatch):
    """The compatibility seam, asserted as the exact old shape rather than as "a 4xx".

    Requests using `text` or `url` get the bare-string body they always got, because every
    existing client and every existing test was written against it. This is scoped to the
    aliases deliberately and dies with them in 0.4.0; a seam with no end date is the second
    code path this design does not have.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    response = _generate(client, {"url": PRIVATE_URL})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert isinstance(detail, str), "an alias request must keep the bare-string detail"
    assert "private or local network" in detail


def test_the_canonical_field_gets_the_new_shape_even_for_one_source(client, monkeypatch):
    """The other half of that seam, and the reason it is keyed on the SPELLING.

    One source sent as `sources` is a client that knows about this feature, so it gets the
    shape this feature defines. Keying on the count instead would have meant the canonical
    field returned two different shapes depending on how many sources happened to be in the
    request, which is the thing a client cannot code against.
    """
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    response = _generate(client, {"sources": [{"kind": "url", "value": PRIVATE_URL}]})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "source_failed"
    assert len(detail["sources"]) == 1


# --------------------------------------------------------------------------
# app.ingest on its own
# --------------------------------------------------------------------------


def test_load_sources_returns_both_lists():
    """The unit form of the per-source claim, without an endpoint in the way."""
    specs = [
        ingest.SourceSpec(kind="text", ref="a", value="real material here"),
        ingest.SourceSpec(kind="url", ref=PRIVATE_URL, value=PRIVATE_URL),
        ingest.SourceSpec(kind="text", ref="c", value="more real material"),
    ]

    sources, failures = ingest.load_sources(specs, main.SOURCE_FAILURE_COPY)

    assert [source.ref for source in sources] == ["a", "c"]
    assert [failure.ref for failure in failures] == [PRIVATE_URL]


def test_load_sources_refuses_the_count_before_reading_anything(monkeypatch):
    """TooManySources is raised before the loop, so nothing is fetched or parsed."""
    monkeypatch.setattr(
        ingest, "from_text", lambda *a, **k: pytest.fail("a source was read past the cap")
    )
    specs = [
        ingest.SourceSpec(kind="text", ref=str(index), value="x")
        for index in range(ingest.MAX_SOURCES + 1)
    ]

    with pytest.raises(ingest.TooManySources):
        ingest.load_sources(specs, main.SOURCE_FAILURE_COPY)


def test_chunk_sources_never_lets_a_chunk_span_two_sources():
    """Chunked per source, so a segment is always from one document.

    Concatenating first would make the chunk on the join a segment the outline is asked to
    summarise as one topic when it is two, and provenance later needs the boundary anyway.
    """
    sources = [
        ingest.Source(key="", kind="text", ref="a", text="AAA"),
        ingest.Source(key="", kind="text", ref="b", text="BBB"),
    ]

    chunks = ingest.chunk_sources(sources)

    assert chunks == ["AAA", "BBB"]
    assert not any("AAA" in chunk and "BBB" in chunk for chunk in chunks)


def test_the_lifted_source_is_the_one_the_evals_use():
    """The lift did not fork the type, asserted by identity rather than by shape.

    evals/sources.py was written to ingest through app.ingest, so its Source was already
    describing this module's output. Two dataclasses with the same fields would satisfy any
    structural check and drift the moment either side gained one.
    """
    from evals import sources as eval_sources

    assert eval_sources.Source is ingest.Source
    assert eval_sources.from_text is ingest.from_text
