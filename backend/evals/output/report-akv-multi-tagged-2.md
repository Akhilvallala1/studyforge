# StudyForge generation eval

## Headline metrics

| Metric | multi-darwin-pep8 |
|---|---|
| Lessons | 7 |
| Quiz items | 41 |
| Structure problems | 5 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.6098 |
| Grounded, extractive items only | 0.6857 |
| Ungrounded items, all | 1 |
| Ungrounded extractive items | 1 |
| Hallucination candidates | 0 |
| Mean grounding recall | 0.8299 |
| Answerable from lesson | 0.6585 |
| Unanswerable items | 2 |
| Giveaway MCQs | 4 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.4091 |
| Concentration vs chunk length | 2.1922 |
| Source recall, mean chunk | 0.9583 |
| Source recall, worst chunk | 0.875 |
| Cost USD | 0.7477 |
| Wall clock s | 336.59 |

## multi-darwin-pep8

Source: text `darwin-origin + pep8-style-guide`, 13,639 chars, 3 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 7 | 7 | 2 | 0 | 7 | 7 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 7 | 16,083 | 24,692 | $0.6977 | 46.0 | 52.6 |
| outline | 1 | 5,101 | 978 | $0.0500 | 14.7 | 14.7 |

### Structure

- 3 modules, 7 lessons, 41 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 5]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 4]
- Lesson content chars: mean 5887, min 5099
- Item kinds: {'mcq': 27, 'short': 14}
- Problems: {'empty_concept': 5}

  - `empty_concept` at module 3 / lesson 2 / item 1: According to PEP 8, which kind of consistency is the most important?
  - `empty_concept` at module 3 / lesson 2 / item 2: What is 'one of Guido's key insights' that PEP 8 cites as the reason for its guidelines?
  - `empty_concept` at module 3 / lesson 2 / item 3: Your team's own written style guide conflicts with a recommendation in PEP 8. What does PEP 8 itself say should happen?
  - `empty_concept` at module 3 / lesson 2 / item 4: Which statement about the scope and history of PEP 8 matches the document?
  - `empty_concept` at module 3 / lesson 2 / item 5: PEP 8 says the style guide 'evolves over time'. Give the two causes it names for that evolution.

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 25/41 answers supported (exact or strong) = 61.0%
- Tiers: {'exact': 3, 'strong': 22, 'partial': 15, 'unsupported': 1}
- Mean best-window recall: 0.830
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 35, 'odd_one_out': 0, 'restatement': 6, 'trivial': 0}
- Extractive items supported: 24/35 = 68.6% (mean window recall 0.851)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 12.9%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 0

#### Ungrounded extractive items

- **module 3 / lesson 2 / item 1** (A Foolish Consistency Is the Hobgoblin of Little Minds)
  - Q: According to PEP 8, which kind of consistency is the most important?
  - Expected answer: `Consistency within one module or function`
  - Best window recall 0.40, global token recall 1.00
  - Closest source text: `table of contents introduction a foolish consistency is the hobgoblin of little minds code lay out indentation tabs or spaces maximum line length should a line break before or after a binary operator blank lines source file encoding imports module`

### Answerability (answer vs its own lesson content)

- 27/41 answerable from the lesson alone = 65.9%
- Tiers: {'exact': 5, 'strong': 22, 'partial': 12, 'unsupported': 2}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 4

#### Items not answerable from their lesson

- **module 2 / lesson 1 / item 5** (Silent and Insensible Work)
  - Q: According to the horticulturist Downing, cited by Darwin, which fruits suffer far more from the curculio beetle in the United States?
  - Expected answer: `Smooth-skinned fruits, compared with those bearing down`
  - Best window recall against lesson: 0.20

- **module 2 / lesson 2 / item 4** (Characters of Trifling Importance)
  - Q: What point is Darwin making with the flock of white sheep and the lamb with the faintest trace of black?
  - Expected answer: `That the occasional destruction of an animal of a particular colour is far from negligible in keeping a colour constant`
  - Best window recall against lesson: 0.44

### Concept coverage across the source

- 22/34 concepts anchored to a source chunk (12 unanchored)
- Chunks containing at least one concept: 3/3 (100.0%)
- Concepts per chunk: [9, 4, 9]
- Lessons per chunk: [0, 0, 2]
- Uncovered chunk indexes: none
- Largest share in one chunk: 40.9%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.5965, 0.2169, 0.1866]
- Actual share per chunk: [0.4091, 0.1818, 0.4091]
- Actual/expected: [0.6858, 0.8384, 2.1922]
- Worst concentration ratio: 2.19

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 95.8%
- Worst chunk: 0 at 87.5%
- Chunks under 50% covered: 0
- Lessons routed per segment: [3, 2, 2]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 56 | 87.5% | 0.853 |
| 1 | 2,747 | 28 | 28 | 100.0% | 0.946 |
| 2 | 3,000 | 9 | 9 | 100.0% | 1.000 |
