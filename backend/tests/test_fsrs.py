"""The vendored FSRS-6 scheduler: constants, curves, state machine, and one worked
example checked step by step against the reference implementation.

The worked example is the real test. The individual formulas can each be right while
the pipeline that chains them is wrong: reading difficulty after updating it instead
of before, or rounding elapsed time up, produces numbers that look plausible and are
off by enough to reschedule everything. Only a multi-step trace catches that.
"""

import inspect
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app import fsrs
from app.fsrs import AGAIN, EASY, GOOD, HARD, Card


def at(*args) -> datetime:
    """A UTC instant. FSRS only ever subtracts these, so the zone is irrelevant to the
    arithmetic, but keeping them aware matches how the rest of the codebase builds
    timestamps and stops a stray local-time value from creeping into a fixture."""
    return datetime(*args, tzinfo=UTC)


T0 = at(2026, 9, 1, 9, 0, 0)


def test_derived_constants_are_exact():
    assert fsrs.DECAY == -0.1542
    assert fsrs.FACTOR == 0.9803464944134797
    assert fsrs.WEIGHTS[20] == 0.1542
    assert len(fsrs.WEIGHTS) == 21


def test_interval_equals_rounded_stability():
    """The interpretability invariant. At desired_retention 0.90 the interval formula
    reduces to round(stability), which is what lets the UI show one number and have it
    mean both "how well you know this" and "when it comes back". Any change to
    DESIRED_RETENTION breaks the equivalence, and this test is the tripwire."""
    assert fsrs.DESIRED_RETENTION == 0.90
    for stability in range(1, 366):
        assert fsrs.interval_days(float(stability)) == stability
    for stability in (1.2, 2.7, 3.49, 7.81, 30.3, 100.7, 364.4):
        assert fsrs.interval_days(stability) == round(stability)


def test_maximum_interval_caps_at_365():
    assert fsrs.interval_days(365.0) == 365
    assert fsrs.interval_days(400.0) == 365
    assert fsrs.interval_days(10_000.0) == 365
    assert fsrs.MAXIMUM_INTERVAL == 365


def test_minimum_interval_is_one_day():
    assert fsrs.interval_days(0.001) == 1
    assert fsrs.interval_days(0.4) == 1


def test_initial_stability_is_the_first_four_weights():
    assert fsrs.initial_stability(AGAIN) == 0.212
    assert fsrs.initial_stability(HARD) == 1.2931
    assert fsrs.initial_stability(GOOD) == 2.3065
    assert fsrs.initial_stability(EASY) == 8.2956
    assert [fsrs.initial_stability(r) for r in fsrs.RATINGS] == list(fsrs.WEIGHTS[0:4])


def test_initial_difficulty():
    assert round(fsrs.initial_difficulty(AGAIN), 4) == 6.4133
    assert round(fsrs.initial_difficulty(HARD), 4) == 5.1122
    assert round(fsrs.initial_difficulty(GOOD), 4) == 2.1181
    assert fsrs.initial_difficulty(EASY) == 1.0


def test_easy_initial_difficulty_is_clamped_from_below_zero():
    """Easy's raw initial difficulty is negative. next_difficulty's mean reversion
    deliberately uses the unclamped value, so the two must stay distinguishable."""
    assert fsrs._initial_difficulty_unclamped(EASY) < 0
    assert fsrs.initial_difficulty(EASY) == fsrs.DIFFICULTY_MIN


def test_new_card_intervals_for_each_rating():
    previews = fsrs.preview(Card(), T0)
    assert previews[AGAIN].interval == timedelta(minutes=10)
    assert previews[HARD].interval == timedelta(minutes=15)
    assert previews[GOOD].interval == timedelta(days=2)
    assert previews[EASY].interval == timedelta(days=8)


def test_new_card_rated_again_persists_as_learning():
    """A card rated Again must not stay "new". Left as new it would look untouched,
    reappear in the new queue, and lose the fact that the learner already missed it."""
    for rating in (AGAIN, HARD):
        card = fsrs.review(Card(), rating, T0).card
        assert card.state == "learning"
        assert card.step == 0
        assert card.reps == 1
        assert card.lapses == 0
        assert card.stability is not None and card.difficulty is not None


def test_new_card_rated_good_or_easy_graduates_to_review():
    for rating in (GOOD, EASY):
        card = fsrs.review(Card(), rating, T0).card
        assert card.state == "review"
        assert card.reps == 1


