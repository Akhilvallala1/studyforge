# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 8 |
| Quiz items | 30 |
| Structure problems | 2 |
| Strict JSON first try | 0.9 |
| Hard parse failures | 1 |
| Grounded, all items (old metric) | 0.1333 |
| Grounded, extractive items only | 0.1538 |
| Ungrounded items, all | 20 |
| Ungrounded extractive items | 17 |
| Hallucination candidates | 13 |
| Mean grounding recall | 0.3677 |
| Answerable from lesson | 0.1667 |
| Unanswerable items | 9 |
| Giveaway MCQs | 1 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 0.4211 |
| Source recall, worst chunk | 0.4211 |
| Cost USD | 0 |
| Wall clock s | 1002.92 |

## prose-short

Source: text `darwin-origin-short`, 2,498 chars, 1 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 9 | 8 | 0 | 0 | 8 | 8 | 1 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 9 | 8,723 | 13,008 | $0.0000 | 103.0 | 125.6 |
| outline | 1 | 675 | 938 | $0.0000 | 76.4 | 76.4 |

### Structure

- 4 modules, 8 lessons, 30 quiz items
- Quiz items per lesson: [4, 3, 4, 4, 4, 4, 3, 4]
- Concepts per lesson: [4, 5, 4, 5, 4, 5, 4, 4]
- Lesson content chars: mean 1145, min 829
- Item kinds: {'mcq': 24, 'short': 6}
- Problems: {'mcq_answer_not_in_options': 1, 'duplicate_question': 1}

  - `mcq_answer_not_in_options` at module 2 / lesson 1 / item 3: answer="'rigidly destroyed' by natural selection"
  - `duplicate_question` at module 2 / lesson 2 / item 3: also at module 2 / lesson 1 / item 1

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 4/30 answers supported (exact or strong) = 13.3%
- Tiers: {'exact': 3, 'strong': 1, 'partial': 6, 'unsupported': 20}
- Mean best-window recall: 0.368
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 1

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 26, 'odd_one_out': 1, 'restatement': 3, 'trivial': 0}
- Extractive items supported: 4/26 = 15.4% (mean window recall 0.387)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 50.1%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 13

  - **module 1 / lesson 1 / item 1** (extractive) novel 75%: Artificial selection is driven by human preferences, while natural selection is random
  - **module 1 / lesson 1 / item 2** (odd_one_out) novel 100%: Human preferences
  - **module 2 / lesson 1 / item 1** (extractive) novel 83%: Organisms can pass on inherited trait variations more easily
  - **module 2 / lesson 2 / item 3** (extractive) novel 86%: That heredity allows traits to be reliably passed down and modified over generations
  - **module 3 / lesson 1 / item 3** (extractive) novel 67%: It allows advantageous variations to persist across generations
  - **module 3 / lesson 2 / item 2** (extractive) novel 80%: By eliminating species that lack advantageous traits
  - **module 3 / lesson 2 / item 3** (extractive) novel 83%: It removes species that fail to adapt to environmental pressures
  - **module 3 / lesson 2 / item 4** (extractive) novel 75%: Because they all evolved from a single ancestor
  - **module 4 / lesson 1 / item 2** (extractive) novel 80%: It accelerates divergence by restricting genetic exchange
  - **module 4 / lesson 1 / item 3** (restatement) novel 78%: It increases competition for limited resources, making small advantages critical for survival
  - **module 4 / lesson 2 / item 1** (extractive) novel 75%: Variations that enhance mating success
  - **module 4 / lesson 2 / item 2** (extractive) novel 83%: It focuses on traits that increase reproductive success, not survival
  - **module 4 / lesson 2 / item 4** (extractive) novel 100%: Competing with rivals for access to mates

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 1** (Comparing Natural and Artificial Selection)
  - Q: What is the primary difference between natural selection and artificial selection?
  - Expected answer: `Artificial selection is driven by human preferences, while natural selection is random`
  - Best window recall 0.25, global token recall 0.25
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 1 / lesson 1 / item 3** (Comparing Natural and Artificial Selection)
  - Q: Why do advantageous variations persist in natural selection?
  - Expected answer: `They are selected for because they improve survival and reproduction`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 1 / lesson 2 / item 2** (The Struggle for Existence)
  - Q: Why does Darwin argue that variations useful in the 'struggle for existence' are preserved?
  - Expected answer: `Because they increase an organism's chances of surviving and reproducing`
  - Best window recall 0.14, global token recall 0.29
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 2 / lesson 1 / item 1** (Inherent Variability in Organisms)
  - Q: What does Darwin mean by 'the whole organisation becomes in some degree plastic' under domestication?
  - Expected answer: `Organisms can pass on inherited trait variations more easily`
  - Best window recall 0.17, global token recall 0.17
  - Closest source text: `plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations`

