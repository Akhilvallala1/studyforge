"""Study planning: the intake rate, the day arithmetic, and the calendar export.

Three things are worth knowing before changing anything here.

THE DAY ARITHMETIC IS THE FEATURE. Almost every assertion below passes an explicit
`now` rather than letting the clock supply one, because the bugs this feature can have
are all bugs about which day it is: the 04:00 study-day boundary, a DST transition
inside the window, and the server's OS timezone leaking in through date.today().

AVAILABLE_DAYS == 0 IS A STATE, NOT AN ERROR. Three separate paths reach it and all
three divide by zero if nobody thought about them, so each has its own test, plus one
for the transition, because a deadline becomes today and then past with no request in
between and the read path has to survive that on its own.

THE .ics ESCAPING IS A SECURITY BOUNDARY. A course title is LLM output going into a
line-oriented format. The per-character table below is necessary and NOT sufficient: it
can be satisfied by an implementation that still lets a title forge a calendar object,
which is why test_a_hostile_title_cannot_forge_a_calendar_object counts structural
lines instead of inspecting characters.
"""

from datetime import UTC, date, datetime, timedelta
from itertools import pairwise

import pytest

from app import ics, models, planning
from app.db import SessionLocal
from tests.conftest import clear_days_off

# A fixed instant, so nothing here depends on the day the suite happens to run.
NOON = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def _completed(days_ago: float) -> datetime:
    """A completed_at that many days before NOON, NAIVE UTC as SQLite stores it.

    Naive on purpose: every timestamp read back out of the database has lost its tzinfo,
    so a fixture that wrote an aware one would be testing a shape production never sees.
    """
    return (NOON - timedelta(days=days_ago)).replace(tzinfo=None)


@pytest.fixture(autouse=True)
def _clean_days_off(monkeypatch):
    """Every test in this file reads a study-day count, so every one needs a clean table.

    Autouse for exactly that reason; see conftest.clear_days_off for why a stray row in a
    global table is an order-dependent failure that surfaces long after it is introduced.

    The timezone is pinned too. days.local_tz reads STUDYFORGE_TIMEZONE on every call, so
    a test elsewhere that sets it, or a developer with it set in their shell, would move
    every boundary asserted below.
    """
    monkeypatch.setenv("STUDYFORGE_TIMEZONE", "UTC")
    clear_days_off()
    yield
    clear_days_off()


def _make_course(lesson_count=6, completed=(), title="Linear Algebra"):
    """A one-module course. `completed` is (lesson_index, completed_at) pairs.

    completed_at is written naive, which is what SQLite stores and what every read path
    gets back.
    """
    session = SessionLocal()
    try:
        course = models.Course(title=title, description="")
        module = models.Module(title="Module 1", position=0)
        for index in range(lesson_count):
            module.lessons.append(
                models.Lesson(
                    title=f"Lesson {index}", position=index, content="# L", concepts=[]
                )
            )
        course.modules.append(module)
        session.add(course)
        session.commit()

        for index, moment in completed:
            module.lessons[index].completed_at = moment
        session.commit()
        return course.id
    finally:
        session.close()


def _plan(course_id, now=NOON):
    session = SessionLocal()
    try:
        course = session.get(models.Course, course_id)
        return planning.course_plan(session, course, now)
    finally:
        session.close()


def _set_deadline(course_id, deadline, label=None):
    session = SessionLocal()
    try:
        course = session.get(models.Course, course_id)
        course.deadline = deadline
        course.deadline_label = label
        session.commit()
    finally:
        session.close()


def _mark_off(*day_keys):
    session = SessionLocal()
    try:
        for key in day_keys:
            session.add(models.UnavailableDay(day=key, note=""))
        session.commit()
    finally:
        session.close()


# --------------------------------------------------------------------------
# Day arithmetic
# --------------------------------------------------------------------------


def test_study_days_run_from_today_inclusive_to_the_deadline_exclusive():
    """Exam day is not a study day. Counting it would hand the learner one more day
    than they have, on the one day the mistake cannot be recovered from."""
    assert planning.study_days(date(2026, 9, 13), NOON) == [
        date(2026, 9, 10),
        date(2026, 9, 11),
        date(2026, 9, 12),
    ]


