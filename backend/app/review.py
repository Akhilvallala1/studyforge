"""Scheduling as a persisted thing: cards, ratings, and the counts the UI reads.

app/fsrs.py is pure arithmetic and app/rating.py is a pure policy. Neither touches a
database, which is what makes them testable. This module is the only place the two
meet SQLAlchemy, so every write to review_cards and review_logs goes through one
function and the log can never drift out of step with the card it describes.

Timezone discipline, which is the trap this module exists to contain: SQLite drops
tzinfo, so every datetime read back is naive UTC, while models.utcnow() returns an
aware one. Subtracting one from the other raises TypeError, and doing it inside the
scheduler would surface as a 500 on a review submission. So every datetime crossing
into fsrs or into a query is forced through _naive_utc first, and everything stored
is naive UTC. app/days.py owns the separate question of when a local day starts.
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app import days, fsrs, models
from app.attempts import LESSON_QUIZ_SOURCE
from app.concepts import normalize_concept
from app.rating import RATING_VERSION, CardRating, rating_v1

logger = logging.getLogger("studyforge.review")

REVIEW_SESSION_SOURCE = "review_session"

DERIVED = "derived"
LEARNER = "learner"

# Mastery thresholds in days of stability. Stability is "days until recall drops to
# 90%", so these read as plain claims: solid survives a week untouched, mastered
# survives three. They are round numbers chosen to be explainable rather than tuned,
# and they live here so the concept map and any future copy agree on one definition.
SOLID_STABILITY_DAYS = 7.0
MASTERED_STABILITY_DAYS = 21.0
# A card can carry high stability and still be forgotten if it was left far past due.
# Bucketing on stability alone would paint those green, so current recall probability
# gets a veto.
MASTERY_MIN_RETRIEVABILITY = 0.80

NOT_STARTED = "not_started"
SHAKY = "shaky"
SOLID = "solid"
MASTERED = "mastered"

# "Concepts you have missed more than once", per the Today screen. Two lapses inside
# the last five ratings, so a single bad day does not flag a concept the learner knows.
ATTENTION_WINDOW = 5
ATTENTION_LAPSES = 2

RETENTION_WINDOW_DAYS = 30
# Below this many reviews, a retention percentage is noise wearing a number's clothes:
# two reviews can only ever read 0%, 50%, or 100%, and it would swing wildly day to
# day. Callers get None and the UI shows a dash.
RETENTION_MIN_SAMPLE = 10

# Fallback seconds per card for the session estimate, used until the learner has
# enough timed reviews of their own to measure.
DEFAULT_SECONDS_PER_CARD = 30.0
DURATION_SAMPLE_SIZE = 200
DURATION_MIN_SAMPLE = 20

DEFAULT_QUEUE_LIMIT = 50


def _naive_utc(moment: datetime) -> datetime:
    """Coerce any datetime to the naive-UTC shape every stored timestamp has."""
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(UTC).replace(tzinfo=None)


def now_utc() -> datetime:
    return _naive_utc(models.utcnow())


# --------------------------------------------------------------------------
# Cards
# --------------------------------------------------------------------------


def to_scheduler_card(row: models.ReviewCard) -> fsrs.Card:
    """The scheduler's view of a persisted card."""
    return fsrs.Card(
        state=row.state,
        stability=row.stability,
        difficulty=row.difficulty,
        due=row.due,
        last_review=row.last_review,
        reps=row.reps,
        lapses=row.lapses,
        step=row.step,
    )


def get_card(session: Session, concept_key: str) -> models.ReviewCard | None:
    if not concept_key:
        return None
    return (
        session.query(models.ReviewCard)
        .filter(models.ReviewCard.concept_key == concept_key)
        .one_or_none()
    )


def _get_or_create_card(
    session: Session, concept_key: str, concept_label: str
) -> models.ReviewCard:
    """Fetch the card for a concept, creating an unscheduled one if it is new.

    Only record_review calls this, so a card row never exists in the "new" state for
    longer than the transaction that rates it. That keeps "has a card" and "has been
    studied" the same question, which is what the concept map's not-started bucket
    relies on.
    """
    row = get_card(session, concept_key)
    if row is not None:
        # The label can improve when a later lesson writes a better-cased version of
        # the same normalized key. The key never changes; only the display name does.
        if concept_label and not row.concept_label:
            row.concept_label = concept_label
        return row
    row = models.ReviewCard(
        concept_key=concept_key,
        concept_label=concept_label or concept_key,
        state=fsrs.NEW,
        fsrs_v=fsrs.FSRS_VERSION,
        weights_hash=fsrs.WEIGHTS_HASH,
    )
    session.add(row)
    session.flush()
    return row


