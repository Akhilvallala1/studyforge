import socket

import httpx
import pytest

from app import ingest
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