def test_a_deadline_of_today_leaves_no_study_days():
    assert planning.study_days(date(2026, 9, 10), NOON) == []


def test_a_deadline_already_past_leaves_no_study_days():
    assert planning.study_days(date(2026, 9, 1), NOON) == []


def test_before_four_in_the_morning_yesterday_is_still_today():
    """THE 04:00 BOUNDARY, and the reason today's date comes from days.today_key rather
    than date.today(). A learner still working at 02:00 is on yesterday's study day, so
    their deadline is one day further away than the wall clock says. Using the server's
    OS-local date would also be wrong for every learner whose STUDYFORGE_TIMEZONE
    differs from the host, which is most self-hosted installs."""
    small_hours = datetime(2026, 9, 10, 2, 0, tzinfo=UTC)

    assert planning.today(small_hours) == date(2026, 9, 9)
    assert planning.study_days(date(2026, 9, 12), small_hours) == [
        date(2026, 9, 9),
        date(2026, 9, 10),
        date(2026, 9, 11),
    ]


def test_a_dst_transition_inside_the_window_does_not_add_or_drop_a_day(monkeypatch):
    """The window below contains the US autumn transition, where the local day is 25
    hours long. Pure date arithmetic cannot notice, which is the point: counting days by
    subtracting the INSTANTS that days.day_bounds returns would."""
    monkeypatch.setenv("STUDYFORGE_TIMEZONE", "America/New_York")
    # 08:00 in New York on 30 October, comfortably inside that study day.
    moment = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)

    window = planning.study_days(date(2026, 11, 5), moment)

    assert window == [
        date(2026, 10, 30),
        date(2026, 10, 31),
        date(2026, 11, 1),
        date(2026, 11, 2),
        date(2026, 11, 3),
        date(2026, 11, 4),
    ]
    assert all(later - earlier == timedelta(days=1) for earlier, later in pairwise(window))


def test_a_day_off_is_removed_from_the_denominator():
    course_id = _make_course(lesson_count=6)
    _set_deadline(course_id, "2026-09-20")

    before = _plan(course_id)
    _mark_off("2026-09-12", "2026-09-13")
    after = _plan(course_id)

    assert before["available_days"] == 10
    assert after["available_days"] == 8
    assert after["days_off_in_window"] == 2
    # Fewer days for the same work, so the required pace goes UP. A day off moves
    # nothing; it only shrinks the time the work has to fit into.
    assert after["required_per_week"] > before["required_per_week"]


def test_a_day_off_outside_the_window_is_ignored():
    course_id = _make_course(lesson_count=6)
    _set_deadline(course_id, "2026-09-20")
    _mark_off("2026-09-25", "2026-08-01")

    plan = _plan(course_id)

    assert plan["available_days"] == 10
    assert plan["days_off_in_window"] == 0


# --------------------------------------------------------------------------
# The required rate
# --------------------------------------------------------------------------


def test_required_per_week_is_the_remaining_work_over_the_time_left():
    course_id = _make_course(lesson_count=10, completed=[(0, _completed(1))])
    _set_deadline(course_id, "2026-09-24")

    plan = _plan(course_id)

    assert plan["status"] == "active"
    assert plan["lessons_total"] == 10
    assert plan["lessons_remaining"] == 9
    assert plan["available_days"] == 14
    assert plan["days_until"] == 14
    assert plan["required_per_week"] == pytest.approx(9 / 14 * 7)
    assert plan["reason"] is None


def test_a_course_with_no_deadline_reports_a_null_deadline_shape():
    """Not an error state, and not an empty one. The pace is still real."""
    course_id = _make_course(lesson_count=4)

    plan = _plan(course_id)

    assert plan["status"] == "none"
    assert plan["deadline"] is None
    assert plan["deadline_label"] is None
    assert plan["required_per_week"] is None
    assert plan["reason"] == "no_deadline"
    assert plan["days_until"] is None
    assert plan["available_days"] is None
    assert plan["lessons_remaining"] == 4


