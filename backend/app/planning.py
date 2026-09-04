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
it is unnecessary. fsrs.interval_days returns the number of days until recall
probability decays to DESIRED_RETENTION, which is 0.90, and a card's due date is set to
now + that interval. So retrievability at a card's own due date is about 0.90 BY
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

from sqlalchemy import func
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
# review.RETENTION_MIN_SAMPLE, for exactly the same reason.
#
# The sample counted against this is every course's completions, not one course's.
# Scoped to a single course the threshold was not merely slow to reach, it was
# UNREACHABLE for any course shorter than five lessons, which turned a sound
# anti-noise rule into a permanent dash. See observed_pace.
PACE_MIN_LESSONS = 5

# status values. "passed" is a state the learner reaches by doing nothing at all: a
# deadline that was valid when they set it becomes today, and then yesterday, with
# nobody touching anything.
NO_DEADLINE = "none"
ACTIVE = "active"
PASSED = "passed"

# Why required_per_week is null, when it is. Null with no reason would make the UI
# guess, and each case wants a different sentence: a passed deadline wants "your deadline
# was the 14th", an all-days-off window wants "you have marked every remaining day off".
# Said as "each" rather than as a count, so that adding a fifth does not quietly make this
# sentence wrong.
REASON_NO_DEADLINE = "no_deadline"
REASON_DEADLINE_PASSED = "deadline_passed"
REASON_DEADLINE_TODAY = "deadline_today"
REASON_ALL_DAYS_OFF = "all_days_off"

# Why finish_projection is null, when it is. A SEPARATE field from `reason` above and
# deliberately so: `reason` explains a missing required_per_week, these explain a
# missing date, and a course can be in both states at once (every remaining day marked
# off AND nothing finished here yet). One field would have to throw one answer away.
REASON_NO_PACE_YET = "no_pace_yet"
REASON_NO_PROGRESS_HERE = "no_progress_in_this_course"
REASON_ALREADY_FINISHED = "already_finished"


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


def available_days(session: Session, deadline: date, now: datetime | None = None) -> dict:
    """Study days left before the deadline, and how many of them were marked off.

    BOTH, from one pass and one query, because they are one question asked once: the
    caller needs the denominator and it needs to tell the learner why the denominator
    shrank. Returned as a dict for the reason review.retention returns one, so course_plan
    can splat it into the payload under exactly the names the API promises rather than
    unpacking a tuple and re-labelling it.

    This function previously returned only the count and course_plan re-implemented the
    whole computation inline to get the second number. Two copies of the same window
    arithmetic, one of them public and untested, is how the two answers eventually
    disagree about the same week.

    A day off shrinks the denominator, which pushes required_per_week UP. It moves
    nothing: no lesson is assigned to a particular day here, and no review card is ever
    touched by this number.
    """
    off = days_off(session)
    window = study_days(deadline, now)
    marked_off = sum(1 for day in window if day.isoformat() in off)
    return {
        "available_days": len(window) - marked_off,
        "days_off_in_window": marked_off,
    }


def _completions_since(
    session: Session, cutoff: datetime, course: models.Course | None = None
) -> int:
    """Lessons completed at or after `cutoff`, everywhere or within one course.

    One query shape for both scopes, so the two rates below can never drift apart on what
    "completed inside the window" means and disagree for a reason nobody can see.
    """
    query = (
        session.query(func.count(models.Lesson.id))
        .filter(models.Lesson.completed_at.isnot(None))
        .filter(models.Lesson.completed_at >= cutoff)
    )
    if course is not None:
        query = query.join(models.Module).filter(models.Module.course_id == course.id)
    return query.scalar() or 0


