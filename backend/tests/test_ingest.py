import json
import socket

import httpx
import pytest

from app import ingest, main, youtube
from app.ingest import chunk_text, clean_text


class TestURLSafety:
    """URL ingest makes the server fetch on a caller's behalf, so it must not become
    a way to read the machine's own network back out as course material."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8000/admin",
            "http://localhost/secrets",
            "http://169.254.169.254/latest/meta-data/",  # cloud metadata
            "http://[::1]/",
            "http://0.0.0.0/",
        ],
    )
    def test_local_and_private_addresses_are_refused(self, url):
        with pytest.raises(ingest.UnsafeURLError):
            ingest.extract_url(url)

    @pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "gopher://x/"])
    def test_only_http_and_https_are_fetched(self, url):
        with pytest.raises(ingest.UnsafeURLError):
            ingest.extract_url(url)

    def test_a_public_url_redirecting_inward_is_refused(self, monkeypatch):
        """The attack a naive fix misses: the supplied URL is public and passes, then
        the response redirects to loopback. Each hop has to be checked, which is why
        redirects are followed by hand rather than by httpx."""
        def fake_get(self, url, *args, **kwargs):
            return httpx.Response(
                302,
                headers={"location": "http://127.0.0.1:9999/internal"},
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.Client, "get", fake_get)
        # Resolve the public host to something routable so the first check passes and
        # the test is genuinely about the second hop. Anything that is already an IP
        # literal resolves to itself, or the loopback target would look public too and
        # the test would pass for the wrong reason.
        def fake_resolve(host, *args, **kwargs):
            address = "93.184.216.34" if host == "example.com" else host
            return [(2, 1, 6, "", (address, 443))]

        monkeypatch.setattr(ingest.socket, "getaddrinfo", fake_resolve)

        with pytest.raises(ingest.UnsafeURLError, match="127.0.0.1"):
            ingest.extract_url("https://example.com/start")

    def test_a_host_with_both_public_and_private_records_is_refused(self, monkeypatch):
        """A name can carry several A records, and httpx may connect to any of them.
        Checking only the first would let an attacker publish one public address and
        one private one and win whenever the private record was picked."""
        monkeypatch.setattr(
            ingest.socket,
            "getaddrinfo",
            lambda *a, **k: [
                (2, 1, 6, "", ("93.184.216.34", 443)),
                (2, 1, 6, "", ("10.0.0.7", 443)),
            ],
        )
        with pytest.raises(ingest.UnsafeURLError):
            ingest.extract_url("https://split-horizon.example/")

    def test_a_name_that_does_not_resolve_is_told_apart_from_a_blocked_one(self, monkeypatch):
        """A name that does not resolve is not a safety refusal. Both stop the fetch, but
        only one is worth pointing at STUDYFORGE_ALLOW_PRIVATE_URLS."""
        def no_such_host(*a, **k):
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

        monkeypatch.setattr(ingest.socket, "getaddrinfo", no_such_host)

        with pytest.raises(ingest.UnresolvableURLError, match="Could not resolve"):
            ingest.extract_url("https://tpyo.example/")

    def test_unresolvable_is_a_kind_of_unsafe_url_error(self, monkeypatch):
        """Pins the subclass relation, which is the only thing this asserts. No reachable
        handler depends on it today: load_source catches UnresolvableURLError first. It is
        here so a caller written against the base class keeps failing closed if one is
        ever added."""
        def no_such_host(*a, **k):
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

        monkeypatch.setattr(ingest.socket, "getaddrinfo", no_such_host)

        with pytest.raises(ingest.UnsafeURLError):
            ingest.extract_url("https://tpyo.example/")

    def test_a_transient_resolver_failure_is_retryable_not_unresolvable(self, monkeypatch):
        """EAI_AGAIN means the resolver itself is having trouble right now, not that the
        name is bad. It must not become UnresolvableURLError (400, do not retry); it
        should fall through to load_source's generic handler, which reports fetch_failed
        (502, safe to retry)."""
        def transient(*a, **k):
            raise socket.gaierror(socket.EAI_AGAIN, "Temporary failure in name resolution")

        monkeypatch.setattr(ingest.socket, "getaddrinfo", transient)

        with pytest.raises(socket.gaierror):
            ingest.extract_url("https://tpyo.example/")

    def test_eai_nodata_is_unresolvable_where_the_platform_defines_it(self, monkeypatch):
        """EAI_NODATA is the other "no such name" spelling. On Windows it is the same
        value as EAI_NONAME, so that arm is invisible here; a distinct sentinel makes the
        branch real on every platform rather than only on the ones where the constants
        differ."""
        monkeypatch.setattr(ingest.socket, "EAI_NODATA", 4242, raising=False)

        def no_data(*a, **k):
            raise socket.gaierror(4242, "No address associated with hostname")

        monkeypatch.setattr(ingest.socket, "getaddrinfo", no_data)

        with pytest.raises(ingest.UnresolvableURLError, match="Could not resolve"):
            ingest.extract_url("https://tpyo.example/")

    def test_a_gaierror_with_no_errno_is_retryable_without_eai_nodata(self, monkeypatch):
        """musl (Alpine) does not define EAI_NODATA at all. Looking it up with a None
        default turns the membership test into `errno in (EAI_NONAME, None)`, and a
        gaierror carrying no errno then matches and is reported as a do-not-retry 400 on
        a URL that may be perfectly fine. A one-argument gaierror is that shape."""
        monkeypatch.delattr(ingest.socket, "EAI_NODATA", raising=False)

        def odd(*a, **k):
            raise socket.gaierror("the resolver said something unexpected")

        monkeypatch.setattr(ingest.socket, "getaddrinfo", odd)

        with pytest.raises(socket.gaierror):
            ingest.extract_url("https://tpyo.example/")

    def test_a_non_gaierror_oserror_is_also_retryable(self, monkeypatch):
        """A downed network (no route, no DNS server reachable) can raise a plain OSError
        rather than a gaierror. That is an infrastructure fault too, not a bad hostname."""
        def network_down(*a, **k):
            raise OSError("Network is unreachable")

        monkeypatch.setattr(ingest.socket, "getaddrinfo", network_down)

        with pytest.raises(OSError) as excinfo:
            ingest.extract_url("https://tpyo.example/")
        assert not isinstance(excinfo.value, ingest.UnsafeURLError)

    def test_allow_private_urls_still_reports_unresolvable_names_the_same_way(
        self, monkeypatch
    ):
        """STUDYFORGE_ALLOW_PRIVATE_URLS is about which resolved addresses are permitted,
        not about whether a name resolves at all. A name that does not exist must come
        back the same way (url_unresolvable) whether or not private addresses are
        allowed, rather than falling to a generic fetch failure once the setting flips."""
        def no_such_host(*a, **k):
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

        monkeypatch.setattr(ingest.socket, "getaddrinfo", no_such_host)
        monkeypatch.setenv("STUDYFORGE_ALLOW_PRIVATE_URLS", "true")

        with pytest.raises(ingest.UnresolvableURLError, match="Could not resolve"):
            ingest.extract_url("https://tpyo.example/")

    @pytest.mark.parametrize("url", ["http://example.com:99999/", "http://example.com:notaport/"])
    def test_a_malformed_port_is_a_bad_request_not_a_gateway_error(self, url):
        """urlparse defers port parsing to attribute access, so this arrives as a bare
        ValueError. Unwrapped it becomes a 502, telling the caller to retry a URL that
        can never work."""
        with pytest.raises(ingest.UnsafeURLError, match="port"):
            ingest.extract_url(url)

    def test_the_redirect_cap_terminates(self, monkeypatch):
        monkeypatch.setattr(
            ingest.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))]
        )
        monkeypatch.setattr(
            httpx.Client,
            "get",
            lambda self, url, *a, **k: httpx.Response(
                302, headers={"location": "/again"}, request=httpx.Request("GET", url)
            ),
        )
        with pytest.raises(ingest.UnsafeURLError, match="too many times"):
            ingest.extract_url("https://example.com/loop")

    def test_a_public_url_still_fetches(self, monkeypatch):
        """The guard must not be so strict that ordinary pages stop working."""
        monkeypatch.setattr(
            ingest.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))]
        )
        monkeypatch.setattr(
            httpx.Client,
            "get",
            lambda self, url, *a, **k: httpx.Response(
                200, text="<h1>Real page</h1><script>x</script>", request=httpx.Request("GET", url)
            ),
        )
        text = ingest.extract_url("https://example.com/article")
        assert "Real page" in text
        assert "script" not in text

    def test_private_addresses_are_allowed_when_explicitly_enabled(self, monkeypatch):
        """A self-hoster ingesting from a wiki on their own LAN is a real use, so the
        default is a setting rather than a ban."""
        monkeypatch.setenv("STUDYFORGE_ALLOW_PRIVATE_URLS", "true")
        monkeypatch.setattr(
            httpx.Client,
            "get",
            lambda self, url, *a, **k: httpx.Response(
                200, text="<p>local wiki</p>", request=httpx.Request("GET", url)
            ),
        )
        assert "local wiki" in ingest.extract_url("http://192.168.1.10/wiki")


def test_clean_text_collapses_whitespace():
    assert clean_text("a  \t b\n\n\n\nc") == "a b\n\nc"


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_chunk_text_single_small():
    assert chunk_text("hello world") == ["hello world"]


def test_chunk_text_packs_paragraphs():
    paras = [f"paragraph {i} " + "x" * 100 for i in range(10)]
    chunks = chunk_text("\n\n".join(paras), max_chars=300)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 300
    # Nothing lost: all paragraphs appear across the chunks
    joined = "\n\n".join(chunks)
    for i in range(10):
        assert f"paragraph {i}" in joined


def test_chunk_text_hard_splits_oversized_paragraph():
    chunks = chunk_text("y" * 1000, max_chars=300)
    assert all(len(c) <= 300 for c in chunks)
    assert sum(len(c) for c in chunks) == 1000


# --------------------------------------------------------------------------
# YouTube sources: video_id routes load_source away from extract_url entirely
# --------------------------------------------------------------------------

YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
GOOD_TEXT = "Gradient descent walks downhill by following the slope. " * 10


def _fake_transcript(text: str) -> youtube.Transcript:
    return youtube.Transcript(
        video_id="dQw4w9WgXcQ",
        title=None,
        captions=(youtube.Caption(start=0.0, duration=1.0, text=text),),
    )


def _pdf_part(label: str) -> tuple:
    return (f"{label}.pdf", f"{label} content: {GOOD_TEXT}".encode(), "application/pdf")


class NeverCalledProvider:
    """See test_multi_source.NeverCalledProvider. Redefined here rather than imported so
    this file does not depend on test collection order or another test module's fixtures."""

    name = "never"
    model = "never"
    is_paid = False

    def generate(self, system, prompt, max_tokens=64000):
        raise AssertionError("a provider was called before the caps refused the request")


