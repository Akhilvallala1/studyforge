# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 9 |
| Quiz items | 52 |
| Structure problems | 8 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.5577 |
| Grounded, extractive items only | 0.617 |
| Ungrounded items, all | 15 |
| Ungrounded extractive items | 10 |
| Hallucination candidates | 7 |
| Mean grounding recall | 0.7004 |
| Answerable from lesson | 0.6154 |
| Unanswerable items | 4 |
| Giveaway MCQs | 2 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 0.9323 |
| Wall clock s | 458.49 |

## prose-short

Source: text `darwin-origin-short`, 2,498 chars, 1 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 9 | 9 | 0 | 0 | 9 | 9 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 9 | 13,131 | 33,017 | $0.8911 | 49.1 | 57.0 |
| outline | 1 | 984 | 1,451 | $0.0412 | 16.6 | 16.6 |

### Structure

- 3 modules, 9 lessons, 52 quiz items
- Quiz items per lesson: [6, 6, 5, 5, 6, 6, 6, 6, 6]
- Concepts per lesson: [4, 5, 5, 5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 6320, min 5088
- Item kinds: {'mcq': 35, 'short': 17}
- Problems: {'duplicate_question': 2, 'empty_concept': 6}

  - `duplicate_question` at module 2 / lesson 1 / item 3: also at module 1 / lesson 3 / item 2
  - `empty_concept` at module 3 / lesson 2 / item 1: According to the chapter's contents line, which three circumstances does Darwin name as favourable and unfavourable to natural selection?
  - `empty_concept` at module 3 / lesson 2 / item 2: How does Darwin define natural selection in this passage?
  - `duplicate_question` at module 3 / lesson 2 / item 2: also at module 1 / lesson 3 / item 4
  - `empty_concept` at module 3 / lesson 2 / item 3: What does Darwin say becomes of variations that are neither useful nor injurious?
  - `empty_concept` at module 3 / lesson 2 / item 4: Over what span does Darwin expect variations useful to a being in the battle of life to occur?
  - `empty_concept` at module 3 / lesson 2 / item 5: Darwin says an individual with any advantage, however slight, would have the best chance of surviving and reproducing. What fact about births and survival does he ask the reader to remember in order to make this point work?
  - `empty_concept` at module 3 / lesson 2 / item 6: Why does the lesson describe the slowness of natural selection as following from Darwin's own argument rather than being an added claim?

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 29/52 answers supported (exact or strong) = 55.8%
- Tiers: {'exact': 4, 'strong': 25, 'partial': 8, 'unsupported': 15}
- Mean best-window recall: 0.700
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 47, 'odd_one_out': 0, 'restatement': 5, 'trivial': 0}
- Extractive items supported: 29/47 = 61.7% (mean window recall 0.743)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 56.7%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 7

  - **module 1 / lesson 2 / item 2** (extractive) novel 90%: The claim covers every part of the organism, but the plasticity it asserts is partial rather than unlimited
  - **module 1 / lesson 2 / item 3** (restatement) novel 65%: Because heredity is what preserves a variation beyond the individual that bears it. Offspring tend to resemble their parents, oddities included, so favourable d
  - **module 1 / lesson 3 / item 1** (extractive) novel 75%: It makes it unsurprising that a variation should turn out useful, since a creature touches its world at innumerable tight points
  - **module 2 / lesson 1 / item 4** (restatement) novel 71%: Because Darwin's claim is probabilistic, not a guarantee: an advantaged individual may still die, and the argument rests on the improved likelihood rather than 
  - **module 2 / lesson 3 / item 4** (extractive) novel 86%: As a tentative illustration, introduced with 'perhaps', rather than a demonstrated case
  - **module 3 / lesson 1 / item 3** (extractive) novel 64%: It lists it as a separate heading standing beside natural selection, not as one of natural selection's listed powers
  - **module 3 / lesson 1 / item 6** (extractive) novel 71%: That leaving offspring, not mere survival, is what carries the advantage forward

#### Ungrounded extractive items

- **module 1 / lesson 2 / item 2** (Variation and the Hereditary Tendency)
  - Q: Darwin writes that under domestication 'the whole organisation becomes in some degree plastic.' Which reading best captures the two qualifications built into that phrase?
  - Expected answer: `The claim covers every part of the organism, but the plasticity it asserts is partial rather than unlimited`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 1 / lesson 2 / item 6** (Variation and the Hereditary Tendency)
  - Q: What point does Darwin make by observing that 'variations useful to man have undoubtedly occurred'?
  - Expected answer: `That since variation throws up peculiarities of every kind, it is not improbable that some should be useful to the being itself`
  - Best window recall 0.33, global token recall 0.56
  - Closest source text: `their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither useful`

- **module 1 / lesson 3 / item 1** (The Web of Mutual Relations)
  - Q: In Darwin's argument, what work does the claim that the mutual relations of organic beings are "infinitely complex and close-fitting" actually do?
  - Expected answer: `It makes it unsurprising that a variation should turn out useful, since a creature touches its world at innumerable tight points`
  - Best window recall 0.17, global token recall 0.17
  - Closest source text: `the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither u`