def record_review(
    session: Session,
    concept_key: str,
    concept_label: str,
    rating: int,
    *,
    now: datetime | None = None,
    suggested_rating: int | None = None,
    rating_source: str = DERIVED,
    rating_v: str = RATING_VERSION,
    attempt_ids: list[int] | None = None,
    items_correct: int = 0,
    items_total: int = 0,
    duration_ms: int | None = None,
) -> models.ReviewLog:
    """Apply one rating to one concept's card and append the log row for it.

    The only writer of review_cards and review_logs. The card update and its log row
    are built from the same fsrs.Review result rather than recomputed separately, so
    stability_after on the log is by construction the stability on the card.

    Does not commit. The caller owns the transaction, because grading a lesson applies
    several ratings and a partial commit would leave some concepts scheduled and
    others not.
    """
    if rating not in fsrs.RATINGS:
        raise ValueError(f"rating must be one of {fsrs.RATINGS}, got {rating!r}")

    moment = now_utc() if now is None else _naive_utc(now)
    card_row = _get_or_create_card(session, concept_key, concept_label)

    before = to_scheduler_card(card_row)
    result = fsrs.review(before, rating, moment)
    after = result.card

    card_row.state = after.state
    card_row.stability = after.stability
    card_row.difficulty = after.difficulty
    card_row.due = after.due
    card_row.last_review = after.last_review
    card_row.reps = after.reps
    card_row.lapses = after.lapses
    card_row.step = after.step
    card_row.fsrs_v = fsrs.FSRS_VERSION
    card_row.weights_hash = fsrs.WEIGHTS_HASH

    log = models.ReviewLog(
        card_id=card_row.id,
        reviewed_at=moment,
        rating=rating,
        suggested_rating=rating if suggested_rating is None else suggested_rating,
        rating_source=rating_source,
        rating_v=rating_v,
        state_before=before.state,
        stability_before=before.stability,
        difficulty_before=before.difficulty,
        elapsed_days=float(result.elapsed_days),
        state_after=after.state,
        stability_after=after.stability,
        difficulty_after=after.difficulty,
        scheduled_days=result.scheduled_days,
        due_after=after.due,
        attempt_ids=list(attempt_ids or []),
        items_correct=items_correct,
        items_total=items_total,
        duration_ms=duration_ms,
        fsrs_v=fsrs.FSRS_VERSION,
        weights_hash=fsrs.WEIGHTS_HASH,
    )
    session.add(log)
    session.flush()
    return log


# --------------------------------------------------------------------------
# Seeding cards from a finished lesson quiz
# --------------------------------------------------------------------------


def _exposure_attempts(
    session: Session, lesson_id: int, since: datetime | None
) -> list[models.Attempt]:
    """Lesson-quiz attempts for this lesson that the card has not been rated on yet.

    `since` is the card's last_review, which is what makes grading idempotent without
    a session id on the attempt row: work already folded into the card is older than
    that timestamp and is skipped. Completing a lesson twice therefore rates nothing
    the second time, and reopening a lesson to redo it rates only the new answers.
    """
    query = (
        session.query(models.Attempt)
        .filter(models.Attempt.lesson_id == lesson_id)
        .filter(models.Attempt.source == LESSON_QUIZ_SOURCE)
    )
    if since is not None:
        query = query.filter(models.Attempt.created_at > since)
    return query.order_by(models.Attempt.attempt_no).all()


