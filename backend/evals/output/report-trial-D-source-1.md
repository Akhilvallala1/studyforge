# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 8 |
| Quiz items | 48 |
| Structure problems | 2 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.4583 |
| Grounded, extractive items only | 0.5 |
| Ungrounded items, all | 12 |
| Ungrounded extractive items | 10 |
| Hallucination candidates | 6 |
| Mean grounding recall | 0.7019 |
| Answerable from lesson | 0.5833 |
| Unanswerable items | 3 |
| Giveaway MCQs | 4 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 0.8655 |
| Wall clock s | 417.75 |

## prose-short

Source: text `darwin-origin-short`, 2,498 chars, 1 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 8 | 8 | 0 | 0 | 8 | 8 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 8 | 11,685 | 30,679 | $0.8254 | 50.1 | 56.4 |
| outline | 1 | 984 | 1,406 | $0.0401 | 16.7 | 16.7 |

### Structure

- 3 modules, 8 lessons, 48 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 6220, min 5281
- Item kinds: {'mcq': 32, 'short': 16}
- Problems: {'duplicate_question': 2}

  - `duplicate_question` at module 3 / lesson 1 / item 2: also at module 1 / lesson 1 / item 4
  - `duplicate_question` at module 3 / lesson 2 / item 2: also at module 1 / lesson 3 / item 3

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 22/48 answers supported (exact or strong) = 45.8%
- Tiers: {'exact': 7, 'strong': 15, 'partial': 14, 'unsupported': 12}
- Mean best-window recall: 0.702
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 44, 'odd_one_out': 0, 'restatement': 4, 'trivial': 0}
- Extractive items supported: 22/44 = 50.0% (mean window recall 0.724)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 34.5%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 6

  - **module 1 / lesson 2 / item 2** (extractive) novel 100%: Every part of the constitution has some give in it, though the amount of give is limited
  - **module 1 / lesson 2 / item 3** (restatement) novel 61%: Because variation alone would be useless if it were not transmitted: a favourable peculiarity would die with the individual. Strong heredity means that once a v
  - **module 1 / lesson 2 / item 6** (extractive) novel 80%: It makes slight differences consequential, so there are countless ways a variation can help or harm its possessor
  - **module 2 / lesson 1 / item 6** (extractive) novel 80%: It makes it plausible that even a slight change could matter to a being embedded in such a dense web of relations
  - **module 2 / lesson 2 / item 3** (extractive) novel 71%: As a tentative possible instance of indifferent variation, hedged with 'perhaps'
  - **module 2 / lesson 2 / item 6** (extractive) novel 67%: A variation that helped an individual live but left no offspring would contribute nothing to the process

#### Ungrounded extractive items

- **module 1 / lesson 2 / item 2** (Variation, Plasticity, and Heredity)
  - Q: Darwin writes that 'under domestication, it may be truly said that the whole organisation becomes in some degree plastic.' Which reading matches the qualifications in that sentence?
  - Expected answer: `Every part of the constitution has some give in it, though the amount of give is limited`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 1 / lesson 2 / item 6** (Variation, Plasticity, and Heredity)
  - Q: What role does the premise about the 'infinitely complex and close-fitting' mutual relations of organic beings play in the argument?
  - Expected answer: `It makes slight differences consequential, so there are countless ways a variation can help or harm its possessor`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation`

- **module 1 / lesson 3 / item 1** (The Web of Mutual Relations)
  - Q: Darwin describes the mutual relations of organic beings with two adjectives. According to the lesson, what does each contribute to his argument?
  - Expected answer: `'Infinitely complex' means the relations are numerous and varied; 'close-fitting' means they are tight, so small differences in a being can matter`
  - Best window recall 0.42, global token recall 0.50
  - Closest source text: `and in a lesser degree those under nature vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations`

- **module 1 / lesson 3 / item 4** (The Web of Mutual Relations)
  - Q: Why does Darwin insert the parenthetical reminder that many more individuals are born than can possibly survive?
  - Expected answer: `Because it explains why even a very slight advantage improves an individual's chance of surviving and procreating`
  - Best window recall 0.45, global token recall 0.64
  - Closest source text: `in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating`

- **module 1 / lesson 3 / item 6** (The Web of Mutual Relations)
  - Q: Which statement best captures how the lesson describes the role of the 'web of mutual relations' in Darwin's chain of reasoning?
  - Expected answer: `It is the hinge between the facts about variation and the conclusion that some variations will be useful`
  - Best window recall 0.43, global token recall 0.57
  - Closest source text: `their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither useful`

- **module 2 / lesson 1 / item 6** (The Core Argument)
  - Q: What work does the premise about the 'infinitely complex and close-fitting' mutual relations of organic beings do in the argument?
  - Expected answer: `It makes it plausible that even a slight change could matter to a being embedded in such a dense web of relations`
  - Best window recall 0.10, global token recall 0.20
  - Closest source text: `vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations`

- **module 2 / lesson 2 / item 3** (The Definition and Its Limits)
  - Q: How does Darwin present polymorphic species in this passage?
  - Expected answer: `As a tentative possible instance of indifferent variation, hedged with 'perhaps'`
  - Best window recall 0.14, global token recall 0.29
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 2 / lesson 2 / item 6** (The Definition and Its Limits)
  - Q: Darwin writes that a favoured individual has the best chance of 'surviving and of procreating their kind'. Why does the second element matter to the argument?
  - Expected answer: `A variation that helped an individual live but left no offspring would contribute nothing to the process`
  - Best window recall 0.11, global token recall 0.22
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 3 / lesson 1 / item 3** (Scope and Reach of Selection)
  - Q: How does "Sexual Selection" appear in the chapter summary?
  - Expected answer: `As a separate listed topic, standing on its own after the three powers of natural selection`
  - Best window recall 0.22, global token recall 0.22
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 3 / lesson 3 / item 6** (Divergence, Extinction, and the Grouping of Life)
  - Q: How does the chapter heading characterise the relationship between extinction and natural selection?
  - Expected answer: `Extinction is presented as something natural selection itself brings about`
  - Best window recall 0.43, global token recall 0.43
  - Closest source text: `trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction`

### Answerability (answer vs its own lesson content)

- 28/48 answerable from the lesson alone = 58.3%
- Tiers: {'exact': 7, 'strong': 21, 'partial': 17, 'unsupported': 3}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 4

#### Items not answerable from their lesson

- **module 1 / lesson 2 / item 2** (Variation, Plasticity, and Heredity)
  - Q: Darwin writes that 'under domestication, it may be truly said that the whole organisation becomes in some degree plastic.' Which reading matches the qualifications in that sentence?
  - Expected answer: `Every part of the constitution has some give in it, though the amount of give is limited`
  - Best window recall against lesson: 0.29

- **module 1 / lesson 2 / item 6** (Variation, Plasticity, and Heredity)
  - Q: What role does the premise about the 'infinitely complex and close-fitting' mutual relations of organic beings play in the argument?
  - Expected answer: `It makes slight differences consequential, so there are countless ways a variation can help or harm its possessor`
  - Best window recall against lesson: 0.30

- **module 3 / lesson 3 / item 6** (Divergence, Extinction, and the Grouping of Life)
  - Q: How does the chapter heading characterise the relationship between extinction and natural selection?
  - Expected answer: `Extinction is presented as something natural selection itself brings about`
  - Best window recall against lesson: 0.43

### Concept coverage across the source

- 30/40 concepts anchored to a source chunk (10 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [30]
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
- Lessons routed per segment: [8]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 2,498 | 19 | 19 | 100.0% | 1.000 |
