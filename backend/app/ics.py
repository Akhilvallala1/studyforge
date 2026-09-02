"""Writing a deadline out as an iCalendar file, safely.

THE THREAT, stated plainly, because it is the reason this module is not four lines of
f-string. A course title is LLM OUTPUT, generated from a document the learner uploaded,
and deadline_label is free text they typed. Both go into a SUMMARY property. iCalendar
is a line-oriented format: one property per line, CRLF-terminated. A raw newline in a
title does not produce an ugly title, it ENDS THE PROPERTY, and everything after it is
parsed as calendar content. A title of

    Algebra<CR><LF>BEGIN:VEVENT<CR><LF>SUMMARY:Injected<CR><LF>END:VEVENT

writes a second event into the learner's calendar. Escaping is the whole feature.

WHY THIS IS NOT IN untrusted.py, AND DOES NOT CALL as_data. untrusted.py neutralizes
forged prompt markers so that a language model reading the text cannot be talked out of
its instructions, and its docstring pins its output bytes as unchangeable because a
shipped prompt depends on them. This is a different job in all three ways that matter.
The output contract is escape-and-PRESERVE, not substitute-and-discard: a course
genuinely called "Sets, Maps, and Folds" must arrive in the calendar with its commas
intact, where as_data would be free to rewrite them. The consumer is a real parser
following RFC 5545, not a model reading prose. And the failure mode is a forged calendar
object rather than a forged instruction. untrusted.py is the sibling this module is
modelled on: ONE MODULE PER STRUCTURED FORMAT, each owning its own escaping, is the
shared discipline. A shared escape function would be the mistake.

NAMED ics.py deliberately. calendar.py would shadow the standard library module, and
icalendar.py would shadow the PyPI package that someone will eventually want to add.

NO DEPENDENCY. RFC 5545 for one all-day VEVENT is about sixty lines of string handling,
and the escaping is the part a library would be trusted for and the part that is easiest
to get right explicitly.
"""

import re
from datetime import UTC, date, datetime, timedelta

PRODID = "-//StudyForge//Study Planning//EN"
VERSION = "2.0"

# RFC 5545 section 3.1: "Lines of text SHOULD NOT be longer than 75 octets, excluding
# the line break." OCTETS, not characters, and that distinction is the subtlest thing in
# this file. Folding a UTF-8 string at 75 CHARACTERS produces lines that are legal but
# too long; folding the ENCODED bytes at 75 without care splits a multibyte sequence in
# half and produces two lines that are not valid UTF-8 at all, which is a corrupt file
# rather than a badly wrapped one.
MAX_LINE_OCTETS = 75

# Control characters that may not appear in an iCalendar value. TAB (0x09) is permitted
# and kept. LF (0x0A) and CR (0x0D) are absent from this class ON PURPOSE: they are
# normalized and then escaped to a literal backslash-n by escape_text, because a newline
# the learner typed is meaningful content, unlike a stray 0x07.
_FORBIDDEN_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def escape_text(value: str | None) -> str:
    r"""Escape one TEXT property value per RFC 5545 section 3.3.11.

    THE ORDER OF THE SUBSTITUTIONS IS LOAD-BEARING and there is only one correct one.

    1. Newlines are normalized first, CRLF and bare CR both to LF, so that the newline
       rule below has a single shape to match. Doing this after escaping would mean
       matching newlines inside text that already contains backslashes.
    2. Control characters are stripped next. Not escaped: they have no escape sequence
       in this format, so the only choices are dropping them or emitting an invalid
       file.
    3. BACKSLASH IS ESCAPED BEFORE EVERYTHING ELSE. This is the classic bug: escaping it
       last would find the backslashes that steps 4 and 5 just introduced and double
       them, turning every escaped comma into a literal backslash followed by a comma,
       which is the opposite of escaping.
    4. Semicolon and comma, which separate parameters and list values.
    5. LF last, to the two literal characters backslash and n. Its backslash must not be
       escaped by step 3, which is exactly why step 3 came first.
    """
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = _FORBIDDEN_CONTROLS.sub("", text)
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    return text.replace("\n", "\\n")


def fold(line: str) -> list[str]:
    """Split one logical line into physical lines of at most 75 OCTETS.

    Continuation lines begin with a single space, which the parser strips when
    unfolding. That leading space is itself an octet, so continuations get 74 octets of
    payload rather than 75; getting this wrong produces 76-octet lines that most parsers
    accept and one will not.

    The multibyte guard is the point of the function. UTF-8 continuation bytes match
    0b10xxxxxx, so if the cut lands on one, the cut is in the middle of a character and
    is walked backwards until it is not. Without it, a title of accented or CJK text
    folds into two undecodable fragments: the file is not merely wrapped oddly, it is
    not valid UTF-8, and the calendar refuses the whole import. A character is at most
    four octets and the smallest limit here is 74, so the walk always terminates with
    room to spare.
    """
    raw = line.encode("utf-8")
    if len(raw) <= MAX_LINE_OCTETS:
        return [line]

    pieces: list[bytes] = []
    start = 0
    limit = MAX_LINE_OCTETS
    while start < len(raw):
        end = min(start + limit, len(raw))
        if end < len(raw):
            while end > start and (raw[end] & 0xC0) == 0x80:
                end -= 1
        pieces.append(raw[start:end])
        start = end
        limit = MAX_LINE_OCTETS - 1
    return [pieces[0].decode("utf-8")] + [" " + piece.decode("utf-8") for piece in pieces[1:]]