def grade_lesson(
    session: Session, lesson: models.Lesson, now: datetime | None = None
) -> list[models.ReviewLog]:
    """Turn a finished lesson quiz into scheduled cards, one per concept.

    This is the seed path: it is how a concept enters the review system at all. The
    lesson quiz has no rating buttons, so the rating is derived from the attempt rows
    by rating_v1, and several items testing one concept collapse into a single rating
    because the card is the concept, not the question.

    Called on lesson completion rather than on each answer. Completion is a boundary
    the learner chose, and grading mid-quiz would schedule a concept off a half-
    finished attempt.
    """
    moment = now_utc() if now is None else _naive_utc(now)
    items = {item.id: item for item in lesson.quiz_items}
    if not items:
        return []

    by_concept: dict[str, str] = {}
    for item in lesson.quiz_items:
        key = normalize_concept(item.concept)
        if key:
            by_concept.setdefault(key, item.concept or key)

    # One query for every card and one for every attempt, then group in Python. Doing
    # it per concept cost three queries each, which grows with the size of the lesson.
    cards = {
        row.concept_key: row
        for row in session.query(models.ReviewCard)
        .filter(models.ReviewCard.concept_key.in_(list(by_concept)))
        .all()
    }
    all_attempts = _exposure_attempts(session, lesson.id, None)
    by_key: dict[str, list[models.Attempt]] = defaultdict(list)
    for attempt in all_attempts:
        by_key[attempt.concept_key].append(attempt)

    logs: list[models.ReviewLog] = []
    for concept_key, concept_label in by_concept.items():
        card_row = cards.get(concept_key)
        # The exposure window is per card: a concept already reviewed is graded only
        # on attempts made since, so recompleting a lesson cannot re-grade old answers.
        since = card_row.last_review if card_row is not None else None
        scoped = [a for a in by_key[concept_key] if since is None or a.created_at > since]
        if not scoped:
            continue

        derived: CardRating = rating_v1(scoped, items)
        if derived.rating is None:
            continue

        durations = [a.elapsed_ms for a in scoped if a.elapsed_ms is not None]
        logs.append(
            record_review(
                session,
                concept_key,
                concept_label,
                derived.rating,
                now=moment,
                suggested_rating=derived.rating,
                rating_source=DERIVED,
                rating_v=derived.rating_v,
                attempt_ids=[a.id for a in scoped],
                items_correct=sum(1 for g in derived.items if g.correct),
                items_total=len(derived.items),
                duration_ms=sum(durations) if durations else None,
            )
        )
    return logs


# --------------------------------------------------------------------------
# Queue and previews
# --------------------------------------------------------------------------


def already_answered_this_exposure(
    session: Session, card: models.ReviewCard, item: models.QuizItem
) -> bool:
    """Has this item already been answered since the card was last reviewed?

    A review is a retrieval test, and the answer endpoint returns the expected answer
    so the learner can judge their own recall. Those two facts together mean a second
    submission must be refused: otherwise the learner reads the key and resubmits it,
    and a failed recall is recorded as a clean one.

    Scoped to the current exposure rather than to all time, so the same question is
    answerable again the next time the concept comes due, which is the entire point of
    spaced repetition.
    """
    query = (
        session.query(models.Attempt.id)
        .filter(models.Attempt.quiz_item_id == item.id)
        .filter(models.Attempt.source == REVIEW_SESSION_SOURCE)
    )
    if card.last_review is not None:
        query = query.filter(models.Attempt.created_at > card.last_review)
    return session.query(query.exists()).scalar() or False


def card_retrievability(row: models.ReviewCard, now: datetime) -> float | None:
    """Current recall probability, or None for a card that has never been scheduled."""
    if row.stability is None or row.last_review is None:
        return None
    return fsrs.retrievability(row.stability, fsrs.elapsed_days(row.last_review, _naive_utc(now)))


def due_cards(session: Session, now: datetime | None = None) -> list[models.ReviewCard]:
    """Every card due at or before `now`, hardest-to-recall first.

    Ordering is by ascending retrievability rather than by due date, and that choice
    matters whenever there is a backlog. Among forty overdue cards the ones about to
    be forgotten are worth more than the ones that merely came due first, and FSRS
    already tells us which is which. Learning and relearning cards come first
    regardless: they are mid-acquisition, where a delay costs the most.

    Sorted in Python because the retrievability formula is a fractional power that
    SQLite has no operator for. The due filter runs in SQL against ix_review_cards_due,
    so only the cards actually due are ever loaded.
    """
    moment = now_utc() if now is None else _naive_utc(now)
    rows = (
        session.query(models.ReviewCard)
        .filter(models.ReviewCard.due.isnot(None))
        .filter(models.ReviewCard.due <= moment)
        .all()
    )

    def sort_key(row: models.ReviewCard) -> tuple[int, float, datetime]:
        mid_acquisition = 0 if row.state in (fsrs.LEARNING, fsrs.RELEARNING) else 1
        recall = card_retrievability(row, moment)
        return (mid_acquisition, 1.0 if recall is None else recall, row.due)

    return sorted(rows, key=sort_key)


