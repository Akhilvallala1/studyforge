"""Local study days, which do not start at midnight.

A day here runs 04:00 local to 04:00 local. Someone who sits down at 23:30 and
finishes at 00:40 did one study session, and a midnight boundary would split it
across two days, break the streak they just extended, and schedule tomorrow's
reviews while they are still doing today's. 04:00 is late enough to cover any
plausible late night and early enough that nobody is starting the next day before it.

The timezone comes from STUDYFORGE_TIMEZONE (an IANA name, default "UTC") and is read
on every call, not captured at import, matching metering.py. That keeps the setting
changeable in a test or a restart without a stale module-level snapshot.
"""

import logging
import os
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models import utcnow

logger = logging.getLogger("studyforge.days")

DEFAULT_TIMEZONE = "UTC"
DAY_START_HOUR = 4

# Zones already reported as unloadable. Without this the warning repeats on every
# single call, and a per-request log line about a config problem is noise that hides
# the one line that mattered.
_WARNED_ZONES: set[str] = set()


def local_tz() -> tzinfo:
    """The configured study timezone, falling back to UTC if it cannot be loaded.

    An unknown name or a missing tzdata package degrades to "days are UTC days" with
    one warning. It must never raise: the dev machine is Windows, where zoneinfo has
    no system database at all, and a scheduling helper is not allowed to take the
    whole API down over a timezone string.
    """
    name = os.environ.get("STUDYFORGE_TIMEZONE", DEFAULT_TIMEZONE)
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        if name not in _WARNED_ZONES:
            _WARNED_ZONES.add(name)
            logger.warning(
                "Timezone %r could not be loaded (is the 'tzdata' package installed?). "
                "Falling back to UTC; study days will start at 04:00 UTC.",
                name,
            )
        return UTC


def _as_local(moment: datetime | None) -> datetime:
    """Coerce a moment to an aware local datetime.

    A naive datetime is read as UTC, because that is what this codebase stores: SQLite
    drops tzinfo on write, so every timestamp read back out of the database is naive
    UTC and would otherwise be reinterpreted as local time and shifted.
    """
    moment = utcnow() if moment is None else moment
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(local_tz())


def day_start(moment: datetime | None = None) -> datetime:
    """The 04:00 local boundary that opened the study day containing `moment`.

    Returned aware in local time, because a day boundary is a wall-clock fact. Use
    day_bounds() when you need instants to compare against stored timestamps.
    """
    local = _as_local(moment)
    day = local.date()
    if local.hour < DAY_START_HOUR:
        day -= timedelta(days=1)
    return datetime.combine(day, time(hour=DAY_START_HOUR), tzinfo=local.tzinfo)


def today_key(now: datetime | None = None) -> str:
    """The local YYYY-MM-DD key of the study day containing `now`.

    This is the string form UnavailableDay stores. A calendar day marked off is a
    calendar day, not an instant, so it is keyed by the date the learner would name.
    """
    return day_start(now).date().isoformat()


def day_bounds(
    day: str | date | None = None, now: datetime | None = None
) -> tuple[datetime, datetime]:
    """Half-open [start, end) instants for one local study day, as naive UTC.

    Naive UTC because that is the shape of every stored timestamp: comparing an aware
    datetime against a naive SQLite column silently compares mismatched text. These
    values are meant to go straight into a query filter.

    The span is not always 24 hours. Across a DST transition the local day is 23 or 25
    hours long, which is correct: the learner's day really was shorter or longer.
    """
    tz = local_tz()
    if day is None:
        day_date = day_start(now).date()
    elif isinstance(day, str):
        day_date = date.fromisoformat(day)
    else:
        day_date = day

    start_local = datetime.combine(day_date, time(hour=DAY_START_HOUR), tzinfo=tz)
    end_local = datetime.combine(day_date + timedelta(days=1), time(hour=DAY_START_HOUR), tzinfo=tz)
    return (
        start_local.astimezone(UTC).replace(tzinfo=None),
        end_local.astimezone(UTC).replace(tzinfo=None),
    )