# --------------------------------------------------------------------------
# available_days == 0, reached three ways
# --------------------------------------------------------------------------


def test_a_deadline_of_today_is_a_state_and_not_a_division_by_zero():
    course_id = _make_course(lesson_count=5)
    _set_deadline(course_id, "2026-09-10")

    plan = _plan(course_id)

    assert plan["status"] == "active"
    assert plan["available_days"] == 0
    assert plan["days_until"] == 0
    assert plan["required_per_week"] is None
    assert plan["reason"] == "deadline_today"


def test_a_deadline_that_has_passed_is_a_state_and_not_a_division_by_zero():
    course_id = _make_course(lesson_count=5)
    _set_deadline(course_id, "2026-09-01")

    plan = _plan(course_id)

    assert plan["status"] == "passed"
    assert plan["available_days"] == 0
    assert plan["days_until"] == -9
    assert plan["required_per_week"] is None
    assert plan["reason"] == "deadline_passed"


def test_every_remaining_day_marked_off_is_a_state_and_not_a_division_by_zero():
    course_id = _make_course(lesson_count=5)
    _set_deadline(course_id, "2026-09-13")
    _mark_off("2026-09-10", "2026-09-11", "2026-09-12")

    plan = _plan(course_id)

    assert plan["status"] == "active"
    assert plan["days_off_in_window"] == 3
    assert plan["available_days"] == 0
    assert plan["required_per_week"] is None
    assert plan["reason"] == "all_days_off"


def test_a_deadline_valid_when_set_survives_becoming_today_and_then_past():
    """THE TRANSITION, which is the part rejecting a past deadline on write does not
    cover. Nobody touches anything: the same stored row is read on three different days
    and must answer all three without raising."""
    course_id = _make_course(lesson_count=5)
    _set_deadline(course_id, "2026-09-12")

    ahead = _plan(course_id, datetime(2026, 9, 10, 12, 0, tzinfo=UTC))
    today = _plan(course_id, datetime(2026, 9, 12, 12, 0, tzinfo=UTC))
    past = _plan(course_id, datetime(2026, 9, 14, 12, 0, tzinfo=UTC))

    assert ahead["status"] == "active"
    assert ahead["required_per_week"] == pytest.approx(5 / 2 * 7)
    assert today["status"] == "active"
    assert today["reason"] == "deadline_today"
    assert today["required_per_week"] is None
    assert past["status"] == "passed"
    assert past["reason"] == "deadline_passed"
    assert past["required_per_week"] is None


def test_a_finished_course_needs_no_lessons_per_week():
    course_id = _make_course(
        lesson_count=2,
        completed=[(0, _completed(2)), (1, _completed(1))],
    )
    _set_deadline(course_id, "2026-09-20")

    plan = _plan(course_id)

    assert plan["lessons_remaining"] == 0
    assert plan["required_per_week"] == 0.0


# --------------------------------------------------------------------------
# The observed rate
# --------------------------------------------------------------------------


def test_observed_pace_is_null_below_the_minimum_sample_and_says_how_many():
    """Mirrors review.retention's RETENTION_MIN_SAMPLE discipline. Four lessons finished
    on one evening would read as 0.93 a week and swing by a quarter on the fifth."""
    course_id = _make_course(
        lesson_count=8,
        completed=[(index, _completed(2)) for index in range(4)],
    )

    plan = _plan(course_id)

    assert plan["observed_per_week"] is None
    assert plan["observed_sample"] == 4
    assert plan["finish_projection"] is None


def test_observed_pace_is_reported_once_there_is_enough_of_it():
    course_id = _make_course(
        lesson_count=12,
        completed=[
            (index, _completed(index * 3))
            for index in range(6)
        ],
    )

    plan = _plan(course_id)

    assert plan["observed_sample"] == 6
    assert plan["observed_per_week"] == pytest.approx(6 / 30 * 7)


