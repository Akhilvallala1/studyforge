# StudyForge generation eval

## Headline metrics

| Metric | multi-darwin-pep8 |
|---|---|
| Lessons | 6 |
| Quiz items | 36 |
| Structure problems | 0 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.5556 |
| Grounded, extractive items only | 0.5588 |
| Ungrounded items, all | 6 |
| Ungrounded extractive items | 6 |
| Hallucination candidates | 1 |
| Mean grounding recall | 0.73 |
| Answerable from lesson | 0.6111 |
| Unanswerable items | 4 |
| Giveaway MCQs | 2 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.5238 |
| Concentration vs chunk length | 2.2966 |
| Source recall, mean chunk | 0.9568 |
| Source recall, worst chunk | 0.9062 |
| Cost USD | 0.6834 |
| Wall clock s | 298.81 |

## multi-darwin-pep8

Source: text `darwin-origin + pep8-style-guide`, 13,639 chars, 3 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 6 | 6 | 1 | 0 | 6 | 6 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 6 | 14,887 | 21,919 | $0.6224 | 46.6 | 50.5 |
| outline | 1 | 5,101 | 1,421 | $0.0610 | 19.5 | 19.5 |

### Structure

- 2 modules, 6 lessons, 36 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 6045, min 4557
- Item kinds: {'mcq': 25, 'short': 11}
- Problems: none

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 20/36 answers supported (exact or strong) = 55.6%
- Tiers: {'exact': 4, 'strong': 16, 'partial': 10, 'unsupported': 6}
- Mean best-window recall: 0.730
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 34, 'odd_one_out': 1, 'restatement': 1, 'trivial': 0}
- Extractive items supported: 19/34 = 55.9% (mean window recall 0.728)
- Odd-one-out items: mean share of their distractors found in the source = 100.0%
- Restatement items: mean share of answer words absent from the source = 0.0%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 1

  - **module 1 / lesson 4 / item 3** (extractive) novel 73%: It gives everyday evidence that conspicuous colour raises the risk of destruction by sight-hunting predators

#### Ungrounded extractive items

- **module 1 / lesson 2 / item 2** (Circumstances Favourable to Selection: A Country Under Change)
  - Q: According to the lesson, what does an island or a barrier-bounded country contribute to the work of natural selection?
  - Expected answer: `It keeps vacant places from being seized by immigrants, so modified natives can come to fill them`
  - Best window recall 0.33, global token recall 0.67
  - Closest source text: `have places in the economy of nature which would assuredly be better filled up if some of the original inhabitants were in some manner modified for had the area been open to immigration these same places would have been seized`

- **module 1 / lesson 3 / item 2** (Nature's Selection Compared with Man's)
  - Q: Darwin lists the breeder feeding a long-beaked and a short-beaked pigeon on the same food, and exposing long- and short-woolled sheep to the same climate. What point are these examples meant to make?
  - Expected answer: `That the breeder selects a character without ever exercising it under the conditions that would suit it`
  - Best window recall 0.43, global token recall 0.43
  - Closest source text: `on the whole machinery of life man selects only for his own good nature only for that of the being which she tends every selected character is fully exercised by her and the being is placed under well suited conditions`

- **module 1 / lesson 4 / item 1** (Selection Acting on Characters of Trifling Importance)
  - Q: According to Darwin, why do we see nothing of natural selection's changes while they are in progress?
  - Expected answer: `Because it works silently and insensibly, and only the long lapse of ages makes its effects visible`
  - Best window recall 0.30, global token recall 0.60
  - Closest source text: `opportunity offers at the improvement of each organic being in relation to its organic and inorganic conditions of life we see nothing of these slow changes in progress until the hand of time has marked the long lapse of ages`

- **module 1 / lesson 4 / item 3** (Selection Acting on Characters of Trifling Importance)
  - Q: What role does the warning against keeping white pigeons play in Darwin's argument?
  - Expected answer: `It gives everyday evidence that conspicuous colour raises the risk of destruction by sight-hunting predators`
  - Best window recall 0.18, global token recall 0.27
  - Closest source text: `so much so that on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour`

- **module 1 / lesson 4 / item 6** (Selection Acting on Characters of Trifling Importance)
  - Q: What point does the flock of white sheep illustrate?
  - Expected answer: `That consistently destroying every individual with the faintest deviation is enough to keep a trifling character constant`
  - Best window recall 0.27, global token recall 0.73
  - Closest source text: `acquired true and constant nor ought we to think that the occasional destruction of an animal of any particular colour would produce little effect we should remember how essential it is in a flock of white sheep to destroy every lamb with the faintest`

- **module 2 / lesson 1 / item 4** (What PEP 8 Is and What It Covers)
  - Q: PEP 8's status is 'Active' and its type is 'Process'. Which reading of these fields matches what the document says about itself?
  - Expected answer: `It is a still-evolving document about how work on Python should be done, rather than a change to the language`
  - Best window recall 0.25, global token recall 0.75
  - Closest source text: `by better adapting them to their altered conditions would tend to be preserved and natural selection would thus have free scope for the work of improvement we have reason to believe as stated in the first chapter that a change`

### Answerability (answer vs its own lesson content)

- 22/36 answerable from the lesson alone = 61.1%
- Tiers: {'exact': 5, 'strong': 17, 'partial': 10, 'unsupported': 4}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 2

#### Items not answerable from their lesson

- **module 1 / lesson 2 / item 2** (Circumstances Favourable to Selection: A Country Under Change)
  - Q: According to the lesson, what does an island or a barrier-bounded country contribute to the work of natural selection?
  - Expected answer: `It keeps vacant places from being seized by immigrants, so modified natives can come to fill them`
  - Best window recall against lesson: 0.44

- **module 1 / lesson 3 / item 2** (Nature's Selection Compared with Man's)
  - Q: Darwin lists the breeder feeding a long-beaked and a short-beaked pigeon on the same food, and exposing long- and short-woolled sheep to the same climate. What point are these examples meant to make?
  - Expected answer: `That the breeder selects a character without ever exercising it under the conditions that would suit it`
  - Best window recall against lesson: 0.43

- **module 1 / lesson 4 / item 1** (Selection Acting on Characters of Trifling Importance)
  - Q: According to Darwin, why do we see nothing of natural selection's changes while they are in progress?
  - Expected answer: `Because it works silently and insensibly, and only the long lapse of ages makes its effects visible`
  - Best window recall against lesson: 0.30

- **module 1 / lesson 4 / item 3** (Selection Acting on Characters of Trifling Importance)
  - Q: What role does the warning against keeping white pigeons play in Darwin's argument?
  - Expected answer: `It gives everyday evidence that conspicuous colour raises the risk of destruction by sight-hunting predators`
  - Best window recall against lesson: 0.27

### Concept coverage across the source

- 21/30 concepts anchored to a source chunk (9 unanchored)
- Chunks containing at least one concept: 3/3 (100.0%)
- Concepts per chunk: [11, 1, 9]
- Lessons per chunk: [0, 0, 2]
- Uncovered chunk indexes: none
- Largest share in one chunk: 52.4%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.5965, 0.2169, 0.1866]
- Actual share per chunk: [0.5238, 0.0476, 0.4286]
- Actual/expected: [0.8781, 0.2196, 2.2966]
- Worst concentration ratio: 2.30

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 95.7%
- Worst chunk: 0 at 90.6%
- Chunks under 50% covered: 0
- Lessons routed per segment: [3, 1, 2]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 58 | 90.6% | 0.918 |
| 1 | 2,747 | 28 | 27 | 96.4% | 0.896 |
| 2 | 3,000 | 9 | 9 | 100.0% | 0.982 |
