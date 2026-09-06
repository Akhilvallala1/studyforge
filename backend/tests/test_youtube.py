"""app.youtube in isolation: URL parsing, and fetch_transcript's exception mapping.

Nothing here touches the network. video_id is pure parsing with no import of the
transcript library at all. fetch_transcript imports youtube_transcript_api inside its
own body (see the module docstring on why), so these tests reach into that library's
YouTubeTranscriptApi class and replace `.list` with a fake, the same way test_ingest.py
replaces httpx.Client.get rather than mocking at the network layer.
"""

import pytest

from app import youtube

GOOD_ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url,expected",
    [
        (f"https://www.youtube.com/watch?v={GOOD_ID}", GOOD_ID),
        (f"https://youtube.com/watch?v={GOOD_ID}", GOOD_ID),
        (f"https://youtu.be/{GOOD_ID}", GOOD_ID),
        (f"https://youtube.com/shorts/{GOOD_ID}", GOOD_ID),
        (f"https://www.youtube.com/embed/{GOOD_ID}", GOOD_ID),
        (f"https://www.youtube.com/live/{GOOD_ID}", GOOD_ID),
        (f"https://m.youtube.com/watch?v={GOOD_ID}", GOOD_ID),
        (f"https://WWW.YOUTUBE.COM/watch?v={GOOD_ID}", GOOD_ID),
        (f"https://www.youtube.com/watch?v={GOOD_ID}&t=42s", GOOD_ID),
        (f"https://www.youtube.com/watch?v={GOOD_ID}&list=PLxyz", GOOD_ID),
        (f"https://youtu.be/{GOOD_ID}?si=abc123XYZ", GOOD_ID),
        (f"https://www.youtube-nocookie.com/embed/{GOOD_ID}", GOOD_ID),
        (f"https://youtube-nocookie.com/embed/{GOOD_ID}", GOOD_ID),
        (GOOD_ID, None),  # a bare id, not a URL
        (f"https://youtu.be/{GOOD_ID[:10]}", None),  # 10 characters
        (f"https://youtu.be/{GOOD_ID}Q", None),  # 12 characters
        ("https://youtube.com/feed/subscriptions", None),  # a feed, not a video
        ("https://youtube.com/@someuser", None),  # a channel, not a video
        ("https://youtube.com/", None),  # bare host
        ("https://example.com/watch?v=" + GOOD_ID, None),  # not a YouTube host
        ("not a url at all", None),
        ("", None),
    ],
)
def test_video_id(url, expected):
    assert youtube.video_id(url) == expected


@pytest.mark.parametrize(
    "url,expected",
    [
        (f"https://www.youtube.com/watch?v={GOOD_ID}", True),
        (f"https://youtube.com/watch?v={GOOD_ID}", True),
        (f"https://m.youtube.com/watch?v={GOOD_ID}", True),
        (f"https://youtu.be/{GOOD_ID}", True),
        (f"https://YOUTU.BE/{GOOD_ID}", True),
        (f"https://www.youtube-nocookie.com/embed/{GOOD_ID}", True),
        ("https://youtube.com/feed/subscriptions", True),  # a YouTube host, just not a video
        ("https://example.com/watch?v=" + GOOD_ID, False),
        ("https://notyoutube.com/watch?v=" + GOOD_ID, False),  # not a substring match
        ("https://youtube.com.evil.example/watch?v=" + GOOD_ID, False),  # nor this one
        ("not a url at all", False),
        ("", False),
    ],
)
def test_is_youtube_url(url, expected):
    assert youtube.is_youtube_url(url) == expected


class _Snippet:
    def __init__(self, text, start, duration):
        self.text = text
        self.start = start
        self.duration = duration


class _FetchedTranscript:
    def __init__(self, snippets):
        self._snippets = snippets

    def __iter__(self):
        return iter(self._snippets)


class _Transcript:
    def __init__(self, snippets):
        self._snippets = snippets

    def fetch(self):
        return _FetchedTranscript(self._snippets)


def _patch_list(monkeypatch, result_or_raiser):
    """Replace YouTubeTranscriptApi.list with something that returns or raises `result_or_raiser`."""
    from youtube_transcript_api import YouTubeTranscriptApi

    if isinstance(result_or_raiser, Exception):
        def fake_list(self, video_id):
            raise result_or_raiser
    else:
        def fake_list(self, video_id):
            return result_or_raiser

    monkeypatch.setattr(YouTubeTranscriptApi, "list", fake_list)