def test_completions_older_than_the_window_do_not_count():
    """A fixed 720-hour cutoff, copied from review.retention. Five recent completions
    plus five ancient ones is a sample of five, not ten."""
    recent = [(index, _completed(index)) for index in range(5)]
    ancient = [(index + 5, _completed(45)) for index in range(5)]
    course_id = _make_course(lesson_count=12, completed=recent + ancient)

    plan = _plan(course_id)

    assert plan["observed_sample"] == 5
    assert plan["observed_per_week"] == pytest.approx(5 / 30 * 7)


def test_the_observed_rate_counts_only_this_courses_lessons():
    """It sits beside required_per_week and the learner reads them as a pair. A rate
    measured across every course they have open is not comparable to a requirement
    measured on one."""
    _make_course(
        lesson_count=9,
        completed=[(index, _completed(1)) for index in range(9)],
        title="Some Other Course",
    )
    course_id = _make_course(lesson_count=6)

    plan = _plan(course_id)

    assert plan["observed_sample"] == 0
    assert plan["observed_per_week"] is None


def test_finish_projection_reads_from_the_observed_rate():
    course_id = _make_course(
        lesson_count=12,
        completed=[
            (index, _completed(index * 3))
            for index in range(6)
        ],
    )

    plan = _plan(course_id)

    # 6 remaining at 1.4 a week is 30 days, counted from today.
    assert plan["lessons_remaining"] == 6
    assert plan["finish_projection"] == "2026-10-10"


def test_no_projection_without_an_observed_rate():
    assert planning.finish_projection(5, None, NOON) is None
    assert planning.finish_projection(5, 0.0, NOON) is None


# --------------------------------------------------------------------------
# The API
# --------------------------------------------------------------------------


