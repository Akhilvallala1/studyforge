"""Deriving FSRS ratings from attempt rows: the per-item grade, the speed budget,
and the rule that collapses several items on one concept into a single rating."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from app import rating
from app.fsrs import AGAIN, EASY, GOOD, HARD


@dataclass
class FakeItem:
    """Stands in for a QuizItem. rating_v1 never touches a Session, so the real ORM
    object buys nothing here and would drag a database into a pure policy test."""

    id: int = 1
    question: str = "What direction does gradient descent step in?"
    kind: str = "short"
    options: list = field(default_factory=list)
    answer: str = "downhill"


@dataclass
class FakeAttempt:
    """Stands in for an Attempt row. It carries the answer and timestamp fields even
    though the rating never reads them, because _attempt_state does: the fake has to
    be shaped like the row the real caller passes in, not like the subset this policy
    happens to use today."""

    quiz_item_id: int = 1
    correct: bool = True
    source: str = "lesson_quiz"
    elapsed_ms: int | None = None
    submitted_answer: str = "downhill"
    expected_answer: str = "downhill"
    created_at: datetime = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)


def _rate(attempts, items):
    return rating.rating_v1(attempts, {item.id: item for item in items})


def test_budget_scales_with_reading_and_typing():
    short_q = FakeItem(question="Q?", answer="a")
    long_q = FakeItem(question="Q?" * 100, answer="a")
    long_answer = FakeItem(question="Q?", answer="a" * 50)
    assert rating.answer_budget_ms(long_q) > rating.answer_budget_ms(short_q)
    assert rating.answer_budget_ms(long_answer) > rating.answer_budget_ms(short_q)


def test_budget_counts_mcq_options_as_reading():
    plain = FakeItem(kind="mcq", question="Pick one", options=[], answer="a")
    with_options = FakeItem(
        kind="mcq", question="Pick one", options=["alpha", "beta", "gamma"], answer="alpha"
    )
    expected = rating.READ_MS_PER_CHAR * len("alpha" + "beta" + "gamma")
    assert rating.answer_budget_ms(with_options) - rating.answer_budget_ms(plain) == expected


def test_mcq_budget_does_not_charge_for_typing():
    """Selecting a long option is one click. Charging typing time for it would make
    every multiple choice item with a wordy answer look impossibly fast."""
    mcq = FakeItem(kind="mcq", question="Q?", options=[], answer="a" * 40)
    short = FakeItem(kind="short", question="Q?", options=[], answer="a" * 40)
    assert rating.answer_budget_ms(mcq) < rating.answer_budget_ms(short)
    assert rating.answer_budget_ms(mcq) == rating.THINK_MS + rating.READ_MS_PER_CHAR * 2 + (
        rating.MCQ_SELECT_MS
    )


def test_is_fast_uses_the_per_item_budget():
    item = FakeItem()
    budget = rating.answer_budget_ms(item)
    assert rating.is_fast(item, int(budget * rating.EASY_SPEED_FRACTION))
    assert rating.is_fast(item, 1)
    assert not rating.is_fast(item, int(budget * rating.EASY_SPEED_FRACTION) + 1)
    assert not rating.is_fast(item, budget)


def test_missing_timing_is_never_fast():
    """Absence of evidence is not evidence of fluency, and Easy is the rating that
    pushes the next review furthest out."""
    assert not rating.is_fast(FakeItem(), None)


def test_incorrect_is_again():
    item = FakeItem()
    result = _rate([FakeAttempt(correct=False)], [item])
    assert result.rating == AGAIN
    assert result.items[0].rating == AGAIN


def test_wrong_then_right_is_hard():
    item = FakeItem()
    result = _rate(
        [FakeAttempt(correct=False), FakeAttempt(correct=True, elapsed_ms=1)],
        [item],
    )
    assert result.rating == HARD
    assert result.items[0].tries == 2


def test_second_try_correct_is_hard_even_when_fast():
    """Needing a retry outranks answering the retry quickly. The learner did not have
    it on recall, which is the thing FSRS is scheduling against."""
    item = FakeItem()
    result = _rate([FakeAttempt(correct=False), FakeAttempt(correct=True, elapsed_ms=1)], [item])
    assert result.rating == HARD


def test_first_try_correct_without_timing_is_good():
    item = FakeItem()
    result = _rate([FakeAttempt(correct=True, elapsed_ms=None)], [item])
    assert result.rating == GOOD
    assert result.items[0].elapsed_ms is None


def test_first_try_correct_and_slow_is_good_not_hard():
    """Slowness never demotes Good in v1. Timing is noisy enough in both directions
    that acting on it symmetrically would schedule from the noise."""
    item = FakeItem()
    slow = rating.answer_budget_ms(item) * 10
    result = _rate([FakeAttempt(correct=True, elapsed_ms=slow)], [item])
    assert result.rating == GOOD


def test_first_try_correct_and_fast_is_easy():
    item = FakeItem()
    fast = int(rating.answer_budget_ms(item) * rating.EASY_SPEED_FRACTION)
    result = _rate([FakeAttempt(correct=True, elapsed_ms=fast)], [item])
    assert result.rating == EASY
    assert result.items[0].fast is True


def test_hard_is_unreachable_from_the_review_path():
    """Review sessions allow exactly one try per item, so a review attempt can never
    look like a retry. Hard exists only for the lesson quiz seed path."""
    item = FakeItem()
    attempts = [FakeAttempt(correct=True, source="review", elapsed_ms=None)]
    result = _rate(attempts, [item])
    assert result.items[0].tries == 0
    assert result.rating == GOOD


def test_tries_ignores_attempt_no_and_other_sources():
    """A first try means the first try of THIS exposure. Attempt.attempt_no counts every
    touch of the item ever recorded, so a concept correctly recalled for the fourth
    time would otherwise be graded as a fourth-try guess."""
    item = FakeItem()
    attempts = [
        FakeAttempt(correct=True, source="review", elapsed_ms=None),
    ]
    result = _rate(attempts, [item])
    assert result.rating == GOOD
    assert result.items[0].tries == 0


def test_any_again_dominates_the_card():
    """Failure dominates. A wrong answer is high signal and low noise: the learner did
    not have it, and one item's failure is enough to bring the whole concept back."""
    a, b, c = FakeItem(id=1), FakeItem(id=2), FakeItem(id=3)
    fast_a = int(rating.answer_budget_ms(a) * rating.EASY_SPEED_FRACTION)
    attempts = [
        FakeAttempt(quiz_item_id=1, correct=True, elapsed_ms=fast_a),
        FakeAttempt(quiz_item_id=2, correct=True, elapsed_ms=fast_a),
        FakeAttempt(quiz_item_id=3, correct=False),
    ]
    assert _rate(attempts, [a, b, c]).rating == AGAIN