def test_stability_clamps_at_floor():
    assert fsrs.short_term_stability(0.001, AGAIN) == fsrs.STABILITY_MIN
    assert fsrs.next_stability(10.0, 0.001, 1.0, AGAIN) == fsrs.STABILITY_MIN
    # Repeated Again ratings must not drive stability to zero or negative.
    stability = 0.05
    for _ in range(20):
        stability = fsrs.short_term_stability(stability, AGAIN)
    assert stability == fsrs.STABILITY_MIN


def test_difficulty_clamps_at_both_ends():
    # Bottom: Easy on an already easy card pushes below 1.
    assert fsrs.next_difficulty(1.0, EASY) == fsrs.DIFFICULTY_MIN
    # Top: a corrupted above-range difficulty is pulled back to 10, not past it.
    assert fsrs.next_difficulty(11.0, AGAIN) == fsrs.DIFFICULTY_MAX
    assert fsrs.DIFFICULTY_MIN == 1.0
    assert fsrs.DIFFICULTY_MAX == 10.0
    for difficulty in (1.0, 2.5, 5.0, 7.5, 10.0):
        for rating in fsrs.RATINGS:
            assert 1.0 <= fsrs.next_difficulty(difficulty, rating) <= 10.0


def test_elapsed_days_truncates_to_whole_days():
    """The weights were fitted against integer day gaps. A fractional day shifts every
    stability update off the fitted curve, so this truncation is algorithm, not
    formatting."""
    last = at(2026, 9, 9, 9, 10, 0)
    assert fsrs.elapsed_days(last, last + timedelta(days=2, hours=23, minutes=50)) == 2
    assert fsrs.elapsed_days(last, last + timedelta(days=3)) == 3
    assert fsrs.elapsed_days(last, last + timedelta(hours=23, minutes=59)) == 0
    assert fsrs.elapsed_days(None, last) == 0
    # A clock that went backwards must not produce a negative gap.
    assert fsrs.elapsed_days(last, last - timedelta(days=5)) == 0


def test_fuzzing_is_absent_from_the_source():
    """Not "fuzzing is off": absent. The UI shows the exact interval on each button
    before the learner presses it, so a randomizer sitting behind a flag is a promise
    waiting to be broken by whoever flips it."""
    source = inspect.getsource(fsrs).lower()
    body = source.split('"""', 2)[-1]
    for banned in ("random", "fuzz", "jitter", "uniform("):
        assert banned not in body


def test_preview_does_not_mutate_and_matches_review():
    card = Card(
        state="review",
        stability=10.0,
        difficulty=5.0,
        due=T0,
        last_review=T0 - timedelta(days=10),
        reps=4,
        lapses=1,
    )
    before = replace(card)
    previews = fsrs.preview(card, T0)
    assert card == before
    assert set(previews) == set(fsrs.RATINGS)
    for rating in fsrs.RATINGS:
        direct = fsrs.review(card, rating, T0)
        assert previews[rating].card == direct.card
        assert previews[rating].interval == direct.interval


def test_review_rejects_an_unknown_rating():
    for rating in (0, 5, "good", None):
        with pytest.raises(ValueError):
            fsrs.review(Card(), rating, T0)


def _assert_step(card, state, stability, difficulty, reps, lapses, due):
    assert card.state == state
    assert round(card.stability, 4) == stability
    assert round(card.difficulty, 4) == difficulty
    assert card.reps == reps
    assert card.lapses == lapses
    assert card.due == due