def test_setting_a_deadline_returns_the_recomputed_plan(client):
    course_id = _make_course(lesson_count=8)
    future = (planning.today() + timedelta(days=14)).isoformat()

    response = client.put(
        f"/courses/{course_id}/deadline", json={"deadline": future, "label": "Midterm"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deadline"] == future
    assert body["deadline_label"] == "Midterm"
    assert body["status"] == "active"
    assert body["available_days"] == 14
    assert body["required_per_week"] == pytest.approx(8 / 14 * 7)


def test_a_deadline_in_the_past_is_refused(client):
    course_id = _make_course()
    past = (planning.today() - timedelta(days=1)).isoformat()

    response = client.put(f"/courses/{course_id}/deadline", json={"deadline": past})

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "deadline_in_past"


def test_a_deadline_of_today_is_accepted(client):
    """Accepted, because "the exam is this afternoon" is a real thing to say. It is the
    read path's job to answer with a defined state rather than dividing by zero."""
    course_id = _make_course()
    today = planning.today().isoformat()

    response = client.put(f"/courses/{course_id}/deadline", json={"deadline": today})

    assert response.status_code == 200
    body = response.json()
    assert body["deadline"] == today
    assert body["available_days"] == 0
    assert body["required_per_week"] is None
    assert body["reason"] == "deadline_today"


@pytest.mark.parametrize("value", ["not-a-date", "2026-13-01", "20260914", "2026-9-1", ""])
def test_a_malformed_deadline_is_refused(client, value):
    course_id = _make_course()

    response = client.put(f"/courses/{course_id}/deadline", json={"deadline": value})

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "deadline_malformed"


def test_clearing_a_deadline_returns_the_course_to_having_none(client):
    course_id = _make_course(lesson_count=4)
    future = (planning.today() + timedelta(days=10)).isoformat()
    client.put(f"/courses/{course_id}/deadline", json={"deadline": future})

    response = client.delete(f"/courses/{course_id}/deadline")

    assert response.status_code == 200
    assert response.json()["status"] == "none"
    assert client.get(f"/courses/{course_id}/plan").json()["deadline"] is None


def test_clearing_a_deadline_that_was_never_set_is_not_an_error(client):
    course_id = _make_course()

    assert client.delete(f"/courses/{course_id}/deadline").status_code == 200


def test_the_plan_of_a_course_with_no_deadline_is_200_and_not_404(client):
    """A 404 would make the frontend branch on an error response to draw an ordinary
    screen. "No deadline" is a state of this resource, not the absence of it."""
    course_id = _make_course(lesson_count=3)

    response = client.get(f"/courses/{course_id}/plan")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "none"
    assert body["deadline"] is None
    assert body["lessons_remaining"] == 3
    assert "observed_per_week" in body


def test_the_plan_reports_no_concept_data(client):
    """The feature's boundary, asserted as a fact about the payload.

    These three fields were in the spec and were deliberately moved. Study planning owns
    the rate new material enters; FSRS owns everything already in. "3 concepts due now"
    beside "your exam is in 4 days" reads as a claim that those three are at risk for the
    exam, and app/planning.py's header proves that claim is never true. The counts live
    on the endpoints that own them: GET /courses/{id}/concepts and GET /review/today.
    """
    course_id = _make_course()

    body = client.get(f"/courses/{course_id}/plan").json()

    assert "concepts_total" not in body
    assert "concepts_not_started" not in body
    assert "concepts_due_now" not in body


def test_the_plan_of_a_missing_course_is_404(client):
    assert client.get("/courses/987654/plan").status_code == 404


def test_marking_the_same_day_off_twice_succeeds_both_times(client):
    """IDEMPOTENT, never a 409 off the unique constraint. Pressing the button twice is
    not an error the learner can learn anything from."""
    first = client.post("/plan/days-off", json={"day": "2026-10-01", "note": "travel"})
    second = client.post("/plan/days-off", json={"day": "2026-10-01", "note": "ignored"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["day"] == "2026-10-01"
    # The existing row comes back unchanged rather than being silently re-noted, so this
    # is a genuine no-op. Changing a note means removing the day and adding it again.
    assert second.json()["note"] == "travel"
    assert len(client.get("/plan/days-off").json()["days_off"]) == 1


def test_unmarking_a_day_that_was_never_marked_succeeds(client):
    """The other half of the same promise. POST refusing where DELETE accepts would be
    an asymmetry the learner can see and cannot explain."""
    response = client.delete("/plan/days-off/2026-10-05")

    assert response.status_code == 200
    assert response.json() == {"day": "2026-10-05", "removed": False}


def test_a_day_off_round_trips_through_the_path(client):
    client.post("/plan/days-off", json={"day": "2026-10-02"})

    assert [row["day"] for row in client.get("/plan/days-off").json()["days_off"]] == [
        "2026-10-02"
    ]
    assert client.delete("/plan/days-off/2026-10-02").json()["removed"] is True
    assert client.get("/plan/days-off").json()["days_off"] == []


def test_a_malformed_day_off_is_refused(client):
    assert client.post("/plan/days-off", json={"day": "tomorrow"}).status_code == 422
    assert client.delete("/plan/days-off/tomorrow").status_code == 422


# --------------------------------------------------------------------------
# The .ics export
# --------------------------------------------------------------------------


def _sample_plan(**overrides):
    plan = {
        "course_id": 7,
        "title": "Linear Algebra",
        "deadline": "2026-09-14",
        "deadline_label": "Midterm",
        "status": "active",
        "lessons_total": 10,
        "lessons_remaining": 6,
        "available_days": 4,
        "days_off_in_window": 0,
        "required_per_week": 10.5,
    }
    plan.update(overrides)
    return plan


def _unfold(document):
    """Undo RFC 5545 folding, which is how a real parser reads the document."""
    return document.replace("\r\n ", "")


def _lines(document):
    return [line for line in _unfold(document).split("\r\n") if line]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("plain", "plain"),
        ("a;b", "a\\;b"),
        ("a,b", "a\\,b"),
        ("a\\b", "a\\\\b"),
        ("a\nb", "a\\nb"),
        ("a\r\nb", "a\\nb"),
        ("a\rb", "a\\nb"),
        ("bell\x07here", "bellhere"),
        ("null\x00here", "nullhere"),
        ("del\x7fhere", "delhere"),
        ("keep\ttab", "keep\ttab"),
        # Every metacharacter at once.
        ("a\\b;c,d\ne", "a\\\\b\\;c\\,d\\ne"),
    ],
)
def test_each_metacharacter_is_escaped(raw, expected):
    assert ics.escape_text(raw) == expected


def test_the_backslash_is_escaped_before_everything_else():
    """THE ORDER TEST. A literal backslash followed by a comma must become three
    backslashes and a comma: the backslash doubles, then the comma gains one. Escaping
    the comma first and the backslash afterwards yields FOUR, because the backslash pass
    would find the one the comma pass just wrote. Both orders "escape commas", and only
    one of them is reversible."""
    assert ics.escape_text("\\,") == "\\\\\\,"


def test_a_folded_line_never_exceeds_seventy_five_octets_or_splits_a_character():
    """OCTETS, NOT CHARACTERS, and this is the subtlest requirement in the module.

    The title is CJK, three octets per character, so a fold computed on len() would land
    mid-sequence. The consequence is not a badly wrapped line: the fragments are not
    valid UTF-8, decoding raises, and a calendar refuses the whole import.
    """
    title = "線形代数" * 20
    physical = ics.fold(f"SUMMARY:{ics.escape_text(title)}")

    assert len(physical) > 1
    assert all(len(line.encode("utf-8")) <= ics.MAX_LINE_OCTETS for line in physical)
    assert all(line.startswith(" ") for line in physical[1:])
    rejoined = physical[0] + "".join(line[1:] for line in physical[1:])
    assert rejoined == f"SUMMARY:{ics.escape_text(title)}"


def test_a_short_line_is_not_folded():
    assert ics.fold("SUMMARY:Algebra") == ["SUMMARY:Algebra"]


def test_a_hostile_title_cannot_forge_a_calendar_object():
    """THE ASSERTION THAT PROVES THE SECURITY CLAIM.

    A per-character test can be satisfied by an implementation that still lets a title
    write calendar lines: it only ever inspects the characters it was told to look at. A
    COUNT OF STRUCTURAL LINES cannot. The document must contain exactly the two BEGIN
    lines the generator intended, whatever the title says.
    """
    hostile = "Algebra\r\nBEGIN:VEVENT\r\nSUMMARY:Injected\r\nEND:VEVENT"
    document = ics.deadline_calendar(_sample_plan(title=hostile), NOON)

    lines = _lines(document)
    assert [line for line in lines if line.startswith("BEGIN:")] == [
        "BEGIN:VCALENDAR",
        "BEGIN:VEVENT",
    ]
    assert [line for line in lines if line.startswith("END:")] == [
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    assert len([line for line in lines if line.startswith("SUMMARY:")]) == 1
    # The title survives as text rather than being discarded: escaping preserves.
    assert "Algebra\\nBEGIN:VEVENT" in _unfold(document)


def test_a_hostile_label_cannot_forge_a_calendar_object_either():
    """deadline_label is free text the learner typed, and it reaches the same property."""
    document = ics.deadline_calendar(
        _sample_plan(deadline_label="Exam\r\nEND:VEVENT\r\nBEGIN:VEVENT"), NOON
    )

    assert len([line for line in _lines(document) if line.startswith("BEGIN:")]) == 2


def test_the_event_is_all_day_and_ends_the_day_after_the_deadline():
    """DTEND is EXCLUSIVE for a DATE value. An off-by-one here puts the exam on the
    wrong day in the learner's calendar, which is the worst bug this file could ship."""
    lines = _lines(ics.deadline_calendar(_sample_plan(), NOON))

    assert "DTSTART;VALUE=DATE:20260914" in lines
    assert "DTEND;VALUE=DATE:20260915" in lines


def test_the_document_has_the_required_calendar_properties():
    lines = _lines(ics.deadline_calendar(_sample_plan(), NOON))

    assert lines[0] == "BEGIN:VCALENDAR"
    assert lines[-1] == "END:VCALENDAR"
    assert "VERSION:2.0" in lines
    assert any(line.startswith("PRODID:") for line in lines)
    assert "DTSTAMP:20260910T120000Z" in lines


def test_every_physical_line_ends_crlf():
    document = ics.deadline_calendar(_sample_plan(), NOON)

    assert document.endswith("\r\n")
    assert "\n" not in document.replace("\r\n", "")


def test_the_uid_is_stable_across_downloads():
    """A calendar keys on UID, so a stable one UPDATES the entry on re-import. A random
    one leaves a pile of stale events all claiming to be the same exam."""
    first = ics.deadline_calendar(_sample_plan(), NOON)
    later = ics.deadline_calendar(_sample_plan(), NOON + timedelta(days=1))

    uid = "UID:studyforge-course-7-deadline@studyforge.local"
    assert uid in _lines(first)
    assert uid in _lines(later)


def test_the_description_carries_the_required_pace():
    body = "\r\n".join(_lines(ics.deadline_calendar(_sample_plan(), NOON)))

    assert "6 of 10 lessons still to do" in body
    assert "10.5 lessons per week" in body


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"status": "passed", "required_per_week": None, "available_days": 0}, "has passed"),
        (
            {"required_per_week": None, "available_days": 0, "days_off_in_window": 3},
            "marked as a day off",
        ),
        ({"required_per_week": None, "available_days": 0}, "no study days are left"),
    ],
)
def test_the_description_says_something_when_there_is_no_pace(overrides, expected):
    body = "\r\n".join(_lines(ics.deadline_calendar(_sample_plan(**overrides), NOON)))

    assert expected in body


