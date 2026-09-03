"""Turn source material (PDF bytes, plain text, or a URL) into cleaned text chunks.

ONE COURSE CAN BE BUILT FROM SEVERAL SOURCES, and `Source` is what one of them is once
it has been read. The dataclass was written for the eval harness, which deliberately
ingests through this module so that it measures the text the generator actually receives.
It lives here now and evals/sources.py imports it: it was already describing this module's
output, and two spellings of it would have drifted the moment either side gained a field.
"""

import io
import ipaddress
import os
import re
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader

MAX_CHUNK_CHARS = 8000

# HOW MANY SOURCES ONE COURSE CAN BE BUILT FROM, and how much text they may amount to.
# These are not tidiness. Generation is synchronous: the whole ingested text goes into the
# outline call, and every lesson the outline invents costs another sequential call, so
# total characters is the one input that bounds both the largest prompt and the number of
# calls after it. Without a ceiling, five long documents turn one request into a wall-clock
# time nothing in the stack is prepared to wait for.
#
# ON THE NUMBERS, and what is and is not measured. MAX_TOTAL_CHARS is about 19 segments at
# MAX_CHUNK_CHARS, the same order as the largest single paste anyone makes today, and
# roughly 37k tokens, which sits comfortably inside Anthropic's window and far outside the
# 8192-token one Ollama defaults to. That last part is not new: a single large paste
# already exceeded it, and ollama_provider refuses from Ollama's own reported counts rather
# than from arithmetic here.
#
# WHAT IS NOT BOUNDED, stated because the comment would otherwise claim more than it has:
# the LESSON COUNT is the model's choice, not a function of these numbers, so wall time is
# bounded only indirectly. If generation starts timing out below these caps, the lesson
# count is the thing to look at, not this constant.
MAX_SOURCES = 5
MAX_TOTAL_CHARS = 150_000

# Real chains stack up (http to https, apex to www, locale, consent), so 5 was tight
# enough to refuse legitimate pages. httpx itself defaults to 20.
MAX_REDIRECTS = 10

# RFC 6598 carrier-grade NAT. Python deliberately reports these as public, but some
# cloud providers use the range for internal networks, so it is checked by hand.
_CGNAT = ipaddress.ip_network("100.64.0.0/10")


class UnsafeURLError(ValueError):
    """The URL points somewhere the server should not fetch on a caller's behalf."""


def _is_internal(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
        or (address.version == 4 and address in _CGNAT)
    )