def test_a_youtube_url_never_calls_extract_url_or_resolves_a_host(monkeypatch):
    """video_id() routes a hit straight to from_youtube. Neither extract_url (which would
    fetch the SPA shell) nor a DNS lookup (there is no caller-controlled host to guard)
    should run at all."""
    monkeypatch.setattr(youtube, "fetch_transcript", lambda vid: _fake_transcript(GOOD_TEXT))

    def _extract_url_boom(url):
        raise AssertionError("extract_url must not be called for a YouTube URL")

    def _getaddrinfo_boom(*args, **kwargs):
        raise AssertionError("getaddrinfo must not be called for a YouTube URL")

    monkeypatch.setattr(ingest, "extract_url", _extract_url_boom)
    monkeypatch.setattr(ingest.socket, "getaddrinfo", _getaddrinfo_boom)

    source = ingest.load_source(
        ingest.SourceSpec(kind="url", ref=YOUTUBE_URL, value=YOUTUBE_URL),
        main.SOURCE_FAILURE_COPY,
    )

    assert source.kind == "url"
    assert source.ref == YOUTUBE_URL
    assert source.text == GOOD_TEXT.strip()


def test_a_non_youtube_url_still_takes_the_extract_url_path(monkeypatch):
    """The routing decision has to actually route both ways, not just the YouTube one."""
    called = []
    monkeypatch.setattr(ingest, "extract_url", lambda url: called.append(url) or GOOD_TEXT)

    source = ingest.load_source(
        ingest.SourceSpec(kind="url", ref="https://example.com/article", value="https://example.com/article"),
        main.SOURCE_FAILURE_COPY,
    )

    assert called == ["https://example.com/article"]
    assert source.text == GOOD_TEXT


