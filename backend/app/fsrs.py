"""FSRS-6 scheduling, transcribed from py-fsrs.

Vendored (not depended on) from py-fsrs release v6.3.2, file `fsrs/scheduler.py`:
https://github.com/open-spaced-repetition/py-fsrs/blob/v6.3.2/src/fsrs/scheduler.py

Upstream is MIT licensed and that notice travels with the code:

    MIT License

    Copyright (c) 2022 Open Spaced Repetition

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

Why vendored: the algorithm is a page of arithmetic whose constants we need to
pin exactly, and pinning them here means a dependency bump can never silently
reschedule every card a learner already has.

Why this module is pure: no `app.*` imports, no database, no I/O, and no clock.
`now` is a required argument on every function that needs one, not a default, so
there is no code path where a test can accidentally schedule against wall time.
The database layer supplies the clock; this file only does arithmetic.

Fuzzing is deliberately absent rather than disabled. Upstream jitters each
interval by a few percent to spread reviews out; our UI shows the learner the
exact interval each button will produce before they press it, so a randomizer
existing at all is a promise waiting to be broken by whoever flips the flag.
"""

import hashlib
import math
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

AGAIN = 1
HARD = 2
GOOD = 3
EASY = 4
RATINGS = (AGAIN, HARD, GOOD, EASY)

NEW = "new"
LEARNING = "learning"
REVIEW = "review"
RELEARNING = "relearning"

FSRS_VERSION = "fsrs6"

# The 21 FSRS-6 default weights. Fitted upstream against a large review corpus;
# meaningless individually, so they are never edited by hand. Retraining them on
# this learner's own history is a later slice, and it must write a new fsrs_v and
# weights_hash rather than reinterpret rows scheduled under these.
WEIGHTS = (
    0.212,
    1.2931,
    2.3065,
    8.2956,
    6.4133,
    0.8334,
    3.0194,
    0.001,
    1.8722,
    0.1666,
    0.796,
    1.4835,
    0.0614,
    0.2629,
    1.6483,
    0.6014,
    1.8729,
    0.5425,
    0.0912,
    0.0658,
    0.1542,
)

# 0.90 is load-bearing beyond "how much do we want to remember". At exactly this
# retention the interval formula collapses to round(stability), which is what lets
# the UI say "stability 12 days" and "next in 12 days" and mean the same thing.
DESIRED_RETENTION = 0.90
MAXIMUM_INTERVAL = 365
LEARNING_STEPS = (timedelta(minutes=10),)
RELEARNING_STEPS = (timedelta(minutes=10),)

DECAY = -WEIGHTS[20]
FACTOR = 0.9 ** (1 / DECAY) - 1

STABILITY_MIN = 0.001
DIFFICULTY_MIN = 1.0
DIFFICULTY_MAX = 10.0


def weights_hash() -> str:
    """Short fingerprint of the active weights, stamped onto every card and log row.

    Without it, a future retrain leaves no way to tell which rows were scheduled
    under which parameters, and the history stops being reproducible.
    """
    digest = hashlib.sha256(",".join(repr(w) for w in WEIGHTS).encode()).hexdigest()
    return digest[:16]


WEIGHTS_HASH = weights_hash()


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def retrievability(stability: float, elapsed: int) -> float:
    """Probability of recall after `elapsed` whole days at this stability."""
    return (1 + FACTOR * elapsed / stability) ** DECAY


def interval_days(stability: float) -> int:
    """Days until recall probability decays to DESIRED_RETENTION, clamped to [1, 365]."""
    raw = (stability / FACTOR) * (DESIRED_RETENTION ** (1 / DECAY) - 1)
    return int(_clamp(round(raw), 1, MAXIMUM_INTERVAL))


def elapsed_days(last_review: datetime | None, now: datetime) -> int:
    """Whole days since the last review, truncated, never negative.

    The truncation is not a rounding convenience, it is part of the algorithm. The
    weights were fitted against integer day gaps, so feeding fractional days in
    shifts every stability update away from the fitted curve. A review 2 days 23
    hours 50 minutes later is 2 days, not 3.
    """
    if last_review is None:
        return 0
    return max(0, (now - last_review).days)


def initial_stability(rating: int) -> float:
    return WEIGHTS[rating - 1]


def _initial_difficulty_unclamped(rating: int) -> float:
    return WEIGHTS[4] - math.e ** (WEIGHTS[5] * (rating - 1)) + 1


def initial_difficulty(rating: int) -> float:
    return _clamp(_initial_difficulty_unclamped(rating), DIFFICULTY_MIN, DIFFICULTY_MAX)


def next_difficulty(difficulty: float, rating: int) -> float:
    """Update difficulty, with a mean reversion pull toward the Easy-rated baseline.

    The pull uses the UNCLAMPED initial difficulty for Easy (a negative number here),
    matching upstream. Clamping it first would change the reversion target.
    """
    delta = -(WEIGHTS[6] * (rating - 3))
    damped = (10 - difficulty) * delta / 9
    arg_2 = difficulty + damped
    arg_1 = _initial_difficulty_unclamped(EASY)
    return _clamp(WEIGHTS[7] * arg_1 + (1 - WEIGHTS[7]) * arg_2, DIFFICULTY_MIN, DIFFICULTY_MAX)


def short_term_stability(stability: float, rating: int) -> float:
    """Stability update for a same-day repeat, where retrievability is not yet meaningful."""
    increase = (math.e ** (WEIGHTS[17] * (rating - 3 + WEIGHTS[18]))) * (stability ** -WEIGHTS[19])
    if rating != AGAIN:
        increase = max(increase, 1.0)
    return max(stability * increase, STABILITY_MIN)


