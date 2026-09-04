# Prompt trials

- `akv-multi-tagged`: 4 run(s)
- `akv-multi-untagged`: 4 run(s)

## Answerable from lesson

| Variant | n | mean | range | spread |
|---|---|---|---|---|
| akv-multi-tagged | 4 | 61.3% | 54.8% to 65.9% | 11.1% |
| akv-multi-untagged | 4 | 50.4% | 45.2% to 53.2% | 8.0% |

## Grounded answers

| Variant | n | mean | range | spread |
|---|---|---|---|---|
| akv-multi-tagged | 4 | 55.6% | 48.8% to 61.0% | 12.2% |
| akv-multi-untagged | 4 | 44.2% | 36.6% to 48.1% | 11.6% |

## Giveaway MCQs

| Variant | n | mean | range | spread |
|---|---|---|---|---|
| akv-multi-tagged | 4 | 2.8 | 0.0 to 5.0 | 5.0 |
| akv-multi-untagged | 4 | 2.2 | 2.0 to 3.0 | 1.0 |

## Hallucination candidates

| Variant | n | mean | range | spread |
|---|---|---|---|---|
| akv-multi-tagged | 4 | 0.5 | 0.0 to 1.0 | 1.0 |
| akv-multi-untagged | 4 | 0.2 | 0.0 to 1.0 | 1.0 |

## Quiz items

| Variant | n | mean | range | spread |
|---|---|---|---|---|
| akv-multi-tagged | 4 | 40.0 | 36.0 to 42.0 | 6.0 |
| akv-multi-untagged | 4 | 46.0 | 41.0 to 54.0 | 13.0 |

## Lessons

| Variant | n | mean | range | spread |
|---|---|---|---|---|
| akv-multi-tagged | 4 | 6.8 | 6.0 to 7.0 | 1.0 |
| akv-multi-untagged | 4 | 7.8 | 7.0 to 9.0 | 2.0 |

## Segment fallback rate

| Variant | n | mean | range | spread |
|---|---|---|---|---|
| akv-multi-tagged | 4 | 0.0% | 0.0% to 0.0% | 0.0% |
| akv-multi-untagged | 4 | 0.0% | 0.0% to 0.0% | 0.0% |

## Is any difference real?

- **Answerable from lesson**: akv-multi-tagged leads akv-multi-untagged, lead 10.9% vs widest within-prompt spread 11.1%: INSIDE the noise, not a result
- **Grounded answers**: akv-multi-tagged leads akv-multi-untagged, lead 11.4% vs widest within-prompt spread 12.2%: INSIDE the noise, not a result

## Reading of the above, added by hand

THE TWO VERDICT LINES ABOVE ARE THE WRONG STATISTIC, not a real negative, and the ship
decision goes the other way. "Lead vs widest within-prompt spread" compares a difference
of means to a RANGE. A range grows with n and is not a standard error, so that heuristic
gets more conservative the more data you collect, which is backwards. Report generation
still emits it; fixing the generator is owed and is not this change.

What the same numbers say when read properly:

- The ranges are DISJOINT on both primary metrics. Answerable: tagged 54.8% to 65.9%,
  untagged 45.2% to 53.2%. Grounded: tagged 48.8% to 61.0%, untagged 36.6% to 48.1%
  (48.8 > 48.1). Complete separation of 4 against 4 is an exact permutation p of
  1/70 = 0.014 one-sided, 0.029 two-sided.
- Segment fallback is 0.0% in both arms, so the gain does not buy a cost regression.
- The correctness argument stands on its own: without the tag the model provably cannot
  tell which document a passage came from, and continuous segment numbering actively
  implies continuity across a seam that is not continuous.

Two caveats that belong with the result:

- Answerability and groundedness are correlated, so this is ONE result, not two.
- It is one document pair at n=4. The effect is real on this corpus. It is not evidence
  of 11 points everywhere.

Worth watching, not blocking: the tagged arm produced fewer lessons (6.8 vs 7.8) and
fewer quiz items (40 vs 46). That is the same lever the routing regression in
outline_system's docstring records, though here answerability rose rather than fell.
