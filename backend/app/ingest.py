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
#
# THE QUANTITY THAT ACTUALLY COSTS MONEY IS THE CHUNK COUNT, not either of these directly.
# Chunks are what generation routes on (generation.SEGMENT_ROUTING_MIN_CHUNKS, currently 3)
# and what the outline prompt is built from, and lessons accrue on top of that. So the
# caps are worth reading as a joint bound on chunks rather than as two independent limits.
#
# NEITHER CAP BOUNDS THE CHUNK COUNT ON ITS OWN, which is the part that is easy to get
# wrong and was. Measured, with MAX_CHUNK_CHARS at 8,000:
#
#   sources  chars each   total    chunks  routed
#         1       3,000    3,000        1  no
#         2       3,000    6,000        2  no
#         3       3,000    9,000        3  YES
#         5       1,000    5,000        5  YES
#         1      10,640   10,640        2  no
#         1      24,000   24,000        3  YES
#
# Read the fourth row against the fifth. FIVE THOUSAND CHARACTERS IS ROUTED AND TEN
# THOUSAND IS NOT, because chunk_sources chunks PER SOURCE, so every source contributes at
# least one chunk however short it is. Routing is therefore not purely a size effect: three
# documents of any length at all cross the threshold, while one document of 10,640 does
# not. A character cap alone leaves the many-small-documents case unbounded, and a source
# cap alone leaves the one-huge-document case unbounded. Together they bound it, and that
# is the only reason both exist.
#
# WHAT ACTUALLY MOVES THE CHUNK COUNT IS PARAGRAPH LENGTH, not source count, and this was
# measured only after two people had guessed otherwise. chunk_text packs whole paragraphs
# greedily and never splits one below MAX_CHUNK_CHARS, so a paragraph just over half the
# chunk size fits ONE per chunk and wastes the rest. Chunks for 150,000 characters:
#
#   paragraph   1 doc  2 docs  3 docs  5 docs
#         200      20      20      21      20
#       1,500      20      20      21      20
#       2,700      28      28      27      30
#       4,001      37      36      36      35   <- worst packing
#       5,000      30      30      30      30
#       7,999      19      20      21      20
#
# Source count moves it by about one. Paragraph length nearly DOUBLES it. So a ceiling of
# the form chars/MAX_CHUNK_CHARS is a LOWER bound and not an upper one, which is the error
# the constant below used to encode: it read 24 while the real worst case was 37.
#
# THE DERIVED CEILING is MAX_TOTAL_CHUNKS, computed from the other two so that raising
# either cap moves it. The factor of two is the packing slack above: a chunk is guaranteed
# only to be more than half full, never to be full.
# test_the_two_caps_together_bound_the_chunk_count is what stops one cap being raised
# without the other being thought about, and it feeds the WORST-PACKING paragraph length
# rather than a convenient one, because the earlier version of it used a single unbroken
# paragraph, which is the BEST case, and passed against a ceiling that was wrong by 13.
#
# WHAT THESE NUMBERS ARE NOT. They do not make a run fit a proxy timeout, and a comment
# claiming they did would be false precision: the LESSON COUNT is the model's choice, not a
# function of any of this, and nginx's default proxy_read_timeout of 60 seconds is already
# short for a single-source run today. That is a deployment note, not something a cap can
# fix. What a cap can do is keep the worst case a known multiple of the ordinary one.
#
# WHY MAX_TOTAL_CHARS IS AS HIGH AS IT IS, since the temptation is to tighten it: this cap
# applies to EVERY request, including the single-source path that has been uncapped since
# the project started. Anything below roughly this figure would start refusing pastes that
# work today, which is a regression for existing users dressed up as a safety limit. It is
# sized to be the first cap those users ever meet, not the tightest defensible number.
MAX_SOURCES = 5
MAX_TOTAL_CHARS = 150_000
# How long a source's label may be. `ref` is FULLY CALLER-CONTROLLED on every kind: the URL
# they typed, the `ref` they sent, or the filename they uploaded under. It is echoed back in
# the source_failed refusal, so an unbounded one is an unbounded string this API repeats to
# whoever sent it, and it is read by whatever builds the generation prompt, where a label is
# a structural marker rather than prose.
#
# THIS IS A BOUND, NOT A DEFUSING, and the distinction matters because the first looks like
# the second. Truncating and flattening stops a label being enormous or spanning lines; it
# does NOT stop one imitating whatever marker the prompt writes around it. That has to
# happen where the marker grammar is known, the way tutor.py scrubs its own fences and
# register labels through untrusted.as_data rather than trusting its inputs to be tame.
MAX_REF_CHARS = 200
# Ceiling on chunks, derived: each source contributes at least one partial chunk, and
# beyond that chunks accrue at no worse than half of MAX_CHUNK_CHARS, because a paragraph
# is packed whole and one just over half the limit leaves the rest of its chunk empty.
# Not enforced separately, because a third cap on the same quantity is a third thing to
# keep consistent; it exists so the joint bound has a name and a test.
MAX_TOTAL_CHUNKS = MAX_SOURCES + 2 * -(-MAX_TOTAL_CHARS // MAX_CHUNK_CHARS)

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


# What a caller is told when the copy dict is missing an entry. Theoretical today, since
# main.py is the only caller and its dict is complete, and closed anyway: a KeyError raised
# inside ingestion is not a SourceError, so load_sources would not catch it and it would
# escape as a 500 with no `detail` at all. That is the same shapeless failure the unvalidated
# `kind` used to produce, and one line is cheaper than trusting a dict to stay complete.
FALLBACK_COPY = "That source could not be read."


def _copy_for(copy: dict[str, str], code: str) -> str:
    return copy.get(code) or FALLBACK_COPY


def clean_ref(raw: str) -> str:
    """A source label, flattened to one line and cut to MAX_REF_CHARS.

    Line breaks go first and that is the half worth explaining. A label is written into
    single-line contexts, an error row and a prompt tag among them, so one carrying a
    newline is a label that continues onto a line of its own where nothing expects it. That
    is the same shape as the register-label forgery tutor.py defends against, one field
    over, and flattening removes the cheapest version of it without pretending to be the
    whole defence. See MAX_REF_CHARS.

    The ellipsis is inside the budget rather than added to it, matching tutor._hard_cut, so
    a truncated label is visibly truncated rather than looking like a shorter name.
    """
    flat = " ".join((raw or "").split())
    if len(flat) <= MAX_REF_CHARS:
        return flat
    return flat[: MAX_REF_CHARS - 3].rstrip() + "..."


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
            raise SourceError(FETCH_FAILED, _copy_for(copy, FETCH_FAILED)) from exc
    elif spec.kind == "pdf":
        try:
            data = spec.value if isinstance(spec.value, bytes) else str(spec.value).encode()
            source = from_pdf_bytes("", spec.ref, data)
        except Exception as exc:
            raise SourceError(PDF_UNREADABLE, _copy_for(copy, PDF_UNREADABLE)) from exc
    else:
        raise ValueError(f"Unknown source kind: {spec.kind!r}")

    if not source.text.strip():
        # A URL that fetched cleanly and a PDF that parsed cleanly can both yield nothing:
        # a scanned page, a JavaScript-rendered site, an empty paste. That is a failure of
        # THIS source rather than of the request, so it is reported like the others.
        raise SourceError(NO_USABLE_TEXT, _copy_for(copy, NO_USABLE_TEXT))
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
    for raw_spec in specs:
        # Cleaned once, here, so the Source and the SourceFailure carry the same label and
        # neither path can be the one that forgot.
        spec = SourceSpec(kind=raw_spec.kind, ref=clean_ref(raw_spec.ref), value=raw_spec.value)
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

    THIS IS ALSO THE COUNT GENERATION SEES, and that identity is worth protecting. The list
    returned here is passed to generation.generate_course unchanged and never re-chunked, so
    len() of it is exactly the number routing keys off. Anything that measured chunks by
    concatenating first would be measuring a different quantity: five 1,000-character
    sources are FIVE chunks here and ONE concatenated, so a concatenating measurement
    reports an unrouted run for a routed one. The eval harness had precisely that bug.
    """
    return [chunk for source in sources for chunk in chunk_text(source.text)]