def test_fetch_transcript_returns_captions_and_joined_text(monkeypatch):
    snippets = [_Snippet("Hello", 0.0, 1.5), _Snippet("world.", 1.5, 1.0)]
    _patch_list(monkeypatch, [_Transcript(snippets)])

    transcript = youtube.fetch_transcript(GOOD_ID)

    assert transcript.video_id == GOOD_ID
    assert [c.text for c in transcript.captions] == ["Hello", "world."]
    assert transcript.captions[1].start == 1.5
    assert transcript.captions[1].duration == 1.0
    assert transcript.text() == "Hello world."


def test_fetch_transcript_collapses_whitespace_in_joined_text(monkeypatch):
    snippets = [_Snippet("  a  ", 0.0, 1.0), _Snippet("b\n", 1.0, 1.0)]
    _patch_list(monkeypatch, [_Transcript(snippets)])

    assert youtube.fetch_transcript(GOOD_ID).text() == "a b"


def test_no_transcripts_available_at_all_is_no_transcript(monkeypatch):
    _patch_list(monkeypatch, [])  # empty TranscriptList

    with pytest.raises(youtube.TranscriptUnavailable) as excinfo:
        youtube.fetch_transcript(GOOD_ID)
    assert excinfo.value.reason == "no_transcript"


def test_transcripts_disabled_is_no_transcript(monkeypatch):
    from youtube_transcript_api import TranscriptsDisabled

    _patch_list(monkeypatch, TranscriptsDisabled(GOOD_ID))

    with pytest.raises(youtube.TranscriptUnavailable) as excinfo:
        youtube.fetch_transcript(GOOD_ID)
    assert excinfo.value.reason == "no_transcript"


def test_video_unavailable_is_unavailable(monkeypatch):
    from youtube_transcript_api import VideoUnavailable

    _patch_list(monkeypatch, VideoUnavailable(GOOD_ID))

    with pytest.raises(youtube.TranscriptUnavailable) as excinfo:
        youtube.fetch_transcript(GOOD_ID)
    assert excinfo.value.reason == "unavailable"


def test_video_unplayable_is_unavailable(monkeypatch):
    from youtube_transcript_api import VideoUnplayable

    _patch_list(monkeypatch, VideoUnplayable(GOOD_ID, "age_restricted", []))

    with pytest.raises(youtube.TranscriptUnavailable) as excinfo:
        youtube.fetch_transcript(GOOD_ID)
    assert excinfo.value.reason == "unavailable"


def test_age_restricted_is_unavailable(monkeypatch):
    from youtube_transcript_api import AgeRestricted

    _patch_list(monkeypatch, AgeRestricted(GOOD_ID))

    with pytest.raises(youtube.TranscriptUnavailable) as excinfo:
        youtube.fetch_transcript(GOOD_ID)
    assert excinfo.value.reason == "unavailable"


def test_invalid_video_id_is_unavailable(monkeypatch):
    from youtube_transcript_api import InvalidVideoId

    _patch_list(monkeypatch, InvalidVideoId(GOOD_ID))

    with pytest.raises(youtube.TranscriptUnavailable) as excinfo:
        youtube.fetch_transcript(GOOD_ID)
    assert excinfo.value.reason == "unavailable"


def test_a_blocked_request_is_fetch_failed_not_unavailable(monkeypatch):
    """RequestBlocked and friends are about the fetch, not about the video, so a caller
    should be told this is worth retrying rather than that the video is broken."""
    from youtube_transcript_api import RequestBlocked

    _patch_list(monkeypatch, RequestBlocked(GOOD_ID))

    with pytest.raises(youtube.TranscriptUnavailable) as excinfo:
        youtube.fetch_transcript(GOOD_ID)
    assert excinfo.value.reason == "fetch_failed"


def test_an_unrelated_exception_is_fetch_failed(monkeypatch):
    """Anything the library did not anticipate falls to fetch_failed rather than
    escaping as a raw exception that main.py has no branch for."""
    _patch_list(monkeypatch, ConnectionError("network blip"))

    with pytest.raises(youtube.TranscriptUnavailable) as excinfo:
        youtube.fetch_transcript(GOOD_ID)
    assert excinfo.value.reason == "fetch_failed"
