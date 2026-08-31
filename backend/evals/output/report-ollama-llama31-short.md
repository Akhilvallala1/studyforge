# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 4 |
| Quiz items | 17 |
| Structure problems | 0 |
| Strict JSON first try | 0.2174 |
| Hard parse failures | 18 |
| Grounded, all items (old metric) | 0.2353 |
| Grounded, extractive items only | 0.2353 |
| Ungrounded items, all | 11 |
| Ungrounded extractive items | 11 |
| Hallucination candidates | 10 |
| Mean grounding recall | 0.4163 |
| Answerable from lesson | 0.6471 |
| Unanswerable items | 2 |
| Giveaway MCQs | 4 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 0.4737 |
| Source recall, worst chunk | 0.4737 |
| Cost USD | 0 |
| Wall clock s | 1183.11 |

## prose-short

Source: text `darwin-origin-short`, 2,498 chars, 1 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 22 | 4 | 20 | 1 | 4 | 4 | 18 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 22 | 21,731 | 19,570 | $0.0000 | 52.0 | 99.2 |
| outline | 1 | 671 | 555 | $0.0000 | 38.3 | 38.3 |

### Structure

- 2 modules, 4 lessons, 17 quiz items
- Quiz items per lesson: [4, 5, 4, 4]
- Concepts per lesson: [5, 4, 5, 4]
- Lesson content chars: mean 1610, min 1052
- Item kinds: {'mcq': 9, 'short': 8}
- Problems: none

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 4/17 answers supported (exact or strong) = 23.5%
- Tiers: {'exact': 3, 'strong': 1, 'partial': 2, 'unsupported': 11}
- Mean best-window recall: 0.416
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 17, 'odd_one_out': 0, 'restatement': 0, 'trivial': 0}
- Extractive items supported: 4/17 = 23.5% (mean window recall 0.416)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 0.0%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 10

  - **module 1 / lesson 1 / item 2** (extractive) novel 100%: They are more likely to die or fail to reproduce.
  - **module 1 / lesson 1 / item 3** (extractive) novel 67%: The adaptation of species to their environment
  - **module 1 / lesson 1 / item 4** (extractive) novel 75%: They are left unchanged and continue to fluctuate.
  - **module 1 / lesson 2 / item 2** (extractive) novel 62%: the advantage which certain individuals have over others, in respect to the possession of the one sex by the other
  - **module 1 / lesson 2 / item 3** (extractive) novel 86%: the peacock's tail, where males have a more elaborate display of feathers
  - **module 1 / lesson 2 / item 4** (extractive) novel 67%: it decreases genetic variation
  - **module 2 / lesson 1 / item 2** (extractive) novel 86%: They are more likely to survive and reproduce, passing on their advantageous traits to their offspring
  - **module 2 / lesson 1 / item 3** (extractive) novel 75%: The population becomes more diverse and distinct
  - **module 2 / lesson 1 / item 4** (extractive) novel 100%: A larger beak in a population of finches
  - **module 2 / lesson 2 / item 3** (extractive) novel 100%: Adaptation to environment

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 2** (What is Natural Selection?)
  - Q: What happens to individuals with traits that are not beneficial to their survival?
  - Expected answer: `They are more likely to die or fail to reproduce.`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 1 / lesson 1 / item 3** (What is Natural Selection?)
  - Q: What is the result of natural selection over many generations?
  - Expected answer: `The adaptation of species to their environment`
  - Best window recall 0.33, global token recall 0.33
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 1 / lesson 1 / item 4** (What is Natural Selection?)
  - Q: How does natural selection affect traits that are neither useful nor injurious?
  - Expected answer: `They are left unchanged and continue to fluctuate.`
  - Best window recall 0.25, global token recall 0.25
  - Closest source text: `in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither useful nor injurious would not be affected by natural selection and would be left`

- **module 1 / lesson 2 / item 2** (Sexual Selection and Interbreeding)
  - Q: What is sexual selection?
  - Expected answer: `the advantage which certain individuals have over others, in respect to the possession of the one sex by the other`
  - Best window recall 0.38, global token recall 0.38
  - Closest source text: `battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others`

- **module 1 / lesson 2 / item 3** (Sexual Selection and Interbreeding)
  - Q: What is an example of sexual selection in nature?
  - Expected answer: `the peacock's tail, where males have a more elaborate display of feathers`
  - Best window recall 0.14, global token recall 0.14
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 1 / lesson 2 / item 4** (Sexual Selection and Interbreeding)
  - Q: What is the effect of small population size on genetic variation?
  - Expected answer: `it decreases genetic variation`
  - Best window recall 0.33, global token recall 0.33
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 2 / lesson 1 / item 2** (The Process of Natural Selection)
  - Q: What happens to individuals with advantageous traits during the process of natural selection?
  - Expected answer: `They are more likely to survive and reproduce, passing on their advantageous traits to their offspring`
  - Best window recall 0.14, global token recall 0.14
  - Closest source text: `way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive`

- **module 2 / lesson 1 / item 3** (The Process of Natural Selection)
  - Q: What is the result of natural selection acting on a population over many generations?
  - Expected answer: `The population becomes more diverse and distinct`
  - Best window recall 0.25, global token recall 0.25
  - Closest source text: `mind in what an endless number of strange peculiarities our domestic productions and in a lesser degree those under nature vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes`

- **module 2 / lesson 1 / item 4** (The Process of Natural Selection)
  - Q: What is an example of an adaptation that could result from natural selection?
  - Expected answer: `A larger beak in a population of finches`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 2 / lesson 2 / item 2** (Grouping of Organic Beings)
  - Q: What happens to individuals with variations that are harmful?
  - Expected answer: `They are less likely to survive and reproduce`
  - Best window recall 0.25, global token recall 0.25
  - Closest source text: `way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive`

- **module 2 / lesson 2 / item 3** (Grouping of Organic Beings)
  - Q: What is the result of natural selection acting on a population?
  - Expected answer: `Adaptation to environment`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

### Answerability (answer vs its own lesson content)

- 11/17 answerable from the lesson alone = 64.7%
- Tiers: {'exact': 7, 'strong': 4, 'partial': 4, 'unsupported': 2}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 4

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 3** (What is Natural Selection?)
  - Q: What is the result of natural selection over many generations?
  - Expected answer: `The adaptation of species to their environment`
  - Best window recall against lesson: 0.33

- **module 1 / lesson 1 / item 4** (What is Natural Selection?)
  - Q: How does natural selection affect traits that are neither useful nor injurious?
  - Expected answer: `They are left unchanged and continue to fluctuate.`
  - Best window recall against lesson: 0.00

### Concept coverage across the source

- 10/18 concepts anchored to a source chunk (8 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [10]
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

- Mean chunk recall: 47.4%
- Worst chunk: 0 at 47.4%
- Chunks under 50% covered: 1
- Lessons routed per segment: [4]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 2,498 | 19 | 9 | 47.4% | 0.563 |
