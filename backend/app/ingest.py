"""Turn source material (PDF bytes, plain text, or a URL) into cleaned text chunks."""

import io
import ipaddress
import os
import re
import socket
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader

MAX_CHUNK_CHARS = 8000

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
