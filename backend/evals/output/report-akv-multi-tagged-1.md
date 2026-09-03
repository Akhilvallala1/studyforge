# StudyForge generation eval

## Headline metrics

| Metric | multi-darwin-pep8 |
|---|---|
| Lessons | 7 |
| Quiz items | 42 |
| Structure problems | 0 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.5714 |
| Grounded, extractive items only | 0.561 |
| Ungrounded items, all | 6 |
| Ungrounded extractive items | 6 |
| Hallucination candidates | 0 |
| Mean grounding recall | 0.7787 |
| Answerable from lesson | 0.5476 |
| Unanswerable items | 4 |
| Giveaway MCQs | 0 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.5714 |
| Concentration vs chunk length | 1.7862 |
| Source recall, mean chunk | 0.9621 |
| Source recall, worst chunk | 0.9219 |
| Cost USD | 0.776 |
| Wall clock s | 346.73 |

## multi-darwin-pep8

Source: text `darwin-origin + pep8-style-guide`, 13,639 chars, 3 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 7 | 7 | 1 | 0 | 7 | 7 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 7 | 16,290 | 25,426 | $0.7171 | 46.9 | 55.9 |
| outline | 1 | 5,101 | 1,335 | $0.0589 | 18.8 | 18.8 |

### Structure

- 3 modules, 7 lessons, 42 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [4, 5, 5, 5, 5, 5, 4]
- Lesson content chars: mean 5680, min 4268
- Item kinds: {'mcq': 28, 'short': 14}
- Problems: none

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 24/42 answers supported (exact or strong) = 57.1%
- Tiers: {'exact': 5, 'strong': 19, 'partial': 12, 'unsupported': 6}
- Mean best-window recall: 0.779
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 41, 'odd_one_out': 0, 'restatement': 1, 'trivial': 0}
- Extractive items supported: 23/41 = 56.1% (mean window recall 0.777)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 0.0%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 0

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 5** (Defining Natural Selection)
  - Q: Darwin writes that 'unless profitable variations do occur, natural selection can do nothing.' What limitation of the process does this state?
  - Expected answer: `That natural selection has no power to create variation of its own; it can only preserve or reject variations that happen to arise, so it depends entirely on a supply of useful variation.`
  - Best window recall 0.36, global token recall 0.50
  - Closest source text: `any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious vari`

- **module 1 / lesson 3 / item 3** (Nature's Selection Compared with Man's)
  - Q: Darwin says man 'protects during each varying season, as far as lies in his power, all his productions.' In his comparison, what is the significance of this?
  - Expected answer: `It shows man's kindness is a defect of method, since he does not rigidly destroy inferior animals as nature does`
  - Best window recall 0.33, global token recall 0.67
  - Closest source text: `he does not exercise a long backed or long legged quadruped in any peculiar manner he exposes sheep with long and short wool to the same climate he does not allow the most vigorous males to struggle for the females he does not rigidly destroy all inferior animals`

- **module 2 / lesson 1 / item 2** (Silent and Insensible Working)
  - Q: Why does Darwin mention that on parts of the Continent people are warned not to keep white pigeons?
  - Expected answer: `To show that hawks hunt by eyesight, so conspicuous colour really does raise the risk of destruction`
  - Best window recall 0.30, global token recall 0.40
  - Closest source text: `to suffer largely from birds of prey and hawks are guided by eyesight to their prey so much so that on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction`

- **module 2 / lesson 2 / item 1** (Characters of Trifling Importance)
  - Q: According to the lesson, why does the fact that hawks are guided by eyesight matter to Darwin's argument?
  - Expected answer: `It explains how a difference in colour alone can become a difference in the chance of being killed`
  - Best window recall 0.14, global token recall 0.71
  - Closest source text: `action extinction caused by natural selection divergence of character related to the diversity of inhabitants of any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains`

- **module 2 / lesson 2 / item 2** (Characters of Trifling Importance)
  - Q: Match Darwin's examples: the alpine ptarmigan is white in winter, the red-grouse is the colour of heather, and the black-grouse is the colour of what?
  - Expected answer: `Peaty earth (peat). Each bird's colouring matches the background it lives against, which Darwin takes as evidence the tints preserve them from danger.`
  - Best window recall 0.31, global token recall 0.44
  - Closest source text: `acted on when we see leaf eating insects green and bark feeders mottled grey the alpine ptarmigan white in winter the red grouse the colour of heather and the black grouse that of peaty earth we must believe that these tints are of service to these birds and insects in preserving them from danger gr`

- **module 2 / lesson 2 / item 3** (Characters of Trifling Importance)
  - Q: What does Darwin say people on parts of the Continent are warned about, and what does he draw from it?
  - Expected answer: `Not to keep white pigeons, since they are the most liable to destruction — showing how strongly predators hunt by sight`
  - Best window recall 0.45, global token recall 0.45
  - Closest source text: `numbers they are known to suffer largely from birds of prey and hawks are guided by eyesight to their prey so much so that on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction`

### Answerability (answer vs its own lesson content)

- 23/42 answerable from the lesson alone = 54.8%
- Tiers: {'exact': 5, 'strong': 18, 'partial': 15, 'unsupported': 4}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 0

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 5** (Defining Natural Selection)
  - Q: Darwin writes that 'unless profitable variations do occur, natural selection can do nothing.' What limitation of the process does this state?
  - Expected answer: `That natural selection has no power to create variation of its own; it can only preserve or reject variations that happen to arise, so it depends entirely on a supply of useful variation.`
  - Best window recall against lesson: 0.43

- **module 2 / lesson 1 / item 2** (Silent and Insensible Working)
  - Q: Why does Darwin mention that on parts of the Continent people are warned not to keep white pigeons?
  - Expected answer: `To show that hawks hunt by eyesight, so conspicuous colour really does raise the risk of destruction`
  - Best window recall against lesson: 0.40

- **module 2 / lesson 2 / item 1** (Characters of Trifling Importance)
  - Q: According to the lesson, why does the fact that hawks are guided by eyesight matter to Darwin's argument?
  - Expected answer: `It explains how a difference in colour alone can become a difference in the chance of being killed`
  - Best window recall against lesson: 0.43

- **module 2 / lesson 2 / item 3** (Characters of Trifling Importance)
  - Q: What does Darwin say people on parts of the Continent are warned about, and what does he draw from it?
  - Expected answer: `Not to keep white pigeons, since they are the most liable to destruction — showing how strongly predators hunt by sight`
  - Best window recall against lesson: 0.45

### Concept coverage across the source

- 21/33 concepts anchored to a source chunk (12 unanchored)
- Chunks containing at least one concept: 3/3 (100.0%)
- Concepts per chunk: [12, 2, 7]
- Lessons per chunk: [1, 0, 2]
- Uncovered chunk indexes: none
- Largest share in one chunk: 57.1%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.5965, 0.2169, 0.1866]
- Actual share per chunk: [0.5714, 0.0952, 0.3333]
- Actual/expected: [0.9579, 0.4391, 1.7862]
- Worst concentration ratio: 1.79

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 96.2%
- Worst chunk: 0 at 92.2%
- Chunks under 50% covered: 0
- Lessons routed per segment: [3, 2, 2]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 59 | 92.2% | 0.908 |
| 1 | 2,747 | 28 | 27 | 96.4% | 0.929 |
| 2 | 3,000 | 9 | 9 | 100.0% | 1.000 |
