# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 9 |
| Quiz items | 53 |
| Structure problems | 0 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.4906 |
| Grounded, extractive items only | 0.5319 |
| Ungrounded items, all | 11 |
| Ungrounded extractive items | 7 |
| Hallucination candidates | 7 |
| Mean grounding recall | 0.6935 |
| Answerable from lesson | 0.5472 |
| Unanswerable items | 5 |
| Giveaway MCQs | 5 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 0.9659 |
| Wall clock s | 471.57 |

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
| lesson | 9 | 13,136 | 34,315 | $0.9236 | 50.5 | 57.0 |
| outline | 1 | 984 | 1,498 | $0.0424 | 17.4 | 17.4 |

### Structure

- 3 modules, 9 lessons, 53 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 5, 6, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 4, 4, 5, 5]
- Lesson content chars: mean 6034, min 4468
- Item kinds: {'mcq': 35, 'short': 18}
- Problems: none

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 26/53 answers supported (exact or strong) = 49.1%
- Tiers: {'exact': 8, 'strong': 18, 'partial': 16, 'unsupported': 11}
- Mean best-window recall: 0.694
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 47, 'odd_one_out': 0, 'restatement': 6, 'trivial': 0}
- Extractive items supported: 25/47 = 53.2% (mean window recall 0.728)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 44.2%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 7

  - **module 1 / lesson 2 / item 5** (restatement) novel 67%: Because without transmission to offspring, an advantageous variation would die with the individual and nothing could accumulate across generations. Variation su
  - **module 1 / lesson 2 / item 6** (extractive) novel 86%: It makes even slight differences in an organism consequential to its success
  - **module 1 / lesson 3 / item 1** (extractive) novel 64%: It makes it credible that a chance variation could matter to a being in some way, since the relations are both numerous and tight enough for small differences t
  - **module 2 / lesson 1 / item 1** (extractive) novel 64%: Because without heavy mortality among the young, a slight advantage would make no difference to who survives and breeds
  - **module 2 / lesson 1 / item 2** (extractive) novel 86%: That the claim concerns probabilities, not guaranteed outcomes for any particular individual
  - **module 2 / lesson 3 / item 4** (extractive) novel 100%: He is proposing the connection as a suggestion that fits the observations, not asserting it as proved
  - **module 3 / lesson 2 / item 2** (extractive) novel 86%: It is set down as a separate heading of its own, not as one of the three named circumstances

#### Ungrounded extractive items

- **module 1 / lesson 2 / item 6** (Variability and Heredity as Preconditions)
  - Q: Darwin asks the reader to bear in mind how "infinitely complex and close-fitting" the mutual relations of organic beings are. What role does this premise play?
  - Expected answer: `It makes even slight differences in an organism consequential to its success`
  - Best window recall 0.14, global token recall 0.14
  - Closest source text: `and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight`

- **module 1 / lesson 3 / item 1** (The Web of Mutual Relations)
  - Q: In Darwin's argument, what work is done by the claim that the mutual relations of organic beings are 'infinitely complex and close-fitting'?
  - Expected answer: `It makes it credible that a chance variation could matter to a being in some way, since the relations are both numerous and tight enough for small differences to count`
  - Best window recall 0.14, global token recall 0.36
  - Closest source text: `character related to the diversity of inhabitants of any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too b`

- **module 2 / lesson 1 / item 1** (Advantage, However Slight)
  - Q: Why does Darwin insert the parenthesis 'remembering that many more individuals are born than can possibly survive' at exactly the point where he draws his conclusion?
  - Expected answer: `Because without heavy mortality among the young, a slight advantage would make no difference to who survives and breeds`
  - Best window recall 0.18, global token recall 0.18
  - Closest source text: `being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight`

- **module 2 / lesson 1 / item 2** (Advantage, However Slight)
  - Q: Darwin writes that individuals with any advantage 'would have the best chance of surviving and of procreating their kind.' What does the phrasing 'best chance' indicate about the strength of his claim?
  - Expected answer: `That the claim concerns probabilities, not guaranteed outcomes for any particular individual`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 2 / lesson 3 / item 3** (The Neutral Case and Polymorphic Species)
  - Q: What group of species does Darwin point to as a place where the fluctuating element may perhaps be seen?
  - Expected answer: `The species called polymorphic — many-formed species that naturalists had already labelled as presenting several forms. Darwin offers them only tentatively, with 'perhaps'.`
  - Best window recall 0.27, global token recall 0.40
  - Closest source text: `hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither useful nor injurious would not be affected by natural selection and would`

- **module 2 / lesson 3 / item 4** (The Neutral Case and Polymorphic Species)
  - Q: Darwin writes 'as perhaps we see in the species called polymorphic.' What does the word 'perhaps' indicate about his claim?
  - Expected answer: `He is proposing the connection as a suggestion that fits the observations, not asserting it as proved`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 2 / item 2** (Conditions Favourable and Unfavourable)
  - Q: How does the chapter summary treat "Slow action" in relation to the three circumstances?
  - Expected answer: `It is set down as a separate heading of its own, not as one of the three named circumstances`
  - Best window recall 0.14, global token recall 0.14
  - Closest source text: `selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances`

### Answerability (answer vs its own lesson content)

- 29/53 answerable from the lesson alone = 54.7%
- Tiers: {'exact': 7, 'strong': 22, 'partial': 19, 'unsupported': 5}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 5

#### Items not answerable from their lesson

- **module 1 / lesson 3 / item 1** (The Web of Mutual Relations)
  - Q: In Darwin's argument, what work is done by the claim that the mutual relations of organic beings are 'infinitely complex and close-fitting'?
  - Expected answer: `It makes it credible that a chance variation could matter to a being in some way, since the relations are both numerous and tight enough for small differences to count`
  - Best window recall against lesson: 0.43

- **module 2 / lesson 1 / item 1** (Advantage, However Slight)
  - Q: Why does Darwin insert the parenthesis 'remembering that many more individuals are born than can possibly survive' at exactly the point where he draws his conclusion?
  - Expected answer: `Because without heavy mortality among the young, a slight advantage would make no difference to who survives and breeds`
  - Best window recall against lesson: 0.27

- **module 2 / lesson 1 / item 2** (Advantage, However Slight)
  - Q: Darwin writes that individuals with any advantage 'would have the best chance of surviving and of procreating their kind.' What does the phrasing 'best chance' indicate about the strength of his claim?
  - Expected answer: `That the claim concerns probabilities, not guaranteed outcomes for any particular individual`
  - Best window recall against lesson: 0.29

- **module 2 / lesson 2 / item 5** (Preservation and Rejection: The Formal Definition)
  - Q: Why is it accurate to say that in Darwin's definition natural selection is a filter rather than a source?
  - Expected answer: `Because the definition speaks only of preserving favourable variations and rejecting injurious ones — the variations must already have arisen before selection can act on them. Selection sorts existing heritable differences; it does not produce them.`
  - Best window recall against lesson: 0.37

- **module 2 / lesson 3 / item 4** (The Neutral Case and Polymorphic Species)
  - Q: Darwin writes 'as perhaps we see in the species called polymorphic.' What does the word 'perhaps' indicate about his claim?
  - Expected answer: `He is proposing the connection as a suggestion that fits the observations, not asserting it as proved`
  - Best window recall against lesson: 0.43

### Concept coverage across the source

- 34/43 concepts anchored to a source chunk (9 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [34]
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
