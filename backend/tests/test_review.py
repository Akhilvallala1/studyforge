"""The scheduling service: seeding cards from lesson quizzes, applying ratings,
and the dashboard figures the Today screen and concept map read.

app/fsrs.py and app/rating.py are covered by their own suites as pure functions.
What is exercised here is everything that only breaks once a database is involved:
the naive/aware datetime boundary, idempotent grading, and the queries.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app import fsrs, models, review
from app.concepts import normalize_concept
from app.db import SessionLocal


def _make_lesson(concepts=("Gradient Descent", "Backpropagation"), items_per_concept=1):
    """A one-module course whose lesson has short-answer items for each concept."""
    session = SessionLocal()
    try:
        course = models.Course(title="Optimization", description="")
        module = models.Module(title="Module 1", position=0)
        lesson = models.Lesson(
            title="Lesson A", position=0, content="# Lesson A", concepts=list(concepts)
        )
        answers = {}
        for index, concept in enumerate(concepts):
            for repeat in range(items_per_concept):
                answer = f"answer-{index}-{repeat}"
                lesson.quiz_items.append(
                    models.QuizItem(
                        question=f"Question {index}.{repeat}?",
                        kind="short",
                        options=[],
                        answer=answer,
                        concept=concept,
                    )
                )
        module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.commit()
        for item in lesson.quiz_items:
            answers[item.id] = item.answer
        return course.id, lesson.id, answers
    finally:
        session.close()


def _make_course(lessons, items_per_concept=1):
    """A one-module course of several lessons, for the concept map's column layout.

    `lessons` is a list of (title, concepts). Lesson titles are deliberately not in
    alphabetical order in the callers, so a test that passes cannot be passing because
    the rows happened to come back sorted by name.
    """
    session = SessionLocal()
    try:
        course = models.Course(title="Replication", description="")
        module = models.Module(title="Module 1", position=0)
        for position, (title, concepts) in enumerate(lessons):
            row = models.Lesson(
                title=title, position=position, content=f"# {title}", concepts=list(concepts)
            )
            for index, concept in enumerate(concepts):
                for repeat in range(items_per_concept):
                    row.quiz_items.append(
                        models.QuizItem(
                            question=f"{title} {index}.{repeat}?",
                            kind="short",
                            options=[],
                            answer=f"answer-{index}-{repeat}",
                            concept=concept,
                        )
                    )
            module.lessons.append(row)
        course.modules.append(module)
        session.add(course)
        session.commit()
        return course.id
    finally:
        session.close()


def _cards():
    session = SessionLocal()
    try:
        return {row.concept_key: row for row in session.query(models.ReviewCard).all()}
    finally:
        session.close()


def _logs():
    session = SessionLocal()
    try:
        return session.query(models.ReviewLog).order_by(models.ReviewLog.id).all()
    finally:
        session.close()


def _seed_card(concept_key="quorum reads", *, ratings=(fsrs.GOOD,), start=None):
    """Drive a card through a rating sequence at one-day intervals, returning its row."""
    session = SessionLocal()
    try:
        moment = start or (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=len(ratings)))
        for rating in ratings:
            review.record_review(session, concept_key, concept_key.title(), rating, now=moment)
            moment += timedelta(days=1)
        session.commit()
        return review.get_card(session, concept_key)
    finally:
        session.close()


@pytest.fixture(autouse=True)
def clean_schedule(client):
    """Empty the scheduling tables before each test in this module.

    conftest points the whole suite at one SQLite file with no per-test reset, which
    the older suites live with by scoping every assertion to ids they just created.
    That does not work here: counts, streaks, and retention are global by definition,
    so a card left behind by the previous test changes the answer. Only the two
    scheduling tables are cleared, never courses or attempts, so nothing another
    module built underneath itself is disturbed.
    """
    session = SessionLocal()
    try:
        session.query(models.ReviewLog).delete()
        session.query(models.ReviewCard).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture
def lesson(client):
    """Takes client so init_db() has run and the review tables exist."""
    return _make_lesson()


class TestLessonSeeding:
    def test_completing_a_lesson_creates_one_card_per_answered_concept(self, client, lesson):
        _, lesson_id, answers = lesson
        for item_id, answer in answers.items():
            client.post(f"/quiz/{item_id}/answer", json={"answer": answer})

        body = client.post(f"/lessons/{lesson_id}/complete").json()
        assert body["scheduled_concepts"] == 2
        assert set(_cards()) == {"gradient descent", "backpropagation"}

    def test_an_unanswered_lesson_schedules_nothing(self, client, lesson):
        _, lesson_id, _ = lesson
        assert client.post(f"/lessons/{lesson_id}/complete").json()["scheduled_concepts"] == 0
        assert _cards() == {}

    def test_completing_twice_does_not_grade_twice(self, client, lesson):
        _, lesson_id, answers = lesson
        for item_id, answer in answers.items():
            client.post(f"/quiz/{item_id}/answer", json={"answer": answer})

        first = client.post(f"/lessons/{lesson_id}/complete").json()
        second = client.post(f"/lessons/{lesson_id}/complete").json()

        assert first["scheduled_concepts"] == 2
        # Every attempt is already inside a rating, so the repeat has nothing left
        # to rate. This is the guard the shared-concept fix had to keep intact.
        assert second["scheduled_concepts"] == 0
        assert len(_logs()) == 2

    def test_a_wrong_answer_derives_again(self, client, lesson):
        _, lesson_id, answers = lesson
        item_id = next(iter(answers))
        client.post(f"/quiz/{item_id}/answer", json={"answer": "definitely wrong"})
        client.post(f"/lessons/{lesson_id}/complete")

        card = _cards()["gradient descent"]
        assert card.state == fsrs.LEARNING
        assert card.stability == pytest.approx(fsrs.WEIGHTS[fsrs.AGAIN - 1])

    def test_the_worst_item_sets_the_concept_rating(self, client):
        """Two items on one concept, one right and one wrong, must rate Again."""
        _, lesson_id, answers = _make_lesson(concepts=("Recursion",), items_per_concept=2)
        item_ids = list(answers)
        client.post(f"/quiz/{item_ids[0]}/answer", json={"answer": answers[item_ids[0]]})
        client.post(f"/quiz/{item_ids[1]}/answer", json={"answer": "wrong"})
        client.post(f"/lessons/{lesson_id}/complete")

        assert _logs()[0].rating == fsrs.AGAIN

    def test_the_log_records_the_evidence_and_the_stamps(self, client, lesson):
        _, lesson_id, answers = lesson
        item_id = next(iter(answers))
        answer_body = client.post(
            f"/quiz/{item_id}/answer", json={"answer": answers[item_id]}
        ).json()
        client.post(f"/lessons/{lesson_id}/complete")

        log = _logs()[0]
        assert log.attempt_ids == [answer_body["attempt_id"]]
        assert log.rating_source == "derived"
        assert log.rating_v == "v1"
        assert log.state_before == fsrs.NEW
        assert log.stability_before is None
        assert log.fsrs_v == fsrs.FSRS_VERSION
        assert log.weights_hash == fsrs.WEIGHTS_HASH


class TestRecordReview:
    def test_the_card_and_its_log_agree(self, client):
        card = _seed_card(ratings=(fsrs.GOOD, fsrs.GOOD))
        log = _logs()[-1]
        assert log.stability_after == pytest.approx(card.stability)
        assert log.difficulty_after == pytest.approx(card.difficulty)
        assert log.due_after == card.due
        assert log.state_after == card.state

    def test_an_again_in_review_counts_a_lapse(self, client):
        card = _seed_card(ratings=(fsrs.GOOD, fsrs.AGAIN))
        assert card.state == fsrs.RELEARNING
        assert card.lapses == 1

    def test_an_again_while_new_is_not_a_lapse(self, client):
        card = _seed_card(ratings=(fsrs.AGAIN,))
        assert card.state == fsrs.LEARNING
        assert card.lapses == 0

    def test_reps_count_every_rating(self, client):
        card = _seed_card(ratings=(fsrs.GOOD, fsrs.AGAIN, fsrs.GOOD))
        assert card.reps == 3

    def test_an_unknown_rating_is_rejected(self, client):
        session = SessionLocal()
        try:
            with pytest.raises(ValueError):
                review.record_review(session, "x", "X", 5)
        finally:
            session.close()

    def test_scheduling_survives_an_aware_now(self, client):
        """Stored timestamps are naive UTC; an aware `now` must not raise.

        This is the failure this module's timezone discipline exists to prevent, and
        it would surface as a 500 on a review submission rather than anywhere obvious.
        """
        session = SessionLocal()
        try:
            review.record_review(session, "aware", "Aware", fsrs.GOOD, now=datetime.now(UTC))
            session.commit()
            card = review.get_card(session, "aware")
            review.record_review(session, "aware", "Aware", fsrs.GOOD, now=datetime.now(UTC))
            session.commit()
            assert card.due is not None and card.due.tzinfo is None
        finally:
            session.close()


class TestQueueAndPreview:
    def test_preview_matches_what_rating_actually_does(self, client):
        """The four button labels are a promise; pressing one must honour it."""
        card = _seed_card(ratings=(fsrs.GOOD, fsrs.GOOD))
        moment = datetime.now(UTC).replace(tzinfo=None)
        promised = {entry["rating"]: entry["interval_days"] for entry in review.preview(card, moment)}

        session = SessionLocal()
        try:
            log = review.record_review(session, card.concept_key, "", fsrs.GOOD, now=moment)
            session.commit()
            assert log.scheduled_days == promised[fsrs.GOOD]
        finally:
            session.close()

    def test_preview_does_not_persist_anything(self, client):
        card = _seed_card(ratings=(fsrs.GOOD, fsrs.GOOD))
        before = (card.stability, card.difficulty, card.due, card.reps)
        review.preview(card, datetime.now(UTC).replace(tzinfo=None))
        after = _cards()[card.concept_key]
        assert (after.stability, after.difficulty, after.due, after.reps) == before

    def test_the_same_rating_twice_gives_the_same_interval(self, client):
        """No fuzz: the interval is a function of the card, not of chance."""
        card = _seed_card(ratings=(fsrs.GOOD, fsrs.GOOD))
        moment = datetime.now(UTC).replace(tzinfo=None)
        assert review.preview(card, moment) == review.preview(card, moment)

    def test_hard_is_never_longer_than_good(self, client):
        card = _seed_card(ratings=(fsrs.GOOD, fsrs.GOOD))
        by_name = {e["name"]: e["interval_days"] for e in review.preview(card, datetime.now(UTC))}
        assert by_name["hard"] <= by_name["good"] <= by_name["easy"]

    def test_the_queue_puts_mid_acquisition_cards_first(self, client):
        past = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=40)
        _seed_card("settled", ratings=(fsrs.GOOD, fsrs.GOOD), start=past)
        _seed_card("wobbling", ratings=(fsrs.GOOD, fsrs.AGAIN), start=past)

        session = SessionLocal()
        try:
            keys = [row.concept_key for row in review.due_cards(session)]
        finally:
            session.close()
        assert keys[0] == "wobbling"

    def test_a_card_that_is_not_due_is_not_queued(self, client):
        _seed_card("fresh", ratings=(fsrs.GOOD, fsrs.EASY), start=datetime.now(UTC).replace(tzinfo=None))
        session = SessionLocal()
        try:
            assert review.due_cards(session) == []
        finally:
            session.close()

    def test_sub_day_intervals_are_labelled_as_within_the_session(self):
        assert review.format_interval(timedelta(minutes=10)) == "< 10 min"
        assert review.format_interval(timedelta(days=1)) == "1 day"
        assert review.format_interval(timedelta(days=6)) == "6 days"
        assert review.format_interval(timedelta(days=60)) == "2 months"


class TestDashboard:
    def test_due_this_week_is_never_less_than_due_today(self, client):
        past = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
        for index in range(3):
            _seed_card(f"concept {index}", ratings=(fsrs.GOOD, fsrs.GOOD), start=past)
        body = client.get("/review/today").json()
        assert body["due_this_week"] >= body["due_today"] >= body["due_now"] >= 1

    def test_a_card_in_its_ten_minute_step_counts_today_but_not_now(self, client, monkeypatch):
        """due_now and due_today must be allowed to disagree, and the Today screen
        depends on it. A card just rated Again is due in ten minutes: it belongs to
        the day's workload, but a session started this second cannot serve it. Gating
        the Start review button on the day figure offered a session with nothing in
        it, which is the bug this separation fixes."""
        # The premise here, that a ten-minute learning step still falls inside "today",
        # is only true as long as `now` is not itself within ten minutes of the 04:00
        # local boundary in app/days.py. Read from the wall clock, this test fails for
        # ten minutes out of every day, wherever that window happens to land. Pinning
        # models.utcnow() (the clock both review.now_utc() and the /review/today route
        # read) to a fixed mid-day moment removes that dependency without loosening
        # what the test actually checks. Do not swap this back for datetime.now(UTC).
        fixed_now = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
        monkeypatch.setattr(models, "utcnow", lambda: fixed_now)

        # _seed_card advances a day per rating, so start two days back to land the
        # Again on now: the ten-minute step has to still be running for this to test
        # anything.
        start = fixed_now.replace(tzinfo=None) - timedelta(days=2)
        _seed_card("lapsed", ratings=(fsrs.GOOD, fsrs.GOOD, fsrs.AGAIN), start=start)

        body = client.get("/review/today").json()
        assert body["due_now"] == 0
        assert body["due_today"] == 1
        # The estimate follows what is servable, so it does not promise work that
        # cannot be started.
        assert body["estimated_minutes"] == 0
        assert client.get("/review/queue").json()["due_total"] == 0

    def test_retention_is_withheld_below_the_sample_floor(self, client):
        _seed_card(ratings=(fsrs.GOOD, fsrs.GOOD))
        body = client.get("/review/today").json()
        assert body["retention"] is None
        assert body["sample_size"] < review.RETENTION_MIN_SAMPLE

    def test_retention_counts_hard_as_retained_and_ignores_same_day_reviews(self, client):
        """Twelve genuine review-state ratings, two of them lapses, reads 10/12."""
        session = SessionLocal()
        try:
            card = models.ReviewCard(concept_key="k", concept_label="K", state=fsrs.REVIEW)
            session.add(card)
            session.flush()
            now = datetime.now(UTC).replace(tzinfo=None)
            ratings = [fsrs.GOOD] * 8 + [fsrs.HARD] * 2 + [fsrs.AGAIN] * 2
            for index, rating in enumerate(ratings):
                session.add(
                    models.ReviewLog(
                        card_id=card.id,
                        reviewed_at=now - timedelta(days=index),
                        rating=rating,
                        suggested_rating=rating,
                        state_before=fsrs.REVIEW,
                        state_after=fsrs.REVIEW,
                        elapsed_days=3.0,
                    )
                )
            # Two decoys, each failing exactly ONE of the filters, so neither filter
            # can be deleted without a test noticing. A single row failing both would
            # leave each filter covered only by the other.
            #
            # Fails only the state filter: a genuine day-later gap, but taken during
            # learning rather than review.
            session.add(
                models.ReviewLog(
                    card_id=card.id,
                    reviewed_at=now,
                    rating=fsrs.AGAIN,
                    suggested_rating=fsrs.AGAIN,
                    state_before=fsrs.LEARNING,
                    state_after=fsrs.REVIEW,
                    elapsed_days=3.0,
                )
            )
            # Fails only the elapsed filter: a review-state card, drilled the same day.
            session.add(
                models.ReviewLog(
                    card_id=card.id,
                    reviewed_at=now,
                    rating=fsrs.AGAIN,
                    suggested_rating=fsrs.AGAIN,
                    state_before=fsrs.REVIEW,
                    state_after=fsrs.REVIEW,
                    elapsed_days=0.0,
                )
            )
            session.commit()
        finally:
            session.close()

        body = client.get("/review/today").json()
        assert body["sample_size"] == 12
        assert body["retention"] == pytest.approx(10 / 12)

    def test_the_streak_survives_a_day_not_yet_studied(self, client):
        """Reviewed yesterday and the day before, nothing today: the streak is alive."""
        session = SessionLocal()
        try:
            card = models.ReviewCard(concept_key="s", concept_label="S", state=fsrs.REVIEW)
            session.add(card)
            session.flush()
            start = review.now_utc() - timedelta(days=1)
            for offset in range(3):
                session.add(
                    models.ReviewLog(
                        card_id=card.id,
                        reviewed_at=start - timedelta(days=offset),
                        rating=fsrs.GOOD,
                        suggested_rating=fsrs.GOOD,
                        state_before=fsrs.REVIEW,
                        state_after=fsrs.REVIEW,
                    )
                )
            session.commit()
        finally:
            session.close()
        assert client.get("/review/today").json()["day_streak"] == 3

    def test_the_streak_is_zero_with_no_history(self, client):
        assert client.get("/review/today").json()["day_streak"] == 0

    def test_the_session_estimate_defaults_to_thirty_seconds_a_card(self, client):
        past = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
        for index in range(4):
            _seed_card(f"est {index}", ratings=(fsrs.GOOD, fsrs.GOOD), start=past)
        assert client.get("/review/today").json()["estimated_minutes"] == 2


class TestNeedsAttention:
    def test_two_lapses_in_the_window_flag_a_concept(self, client):
        _seed_card("shaky", ratings=(fsrs.GOOD, fsrs.AGAIN, fsrs.GOOD, fsrs.AGAIN))
        flagged = client.get("/review/today").json()["needs_attention"]
        assert [entry["concept_key"] for entry in flagged] == ["shaky"]
        assert flagged[0]["missed"] == 2
        assert flagged[0]["of"] == 4

    def test_one_lapse_does_not_flag(self, client):
        _seed_card("fine", ratings=(fsrs.GOOD, fsrs.AGAIN, fsrs.GOOD))
        assert client.get("/review/today").json()["needs_attention"] == []

    def test_lapses_older_than_the_window_stop_counting(self, client):
        """Also pins the absence of hysteresis, which is deliberate: needs_attention
        recomputes from the recent ratings on every request with no persisted flag, so
        a concept leaves the list the moment its lapses age out of the window. Adding
        hysteresis later needs a stored flag to attach to, which is a schema change
        and a product decision, not a quiet code change."""
        _seed_card(
            "recovered",
            ratings=(fsrs.AGAIN, fsrs.AGAIN, fsrs.GOOD, fsrs.GOOD, fsrs.GOOD, fsrs.GOOD, fsrs.GOOD),
        )
        assert client.get("/review/today").json()["needs_attention"] == []



class TestMastery:
    @pytest.mark.parametrize(
        ("stability", "expected"),
        [(3.0, review.SHAKY), (7.0, review.SOLID), (20.9, review.SOLID), (21.0, review.MASTERED)],
    )
    def test_buckets_at_each_threshold(self, client, stability, expected):
        row = models.ReviewCard(
            concept_key="b",
            concept_label="B",
            state=fsrs.REVIEW,
            stability=stability,
            difficulty=5.0,
            last_review=review.now_utc(),
        )
        assert review.mastery_bucket(row, review.now_utc()) == expected

    def test_a_concept_with_no_card_is_not_started(self):
        assert review.mastery_bucket(None) == review.NOT_STARTED

    def test_a_long_overdue_card_is_shaky_however_stable(self):
        """High stability plus a long absence is a forgotten concept, not a mastered one."""
        row = models.ReviewCard(
            concept_key="stale",
            concept_label="Stale",
            state=fsrs.REVIEW,
            stability=40.0,
            difficulty=5.0,
            last_review=review.now_utc() - timedelta(days=900),
        )
        assert review.mastery_bucket(row, review.now_utc()) == review.SHAKY

    def test_the_concept_map_reports_every_concept_in_the_course(self, client, lesson):
        course_id, lesson_id, answers = lesson
        item_id = next(iter(answers))
        client.post(f"/quiz/{item_id}/answer", json={"answer": answers[item_id]})
        client.post(f"/lessons/{lesson_id}/complete")

        body = client.get(f"/courses/{course_id}/concepts").json()
        buckets = {entry["concept_label"].lower(): entry["bucket"] for entry in body["concepts"]}
        assert buckets["gradient descent"] != review.NOT_STARTED
        assert buckets["backpropagation"] == review.NOT_STARTED
        # No prerequisite graph exists, so nothing may claim to be locked.
        assert all(entry["bucket"] != "locked" for entry in body["concepts"])

    def test_an_unknown_course_is_404(self, client):
        assert client.get("/courses/999999/concepts").status_code == 404

    def test_concepts_are_grouped_under_the_lesson_that_introduces_them(self, client):
        """Course order, not alphabetical order, and a repeat stays in its first column."""
        course_id = _make_course(
            [
                ("Zebra lesson", ["Replication log", "Shared concept"]),
                ("Alpha lesson", ["Shared concept", "Quorums"]),
            ]
        )
        body = client.get(f"/courses/{course_id}/concepts").json()

        assert [entry["title"] for entry in body["lessons"]] == ["Zebra lesson", "Alpha lesson"]
        columns = {entry["concept_label"]: entry["lesson_index"] for entry in body["concepts"]}
        assert columns["Replication log"] == 0
        assert columns["Quorums"] == 1
        # Taught in lesson 1 and revisited in lesson 2: it belongs to the lesson that
        # introduced it, and appears once rather than in both columns.
        assert columns["Shared concept"] == 0
        assert [entry["concept_label"] for entry in body["concepts"]].count("Shared concept") == 1

    def test_course_order_is_module_position_then_lesson_position(self, client):
        """Columns follow (module.position, lesson.position), not row order.

        Every row here is created in the wrong order on purpose: the second module is
        inserted first, and inside the first module the later lesson is inserted first.
        So lesson ids run exactly backwards from course order. A map built from ids or
        from insertion order would come out reversed and still look entirely plausible
        on screen, which is the failure this guards.
        """
        session = SessionLocal()
        try:
            course = models.Course(title="Ordering", description="")
            second = models.Module(title="Second module", position=1)
            second.lessons.append(
                models.Lesson(
                    title="Third lesson", position=0, content="# Third", concepts=["gamma qq"]
                )
            )
            first = models.Module(title="First module", position=0)
            first.lessons.append(
                models.Lesson(
                    title="Second lesson", position=1, content="# Second", concepts=["beta qq"]
                )
            )
            first.lessons.append(
                models.Lesson(
                    title="First lesson", position=0, content="# First", concepts=["alpha qq"]
                )
            )
            course.modules.append(second)
            course.modules.append(first)
            session.add(course)
            session.commit()
            course_id = course.id
            # The premise of the test: ids really do run backwards from course order.
            assert min(lesson.id for lesson in second.lessons) < min(
                lesson.id for lesson in first.lessons
            )
        finally:
            session.close()

        body = client.get(f"/courses/{course_id}/concepts").json()
        assert [entry["title"] for entry in body["lessons"]] == [
            "First lesson",
            "Second lesson",
            "Third lesson",
        ]
        columns = {entry["concept_label"]: entry["lesson_index"] for entry in body["concepts"]}
        assert columns == {"alpha qq": 0, "beta qq": 1, "gamma qq": 2}

    def test_occurrences_count_every_mention_across_the_course(self, client):
        course_id = _make_course(
            [("Lesson A", ["Repeated", "Once"]), ("Lesson B", ["Repeated"])],
            items_per_concept=1,
        )
        body = client.get(f"/courses/{course_id}/concepts").json()
        counts = {entry["concept_label"]: entry["occurrences"] for entry in body["concepts"]}
        # "Repeated" is named in two lesson concept lists and by one quiz item in each.
        assert counts["Repeated"] == 4
        assert counts["Once"] == 2

    def test_no_edges_are_ever_offered(self, client, lesson):
        """The flag the map branches on. Nothing extracts prerequisites, so it stays False."""
        course_id, _, _ = lesson
        assert client.get(f"/courses/{course_id}/concepts").json()["edges_available"] is False

    def test_the_weakest_concept_names_the_comparison_it_made(self, client, lesson):
        course_id, lesson_id, answers = lesson
        item_id = next(iter(answers))
        client.post(f"/quiz/{item_id}/answer", json={"answer": answers[item_id]})
        client.post(f"/lessons/{lesson_id}/complete")

        weakest = client.get(f"/courses/{course_id}/concepts").json()["weakest"]
        assert weakest["reason"] == "lowest_stability"
        assert weakest["stability"] is not None
        assert weakest["concept_label"].lower() == "gradient descent"

    def test_a_course_nobody_has_studied_has_no_weakest_concept(self, client, lesson):
        """Never-seen concepts have no stability to be lowest, so the callout is absent."""
        course_id, _, _ = lesson
        body = client.get(f"/courses/{course_id}/concepts").json()
        assert all(entry["bucket"] == review.NOT_STARTED for entry in body["concepts"])
        assert body["weakest"] is None

    def test_a_course_with_no_concepts_still_reports_its_lessons(self, client):
        """The empty state the map renders: columns exist, nothing sits in them."""
        course_id = _make_course([("Empty lesson", [])])
        body = client.get(f"/courses/{course_id}/concepts").json()
        assert body["concepts"] == []
        assert body["weakest"] is None
        assert [entry["title"] for entry in body["lessons"]] == ["Empty lesson"]


class TestReviewEndpoints:
    def _due_card(self, client):
        # A concept name unique to this test. Concept keys are global by design, so a
        # shared name would legitimately draw review questions from lessons other
        # tests left behind, and the assertions below would be testing that instead.
        concept = f"Concept {uuid4().hex[:8]}"
        past = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
        _, lesson_id, answers = _make_lesson(concepts=(concept,))
        item_id = next(iter(answers))
        client.post(f"/quiz/{item_id}/answer", json={"answer": answers[item_id]})
        client.post(f"/lessons/{lesson_id}/complete")
        session = SessionLocal()
        try:
            card = review.get_card(session, normalize_concept(concept))
            card.state = fsrs.REVIEW
            card.due = past
            card.last_review = past
            card.stability = 5.0
            card.difficulty = 5.0
            session.commit()
            return card.id, item_id, answers[item_id]
        finally:
            session.close()

    def test_the_queue_serves_a_question_without_its_answer(self, client):
        card_id, item_id, answer = self._due_card(client)
        body = client.get("/review/queue").json()
        assert body["due_total"] == 1
        card = body["cards"][0]
        assert card["card_id"] == card_id
        assert card["item"]["id"] == item_id
        assert answer not in str(card)
        assert [entry["name"] for entry in card["preview"]] == ["again", "hard", "good", "easy"]

    def test_answering_reveals_the_key_and_suggests_a_rating(self, client):
        card_id, item_id, answer = self._due_card(client)
        body = client.post(
            f"/review/cards/{card_id}/answer", json={"item_id": item_id, "answer": answer}
        ).json()
        assert body["correct"] is True
        assert body["expected"] == answer
        assert body["suggested_rating"] in fsrs.RATINGS

    def test_answering_records_a_review_source_attempt(self, client):
        card_id, item_id, answer = self._due_card(client)
        client.post(f"/review/cards/{card_id}/answer", json={"item_id": item_id, "answer": answer})
        session = SessionLocal()
        try:
            sources = [
                row.source
                for row in session.query(models.Attempt)
                .filter(models.Attempt.quiz_item_id == item_id)
                .order_by(models.Attempt.attempt_no)
            ]
        finally:
            session.close()
        assert sources == ["lesson_quiz", "review_session"]

    def test_a_second_answer_to_the_same_item_is_refused(self, client):
        """The answer response hands back the expected answer so the learner can judge
        their own recall. If a resubmit were accepted, answering wrong, reading the
        key and sending it back would be recorded as a clean recall, which defeats the
        retrieval test the card exists to run."""
        card_id, item_id, answer = self._due_card(client)

        first = client.post(
            f"/review/cards/{card_id}/answer",
            json={"item_id": item_id, "answer": "definitely wrong"},
        ).json()
        assert first["correct"] is False
        revealed = first["expected"]

        retry = client.post(
            f"/review/cards/{card_id}/answer",
            json={"item_id": item_id, "answer": revealed},
        )
        assert retry.status_code == 409

        session = SessionLocal()
        try:
            written = (
                session.query(models.Attempt)
                .filter(models.Attempt.quiz_item_id == item_id)
                .filter(models.Attempt.source == review.REVIEW_SESSION_SOURCE)
                .count()
            )
        finally:
            session.close()
        assert written == 1

        # The block is scoped to this exposure: once the card is rated and comes due
        # again, the same item is answerable, which is the point of spaced repetition.
        client.post(f"/review/cards/{card_id}/rate", json={"rating": fsrs.GOOD})
        again = client.post(
            f"/review/cards/{card_id}/answer", json={"item_id": item_id, "answer": answer}
        )
        assert again.status_code == 200

    def test_an_item_from_another_concept_is_rejected(self, client):
        card_id, _, _ = self._due_card(client)
        _, _, other = _make_lesson(concepts=("Something Else",))
        other_item = next(iter(other))
        resp = client.post(
            f"/review/cards/{card_id}/answer",
            json={"item_id": other_item, "answer": "whatever"},
        )
        assert resp.status_code == 400

    def test_rating_reschedules_the_card(self, client):
        card_id, _, _ = self._due_card(client)
        body = client.post(f"/review/cards/{card_id}/rate", json={"rating": fsrs.GOOD}).json()
        assert body["state"] == fsrs.REVIEW
        assert body["scheduled_days"] >= 1
        assert body["reps"] == 2

    def test_an_override_is_recorded_as_the_learner_s(self, client):
        card_id, _, _ = self._due_card(client)
        client.post(
            f"/review/cards/{card_id}/rate",
            json={"rating": fsrs.AGAIN, "suggested_rating": fsrs.GOOD},
        )
        log = _logs()[-1]
        assert log.rating == fsrs.AGAIN
        assert log.suggested_rating == fsrs.GOOD
        assert log.rating_source == "learner"

    def test_agreeing_with_the_suggestion_is_not_an_override(self, client):
        card_id, _, _ = self._due_card(client)
        client.post(
            f"/review/cards/{card_id}/rate",
            json={"rating": fsrs.GOOD, "suggested_rating": fsrs.GOOD},
        )
        assert _logs()[-1].rating_source == "derived"

    def test_an_out_of_range_rating_is_rejected(self, client):
        card_id, _, _ = self._due_card(client)
        assert client.post(f"/review/cards/{card_id}/rate", json={"rating": 9}).status_code == 400

    def test_unknown_cards_are_404(self, client):
        assert client.post("/review/cards/999999/rate", json={"rating": 3}).status_code == 404
        assert (
            client.post(
                "/review/cards/999999/answer", json={"item_id": 1, "answer": "x"}
            ).status_code
            == 404
        )
