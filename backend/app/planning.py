"""How fast new material has to go in to beat a deadline.

WHAT THIS MODULE OWNS, and the sentence that draws the line: STUDY PLANNING OWNS THE
RATE NEW MATERIAL ENTERS. FSRS KEEPS OWNING EVERYTHING ALREADY IN. Reviews are
scheduled by memory decay, lessons by the calendar, and the two never negotiate.

The gap this fills. A ReviewCard only comes into existence through record_review, which
for a new concept is only reached by grade_lesson when a lesson is completed. FSRS
therefore has no opinion whatsoever about material the learner has not met yet, and a
learner with an exam on Friday and five unfinished lessons is told "Nothing is due for
review". That is true about their memory and dangerous about their exam. Everything here
is about the five lessons; nothing here is about the cards.

WHY NOTHING HERE READS A CARD, STATED AS A PROOF RATHER THAN A PREFERENCE.

The tempting next feature is "pull reviews forward so nothing is shaky on exam day", and
it is unnecessary. fsrs.interval_days (fsrs.py:91-94) returns the number of days until
recall probability decays to DESIRED_RETENTION, which is 0.90, and a card's due date is
set to now + that interval. So retrievability at a card's own due date is about 0.90 BY
CONSTRUCTION, and strictly higher at every moment before it. Take any card whose due
date falls after the deadline: on the deadline day it has not yet reached its due date,
so its predicted recall is at least ~0.90. It is not at risk. The set of cards that
would need pulling forward for the deadline is EMPTY, not small.

That is why this module must not reorder, filter, or cap due_cards, pick_items or the
review queue by deadline, must not add a cram or practice-everything action, and must
not tell the learner a concept is at risk because its card is due after the exam. There
is no version of that claim this data supports. If you opened this file to add
deadline-aware review ordering, this paragraph is the answer.

DAY ARITHMETIC, which is where the bugs in this feature live.

Today's local date comes from days.today_key, which is day_start().date() and therefore
already carries the 04:00 study-day boundary: a learner still working at 02:00 is on
yesterday's study day, and their deadline is one day further away than the wall clock
says. Everything after that is pure datetime.date arithmetic with timedelta(days=1),
which is immune to DST because a date has no hours to lose.

Two things this deliberately does not use. days.day_bounds returns INSTANTS, and
counting calendar days by subtracting instants is wrong across a DST transition, where a
local day is 23 or 25 hours long. And date.today() is the SERVER's OS-local date, which
is wrong whenever STUDYFORGE_TIMEZONE differs from the host, and wrong for every learner
between midnight and 04:00 even when it does not.
"""

import math
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app import days, models

# The single source of course ordering, and the only thing this module takes from
# review.py. Planning composes with the scheduler; it does not reach into it.
from app.review import course_lessons

# How far back the observed pace is measured.
PACE_WINDOW_DAYS = 30
# Below this many completed lessons, a lessons-per-week figure is noise wearing a
# number's clothes: two lessons finished on the same evening reads as 0.47/week and
# would swing by a third every time one more landed. Callers get None and the sample
# size, and the UI shows a dash. Exactly the discipline review.retention applies with
# RETENTION_MIN_SAMPLE (review.py:578-601), for exactly the same reason.
PACE_MIN_LESSONS = 5

# status values. "passed" is a state the learner reaches by doing nothing at all: a
# deadline that was valid when they set it becomes today, and then yesterday, with
# nobody touching anything.
NO_DEADLINE = "none"
ACTIVE = "active"
PASSED = "passed"

# Why required_per_week is null, when it is. Null with no reason would make the UI
# guess, and the three cases want different sentences: a passed deadline wants
# "your deadline was the 14th", an all-days-off window wants "you have marked every
# remaining day off".
REASON_NO_DEADLINE = "no_deadline"
REASON_DEADLINE_PASSED = "deadline_passed"
REASON_DEADLINE_TODAY = "deadline_today"
REASON_ALL_DAYS_OFF = "all_days_off"


def _naive_utc(moment: datetime) -> datetime:
    """Coerce a datetime to the naive-UTC shape every stored timestamp has.

    SQLite drops tzinfo on write, so a stored completed_at read back is naive, while
    models.utcnow() is aware. Comparing the two raises TypeError. review.py contains the
    same three lines and the duplication is deliberate: importing a private helper from
    it would couple this module to the scheduler, which is the one thing the boundary
    above is for.
    """
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(UTC).replace(tzinfo=None)


def today(now: datetime | None = None) -> date:
    """The learner's local study day as a date, 04:00 boundary included."""
    return date.fromisoformat(days.today_key(now))