def observed_pace(
    session: Session, course: models.Course, now: datetime | None = None
) -> dict:
    """Two rates: how fast the learner finishes lessons anywhere, and how fast in here.

    TWO NUMBERS, NOT ONE, AND THE NAMES CARRY THE DIFFERENCE, because rendering the wrong
    one is the whole hazard. observed_per_week_all_courses is what the page DISPLAYS and
    counts every course. observed_per_week_this_course is what the finish date is BUILT
    FROM and counts only this one. Neither is allowed to be the bare "observed_per_week"
    that used to sit here, because that name meant different things in different weeks and
    said nothing about its own scope.

    WHY THE DISPLAYED RATE COUNTS EVERY COURSE. PACE_MIN_LESSONS is 5, and scoped to one
    course that threshold was not slow to reach, it was UNREACHABLE for any course with
    fewer than five lessons: a permanent dash however much work the learner did. Counting
    everywhere keeps the anti-noise minimum and makes it reachable.

    WHY THE PROJECTION RATE COUNTS ONLY THIS COURSE. The projection divides THIS course's
    remaining lessons, so dividing them by the learner's whole throughput answers a
    question nobody asked: the date they would finish if they abandoned everything else.
    That is wrong by roughly the number of courses they have in flight, and always in the
    optimistic direction, which is the dangerous direction for a deadline feature.
    Projecting from this course's SHARE of the throughput is what makes the date honest,
    and that share reduces algebraically to this course's own completion rate, which is
    what is measured here.

    BOTH RATES ARE GATED ON THE SAME CROSS-COURSE SAMPLE, deliberately. The minimum exists
    to stop a rate lurching on one more completion, and making a second, smaller
    per-course sample clear it separately would put the unreachable threshold straight back
    for exactly the short courses this was changed for.

    A LESSON COUNTS AT MOST ONCE, whatever the learner does to it. completed_at is a
    single nullable column, not an event log: un-completing sets it back to NULL (see
    uncomplete_lesson in main.py) and re-completing overwrites it. So there is no double
    counting to defend against across courses, and a re-completed lesson simply re-enters
    the window at its new timestamp.

    Lessons of a DELETED course stop counting, because Course cascades to modules and
    lessons, so the history goes with it and this rate drops retroactively. That is LIVE
    behaviour, not a hypothetical: DELETE /courses/{course_id} exists.

    Note how far the effect reaches, because it is wider than it first looks. This rate
    counts completions across every course, so deleting one lowers the figure displayed on
    all the OTHERS, and if the remaining total falls under PACE_MIN_LESSONS they lose their
    rate and their projected date entirely. Nothing is wrong when that happens: the rate is
    a measurement over surviving history, and the history really did get smaller. Keeping
    it stable across deletions would mean an append-only completion log, which is a larger
    thing than this one number is worth.

    THE WINDOW IS UNCHANGED: a fixed 720 HOURS, and still the one piece of day arithmetic
    in this module NOT built out of days.py. It copies review.retention exactly, one
    cutoff at moment - 30 days and a single >= comparison. Because it never decomposes
    the span into local days there is no DST transition for it to get wrong, and a rate
    over a month does not care whether that month contained an hour more or less.

    Counted in SQL rather than in Python, which is the other half of the widening. The
    caller only ever holds one course's lessons, and loading every lesson of every course
    into memory to count a scalar would be a real cost on a large library.
    """
    moment = _naive_utc(models.utcnow() if now is None else now)
    cutoff = moment - timedelta(days=PACE_WINDOW_DAYS)
    everywhere = _completions_since(session, cutoff)
    if everywhere < PACE_MIN_LESSONS:
        return {
            "observed_per_week_all_courses": None,
            "observed_sample_all_courses": everywhere,
            "observed_per_week_this_course": None,
        }
    here = _completions_since(session, cutoff, course)
    return {
        "observed_per_week_all_courses": everywhere / PACE_WINDOW_DAYS * 7,
        "observed_sample_all_courses": everywhere,
        "observed_per_week_this_course": here / PACE_WINDOW_DAYS * 7,
    }


def _projection(
    lessons_remaining: int,
    per_week_all_courses: float | None,
    per_week_this_course: float | None,
    now: datetime | None = None,
) -> tuple[str | None, str | None]:
    """(date, reason). Exactly one of them is ever set, which is the point.

    A bare null date makes the UI guess, and the three ways of not having one want
    different sentences. Ordered so each branch is a genuinely different state rather than
    a fallback for the one above it.

    lessons_remaining == 0 is checked FIRST and returns no date at all. It used to return
    TODAY with a null reason, and that was a trap of exactly the kind this module spent a
    commit removing elsewhere: "finishes today" is a true-looking sentence to print about
    a course finished last year, and nothing in the payload said otherwise, so
    finish_projection could not be read without also reading lessons_remaining. A field
    that needs a second field to interpret, with no hint that it does, is a wrong answer
    nobody goes looking for. A projection is a claim about remaining work; when there is
    none, the honest answer is that there is nothing to project, and the reason carries
    the meaning.

    It stays FIRST because the two checks below would each give a true but useless answer
    about a finished course: a course completed long ago has no completions inside the
    window, so the zero-share branch would report "nothing finished here yet" about a
    course that is entirely finished.
    """
    if lessons_remaining == 0:
        return None, REASON_ALREADY_FINISHED
    if per_week_all_courses is None:
        return None, REASON_NO_PACE_YET
    if not per_week_this_course:
        # THE STATE THE WIDENING CREATED, and it is not a bug to paper over. The learner
        # has cleared the minimum across their other courses but finished nothing here, so
        # there is no evidence of pace INTO this course and no honest date to give. It
        # reaches the screen as a reason a learner can act on ("you have been studying,
        # just not this") rather than as a blank or a division by zero.
        return None, REASON_NO_PROGRESS_HERE
    return finish_projection(lessons_remaining, per_week_this_course, now), None