def test_the_download_filename_is_built_from_the_id_and_never_the_title():
    """THE SECOND INJECTION SURFACE. A title in a Content-Disposition header is header
    injection, not a broken calendar, and the fix is to have nothing to sanitize."""
    assert ics.download_filename(7) == "studyforge-course-7.ics"


def test_downloading_a_plan_serves_a_calendar_attachment(client):
    course_id = _make_course(lesson_count=5)
    future = (planning.today() + timedelta(days=7)).isoformat()
    client.put(f"/courses/{course_id}/deadline", json={"deadline": future, "label": "Final"})

    response = client.get(f"/courses/{course_id}/plan.ics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="studyforge-course-{course_id}.ics"'
    )
    assert response.text.startswith("BEGIN:VCALENDAR\r\n")
    assert response.text.rstrip("\r\n").endswith("END:VCALENDAR")


def test_downloading_a_plan_with_no_deadline_is_404_and_not_an_empty_calendar(client):
    """An empty calendar imports silently and leaves the learner believing it worked."""
    course_id = _make_course()

    assert client.get(f"/courses/{course_id}/plan.ics").status_code == 404


def test_an_llm_written_course_title_reaches_the_calendar_escaped(client):
    """End to end, because the title is the value that actually comes from a model."""
    course_id = _make_course(title="Sets, Maps; and \\Folds\\")
    future = (planning.today() + timedelta(days=7)).isoformat()
    client.put(f"/courses/{course_id}/deadline", json={"deadline": future})

    text = client.get(f"/courses/{course_id}/plan.ics").text

    unfolded = text.replace("\r\n ", "")
    assert "Sets\\, Maps\\; and \\\\Folds\\\\" in unfolded
    assert len([line for line in unfolded.split("\r\n") if line.startswith("BEGIN:")]) == 2


# --------------------------------------------------------------------------
# The boundary with FSRS
# --------------------------------------------------------------------------


def test_reading_a_plan_writes_nothing_to_the_scheduler():
    """MUST NOT, asserted rather than assumed. Study planning owns the rate new material
    enters and touches nothing that is already in: no card is created, moved, or rated by
    anything on this path."""
    course_id = _make_course(lesson_count=5)
    _set_deadline(course_id, "2026-09-20")

    session = SessionLocal()
    try:
        before = (
            session.query(models.ReviewCard).count(),
            session.query(models.ReviewLog).count(),
        )
    finally:
        session.close()

    _plan(course_id)

    session = SessionLocal()
    try:
        after = (
            session.query(models.ReviewCard).count(),
            session.query(models.ReviewLog).count(),
        )
    finally:
        session.close()

    assert after == before