def _allow_private_hosts() -> bool:
    """Whether to permit fetching private, loopback and link-local addresses.

    Off by default. A self-hoster running StudyForge alongside a wiki on the same
    LAN has a real reason to turn it on, so this is a setting rather than a ban, but
    it must be a deliberate act: the safe default protects anyone who exposes the
    API to people they do not fully trust.
    """
    return os.environ.get("STUDYFORGE_ALLOW_PRIVATE_URLS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _check_host(url: str) -> None:
    """Reject a URL that would make the server fetch something on its own network.

    Without this the URL ingest is a server-side request forgery surface: anyone who
    can reach the API can use it to probe localhost and the private network, reading
    back whatever responds as course material. That matters even for a self-hosted
    app the moment it is exposed beyond one machine, and a cloud deployment would
    hand out its metadata endpoint.

    Every hostname the request touches is checked, not only the first, because a
    permitted public URL is free to redirect to 127.0.0.1.

    The name is classified by what it RESOLVES to, never by how it is spelled. That
    is what makes the alternate-encoding tricks (decimal and octal IPs, IPv4-mapped
    IPv6, fullwidth digits, IDN homographs) uninteresting: either the name resolves
    and the address is judged, or it does not and the fetch is refused.

    Known limitation, deliberately not fixed: the name is resolved here and resolved
    again by httpx when it connects, so a domain the attacker controls with a
    sub-second TTL could in principle answer differently the second time. Closing
    that means connecting to the validated address with a Host header through a
    custom transport, which is disproportionate for a self-hosted study app.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError(f"Only http and https URLs can be fetched, not {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise UnsafeURLError("That URL has no host")
    try:
        port = parsed.port
    except ValueError as exc:
        # urlparse defers port parsing to attribute access, so a malformed port
        # arrives here as a bare ValueError. Left unwrapped it escapes as a generic
        # failure and the caller is told to retry a URL that cannot work.
        raise UnsafeURLError("That URL has an invalid port") from exc
    if _allow_private_hosts():
        return

    try:
        # Every address the name resolves to, since a name can carry both a public
        # and a private record and httpx may pick either.
        infos = socket.getaddrinfo(host, port or (443 if parsed.scheme == "https" else 80))
    except OSError as exc:
        raise UnsafeURLError(f"Could not resolve {host}") from exc

    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if _is_internal(address):
            # Deliberately not naming the resolved address. This message reaches the
            # UI verbatim, and reporting "resolves to 10.1.2.3" versus "could not
            # resolve" turns the endpoint into an internal DNS oracle. The half that
            # helps a legitimate user is kept.
            raise UnsafeURLError(
                f"{host} is on a private or local network, which StudyForge will not "
                "fetch. Set STUDYFORGE_ALLOW_PRIVATE_URLS=true if that is deliberate."
            )


def extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def extract_url(url: str) -> str:
    """Fetch a page and strip it to text, refusing to fetch private addresses.

    Redirects are followed by hand rather than by httpx so that each hop can be
    checked. Handing follow_redirects to the client would check only the URL the
    caller supplied, and the interesting attack is a public URL that redirects
    inward.
    """
    with httpx.Client(follow_redirects=False, timeout=30) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _check_host(url)
            response = client.get(url)
            if not response.is_redirect:
                break
            location = response.headers.get("location")
            if not location:
                break
            url = str(response.url.join(location))
        else:
            raise UnsafeURLError("That URL redirected too many times")

    response.raise_for_status()
    html = response.text
    # Crude tag strip - good enough for the MVP; a real HTML-to-text pass is a TODO.
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return clean_text(text)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split on paragraph boundaries, packing paragraphs up to max_chars per chunk."""
    text = clean_text(text)
    if not text:
        return []
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in paragraphs:
        # A single paragraph longer than max_chars gets hard-split.
        while len(para) > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current, current_len = [], 0
            chunks.append(para[:max_chars])
            para = para[max_chars:]
        if current_len + len(para) + 2 > max_chars and current:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(para)
        current_len += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


# --------------------------------------------------------------------------
# One course, several sources
# --------------------------------------------------------------------------


@dataclass
class Source:
    """One piece of source material, after it has been read into text.

    Lifted from evals/sources.py rather than copied. `key` is a short stable handle the
    eval harness groups by; the app leaves it empty, because nothing in the request path
    needs to name a source twice.
    """

    key: str
    kind: str  # "url" | "text" | "pdf"
    ref: str
    text: str

    def meta(self) -> dict:
        return {"key": self.key, "kind": self.kind, "ref": self.ref}


@dataclass
class SourceSpec:
    """One piece of source material BEFORE it has been read: what to fetch, not what was.

    A separate type from Source and deliberately not the same one carrying an empty `text`.
    The whole point of the pair is that a spec can fail to become a source, and a type that
    could be either would have to be checked at every use to find out which it was.
    """

    kind: str
    ref: str
    value: str | bytes


@dataclass
class SourceFailure:
    """One source that could not be read, and why, in the terms the caller reports.

    `error` is a code a client branches on and `message` is a sentence a person reads,
    matching the refusal shape the rest of this API uses. The message is the SAME copy the
    single-source path has always returned, so multi-source reporting is that message
    repeated per source rather than a second vocabulary.
    """

    kind: str
    ref: str
    error: str
    message: str

    def payload(self) -> dict:
        return {"kind": self.kind, "ref": self.ref, "error": self.error, "message": self.message}


class TooManySources(ValueError):
    """More sources than MAX_SOURCES. Raised before anything is fetched."""


# The per-source failure codes and the copy that goes with them. The copy is duplicated
# from main.py's constants ON PURPOSE not at all: main.py passes it in, so there is one
# definition of each sentence and this module holds none of it.
UNSAFE_URL = "unsafe_url"
FETCH_FAILED = "fetch_failed"
PDF_UNREADABLE = "pdf_unreadable"
NO_USABLE_TEXT = "no_usable_text"


def from_url(key: str, url: str) -> Source:
    return Source(key=key, kind="url", ref=url, text=extract_url(url))


def from_text(key: str, label: str, text: str) -> Source:
    return Source(key=key, kind="text", ref=label, text=clean_text(text))


def from_pdf_bytes(key: str, label: str, data: bytes) -> Source:
    return Source(key=key, kind="pdf", ref=label, text=extract_pdf(data))


def load_source(spec: SourceSpec, copy: dict[str, str]) -> Source:
    """Read one spec, or raise. `copy` maps a failure code to the sentence for it.

    The copy is injected rather than held here because those sentences are user-facing
    product text that already lives in main.py, and a second copy of a sentence is a second
    thing to edit. This module knows which failure happened; main.py knows how to say it.
    """
    if spec.kind == "text":
        source = from_text("", spec.ref, spec.value if isinstance(spec.value, str) else "")
    elif spec.kind == "url":
        try:
            source = from_url("", str(spec.value))
        except UnsafeURLError as exc:
            # The guard's OWN message, not a generic one. It names the host and says how a
            # self-hoster turns the check off, which is the whole value of it.
            raise SourceError(UNSAFE_URL, str(exc)) from exc
        except Exception as exc:
            raise SourceError(FETCH_FAILED, copy[FETCH_FAILED]) from exc
    elif spec.kind == "pdf":
        try:
            data = spec.value if isinstance(spec.value, bytes) else str(spec.value).encode()
            source = from_pdf_bytes("", spec.ref, data)
        except Exception as exc:
            raise SourceError(PDF_UNREADABLE, copy[PDF_UNREADABLE]) from exc
    else:
        raise ValueError(f"Unknown source kind: {spec.kind!r}")

    if not source.text.strip():
        # A URL that fetched cleanly and a PDF that parsed cleanly can both yield nothing:
        # a scanned page, a JavaScript-rendered site, an empty paste. That is a failure of
        # THIS source rather than of the request, so it is reported like the others.
        raise SourceError(NO_USABLE_TEXT, copy[NO_USABLE_TEXT])
    return source


class SourceError(Exception):
    """One source failed. Carries the code and the sentence, nothing else."""

    def __init__(self, error: str, message: str):
        super().__init__(message)
        self.error = error
        self.message = message


def load_sources(
    specs: list[SourceSpec], copy: dict[str, str]
) -> tuple[list[Source], list[SourceFailure]]:
    """Read every spec and return BOTH what worked and what did not.

    EVERY OUTCOME, NOT THE FIRST FAILURE, and that is the point of the function. A caller
    that stopped at the first bad URL would make someone fix five sources one request at a
    time, learning about the second only after correcting the first. The loop has no early
    exit for exactly that reason, and the test that matters mixes good and bad and counts
    both lists.

    The count cap is checked BEFORE the loop, so an over-limit request costs no fetches at
    all rather than MAX_SOURCES of them. The size cap is not checked here, because the size
    is not known until the fetching is done; the caller applies MAX_TOTAL_CHARS to what
    comes back.
    """
    if len(specs) > MAX_SOURCES:
        raise TooManySources(len(specs))

    sources: list[Source] = []
    failures: list[SourceFailure] = []
    for spec in specs:
        try:
            sources.append(load_source(spec, copy))
        except SourceError as exc:
            failures.append(
                SourceFailure(kind=spec.kind, ref=spec.ref, error=exc.error, message=exc.message)
            )
    return sources, failures


def total_chars(sources: list[Source]) -> int:
    return sum(len(source.text) for source in sources)


def chunk_sources(sources: list[Source]) -> list[str]:
    """Every source chunked, in order, with no chunk spanning two sources.

    Chunking per source rather than concatenating first. The texts are unrelated documents,
    so a chunk straddling the join would be a segment the outline is asked to summarise as
    one topic when it is two, and provenance (a later task) needs the boundary to survive
    anyway.
    """
    return [chunk for source in sources for chunk in chunk_text(source.text)]