def recall_stability(
    difficulty: float, stability: float, recall_probability: float, rating: int
) -> float:
    """Stability after a successful recall. Lower retrievability means a bigger gain."""
    hard_penalty = WEIGHTS[15] if rating == HARD else 1
    easy_bonus = WEIGHTS[16] if rating == EASY else 1
    return stability * (
        1
        + (math.e ** WEIGHTS[8])
        * (11 - difficulty)
        * (stability ** -WEIGHTS[9])
        * ((math.e ** ((1 - recall_probability) * WEIGHTS[10])) - 1)
        * hard_penalty
        * easy_bonus
    )


def forget_stability(difficulty: float, stability: float, recall_probability: float) -> float:
    """Stability after a lapse. Never above what a same-day Again would have produced."""
    long_term = (
        WEIGHTS[11]
        * (difficulty ** -WEIGHTS[12])
        * (((stability + 1) ** WEIGHTS[13]) - 1)
        * (math.e ** ((1 - recall_probability) * WEIGHTS[14]))
    )
    short_term = stability / (math.e ** (WEIGHTS[17] * WEIGHTS[18]))
    return min(long_term, short_term)


def next_stability(
    difficulty: float, stability: float, recall_probability: float, rating: int
) -> float:
    if rating == AGAIN:
        value = forget_stability(difficulty, stability, recall_probability)
    else:
        value = recall_stability(difficulty, stability, recall_probability, rating)
    return max(value, STABILITY_MIN)


@dataclass
class Card:
    """The scheduler's view of one card. Mirrors the persisted ReviewCard columns.

    stability and difficulty are both None exactly while state is "new". One set and
    the other not is a corrupted row, not a state this module can schedule from.
    """

    state: str = NEW
    stability: float | None = None
    difficulty: float | None = None
    due: datetime | None = None
    last_review: datetime | None = None
    reps: int = 0
    lapses: int = 0
    step: int = 0


@dataclass
class Review:
    """The outcome of rating a card: the new card, plus what the log row needs.

    `card` is a new object. `review()` never mutates its argument, which is what makes
    running it four times for a preview safe.
    """

    card: Card
    rating: int
    elapsed_days: int
    retrievability: float | None
    interval: timedelta
    scheduled_days: int


def review(card: Card, rating: int, now: datetime) -> Review:
    """Apply one rating and return the resulting card.

    `now` is required, not defaulted, so scheduling can never silently read the clock.
    """
    if rating not in RATINGS:
        raise ValueError(f"rating must be one of {RATINGS}, got {rating!r}")

    elapsed = elapsed_days(card.last_review, now)
    recall_probability = None if card.stability is None else retrievability(card.stability, elapsed)

    if card.stability is None or card.difficulty is None:
        stability = initial_stability(rating)
        difficulty = initial_difficulty(rating)
    elif elapsed < 1:
        # Same-day repeat: retrievability has barely moved, so the short-term curve
        # applies. Difficulty still updates, because the rating is still evidence.
        stability = short_term_stability(card.stability, rating)
        difficulty = next_difficulty(card.difficulty, rating)
    else:
        # Difficulty is read before it is written: upstream feeds the pre-review
        # difficulty into the stability update, then advances it.
        stability = next_stability(card.difficulty, card.stability, recall_probability, rating)
        difficulty = next_difficulty(card.difficulty, rating)

    state = card.state
    step = card.step
    lapses = card.lapses

    # A brand new card is upstream's learning-step-0 card under a different name, so
    # it takes the learning branch. That is what makes new + Again persist as
    # "learning" instead of leaving the card looking untouched.
    if state == NEW:
        state, step = LEARNING, 0

    if state in (LEARNING, RELEARNING):
        steps = LEARNING_STEPS if state == LEARNING else RELEARNING_STEPS
        if rating == AGAIN:
            step = 0
            interval = steps[step]
        elif rating == HARD:
            if step == 0 and len(steps) == 1:
                interval = steps[0] * 1.5
            elif step == 0 and len(steps) >= 2:
                interval = (steps[0] + steps[1]) / 2
            else:
                interval = steps[step]
        elif rating == GOOD:
            if step + 1 == len(steps):
                state, step = REVIEW, 0
                interval = timedelta(days=interval_days(stability))
            else:
                step += 1
                interval = steps[step]
        else:
            state, step = REVIEW, 0
            interval = timedelta(days=interval_days(stability))
    elif rating == AGAIN:
        # The only path that counts as a lapse: the learner had graduated the card
        # to review and lost it. Failing a learning step is not forgetting, it is
        # not having learned it yet.
        state, step = RELEARNING, 0
        lapses += 1
        interval = RELEARNING_STEPS[0]
    else:
        interval = timedelta(days=interval_days(stability))

    return Review(
        card=Card(
            state=state,
            stability=stability,
            difficulty=difficulty,
            due=now + interval,
            last_review=now,
            reps=card.reps + 1,
            lapses=lapses,
            step=step,
        ),
        rating=rating,
        elapsed_days=elapsed,
        retrievability=recall_probability,
        interval=interval,
        scheduled_days=interval.days,
    )


def preview(card: Card, now: datetime) -> dict[int, Review]:
    """What each of the four ratings would do to this card, keyed by rating.

    This runs the real `review()` on a copy per rating rather than reimplementing the
    interval arithmetic. A second implementation would be a second source of truth,
    and the button labels would eventually disagree with what pressing them does.
    """
    return {rating: review(replace(card), rating, now) for rating in RATINGS}