def parse_deadline(value: str | None) -> date | None:
    """A stored YYYY-MM-DD as a date, or None if it is absent or unreadable.

    Unreadable rather than raising, because the column is free text as far as SQLite is
    concerned: a row hand-edited into an invalid date must degrade to "this course has
    no usable deadline" rather than taking down the course's plan endpoint.
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def days_off(session: Session) -> set[str]:
    """Every day the learner has marked off, as YYYY-MM-DD keys.

    Global, not per course: the table has no course_id, and that is deliberate. See
    models.UnavailableDay.
    """
    return {day for (day,) in session.query(models.UnavailableDay.day).all()}


def study_days(deadline: date, now: datetime | None = None) -> list[date]:
    """Local days from today INCLUSIVE to the deadline EXCLUSIVE.

    The deadline day itself is not a study day. The deadline is the moment the material
    has to already be known: counting exam day as time to learn in would hand the
    learner one more day than they have, on the one day the error cannot be recovered
    from. A deadline of today therefore yields an empty list, which is a real state and
    not an error; see course_plan.

    Pure date arithmetic, so a DST transition inside the window cannot add or drop a day.
    """
    start = today(now)
    if deadline <= start:
        return []
    return [start + timedelta(days=offset) for offset in range((deadline - start).days)]


def available_days(session: Session, deadline: date, now: datetime | None = None) -> int:
    """Study days left before the deadline, with the learner's days off removed.

    A day off shrinks the denominator, which pushes required_per_week UP. It moves
    nothing: no lesson is assigned to a particular day here, and no review card is ever
    touched by this number.
    """
    off = days_off(session)
    return sum(1 for day in study_days(deadline, now) if day.isoformat() not in off)


def observed_pace(
    session: Session,
    lessons: list[models.Lesson],
    now: datetime | None = None,
) -> dict:
    """Lessons per week the learner has actually been completing, over 30 days.

    Scoped to THIS COURSE's lessons, which the spec left open and which matters. The
    figure sits next to required_per_week and the learner reads them as a pair: "you
    need 4 a week, you have been doing 2.3". A rate measured across every course they
    have ever opened is not comparable to a requirement measured on one, and the
    comparison is the entire point of showing it.

    THE WINDOW IS A FIXED 720 HOURS, not thirty local days, and this is the one piece of
    day arithmetic in this module that is NOT built out of days.py. It copies
    review.retention (review.py:587-596) exactly: one cutoff at moment - 30 days and a
    single >= comparison. Because it never decomposes the span into local days, there is
    no DST transition for it to get wrong, and a rate over a month does not care whether
    that month contained an hour more or less. Rebuilding it on day_bounds would add a
    per-day loop, 30 boundary computations, and a class of bug, to move a denominator by
    one part in 720.
    """
    moment = _naive_utc(models.utcnow() if now is None else now)
    cutoff = moment - timedelta(days=PACE_WINDOW_DAYS)
    completed = [
        lesson
        for lesson in lessons
        if lesson.completed_at is not None and _naive_utc(lesson.completed_at) >= cutoff
    ]
    sample = len(completed)
    if sample < PACE_MIN_LESSONS:
        return {"observed_per_week": None, "observed_sample": sample}
    return {"observed_per_week": sample / PACE_WINDOW_DAYS * 7, "observed_sample": sample}


def finish_projection(
    lessons_remaining: int,
    observed_per_week: float | None,
    now: datetime | None = None,
) -> str | None:
    """The day the learner finishes the course at the pace they are actually going.

    None unless the observed rate is both known and above zero, because the alternative
    is a projection of infinity dressed up as a date.

    Days off are NOT subtracted again here. observed_per_week is a measurement, and the
    thirty days it was measured over already contain whatever days the learner took off
    during them. Removing marked days from a rate that already reflects them would
    penalise the same absence twice.
    """
    if observed_per_week is None or observed_per_week <= 0:
        return None
    days_needed = math.ceil(lessons_remaining * 7 / observed_per_week)
    return (today(now) + timedelta(days=days_needed)).isoformat()


def course_plan(session: Session, course: models.Course, now: datetime | None = None) -> dict:
    """Everything the plan screen needs, and deliberately nothing else.

    NOTE WHAT THIS FUNCTION NEVER TOUCHES: no concept, no card, no mastery bucket, no
    retrievability. Its whole input is the course's lessons, their completed_at, the
    deadline and the days off. The feature's boundary is not just documented at the top
    of this file, it is visible in the call graph.

    A course with no deadline still gets a full answer rather than an error. The
    observed pace is real and worth showing either way, and the endpoint returning 200
    here is what stops the frontend having to branch on a 404 to draw a normal screen.
    """
    lessons = course_lessons(session, course)
    lessons_total = len(lessons)
    lessons_remaining = sum(1 for lesson in lessons if lesson.completed_at is None)
    pace = observed_pace(session, lessons, now)

    payload = {
        "course_id": course.id,
        "title": course.title,
        "deadline": course.deadline,
        "deadline_label": course.deadline_label,
        "lessons_total": lessons_total,
        "lessons_remaining": lessons_remaining,
        "required_per_week": None,
        "reason": REASON_NO_DEADLINE,
        "days_until": None,
        "available_days": None,
        "days_off_in_window": None,
        "status": NO_DEADLINE,
        **pace,
        "finish_projection": finish_projection(
            lessons_remaining, pace["observed_per_week"], now
        ),
    }

    deadline = parse_deadline(course.deadline)
    if deadline is None:
        return payload

    start = today(now)
    window = study_days(deadline, now)
    off = days_off(session)
    marked_off = sum(1 for day in window if day.isoformat() in off)
    open_days = len(window) - marked_off

    payload["days_until"] = (deadline - start).days
    payload["available_days"] = open_days
    payload["days_off_in_window"] = marked_off
    payload["status"] = PASSED if deadline < start else ACTIVE

    # AVAILABLE_DAYS == 0 IS A DEFINED STATE, NOT AN ERROR, and it is the likeliest 500
    # in this feature: required = remaining / available * 7 divides by zero. It is
    # reachable three ways and only one of them involves anyone doing anything. The
    # deadline can BE today; it can have PASSED since it was set, with no request in
    # between; or every remaining day can be marked off. A deadline the learner set
    # perfectly well last month turns into this on its own, so the read path has to
    # answer it calmly. Rejecting a past deadline on write (which PUT does) does not
    # help at all, because nothing was written.
    if open_days > 0:
        payload["required_per_week"] = lessons_remaining / open_days * 7
        payload["reason"] = None
    elif deadline < start:
        payload["reason"] = REASON_DEADLINE_PASSED
    elif deadline == start:
        payload["reason"] = REASON_DEADLINE_TODAY
    else:
        payload["reason"] = REASON_ALL_DAYS_OFF

    return payload