def format_interval(interval: timedelta) -> str:
    """Human label for a scheduled gap, matching the review screen's button captions.

    Sub-day gaps render as "< N min" rather than "N min" because that is what actually
    happens: the card's stored due time is N minutes out, but the session queue brings
    it back within the same sitting, several cards later. Saying "10 min" would promise
    a wait the learner never experiences.
    """
    total_minutes = interval.total_seconds() / 60
    if interval < timedelta(days=1):
        return f"< {max(1, round(total_minutes))} min"
    day_count = interval.days
    if day_count < 30:
        return f"{day_count} day" + ("" if day_count == 1 else "s")
    months = round(day_count / 30)
    return f"{months} month" + ("" if months == 1 else "s")


def preview(row: models.ReviewCard, now: datetime | None = None) -> list[dict]:
    """What each of the four buttons would do to this card, in rating order.

    The review screen prints these next to the buttons before the learner picks one,
    so they have to be exactly what pressing the button produces. Two things make that
    true: fsrs.preview runs the real transition rather than a parallel estimate, and
    the scheduler has no fuzz, so the same rating on the same card is always the same
    interval.
    """
    moment = now_utc() if now is None else _naive_utc(now)
    outcomes = fsrs.preview(to_scheduler_card(row), moment)
    names = {fsrs.AGAIN: "again", fsrs.HARD: "hard", fsrs.GOOD: "good", fsrs.EASY: "easy"}
    return [
        {
            "rating": rating,
            "name": names[rating],
            "interval_minutes": round(outcomes[rating].interval.total_seconds() / 60),
            "interval_days": outcomes[rating].scheduled_days,
            "label": format_interval(outcomes[rating].interval),
            "state": outcomes[rating].card.state,
        }
        for rating in fsrs.RATINGS
    ]


def concept_item_index(session: Session) -> dict[str, list[models.QuizItem]]:
    """Every quiz item grouped by the concept it tests, in one query.

    Concept keys are global by design, so a concept met in two courses draws review
    questions from both. That is the payoff for one card per concept rather than one
    per course.

    Grouped in Python because quiz_items stores the raw label and the grouping key is
    normalize_concept() of it, which SQLite cannot compute or index. Built once per
    request and passed down: doing it per card turned a queue render into one full
    scan of quiz_items per card.
    """
    index: dict[str, list[models.QuizItem]] = defaultdict(list)
    for item in session.query(models.QuizItem).filter(models.QuizItem.concept != "").all():
        key = normalize_concept(item.concept)
        if key:
            index[key].append(item)
    return index


def pick_items(
    session: Session,
    concept_keys: list[str],
    index: dict[str, list[models.QuizItem]] | None = None,
) -> dict[str, models.QuizItem]:
    """Choose which question to ask for each concept: the one asked least recently.

    Rotating through a concept's items stops a card from decaying into one memorized
    string. Items never asked come first, since an unseen question is the strongest
    test of the concept rather than of the answer.

    Two queries total regardless of how many concepts are asked for, which is what
    keeps rendering a fifty card queue from being a hundred round trips.
    """
    index = concept_item_index(session) if index is None else index
    candidates = {key: index.get(key, []) for key in concept_keys}
    item_ids = [item.id for items in candidates.values() for item in items]
    if not item_ids:
        return {}

    last_seen = dict(
        session.query(models.Attempt.quiz_item_id, func.max(models.Attempt.created_at))
        .filter(models.Attempt.quiz_item_id.in_(item_ids))
        .group_by(models.Attempt.quiz_item_id)
        .all()
    )

    chosen: dict[str, models.QuizItem] = {}
    for key, items in candidates.items():
        if not items:
            continue
        # Partitioned rather than sorted with a sentinel date, so a "never asked" item
        # is never compared against a timestamp. id breaks ties, making the choice
        # stable rather than dependent on row order.
        unseen = [item for item in items if item.id not in last_seen]
        if unseen:
            chosen[key] = min(unseen, key=lambda item: item.id)
        else:
            chosen[key] = min(items, key=lambda item: (last_seen[item.id], item.id))
    return chosen


# --------------------------------------------------------------------------
# Dashboard queries
# --------------------------------------------------------------------------


def due_counts(session: Session, now: datetime | None = None) -> dict:
    """Cards due by the end of today, and by the end of the next seven days.

    Both include everything already overdue, because a card that slipped is still due.
    "This week" is therefore never smaller than "today", which the dashboard relies on.
    Day ends come from app/days.py, so both respect the 04:00 local boundary rather
    than splitting a late-night session across two days.
    """
    moment = now_utc() if now is None else _naive_utc(now)
    _, today_end = days.day_bounds(now=moment)
    week_end = today_end + timedelta(days=6)

    def count_before(limit: datetime) -> int:
        return (
            session.query(func.count(models.ReviewCard.id))
            .filter(models.ReviewCard.due.isnot(None))
            .filter(models.ReviewCard.due < limit)
            .scalar()
            or 0
        )

    return {"due_today": count_before(today_end), "due_this_week": count_before(week_end)}