def test_hard_beats_easy_and_good():
    a, b = FakeItem(id=1), FakeItem(id=2)
    fast = int(rating.answer_budget_ms(a) * rating.EASY_SPEED_FRACTION)
    attempts = [
        FakeAttempt(quiz_item_id=1, correct=True, elapsed_ms=fast),
        FakeAttempt(quiz_item_id=2, correct=False),
        FakeAttempt(quiz_item_id=2, correct=True, elapsed_ms=fast),
    ]
    assert _rate(attempts, [a, b]).rating == HARD


def test_easy_requires_unanimity():
    """One fast answer is not allowed to push the card up, because speed is the noisy
    signal. Over-reviewing costs minutes; under-reviewing costs the memory."""
    a, b = FakeItem(id=1), FakeItem(id=2)
    fast = int(rating.answer_budget_ms(a) * rating.EASY_SPEED_FRACTION)
    mixed = [
        FakeAttempt(quiz_item_id=1, correct=True, elapsed_ms=fast),
        FakeAttempt(quiz_item_id=2, correct=True, elapsed_ms=None),
    ]
    assert _rate(mixed, [a, b]).rating == GOOD

    both_fast = [
        FakeAttempt(quiz_item_id=1, correct=True, elapsed_ms=fast),
        FakeAttempt(quiz_item_id=2, correct=True, elapsed_ms=fast),
    ]
    assert _rate(both_fast, [a, b]).rating == EASY


def test_no_gradeable_attempts_yields_no_rating():
    """Nothing to schedule from. A default of Good here would invent a review the
    learner never did."""
    assert _rate([], [FakeItem()]).rating is None
    orphan = [FakeAttempt(quiz_item_id=99, correct=True)]
    assert _rate(orphan, [FakeItem(id=1)]).rating is None


def test_rating_version_is_stamped_on_every_result():
    result = _rate([FakeAttempt(correct=True)], [FakeItem()])
    assert result.rating_v == rating.RATING_VERSION == "v1"


def test_grades_carry_the_evidence_that_produced_them():
    item = FakeItem()
    fast = int(rating.answer_budget_ms(item) * rating.EASY_SPEED_FRACTION)
    grade = _rate([FakeAttempt(correct=True, elapsed_ms=fast)], [item]).items[0]
    assert grade.quiz_item_id == item.id
    assert grade.correct is True
    assert grade.elapsed_ms == fast
    assert grade.budget_ms == rating.answer_budget_ms(item)
    assert grade.fast is True


@pytest.mark.parametrize("constant", ["READ_MS_PER_CHAR", "TYPE_MS_PER_CHAR", "THINK_MS"])
def test_speed_constants_are_positive(constant):
    assert getattr(rating, constant) > 0


def test_rating_v1_takes_no_session():
    """Purity is the contract: attempts and items in, a rating out. A Session
    parameter would make the policy untestable without a database and would let a
    query creep into the middle of a scheduling decision."""
    import inspect

    params = list(inspect.signature(rating.rating_v1).parameters)
    assert params == ["attempts", "items"]