def test_worked_example_five_reviews():
    """Five reviews traced end to end, asserting every field at every step.

    Step 3 is the one that matters most: elapsed time runs from the previous review
    (09-03), not from the card's creation, so a card can be eleven days old and still
    have a six day gap. Step 5 is the truncation case: the gap is 2 days 23 hours 50
    minutes and must count as 2 days. If retrievability there comes out 0.8783 the
    truncation is right; 3 days would give a visibly different number.
    """
    card = Card()

    # 1. First ever review, rated Good. No history, so the initial curves apply.
    result = fsrs.review(card, GOOD, T0)
    card = result.card
    assert result.retrievability is None
    assert result.elapsed_days == 0
    _assert_step(card, "review", 2.3065, 2.1181, 1, 0, at(2026, 9, 3, 9, 0))

    # 2. Two days later, Good again. Recall succeeded, so stability jumps.
    result = fsrs.review(card, GOOD, T0 + timedelta(days=2))
    card = result.card
    assert result.elapsed_days == 2
    assert round(result.retrievability, 4) == 0.9095
    _assert_step(card, "review", 10.9643, 2.1112, 2, 0, at(2026, 9, 14, 9, 0))

    # 3. Six days after that review (not eleven days after step 1), forgotten.
    # This is the only lapse in the trace: review -> relearning.
    result = fsrs.review(card, AGAIN, T0 + timedelta(days=8))
    card = result.card
    assert result.elapsed_days == 6
    assert round(result.retrievability, 4) == 0.9359
    _assert_step(card, "relearning", 1.4494, 7.3922, 3, 1, at(2026, 9, 9, 9, 10))
    assert card.step == 0

    # 4. Ten minutes later, recovered. Same day, so the short-term curve applies and
    # reps still increments: a relearning step is a real review.
    result = fsrs.review(card, GOOD, T0 + timedelta(days=8, minutes=10))
    card = result.card
    assert result.elapsed_days == 0
    _assert_step(card, "review", 1.4861, 7.3801, 4, 1, at(2026, 9, 10, 9, 10))

    # 5. Gap of 2 days 23 hours 50 minutes, which truncates to 2 days. Rated Hard,
    # which applies the hard penalty to the stability gain but is not a lapse.
    result = fsrs.review(card, HARD, T0 + timedelta(days=11))
    card = result.card
    assert result.elapsed_days == 2
    assert round(result.retrievability, 4) == 0.8783
    _assert_step(card, "review", 3.4888, 8.2460, 5, 1, at(2026, 9, 15, 9, 0))


def test_lapses_only_count_review_failures():
    """Failing a learning step is not forgetting, it is not having learned it yet.
    Counting those as lapses would make every new card look like a problem concept."""
    card = fsrs.review(Card(), AGAIN, T0).card
    assert card.state == "learning"
    assert card.lapses == 0

    card = fsrs.review(card, AGAIN, T0 + timedelta(minutes=10)).card
    assert card.state == "learning"
    assert card.lapses == 0
    assert card.reps == 2

    card = fsrs.review(card, GOOD, T0 + timedelta(minutes=20)).card
    assert card.state == "review"
    assert card.lapses == 0

    card = fsrs.review(card, AGAIN, T0 + timedelta(days=3)).card
    assert card.state == "relearning"
    assert card.lapses == 1


def test_learning_and_relearning_step_intervals():
    learning = fsrs.review(Card(), AGAIN, T0).card
    previews = fsrs.preview(learning, T0 + timedelta(minutes=10))
    assert previews[AGAIN].interval == timedelta(minutes=10)
    assert previews[HARD].interval == timedelta(minutes=15)
    assert previews[GOOD].card.state == "review"
    assert previews[EASY].card.state == "review"

    graduated = fsrs.review(Card(), GOOD, T0).card
    relearning = fsrs.review(graduated, AGAIN, T0 + timedelta(days=5)).card
    assert relearning.state == "relearning"
    previews = fsrs.preview(relearning, T0 + timedelta(days=5, minutes=10))
    assert previews[AGAIN].interval == timedelta(minutes=10)
    assert previews[AGAIN].card.state == "relearning"
    assert previews[HARD].interval == timedelta(minutes=15)
    assert previews[HARD].card.state == "relearning"
    assert previews[GOOD].card.state == "review"
    assert previews[EASY].card.state == "review"
    # A second failure inside relearning is not a second lapse.
    assert previews[AGAIN].card.lapses == relearning.lapses


def test_review_intervals_are_round_stability():
    card = Card(
        state="review",
        stability=40.0,
        difficulty=5.0,
        due=T0,
        last_review=T0 - timedelta(days=40),
        reps=6,
    )
    for rating in (HARD, GOOD, EASY):
        result = fsrs.review(card, rating, T0)
        assert result.card.state == "review"
        assert result.interval == timedelta(days=round(result.card.stability))
        assert result.scheduled_days == round(result.card.stability)


def test_scheduled_days_is_zero_for_sub_day_steps():
    """review_logs.scheduled_days is whole days, so a ten minute step logs 0 rather
    than rounding up to a day the learner was never given."""
    result = fsrs.review(Card(), AGAIN, T0)
    assert result.scheduled_days == 0
    assert result.card.due == T0 + timedelta(minutes=10)


def test_weights_hash_is_short_and_stable():
    assert fsrs.WEIGHTS_HASH == fsrs.weights_hash()
    assert len(fsrs.WEIGHTS_HASH) == 16
    assert fsrs.FSRS_VERSION == "fsrs6"