def retention(session: Session, now: datetime | None = None) -> dict:
    """Share of genuinely due reviews the learner still remembered, over 30 days.

    Every filter here is load-bearing. state_before == "review" drops learning and
    relearning steps, and elapsed_days >= 1 drops same-day repeats; both are near
    certain successes minutes apart, and counting them drags the figure toward 100%
    where it stops meaning anything. A rating above Again counts as remembered, so
    Hard passes: recalling something with effort is still recalling it.
    """
    moment = now_utc() if now is None else _naive_utc(now)
    cutoff = moment - timedelta(days=RETENTION_WINDOW_DAYS)

    rows = (
        session.query(models.ReviewLog.rating)
        .filter(models.ReviewLog.reviewed_at >= cutoff)
        .filter(models.ReviewLog.state_before == fsrs.REVIEW)
        .filter(models.ReviewLog.elapsed_days >= 1)
        .all()
    )
    total = len(rows)
    if total < RETENTION_MIN_SAMPLE:
        return {"retention": None, "sample_size": total}
    retained = sum(1 for (rating,) in rows if rating > fsrs.AGAIN)
    return {"retention": retained / total, "sample_size": total}


def day_streak(session: Session, now: datetime | None = None) -> int:
    """Consecutive study days ending today, or ending yesterday if today is untouched.

    The yesterday fallback is the point. Counting only from today would show a learner
    on a twelve day streak a zero every morning until they sat down, which is both
    wrong and discouraging: the streak is alive, it just has not been extended yet.

    Any review counts, including one derived from finishing a lesson quiz, so a day
    spent on new material keeps the streak.
    """
    moment = now_utc() if now is None else _naive_utc(now)
    # Bounded scan: a streak longer than this is not a problem this product has, and
    # an unbounded one would read every log row the learner has ever written.
    horizon = moment - timedelta(days=400)
    stamps = (
        session.query(models.ReviewLog.reviewed_at)
        .filter(models.ReviewLog.reviewed_at >= horizon)
        .all()
    )
    studied = {days.today_key(stamp) for (stamp,) in stamps}
    if not studied:
        return 0

    cursor = days.day_start(moment).date()
    if cursor.isoformat() not in studied:
        cursor -= timedelta(days=1)

    streak = 0
    while cursor.isoformat() in studied:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def seconds_per_card(session: Session) -> float:
    """Median seconds the learner spends on a review card, for the session estimate.

    This is what elapsed_ms is genuinely good for. It is too noisy and too often null
    to drive scheduling, but a median over a couple of hundred answers is a perfectly
    honest basis for telling someone a session will take about nine minutes.
    """
    rows = (
        session.query(models.Attempt.elapsed_ms)
        .filter(models.Attempt.source == REVIEW_SESSION_SOURCE)
        .filter(models.Attempt.elapsed_ms.isnot(None))
        .order_by(models.Attempt.id.desc())
        .limit(DURATION_SAMPLE_SIZE)
        .all()
    )
    samples = sorted(value for (value,) in rows)
    if len(samples) < DURATION_MIN_SAMPLE:
        return DEFAULT_SECONDS_PER_CARD
    middle = len(samples) // 2
    if len(samples) % 2:
        median_ms = float(samples[middle])
    else:
        median_ms = (samples[middle - 1] + samples[middle]) / 2
    return median_ms / 1000


def estimated_minutes(session: Session, card_count: int) -> int:
    return max(1, round(card_count * seconds_per_card(session) / 60)) if card_count else 0


# --------------------------------------------------------------------------
# Mastery and attention
# --------------------------------------------------------------------------


def mastery_bucket(row: models.ReviewCard | None, now: datetime | None = None) -> str:
    """Which concept-map colour this card earns.

    Note what is missing: there is no "locked" bucket, because nothing in the data
    model records concept prerequisites yet. Lesson.concepts is a flat list with no
    edges. Inventing a lock from lesson order would gate content on an ordering the
    course author never asserted, so until a real prerequisite graph exists, no
    concept is ever reported locked.
    """
    if row is None or row.state == fsrs.NEW or row.stability is None:
        return NOT_STARTED
    moment = now_utc() if now is None else _naive_utc(now)
    recall = card_retrievability(row, moment)
    if row.state != fsrs.REVIEW:
        return SHAKY
    if recall is not None and recall < MASTERY_MIN_RETRIEVABILITY:
        return SHAKY
    if row.stability >= MASTERED_STABILITY_DAYS:
        return MASTERED
    if row.stability >= SOLID_STABILITY_DAYS:
        return SOLID
    return SHAKY