def finish_projection(
    lessons_remaining: int,
    per_week_this_course: float | None,
    now: datetime | None = None,
) -> str | None:
    """The day the learner finishes THIS course at the pace they are putting into it.

    None unless the rate is both known and above zero, because the alternative is a
    projection of infinity dressed up as a date. Callers that need to TELL the learner why
    there is no date go through _projection, which turns each of those cases into a reason
    code instead of a bare null.

    THE RATE PASSED IN MUST BE THIS COURSE'S, not the cross-course figure the page
    displays, and the parameter is named so that passing the wrong one looks wrong at the
    call site. lessons_remaining counts one course, so dividing it by the learner's whole
    throughput answers "when would I finish if I abandoned my other courses", which is
    optimistic by roughly the number of courses they have open and never pessimistic. See
    observed_pace.

    Days off are NOT subtracted again here, and the argument survives the rate becoming
    per-course. per_week_this_course is a MEASUREMENT over a fixed thirty-day window, so
    the days the learner took off inside that window are already in its denominator: they
    are days on which no lesson was finished, and the window counts them either way.
    Subtracting marked days from a rate that already reflects them would penalise the same
    absence twice. That reasoning turns only on the rate being measured over a fixed
    calendar span, not on WHICH lessons it counts, which is why narrowing the scope to one
    course left it intact.

    WHAT IT DOES NOT CLAIM: days marked off in the FUTURE are not subtracted either, and
    that is a different question. required_per_week does subtract them, because it is
    prescriptive and divides by the calendar that actually remains. This is descriptive
    and carries the learner's past mix of working and idle days forward, so subtracting
    marked future days would double count the ordinary ones to count the exceptional ones
    correctly. Neither treatment is error free; this one is at least consistent with how
    the rate was measured.

    """
    if per_week_this_course is None or per_week_this_course <= 0:
        return None
    days_needed = math.ceil(lessons_remaining * 7 / per_week_this_course)
    return (today(now) + timedelta(days=days_needed)).isoformat()


def course_plan(session: Session, course: models.Course, now: datetime | None = None) -> dict:
    """Everything the plan screen needs, and deliberately nothing else.

    NOTE WHAT THIS FUNCTION NEVER TOUCHES: no concept, no card, no mastery bucket, no
    retrievability. Its inputs are this course's lessons, the deadline, the days off, and
    a count of lesson completions across every course for the observed pace. The feature's
    boundary is unchanged and still visible in the call graph: no concept data anywhere on
    this path.

    TWO RATES REACH THE PAYLOAD AND THEY ARE NOT INTERCHANGEABLE.
    observed_per_week_all_courses is the displayed figure and counts every course.
    observed_per_week_this_course counts only this one and is what finish_projection is
    built from. So the learner sees a date that does NOT equal lessons_remaining divided
    by the displayed rate, and that is correct rather than a rounding bug: the two numbers
    answer different questions, and the copy has to say which one the date came from. For
    a single course the two rates are equal and the distinction costs nothing.

    A course with no deadline still gets a full answer rather than an error. The
    observed pace is real and worth showing either way, and the endpoint returning 200
    here is what stops the frontend having to branch on a 404 to draw a normal screen.
    """
    lessons = course_lessons(session, course)
    lessons_total = len(lessons)
    lessons_remaining = sum(1 for lesson in lessons if lesson.completed_at is None)
    pace = observed_pace(session, course, now)
    projection, projection_reason = _projection(
        lessons_remaining,
        pace["observed_per_week_all_courses"],
        pace["observed_per_week_this_course"],
        now,
    )

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
        "finish_projection": projection,
        "projection_reason": projection_reason,
    }

    deadline = parse_deadline(course.deadline)
    if deadline is None:
        return payload

    start = today(now)
    payload["days_until"] = (deadline - start).days
    payload["status"] = PASSED if deadline < start else ACTIVE
    payload.update(available_days(session, deadline, now))
    open_days = payload["available_days"]

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
