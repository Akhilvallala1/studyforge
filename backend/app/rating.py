"""Deriving an FSRS rating from what the learner actually did.

FSRS wants one of four self-reported ratings per card. Asking a learner to
self-report is asking them to grade their own memory, which they are famously bad
at, so we derive the rating from the attempt rows instead: right or wrong, how many
tries, and how long it took.

Versioning is the point of the name. rating_v1 is frozen. If the policy changes,
add rating_v2 and leave this function alone: every review_logs row records the
rating_v it was derived under, and editing v1 in place would silently reinterpret
history that was scheduled by different rules. The stored rating stays what it was;
only new reviews get the new derivation.

Pure by construction: it takes attempt rows and quiz items, never a Session, so the
policy can be tested exhaustively without a database.
"""

from dataclasses import dataclass, field

from app.attempts import _attempt_state
from app.fsrs import AGAIN, EASY, GOOD, HARD

RATING_VERSION = "v1"
RATING_SOURCE = "derived"

# Provisional constants. These are a reading-speed model, not measurements: roughly
# 200 words per minute of technical prose, a beat to think, and a typing rate for
# short answers. They are deliberately crude because the thing they gate (Easy versus
# Good) costs the learner a few extra minutes when wrong, never a forgotten concept.
#
# Empirical upgrade path: once this learner has 200 or more first-try-correct attempts
# with a non-null elapsed_ms, replace the fixed EASY_SPEED_FRACTION with their own
# 25th percentile of (elapsed_ms / answer_budget_ms). That calibrates "fast" against
# how fast this person actually is rather than against an invented reader, and it
# ships as rating_v2, not as an edit here.
READ_MS_PER_CHAR = 60
TYPE_MS_PER_CHAR = 270
THINK_MS = 2000
MCQ_SELECT_MS = 1500
SHORT_ANSWER_MS = 2000
EASY_SPEED_FRACTION = 0.6


def answer_budget_ms(item) -> int:
    """How long a fluent answer to this item should plausibly take, in milliseconds.

    A per-item budget rather than one global threshold, because a 30-character
    multiple choice question and a 400-character question with a typed answer are
    not the same task, and a fixed threshold would call the first one slow and the
    second one instant.
    """
    read_chars = len(item.question or "") + sum(len(option or "") for option in (item.options or []))
    if item.kind == "mcq":
        produce_ms = MCQ_SELECT_MS
    else:
        produce_ms = SHORT_ANSWER_MS + TYPE_MS_PER_CHAR * len(item.answer or "")
    return THINK_MS + READ_MS_PER_CHAR * read_chars + produce_ms


def is_fast(item, elapsed_ms: int | None) -> bool:
    """True only with positive evidence of speed.

    A missing elapsed_ms is not a slow answer and not a fast one. It resolves to
    Good, never Easy: absence of evidence is not evidence of fluency, and Easy is
    the rating that pushes the next review furthest away.
    """
    if elapsed_ms is None:
        return False
    return elapsed_ms <= EASY_SPEED_FRACTION * answer_budget_ms(item)


@dataclass
class ItemGrade:
    """One quiz item's contribution to a card's rating, with the inputs that produced it."""

    quiz_item_id: int
    rating: int
    correct: bool
    tries: int
    elapsed_ms: int | None
    budget_ms: int
    fast: bool


@dataclass
class CardRating:
    """The rating for one card, plus the per-item grades it collapsed from.

    rating is None when no attempt in this exposure touched a known item, which means
    there is nothing to schedule from. Callers must not record a review for it.
    """

    rating: int | None
    rating_v: str = RATING_VERSION
    items: list[ItemGrade] = field(default_factory=list)


def grade_item(attempts, item) -> ItemGrade:
    """Grade one item from this exposure's attempts on it.

    "First try" here means first try of THIS exposure, which is not Attempt.attempt_no:
    that counts every touch of the item across every source and every session, so a
    concept reviewed correctly for the fourth time would look like a fourth-try guess.
    The count comes from _attempt_state, the same summary the lesson quiz UI reads, so
    there is one definition of "a lesson quiz try" rather than two that can drift.

    Review sessions allow exactly one try per item, so tries is never above 1 on that
    path and Hard is unreachable from it. Hard exists for the lesson-quiz seed path,
    where the learner may retry until they get it.
    """
    state = _attempt_state(list(attempts))
    tries = state["attempts"]
    correct = state["ever_correct"]

    scoring = next((a for a in attempts if a.correct), None)
    elapsed_ms = scoring.elapsed_ms if scoring is not None else None
    budget_ms = answer_budget_ms(item)
    fast = correct and is_fast(item, elapsed_ms)

    if not correct:
        rating = AGAIN
    elif tries > 1:
        rating = HARD
    else:
        # Derivation stops at Good and never reaches Easy, deliberately.
        #
        # Easy applies the w16 bonus (1.87x) to the stability increment, so a wrong
        # Easy is a silently over-long gap and a concept the learner loses without
        # warning. A wrong Good costs a few minutes of reviewing something known.
        # When one direction of error is that much cheaper, take it.
        #
        # The evidence for Easy is also weak where derivation runs. elapsed_ms is
        # optional on the request and discarded when implausible, so identical
        # knowledge would schedule differently depending on whether the browser
        # reported a number. On a multiple-choice item, fast and correct is
        # confounded with recognition and with guessing, and recognition is not what
        # is being scheduled.
        #
        # Easy stays reachable where the evidence is good: the learner presses it in
        # a review session, having just seen whether they truly recalled it. Timing
        # still earns its keep in the session-length estimate.
        rating = GOOD

    return ItemGrade(
        quiz_item_id=item.id,
        rating=rating,
        correct=correct,
        tries=tries,
        elapsed_ms=elapsed_ms,
        budget_ms=budget_ms,
        fast=fast,
    )


def rating_v1(attempts, items) -> CardRating:
    """Derive one card's FSRS rating from the attempts in this exposure.

    `attempts` is the attempt rows for this exposure; `items` maps quiz_item_id to the
    quiz item. Several items can test one concept, and the card is the concept, so the
    per-item grades collapse to one rating:

      any item Again -> Again; else any Hard -> Hard; else all Easy -> Easy; else Good.

    Failure dominates and Easy requires unanimity, because the two signals are not
    equally trustworthy. A wrong answer is high signal and low noise: the learner did
    not have it. Speed is noisy in both directions, since a phone call, a re-read, or
    a lucky guess all move it. So one wrong answer is allowed to drag the whole card
    down, while one fast answer is not allowed to push it up.

    The asymmetry in the costs points the same way. Under-reviewing costs the memory,
    which is the thing being bought. Over-reviewing costs a few minutes. When the
    evidence is mixed, spend the minutes.
    """
    by_item: dict[int, list] = {}
    for attempt in attempts:
        if attempt.quiz_item_id in items:
            by_item.setdefault(attempt.quiz_item_id, []).append(attempt)

    grades = [grade_item(rows, items[item_id]) for item_id, rows in by_item.items()]
    if not grades:
        return CardRating(rating=None)

    ratings = [g.rating for g in grades]
    if AGAIN in ratings:
        card_rating = AGAIN
    elif HARD in ratings:
        card_rating = HARD
    elif all(r == EASY for r in ratings):
        card_rating = EASY
    else:
        card_rating = GOOD

    return CardRating(rating=card_rating, items=grades)