def _recent_ratings(session: Session, card_ids: list[int]) -> dict[int, list[int]]:
    """The last few ratings per card, newest first, in one query rather than N."""
    if not card_ids:
        return {}
    rows = (
        session.query(models.ReviewLog.card_id, models.ReviewLog.rating, models.ReviewLog.id)
        .filter(models.ReviewLog.card_id.in_(card_ids))
        .order_by(models.ReviewLog.card_id, models.ReviewLog.id.desc())
        .all()
    )
    grouped: dict[int, list[int]] = defaultdict(list)
    for card_id, rating, _ in rows:
        if len(grouped[card_id]) < ATTENTION_WINDOW:
            grouped[card_id].append(rating)
    return grouped


def needs_attention(session: Session, now: datetime | None = None) -> list[dict]:
    """Concepts the learner keeps losing: two or more lapses in the last five ratings.

    Deliberately triggered on the lapse pattern rather than on FSRS difficulty. The
    difficulty parameter is a latent value that drifts on every review including
    successful ones, so a threshold on it fires at moments the learner cannot connect
    to anything they did. "You missed this 3 of the last 4 times" is a claim they can
    check against their own memory, and it is what the screen already says.
    """
    moment = now_utc() if now is None else _naive_utc(now)
    cards = {row.id: row for row in session.query(models.ReviewCard).all()}
    ratings = _recent_ratings(session, list(cards))

    flagged = []
    for card_id, recent in ratings.items():
        misses = sum(1 for rating in recent if rating == fsrs.AGAIN)
        if misses < ATTENTION_LAPSES:
            continue
        row = cards[card_id]
        flagged.append(
            {
                "concept_key": row.concept_key,
                "concept_label": row.concept_label,
                "missed": misses,
                "of": len(recent),
                "retrievability": card_retrievability(row, moment),
                "lapses": row.lapses,
                # Carried rather than looked up again by the caller: the card is
                # already in hand here, and re-fetching it per flagged concept was an
                # N+1 on a list the dashboard renders on every load.
                "due": row.due,
                "is_due": row.due is not None and row.due <= moment,
            }
        )
    flagged.sort(key=lambda entry: (-entry["missed"], entry["concept_label"]))
    return flagged


def course_concepts(session: Session, course: models.Course, now: datetime | None = None) -> list[dict]:
    """Every concept in a course with its mastery bucket, for the concept map.

    A Python join, not a SQL one: the concepts live in Lesson.concepts, a JSON column
    SQLite cannot index into, and review_cards has no course id because concepts are
    global. The lessons and their quiz items are pulled in one eager query rather than
    lazy-loading per lesson, which otherwise costs a query per lesson and grows with
    the size of the course. Card lookups are chunked against SQLite's parameter limit.
    """
    moment = now_utc() if now is None else _naive_utc(now)
    lessons = (
        session.query(models.Lesson)
        .join(models.Module)
        .filter(models.Module.course_id == course.id)
        .options(selectinload(models.Lesson.quiz_items))
        .all()
    )

    labels: dict[str, str] = {}
    for lesson in lessons:
        for raw in lesson.concepts or []:
            key = normalize_concept(raw if isinstance(raw, str) else "")
            if key:
                labels.setdefault(key, raw)
        for item in lesson.quiz_items:
            key = normalize_concept(item.concept)
            if key:
                labels.setdefault(key, item.concept)

    cards: dict[str, models.ReviewCard] = {}
    keys = list(labels)
    chunk = 500
    for start in range(0, len(keys), chunk):
        rows = (
            session.query(models.ReviewCard)
            .filter(models.ReviewCard.concept_key.in_(keys[start : start + chunk]))
            .all()
        )
        cards.update({row.concept_key: row for row in rows})

    result = []
    for key, label in sorted(labels.items()):
        row = cards.get(key)
        result.append(
            {
                "concept_key": key,
                "concept_label": label,
                "bucket": mastery_bucket(row, moment),
                "stability": None if row is None else row.stability,
                "retrievability": None if row is None else card_retrievability(row, moment),
                "due": None if row is None else row.due,
                "lapses": 0 if row is None else row.lapses,
            }
        )
    return result