def _property(name: str, value: str) -> list[str]:
    """One property as its folded physical lines. The value must already be escaped."""
    return fold(f"{name}:{value}")


def _as_date_value(day: date) -> str:
    """YYYYMMDD, the DATE value form used by an all-day event."""
    return day.strftime("%Y%m%d")


def _as_utc_stamp(moment: datetime) -> str:
    """YYYYMMDDTHHMMSSZ. DTSTAMP is always UTC, which is what the trailing Z asserts."""
    if moment.tzinfo is not None:
        moment = moment.astimezone(UTC).replace(tzinfo=None)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def event_uid(course_id: int) -> str:
    """A UID that is the same on every download of the same course's deadline.

    Stability is the whole requirement. A calendar treats UID as the identity of the
    event, so re-importing after changing a deadline UPDATES the existing entry. A
    random UID per download would leave the learner with one stale event per time they
    pressed the button, all claiming to be their exam, on different days.
    """
    return f"studyforge-course-{course_id}-deadline@studyforge.local"


def download_filename(course_id: int) -> str:
    """The Content-Disposition filename. Hardcoded shape, and that is a security choice.

    THIS IS THE SECOND INJECTION SURFACE AND THE ONE THAT GETS MISSED. Everyone
    remembers to escape the title into the body; deriving a friendly filename from the
    same title puts LLM output into an HTTP RESPONSE HEADER, where a CRLF is header
    injection rather than a broken calendar. The fix is not to sanitize a derived
    filename, because that is a second escaping problem with a different grammar that
    has to stay correct forever. It is to have nothing to sanitize: the only variable
    here is an integer primary key.

    THE FRONTEND MIRRORS THIS SHAPE, at coursePlanIcsFilename in
    frontend/src/lib/api.ts, so the plan page can tell the learner what the download
    will be called before they click it. It cannot read the name back off the response:
    the link is a plain anchor, so the browser consumes the Content-Disposition and the
    page never sees it. RENAMING HERE MEANS RENAMING THERE. This side is pinned by
    test_the_download_filename_is_built_from_the_id_and_never_the_title and by the
    header assertion in the endpoint test, so a change here cannot pass unnoticed;
    nothing pins the copy, which would simply go on naming the old file.
    """
    return f"studyforge-course-{course_id}.ics"


def _description(plan: dict) -> str:
    """What the learner reads inside the event: where they stand and what pace it takes.

    Written from the same numbers the plan endpoint returns, so the calendar and the
    screen can never quote different figures. The null-required_per_week states get
    their own sentences rather than a blank line, because "no study days left" is
    information and an empty description is not.
    """
    remaining = plan["lessons_remaining"]
    total = plan["lessons_total"]
    open_days = plan["available_days"]
    required = plan["required_per_week"]

    head = f"{remaining} of {total} lessons still to do."
    if required is not None:
        return (
            f"{head} {open_days} study days left, so about {required:.1f} lessons per "
            f"week to be ready in time. Tracked in StudyForge."
        )
    if plan["status"] == "passed":
        return f"{head} This deadline has passed. Tracked in StudyForge."
    if plan["days_off_in_window"]:
        return (
            f"{head} Every remaining day is marked as a day off, so there is no study "
            f"time left before this. Tracked in StudyForge."
        )
    return f"{head} This is today, so no study days are left before it. Tracked in StudyForge."


def deadline_calendar(plan: dict, now: datetime | None = None) -> str:
    """A one-event VCALENDAR for a course's deadline, CRLF-terminated.

    ONE ALL-DAY EVENT, NOT A DAILY STUDY SCHEDULE. Thirty "Study Linear Algebra" entries
    is a calendar the learner deletes within a day, and it would also be a lie about
    what this feature knows: nothing here assigns a lesson to a particular date, it
    computes a rate. The required pace goes in the DESCRIPTION of the one event that
    corresponds to a real appointment they actually have.

    DTEND IS THE DAY AFTER THE DEADLINE because DTEND is EXCLUSIVE for a DATE value.
    Setting it equal to DTSTART produces a zero-length event that some clients hide and
    others show on the wrong day, and the off-by-one shows up as the exam landing a day
    early, which is the single most damaging bug this file could ship.

    Every line ends CRLF regardless of the platform this runs on, so the bytes are the
    same from a Windows dev box and a Linux container.
    """
    deadline = date.fromisoformat(plan["deadline"])
    stamp = _as_utc_stamp(datetime.now(UTC) if now is None else now)

    label = (plan.get("deadline_label") or "").strip()
    title = plan.get("title") or ""
    summary = f"{label}: {title}" if label else f"{title} deadline"

    lines = [
        "BEGIN:VCALENDAR",
        f"VERSION:{VERSION}",
        *_property("PRODID", escape_text(PRODID)),
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        *_property("UID", event_uid(plan["course_id"])),
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{_as_date_value(deadline)}",
        f"DTEND;VALUE=DATE:{_as_date_value(deadline + timedelta(days=1))}",
        *_property("SUMMARY", escape_text(summary)),
        *_property("DESCRIPTION", escape_text(_description(plan))),
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"