- **module 1 / lesson 3 / item 5** (The Web of Mutual Relations)
  - Q: Darwin writes that "variations useful to man have undoubtedly occurred." How does he use this admitted fact?
  - Expected answer: `He asks why nature, with far more relations at stake and thousands of generations, should be the one arena where useful variations never arise`
  - Best window recall 0.31, global token recall 0.46
  - Closest source text: `each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of gen`

- **module 2 / lesson 1 / item 1** (The Logic of Advantage)
  - Q: In Darwin's chain of reasoning, what role does the parenthetical remark that 'many more individuals are born than can possibly survive' play?
  - Expected answer: `It establishes that a filter must operate on each generation, so a slight advantage decides which side of the filter an individual falls on`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight`

- **module 2 / lesson 3 / item 4** (The Neutral Case and Polymorphic Species)
  - Q: How does Darwin present the polymorphic species as evidence?
  - Expected answer: `As a tentative illustration, introduced with 'perhaps', rather than a demonstrated case`
  - Best window recall 0.14, global token recall 0.14
  - Closest source text: `would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither useful nor injurious would not be affected by natural selection and would be left a fluctuating element as perhaps`

- **module 3 / lesson 1 / item 3** (Reach of Selection: Trifling Characters, All Ages, Both Sexes, and Sexual Selection)
  - Q: How does the chapter's opening summary treat sexual selection?
  - Expected answer: `It lists it as a separate heading standing beside natural selection, not as one of natural selection's listed powers`
  - Best window recall 0.27, global token recall 0.27
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all`

- **module 3 / lesson 1 / item 6** (Reach of Selection: Trifling Characters, All Ages, Both Sexes, and Sexual Selection)
  - Q: Darwin's phrase about advantaged individuals is that they have the best chance of 'surviving and of procreating their kind.' What does the second half add?
  - Expected answer: `That leaving offspring, not mere survival, is what carries the advantage forward`
  - Best window recall 0.14, global token recall 0.14
  - Closest source text: `the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage`

- **module 3 / lesson 2 / item 2** (Conditions of Action: Intercrossing, Isolation, Numbers, and Slow Action)
  - Q: How does Darwin define natural selection in this passage?
  - Expected answer: `The keeping of favourable variations together with the discarding of injurious ones`
  - Best window recall 0.43, global token recall 0.43
  - Closest source text: `slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations`

- **module 3 / lesson 2 / item 6** (Conditions of Action: Intercrossing, Isolation, Numbers, and Slow Action)
  - Q: Why does the lesson describe the slowness of natural selection as following from Darwin's own argument rather than being an added claim?
  - Expected answer: `Because the process waits on variations that only sometimes appear and then works on advantages that may be very slight`
  - Best window recall 0.22, global token recall 0.33
  - Closest source text: `their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes`

### Answerability (answer vs its own lesson content)

- 32/52 answerable from the lesson alone = 61.5%
- Tiers: {'exact': 4, 'strong': 28, 'partial': 16, 'unsupported': 4}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 2

#### Items not answerable from their lesson

- **module 1 / lesson 2 / item 2** (Variation and the Hereditary Tendency)
  - Q: Darwin writes that under domestication 'the whole organisation becomes in some degree plastic.' Which reading best captures the two qualifications built into that phrase?
  - Expected answer: `The claim covers every part of the organism, but the plasticity it asserts is partial rather than unlimited`
  - Best window recall against lesson: 0.40

- **module 1 / lesson 3 / item 1** (The Web of Mutual Relations)
  - Q: In Darwin's argument, what work does the claim that the mutual relations of organic beings are "infinitely complex and close-fitting" actually do?
  - Expected answer: `It makes it unsurprising that a variation should turn out useful, since a creature touches its world at innumerable tight points`
  - Best window recall against lesson: 0.33

- **module 2 / lesson 1 / item 4** (The Logic of Advantage)
  - Q: Darwin says an individual with an advantage would have 'the best chance' of surviving and procreating. Why does the lesson stress the word 'chance'?
  - Expected answer: `Because Darwin's claim is probabilistic, not a guarantee: an advantaged individual may still die, and the argument rests on the improved likelihood rather than on certain survival.`
  - Best window recall against lesson: 0.47

- **module 3 / lesson 1 / item 6** (Reach of Selection: Trifling Characters, All Ages, Both Sexes, and Sexual Selection)
  - Q: Darwin's phrase about advantaged individuals is that they have the best chance of 'surviving and of procreating their kind.' What does the second half add?
  - Expected answer: `That leaving offspring, not mere survival, is what carries the advantage forward`
  - Best window recall against lesson: 0.43

### Concept coverage across the source

- 28/44 concepts anchored to a source chunk (16 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [28]
- Lessons per chunk: [4]
- Uncovered chunk indexes: none
- Largest share in one chunk: 100.0%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [1.0]
- Actual share per chunk: [1.0]
- Actual/expected: [1.0]
- Worst concentration ratio: 1.00

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 100.0%
- Worst chunk: 0 at 100.0%
- Chunks under 50% covered: 0
- Lessons routed per segment: [9]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 2,498 | 19 | 19 | 100.0% | 1.000 |