- **module 2 / lesson 1 / item 2** (Inherent Variability in Organisms)
  - Q: Why does Darwin mention 'polymorphic' species in the context of natural selection?
  - Expected answer: `To illustrate how variation exists without selective pressure`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 2 / lesson 2 / item 2** (Lesson)
  - Q: Why are neutral variations described as 'fluctuating elements'?
  - Expected answer: `They neither improve nor harm survival, so they persist`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither`

- **module 2 / lesson 2 / item 3** (Lesson)
  - Q: What does Darwin mean by 'the whole organisation becomes in some degree plastic' under domestication?
  - Expected answer: `That heredity allows traits to be reliably passed down and modified over generations`
  - Best window recall 0.14, global token recall 0.14
  - Closest source text: `be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations`

- **module 2 / lesson 2 / item 4** (Lesson)
  - Q: Which outcome is most directly caused by the 'struggle for existence'?
  - Expected answer: `Individuals with advantageous traits surviving and reproducing more`
  - Best window recall 0.40, global token recall 0.40
  - Closest source text: `the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving`

- **module 3 / lesson 1 / item 3** (Divergence and Extinction)
  - Q: How does the text describe the role of heredity in natural selection?
  - Expected answer: `It allows advantageous variations to persist across generations`
  - Best window recall 0.33, global token recall 0.33
  - Closest source text: `be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations`

- **module 3 / lesson 2 / item 1** (Grouping of Organic Beings)
  - Q: What does natural selection primarily act upon according to Darwin's explanation?
  - Expected answer: `Variations that confer survival advantages`
  - Best window recall 0.25, global token recall 0.25
  - Closest source text: `plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations`

- **module 3 / lesson 2 / item 2** (Grouping of Organic Beings)
  - Q: How does natural selection contribute to the grouping of species in taxonomic classifications?
  - Expected answer: `By eliminating species that lack advantageous traits`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 3 / lesson 2 / item 3** (Grouping of Organic Beings)
  - Q: What role does extinction play in the process of natural selection according to the passage?
  - Expected answer: `It removes species that fail to adapt to environmental pressures`
  - Best window recall 0.17, global token recall 0.17
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 3 / lesson 2 / item 4** (Grouping of Organic Beings)
  - Q: Why do species within the same taxonomic group often share similar characteristics?
  - Expected answer: `Because they all evolved from a single ancestor`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 4 / lesson 1 / item 2** (Circumstances Favoring Selection)
  - Q: How does isolation influence evolutionary trajectories according to Darwin?
  - Expected answer: `It accelerates divergence by restricting genetic exchange`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence`

- **module 4 / lesson 2 / item 1** (Sexual Selection and Its Impact)
  - Q: What does sexual selection primarily act upon, according to Darwin's text?
  - Expected answer: `Variations that enhance mating success`
  - Best window recall 0.25, global token recall 0.25
  - Closest source text: `plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations`

- **module 4 / lesson 2 / item 2** (Sexual Selection and Its Impact)
  - Q: How does sexual selection differ from natural selection, as implied in the source?
  - Expected answer: `It focuses on traits that increase reproductive success, not survival`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 4 / lesson 2 / item 4** (Sexual Selection and Its Impact)
  - Q: Which of the following is a key mechanism of sexual selection?
  - Expected answer: `Competing with rivals for access to mates`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

### Answerability (answer vs its own lesson content)

- 5/30 answerable from the lesson alone = 16.7%
- Tiers: {'exact': 3, 'strong': 2, 'partial': 16, 'unsupported': 9}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 1

#### Items not answerable from their lesson

- **module 1 / lesson 2 / item 2** (The Struggle for Existence)
  - Q: Why does Darwin argue that variations useful in the 'struggle for existence' are preserved?
  - Expected answer: `Because they increase an organism's chances of surviving and reproducing`
  - Best window recall against lesson: 0.29

- **module 2 / lesson 1 / item 1** (Inherent Variability in Organisms)
  - Q: What does Darwin mean by 'the whole organisation becomes in some degree plastic' under domestication?
  - Expected answer: `Organisms can pass on inherited trait variations more easily`
  - Best window recall against lesson: 0.17

- **module 2 / lesson 1 / item 2** (Inherent Variability in Organisms)
  - Q: Why does Darwin mention 'polymorphic' species in the context of natural selection?
  - Expected answer: `To illustrate how variation exists without selective pressure`
  - Best window recall against lesson: 0.40

- **module 2 / lesson 1 / item 4** (Inherent Variability in Organisms)
  - Q: How does Darwin describe the relationship between variation and survival?
  - Expected answer: `Individuals with advantageous variations have 'the best chance of surviving and of procreating their kind'`
  - Best window recall against lesson: 0.12

- **module 2 / lesson 2 / item 4** (Lesson)
  - Q: Which outcome is most directly caused by the 'struggle for existence'?
  - Expected answer: `Individuals with advantageous traits surviving and reproducing more`
  - Best window recall against lesson: 0.40

- **module 3 / lesson 1 / item 2** (Divergence and Extinction)
  - Q: Which type of variation is preserved by natural selection according to the text?
  - Expected answer: `Variations useful to the organism`
  - Best window recall against lesson: 0.33

- **module 3 / lesson 1 / item 3** (Divergence and Extinction)
  - Q: How does the text describe the role of heredity in natural selection?
  - Expected answer: `It allows advantageous variations to persist across generations`
  - Best window recall against lesson: 0.33

- **module 3 / lesson 2 / item 3** (Grouping of Organic Beings)
  - Q: What role does extinction play in the process of natural selection according to the passage?
  - Expected answer: `It removes species that fail to adapt to environmental pressures`
  - Best window recall against lesson: 0.17

- **module 4 / lesson 1 / item 2** (Circumstances Favoring Selection)
  - Q: How does isolation influence evolutionary trajectories according to Darwin?
  - Expected answer: `It accelerates divergence by restricting genetic exchange`
  - Best window recall against lesson: 0.20

### Concept coverage across the source

- 12/35 concepts anchored to a source chunk (23 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [12]
- Lessons per chunk: [0]
- Uncovered chunk indexes: none
- Largest share in one chunk: 100.0%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [1.0]
- Actual share per chunk: [1.0]
- Actual/expected: [1.0]
- Worst concentration ratio: 1.00

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 42.1%
- Worst chunk: 0 at 42.1%
- Chunks under 50% covered: 1
- Lessons routed per segment: [8]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 2,498 | 19 | 8 | 42.1% | 0.538 |