@pytest.mark.parametrize(
    "bad_url",
    [
        "https://www.youtube.com/watch?v=abc",  # too short to be a real id
        "https://youtu.be/dQw4w9WgXcQXX",  # too long
        "https://www.youtube.com/feed/subscriptions",  # a feed, not a video
        "https://www.youtube.com/@someuser",  # a channel, not a video
        "https://www.youtube.com/",  # bare host
    ],
)
def test_a_youtube_host_with_no_parseable_video_id_is_refused(monkeypatch, bad_url):
    """A typo'd or non-video YouTube link must not fall through to extract_url and
    fetch the SPA shell; it should be refused with youtube_bad_url instead."""

    def _extract_url_boom(url):
        raise AssertionError("extract_url must not be called for a YouTube host")

    monkeypatch.setattr(ingest, "extract_url", _extract_url_boom)

    with pytest.raises(ingest.SourceError) as excinfo:
        ingest.load_source(
            ingest.SourceSpec(kind="url", ref=bad_url, value=bad_url),
            main.SOURCE_FAILURE_COPY,
        )
    assert excinfo.value.error == ingest.YOUTUBE_BAD_URL
    assert excinfo.value.message == main.YOUTUBE_BAD_URL_MESSAGE


@pytest.mark.parametrize(
    "reason,code",
    [
        ("no_transcript", ingest.YOUTUBE_NO_TRANSCRIPT),
        ("unavailable", ingest.YOUTUBE_UNAVAILABLE),
    ],
)
def test_transcript_unavailable_reasons_map_to_their_own_codes(monkeypatch, reason, code):
    def _raise(video_id):
        raise youtube.TranscriptUnavailable(reason)

    monkeypatch.setattr(youtube, "fetch_transcript", _raise)

    with pytest.raises(ingest.SourceError) as excinfo:
        ingest.load_source(
            ingest.SourceSpec(kind="url", ref=YOUTUBE_URL, value=YOUTUBE_URL),
            main.SOURCE_FAILURE_COPY,
        )
    assert excinfo.value.error == code
    assert excinfo.value.message == main.SOURCE_FAILURE_COPY[code]


