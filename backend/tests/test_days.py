"""Local study days that start at 04:00, survive DST, and never crash on a bad zone."""

import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest

from app import days


def stored(text: str) -> datetime:
    """A timestamp in the shape SQLite hands back: naive, meaning UTC.

    day_bounds returns these because that is what they have to be comparable against.
    Built from an ISO string rather than datetime(...) so the naive-ness reads as the
    deliberate choice it is, not as a forgotten tzinfo argument.
    """
    return datetime.fromisoformat(text)


NY = "America/New_York"


@pytest.fixture
def new_york(monkeypatch):
    monkeypatch.setenv("STUDYFORGE_TIMEZONE", NY)
    return ZoneInfo(NY)


@pytest.fixture(autouse=True)
def _clear_warning_memo():
    """local_tz warns once per bad zone name and remembers. Tests must not inherit
    another test's memo, or the "exactly one warning" assertion passes vacuously."""
    days._WARNED_ZONES.clear()
    yield
    days._WARNED_ZONES.clear()


def test_default_timezone_is_utc(monkeypatch):
    monkeypatch.delenv("STUDYFORGE_TIMEZONE", raising=False)
    tz = days.local_tz()
    assert tz.utcoffset(stored("2026-09-01T12:00")) == timedelta(0)
    assert days.day_bounds("2026-09-01") == (
        stored("2026-09-01T04:00"),
        stored("2026-09-02T04:00"),
    )


def test_timezone_is_read_at_call_time(monkeypatch):
    """Read per call, not captured at import, so a changed setting takes effect without
    a restart and a test does not have to reload the module."""
    monkeypatch.setenv("STUDYFORGE_TIMEZONE", NY)
    assert str(days.local_tz()) == NY
    monkeypatch.setenv("STUDYFORGE_TIMEZONE", "Asia/Tokyo")
    assert str(days.local_tz()) == "Asia/Tokyo"


def test_day_starts_at_four_am_local(new_york):
    moment = datetime(2026, 9, 2, 13, 0, tzinfo=new_york)
    start = days.day_start(moment)
    assert start == datetime(2026, 9, 2, 4, 0, tzinfo=new_york)
    assert days.DAY_START_HOUR == 4


def test_late_night_counts_toward_the_day_it_feels_like(new_york):
    """23:30 to 00:40 is one study session. A midnight boundary would split it, break
    the streak the learner just extended, and hand them tomorrow's queue mid-session."""
    evening = datetime(2026, 9, 1, 23, 30, tzinfo=new_york)
    after_midnight = datetime(2026, 9, 2, 0, 40, tzinfo=new_york)
    assert days.today_key(evening) == "2026-09-01"
    assert days.today_key(after_midnight) == "2026-09-01"
    assert days.day_start(evening) == days.day_start(after_midnight)


def test_three_fifty_nine_and_four_oh_one_are_different_days(new_york):
    before = datetime(2026, 9, 2, 3, 59, tzinfo=new_york)
    after = datetime(2026, 9, 2, 4, 1, tzinfo=new_york)
    assert days.today_key(before) == "2026-09-01"
    assert days.today_key(after) == "2026-09-02"
    assert days.day_start(before) != days.day_start(after)


def test_naive_timestamps_are_read_as_utc(new_york):
    """Every timestamp read back out of SQLite is naive UTC. Treating one as local
    time would shift it by the offset and land some sessions on the wrong day."""
    naive = stored("2026-09-02T03:00")  # 03:00 UTC == 23:00 previous day in New York
    assert days.today_key(naive) == days.today_key(naive.replace(tzinfo=UTC))
    assert days.today_key(naive) == "2026-09-01"


def test_day_bounds_are_naive_utc_and_half_open(new_york):
    start, end = days.day_bounds("2026-09-01")
    assert start.tzinfo is None and end.tzinfo is None
    assert start == stored("2026-09-01T08:00")
    assert end == stored("2026-09-02T08:00")
    # Half open: the next day's start is this day's end, with no gap and no overlap.
    assert days.day_bounds("2026-09-02")[0] == end


def test_day_bounds_defaults_to_today(new_york):
    now = datetime(2026, 9, 2, 13, 0, tzinfo=new_york)
    assert days.day_bounds(now=now) == days.day_bounds("2026-09-02")


def test_spring_forward_day_is_twenty_three_hours(new_york):
    """2026-03-08 02:00 EST becomes 03:00 EDT. The study day that contains the
    transition really is an hour shorter, and pretending otherwise would put the
    boundary an hour into the next day."""
    start, end = days.day_bounds("2026-03-07")
    assert start == stored("2026-03-07T09:00")
    assert end == stored("2026-03-08T08:00")
    assert end - start == timedelta(hours=23)


def test_fall_back_day_is_twenty_five_hours(new_york):
    """2026-11-01 02:00 EDT becomes 01:00 EST."""
    start, end = days.day_bounds("2026-10-31")
    assert start == stored("2026-10-31T08:00")
    assert end == stored("2026-11-01T09:00")
    assert end - start == timedelta(hours=25)


def test_days_around_a_transition_stay_contiguous(new_york):
    """Whatever the lengths, consecutive days must still tile the timeline exactly."""
    for first, second in (("2026-03-07", "2026-03-08"), ("2026-10-31", "2026-11-01")):
        assert days.day_bounds(first)[1] == days.day_bounds(second)[0]


def test_unknown_zone_falls_back_to_utc_with_one_warning(monkeypatch, caplog):
    monkeypatch.setenv("STUDYFORGE_TIMEZONE", "Not/AZone")
    with caplog.at_level(logging.WARNING, logger="studyforge.days"):
        assert days.local_tz() is UTC
        assert days.local_tz() is UTC
        assert days.local_tz() is UTC
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "Not/AZone" in warnings[0].getMessage()


def test_missing_tzdata_degrades_instead_of_crashing(monkeypatch, caplog):
    """On Windows there is no system timezone database, so a missing tzdata package
    makes every lookup raise. Days becoming UTC days is a wrong answer; the API
    failing to start over a timezone string is a worse one."""

    def no_tzdata(name):
        raise ZoneInfoNotFoundError(f"No time zone found with key {name}")

    monkeypatch.setenv("STUDYFORGE_TIMEZONE", NY)
    monkeypatch.setattr(days, "ZoneInfo", no_tzdata)
    with caplog.at_level(logging.WARNING, logger="studyforge.days"):
        assert days.local_tz() is UTC
        assert days.today_key(datetime(2026, 9, 2, 3, 0, tzinfo=UTC)) == "2026-09-01"
        assert days.day_bounds("2026-09-01") == (
            stored("2026-09-01T04:00"),
            stored("2026-09-02T04:00"),
        )
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_today_key_defaults_to_now(new_york):
    key = days.today_key()
    assert len(key) == 10
    assert key.count("-") == 2
    # Whatever "now" is, it must be inside the bounds of the day it names.
    start, end = days.day_bounds(key)
    now = datetime.now(UTC).replace(tzinfo=None)
    assert start <= now < end
