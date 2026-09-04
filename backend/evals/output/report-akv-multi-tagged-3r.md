# StudyForge generation eval

## Headline metrics

| Metric | multi-darwin-pep8 |
|---|---|
| Lessons | 7 |
| Quiz items | 41 |
| Structure problems | 0 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.4878 |
| Grounded, extractive items only | 0.5 |
| Ungrounded items, all | 7 |
| Ungrounded extractive items | 6 |
| Hallucination candidates | 1 |
| Mean grounding recall | 0.7451 |
| Answerable from lesson | 0.6341 |
| Unanswerable items | 3 |
| Giveaway MCQs | 5 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.52 |
| Concentration vs chunk length | 1.9291 |
| Source recall, mean chunk | 0.9725 |
| Source recall, worst chunk | 0.9531 |
| Cost USD | 0.7864 |
| Wall clock s | 348 |

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
| lesson | 7 | 16,219 | 26,044 | $0.7322 | 47.3 | 58.0 |
| outline | 1 | 5,101 | 1,150 | $0.0543 | 17.1 | 17.1 |

### Structure

- 3 modules, 7 lessons, 41 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 5]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 6321, min 4699
- Item kinds: {'mcq': 27, 'short': 14}
- Problems: none

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 20/41 answers supported (exact or strong) = 48.8%
- Tiers: {'exact': 7, 'strong': 13, 'partial': 14, 'unsupported': 7}
- Mean best-window recall: 0.745
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 36, 'odd_one_out': 0, 'restatement': 5, 'trivial': 0}
- Extractive items supported: 18/36 = 50.0% (mean window recall 0.757)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 12.4%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 1

  - **module 2 / lesson 1 / item 2** (extractive) novel 67%: To supply evidence that predators hunting by sight destroy conspicuously coloured birds most

#### Ungrounded extractive items

- **module 1 / lesson 3 / item 2** (Nature's Selection Compared with Man's)
  - Q: Darwin lists the breeder who feeds long-beaked and short-beaked pigeons the same food and exposes long- and short-woolled sheep to the same climate. What point do these examples establish?
  - Expected answer: `That the breeder preserves characters without ever exercising or testing them, whereas nature fully exercises every character she selects`
  - Best window recall 0.46, global token recall 0.62
  - Closest source text: `of life man selects only for his own good nature only for that of the being which she tends every selected character is fully exercised by her and the being is placed under well suited conditions of life man keeps the natives of many climates in the same country he seldom exercises`

- **module 2 / lesson 1 / item 2** (The Silent and Insensible Work of Selection)
  - Q: Why does Darwin mention that on parts of the Continent people are warned not to keep white pigeons?
  - Expected answer: `To supply evidence that predators hunting by sight destroy conspicuously coloured birds most`
  - Best window recall 0.11, global token recall 0.33
  - Closest source text: `long backed or long legged quadruped in any peculiar manner he exposes sheep with long and short wool to the same climate he does not allow the most vigorous males to struggle for the females he does not rigidly destroy`

- **module 2 / lesson 1 / item 4** (The Silent and Insensible Work of Selection)
  - Q: How does Darwin use Downing's observations about smooth versus downy fruits and purple versus yellow plums?
  - Expected answer: `He argues that if such differences matter even with all the aids of art, they would decide success in nature`
  - Best window recall 0.44, global token recall 0.56
  - Closest source text: `whereas another disease attacks yellow fleshed peaches far more than those with other coloured flesh if with all the aids of art these slight differences make a great difference in cultivating the several varieties assuredly in a state of nature`

- **module 3 / lesson 1 / item 3** (What PEP 8 Is and What It Covers)
  - Q: PEP 8 records its Status as "Active" and its Type as "Process". Which reading of those fields is consistent with what the document says about itself?
  - Expected answer: `It is a living document that keeps evolving as conventions appear and the language changes, and it describes practice rather than altering the language`
  - Best window recall 0.33, global token recall 0.42
  - Closest source text: `this document and pep 257 docstring conventions were adapted from guido s original python style guide essay with some additions from barry s style guide 2 this style guide evolves over time as additional conventions are identified and past conventions are rendered obsolete by changes in the language`

- **module 3 / lesson 1 / item 5** (What PEP 8 Is and What It Covers)
  - Q: In the section "A Foolish Consistency is the Hobgoblin of Little Minds", PEP 8 ranks three kinds of consistency. Which is described as the most important?
  - Expected answer: `Consistency within one module or function`
  - Best window recall 0.40, global token recall 1.00
  - Closest source text: `table of contents introduction a foolish consistency is the hobgoblin of little minds code lay out indentation tabs or spaces maximum line length should a line break before or after a binary operator blank lines source file encoding imports module`

- **module 3 / lesson 2 / item 3** (Readability, Consistency, and Their Limits)
  - Q: PEP 8 ranks three kinds of consistency. Which statement matches its ranking?
  - Expected answer: `Consistency within one module or function outranks consistency within a project, which outranks consistency with PEP 8.`
  - Best window recall 0.44, global token recall 0.89
  - Closest source text: `to improve the readability of code and make it consistent across the wide spectrum of python code as pep 20 says readability counts a style guide is about consistency consistency with this style guide is important consistency within a project`

### Answerability (answer vs its own lesson content)

- 26/41 answerable from the lesson alone = 63.4%
- Tiers: {'exact': 8, 'strong': 18, 'partial': 12, 'unsupported': 3}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 5

#### Items not answerable from their lesson

- **module 1 / lesson 3 / item 2** (Nature's Selection Compared with Man's)
  - Q: Darwin lists the breeder who feeds long-beaked and short-beaked pigeons the same food and exposes long- and short-woolled sheep to the same climate. What point do these examples establish?
  - Expected answer: `That the breeder preserves characters without ever exercising or testing them, whereas nature fully exercises every character she selects`
  - Best window recall against lesson: 0.38

- **module 2 / lesson 1 / item 2** (The Silent and Insensible Work of Selection)
  - Q: Why does Darwin mention that on parts of the Continent people are warned not to keep white pigeons?
  - Expected answer: `To supply evidence that predators hunting by sight destroy conspicuously coloured birds most`
  - Best window recall against lesson: 0.33

- **module 3 / lesson 1 / item 3** (What PEP 8 Is and What It Covers)
  - Q: PEP 8 records its Status as "Active" and its Type as "Process". Which reading of those fields is consistent with what the document says about itself?
  - Expected answer: `It is a living document that keeps evolving as conventions appear and the language changes, and it describes practice rather than altering the language`
  - Best window recall against lesson: 0.42

### Concept coverage across the source

- 25/35 concepts anchored to a source chunk (10 unanchored)
- Chunks containing at least one concept: 3/3 (100.0%)
- Concepts per chunk: [13, 3, 9]
- Lessons per chunk: [0, 0, 2]
- Uncovered chunk indexes: none
- Largest share in one chunk: 52.0%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.5965, 0.2169, 0.1866]
- Actual share per chunk: [0.52, 0.12, 0.36]
- Actual/expected: [0.8717, 0.5533, 1.9291]
- Worst concentration ratio: 1.93

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 97.2%
- Worst chunk: 0 at 95.3%
- Chunks under 50% covered: 0
- Lessons routed per segment: [3, 2, 2]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 61 | 95.3% | 0.952 |
| 1 | 2,747 | 28 | 27 | 96.4% | 0.903 |
| 2 | 3,000 | 9 | 9 | 100.0% | 0.963 |