def test_transcript_unavailable_fetch_failed_falls_to_the_existing_code(monkeypatch):
    """The one TranscriptUnavailable reason that is NOT a new code: a retryable fetch
    problem is reported the same way any other fetch failure is."""

    def _raise(video_id):
        raise youtube.TranscriptUnavailable("fetch_failed")

    monkeypatch.setattr(youtube, "fetch_transcript", _raise)

    with pytest.raises(ingest.SourceError) as excinfo:
        ingest.load_source(
            ingest.SourceSpec(kind="url", ref=YOUTUBE_URL, value=YOUTUBE_URL),
            main.SOURCE_FAILURE_COPY,
        )
    assert excinfo.value.error == ingest.FETCH_FAILED
    assert excinfo.value.error not in {ingest.YOUTUBE_NO_TRANSCRIPT, ingest.YOUTUBE_UNAVAILABLE}


def test_a_captionless_video_is_a_422_source_failed_with_its_own_sentence(client, monkeypatch):
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    def _raise(video_id):
        raise youtube.TranscriptUnavailable("no_transcript")

    monkeypatch.setattr(youtube, "fetch_transcript", _raise)

    response = client.post(
        "/courses/generate", json={"sources": [{"kind": "url", "value": YOUTUBE_URL}]}
    )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "source_failed"
    (entry,) = detail["sources"]
    assert entry["error"] == ingest.YOUTUBE_NO_TRANSCRIPT
    assert entry["error"] != ingest.NO_USABLE_TEXT
    assert entry["message"] == main.YOUTUBE_NO_TRANSCRIPT_MESSAGE


def test_a_mixed_pdf_and_captionless_video_reports_only_the_video(client, monkeypatch):
    """One readable PDF plus one captionless video: exactly one failure, and `index`
    points at the video's position in the combined request, not the PDF's."""
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())
    monkeypatch.setattr(ingest, "extract_pdf", lambda data: data.decode())

    def _raise(video_id):
        raise youtube.TranscriptUnavailable("no_transcript")

    monkeypatch.setattr(youtube, "fetch_transcript", _raise)

    response = client.post(
        "/courses/generate/multipart",
        data={"sources": json.dumps([{"kind": "url", "value": YOUTUBE_URL}])},
        files=[("file", _pdf_part("good"))],
    )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "source_failed"
    (entry,) = detail["sources"]
    assert entry["index"] == 0, "the video was sent first (sources, then file)"
    assert entry["kind"] == "url"
    assert entry["error"] == ingest.YOUTUBE_NO_TRANSCRIPT


@pytest.mark.parametrize(
    "code,message",
    [
        (ingest.YOUTUBE_NO_TRANSCRIPT, main.YOUTUBE_NO_TRANSCRIPT_MESSAGE),
        (ingest.YOUTUBE_UNAVAILABLE, main.YOUTUBE_UNAVAILABLE_MESSAGE),
        (ingest.YOUTUBE_BAD_URL, main.YOUTUBE_BAD_URL_MESSAGE),
    ],
)
def test_each_new_code_gets_its_own_sentence_through_legacy_refusal(code, message):
    """Not the fallback. Without a branch for a new code, _legacy_refusal falls through
    to "No usable text found in the source", which would be a wrong sentence for all
    three of these."""
    failure = ingest.SourceFailure(
        kind="url", ref=YOUTUBE_URL, error=code, message=message, index=0
    )

    exc = main._legacy_refusal(failure, stage="url")

    assert exc.status_code == 400
    assert exc.detail == message
    assert exc.detail != "No usable text found in the source"


def test_the_legacy_single_url_body_gets_the_new_message_too(client, monkeypatch):
    """The deprecated single-`url` request path routes through the same failure codes,
    so it must not regress to the generic fallback sentence either."""
    monkeypatch.setattr(main, "get_provider", lambda: NeverCalledProvider())

    def _raise(video_id):
        raise youtube.TranscriptUnavailable("unavailable")

    monkeypatch.setattr(youtube, "fetch_transcript", _raise)

    response = client.post("/courses/generate", json={"url": YOUTUBE_URL})

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == main.YOUTUBE_UNAVAILABLE_MESSAGE
