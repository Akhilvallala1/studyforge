"""Turn a YouTube URL into the video id, and a video id into its transcript text.

`is_youtube_url` and `video_id` are pure parsing: no network, no import of the
transcript library, so either is free to call from anywhere that needs to recognise a
YouTube URL. `fetch_transcript` is
the only function in this module (or anywhere else in the app) that imports
`youtube_transcript_api`, so swapping that dependency later, or mocking it in a test,
touches this one function and nothing that calls it.
"""

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

# Every current YouTube video id is exactly 11 of these characters. Anything else is
# either not a video id or a share link's tracking suffix, not a shorter/longer id.
WATCH_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_PATH_KINDS = ("shorts", "embed", "live")


def is_youtube_url(url: str) -> bool:
    """True if `url`'s host is one of YouTube's, matched exactly (never by substring)
    against `_HOSTS`, so a lookalike like youtube.com.evil.example reads as "not
    YouTube" and falls through to the ordinary, SSRF-checked URL path rather than into
    the branch that skips it. Call this before `video_id` to tell "not a video link at
    all" from "a video link `video_id` could not parse".
    """
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and host in _HOSTS


def video_id(url: str) -> str | None:
    """The 11-character video id in a YouTube URL, or None if none could be parsed.

    Only meaningful once `is_youtube_url(url)` is True; on a non-YouTube URL this also
    returns None, but that case is `is_youtube_url`'s to report, not this function's.
    For a recognised YouTube host, None means the URL names no video: a channel or feed
    page, a bare host, or a candidate id of the wrong length.
    """
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or host not in _HOSTS:
        return None

    candidate: str | None = None
    if host in {"youtu.be", "www.youtu.be"}:
        parts = [p for p in parsed.path.split("/") if p]
        candidate = parts[0] if parts else None
    else:
        parts = [p for p in parsed.path.split("/") if p]
        if parts and parts[0] in _PATH_KINDS:
            candidate = parts[1] if len(parts) > 1 else None
        elif not parts or parts[0] == "watch":
            candidate = (parse_qs(parsed.query).get("v") or [None])[0]

    if candidate and WATCH_ID.match(candidate):
        return candidate
    return None


@dataclass(frozen=True)
class Caption:
    """One transcript line, with its position in the video.

    start/duration are unused by Phase A, which only reads `Transcript.text()`, but are
    kept because Phase C anchors a lesson's timestamp links off exactly these offsets and
    re-fetching later to recover them would repeat a network call for data already in hand.
    """

    start: float
    duration: float
    text: str


@dataclass(frozen=True)
class Transcript:
    video_id: str
    title: str | None
    captions: tuple[Caption, ...]

    def text(self) -> str:
        joined = " ".join(caption.text for caption in self.captions)
        return re.sub(r"\s+", " ", joined).strip()


class TranscriptUnavailable(Exception):
    """No usable transcript for this video. `reason` is one of "no_transcript",
    "unavailable" or "fetch_failed"; see fetch_transcript for what each means."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def fetch_transcript(video_id: str) -> Transcript:
    """Fetch the transcript for a video id (not a URL; see the module's `video_id`).

    Raises TranscriptUnavailable with:
      "no_transcript": the video has no captions in any language.
      "unavailable": the video itself cannot be watched (removed, private, age-gated,
        or the id does not name a real video).
      "fetch_failed": YouTube could be reached but the transcript could not, for a
        reason worth retrying rather than treating as a property of the video (rate
        limiting, a blocked request, a malformed response).

    The library's `.list()` already picks the first available transcript in whatever
    language exists; this does not restrict to English, since course generation reads
    the transcript as source text in whatever language it is in.
    """
    from youtube_transcript_api import (
        AgeRestricted,
        CouldNotRetrieveTranscript,
        InvalidVideoId,
        TranscriptsDisabled,
        VideoUnavailable,
        VideoUnplayable,
        YouTubeTranscriptApi,
    )

    try:
        available = YouTubeTranscriptApi().list(video_id)
        transcript = next(iter(available), None)
        if transcript is None:
            raise TranscriptUnavailable("no_transcript")
        fetched = transcript.fetch()
    except TranscriptUnavailable:
        raise
    except TranscriptsDisabled as exc:
        raise TranscriptUnavailable("no_transcript") from exc
    except (VideoUnavailable, VideoUnplayable, AgeRestricted, InvalidVideoId) as exc:
        raise TranscriptUnavailable("unavailable") from exc
    except CouldNotRetrieveTranscript as exc:
        # Every other library-specific failure: blocked or rate-limited requests, a
        # missing consent cookie, a captions response that failed to parse. All of
        # these are about the fetch, not the video, so all retry the same way.
        raise TranscriptUnavailable("fetch_failed") from exc
    except Exception as exc:
        raise TranscriptUnavailable("fetch_failed") from exc

    captions = tuple(
        Caption(start=snippet.start, duration=snippet.duration, text=snippet.text)
        for snippet in fetched
    )
    return Transcript(video_id=video_id, title=None, captions=captions)
