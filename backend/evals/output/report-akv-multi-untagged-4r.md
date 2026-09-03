# StudyForge generation eval

## Headline metrics

| Metric | multi-darwin-pep8 |
|---|---|
| Lessons | 8 |
| Quiz items | 47 |
| Structure problems | 6 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.4681 |
| Grounded, extractive items only | 0.5 |
| Ungrounded items, all | 9 |
| Ungrounded extractive items | 7 |
| Hallucination candidates | 0 |
| Mean grounding recall | 0.7168 |
| Answerable from lesson | 0.5319 |
| Unanswerable items | 4 |
| Giveaway MCQs | 2 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.3913 |
| Concentration vs chunk length | 2.0969 |
| Source recall, mean chunk | 0.9844 |
| Source recall, worst chunk | 0.9531 |
| Cost USD | 0.8423 |
| Wall clock s | 372.83 |

## multi-darwin-pep8

Source: text `darwin-origin + pep8-style-guide`, 13,639 chars, 3 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 8 | 8 | 2 | 0 | 8 | 8 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 8 | 17,808 | 27,625 | $0.7797 | 44.0 | 52.0 |
| outline | 1 | 4,934 | 1,519 | $0.0626 | 20.5 | 20.5 |

### Structure

- 3 modules, 8 lessons, 47 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 5, 6, 6]
- Concepts per lesson: [4, 5, 5, 5, 5, 5, 4, 5]
- Lesson content chars: mean 5607, min 4536
- Item kinds: {'mcq': 33, 'short': 14}
- Problems: {'empty_concept': 6}

  - `empty_concept` at module 2 / lesson 1 / item 1: According to Darwin, what does our imperfect view into long past geological ages allow us to see?
  - `empty_concept` at module 2 / lesson 1 / item 2: Why does Darwin think colour could be an effective target of natural selection in grouse?
  - `empty_concept` at module 2 / lesson 1 / item 3: Darwin answers the objection that occasional destruction of animals of one colour would have little effect. What example does he use, and what does it show?
  - `empty_concept` at module 2 / lesson 1 / item 4: Which of Downing's observations does Darwin cite?
  - `empty_concept` at module 2 / lesson 1 / item 5: In Darwin's phrase, natural selection works at the improvement of each being 'in relation to' what?
  - `empty_concept` at module 2 / lesson 1 / item 6: What is the logic of Darwin's move from the orchard to the state of nature?

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 22/47 answers supported (exact or strong) = 46.8%
- Tiers: {'exact': 4, 'strong': 18, 'partial': 16, 'unsupported': 9}
- Mean best-window recall: 0.717
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 42, 'odd_one_out': 0, 'restatement': 5, 'trivial': 0}
- Extractive items supported: 21/42 = 50.0% (mean window recall 0.734)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 18.2%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 0

#### Ungrounded extractive items

- **module 1 / lesson 3 / item 2** (Nature's Selection Compared with Man's)
  - Q: Darwin says the breeder 'feeds a long and a short beaked pigeon on the same food' and 'exposes sheep with long and short wool to the same climate.' What defect in man's selection do these examples illustrate?
  - Expected answer: `He selects a character but never exercises it or places the being under conditions fitted to it, as nature always does`
  - Best window recall 0.44, global token recall 0.67
  - Closest source text: `on the whole machinery of life man selects only for his own good nature only for that of the being which she tends every selected character is fully exercised by her and the being is placed under well suited conditions`

- **module 2 / lesson 1 / item 5** (Daily and Hourly Scrutiny)
  - Q: In Darwin's phrase, natural selection works at the improvement of each being 'in relation to' what?
  - Expected answer: `In relation to its organic and inorganic conditions of life — so what counts as a good variation depends on the being's competitors, enemies and physical surroundings rather than being absolute.`
  - Best window recall 0.44, global token recall 0.69
  - Closest source text: `it may be said that natural selection is daily and hourly scrutinising throughout the world every variation even the slightest rejecting that which is bad preserving and adding up all that is good silently and insensibly working whenever and wherever opportunity offers at the improvement of each org`

- **module 2 / lesson 2 / item 1** (Characters of Trifling Importance)
  - Q: Why does Darwin bring up the warning, on parts of the Continent, against keeping white pigeons?
  - Expected answer: `It gives practical evidence that a conspicuous colour really does make an animal more liable to destruction by predators that hunt by sight`
  - Best window recall 0.31, global token recall 0.46
  - Closest source text: `most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant nor ought we to think that the occasional destruction of an animal`

- **module 2 / lesson 2 / item 5** (Characters of Trifling Importance)
  - Q: Darwin says grouse would increase in countless numbers if not destroyed at some period of their lives. What role does this observation play in his argument about their heather-like colour?
  - Expected answer: `It establishes that heavy mortality must be occurring, and since much of it comes from sight-hunting birds of prey, colour becomes decisive for survival`
  - Best window recall 0.27, global token recall 0.40
  - Closest source text: `to suffer largely from birds of prey and hawks are guided by eyesight to their prey so much so that on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in givi`

- **module 2 / lesson 3 / item 2** (Evidence from Cultivated Plants)
  - Q: Darwin reports two disease observations involving the colour yellow. What is notable about how they relate to one another?
  - Expected answer: `Yellow protects in one case and exposes in the other: yellow plums resist a disease that hits purple ones, while yellow-fleshed peaches are the ones singled out by another disease`
  - Best window recall 0.44, global token recall 0.69
  - Closest source text: `the colour of the flesh are considered by botanists as characters of the most trifling importance yet we hear from an excellent horticulturist downing that in the united states smooth skinned fruits suffer far more from a beetle a curculio than those with down that purple plums suffer far more from `

- **module 3 / lesson 1 / item 1** (What PEP 8 Is and What It Covers)
  - Q: What do the Status and Type fields of PEP 8 tell you about the document?
  - Expected answer: `It is Active and of type Process: a living document about a way of working, not a change to the language`
  - Best window recall 0.33, global token recall 0.89
  - Closest source text: `for python code pep 8 style guide for python code author guido van rossum lt guido at python org gt barry warsaw lt barry at python org gt alyssa coghlan lt ncoghlan at gmail com gt status active type process`

- **module 3 / lesson 2 / item 4** (Readability, Consistency, and the Foolish Hobgoblin)
  - Q: In PEP 8's ranking of kinds of consistency, which is described as the most important?
  - Expected answer: `Consistency within one module or function`
  - Best window recall 0.40, global token recall 1.00
  - Closest source text: `table of contents introduction a foolish consistency is the hobgoblin of little minds code lay out indentation tabs or spaces maximum line length should a line break before or after a binary operator blank lines source file encoding imports module`

### Answerability (answer vs its own lesson content)

- 25/47 answerable from the lesson alone = 53.2%
- Tiers: {'exact': 5, 'strong': 20, 'partial': 18, 'unsupported': 4}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 2

#### Items not answerable from their lesson

- **module 1 / lesson 3 / item 2** (Nature's Selection Compared with Man's)
  - Q: Darwin says the breeder 'feeds a long and a short beaked pigeon on the same food' and 'exposes sheep with long and short wool to the same climate.' What defect in man's selection do these examples illustrate?
  - Expected answer: `He selects a character but never exercises it or places the being under conditions fitted to it, as nature always does`
  - Best window recall against lesson: 0.44

- **module 2 / lesson 2 / item 1** (Characters of Trifling Importance)
  - Q: Why does Darwin bring up the warning, on parts of the Continent, against keeping white pigeons?
  - Expected answer: `It gives practical evidence that a conspicuous colour really does make an animal more liable to destruction by predators that hunt by sight`
  - Best window recall against lesson: 0.46

- **module 2 / lesson 2 / item 2** (Characters of Trifling Importance)
  - Q: What point is Darwin making with the flock of white sheep in which every lamb with the faintest trace of black is destroyed?
  - Expected answer: `That the occasional destruction of animals of a particular colour is far from a negligible effect, since it is exactly how a colour is kept true`
  - Best window recall against lesson: 0.42

- **module 2 / lesson 2 / item 5** (Characters of Trifling Importance)
  - Q: Darwin says grouse would increase in countless numbers if not destroyed at some period of their lives. What role does this observation play in his argument about their heather-like colour?
  - Expected answer: `It establishes that heavy mortality must be occurring, and since much of it comes from sight-hunting birds of prey, colour becomes decisive for survival`
  - Best window recall against lesson: 0.13

### Concept coverage across the source

- 23/38 concepts anchored to a source chunk (15 unanchored)
- Chunks containing at least one concept: 3/3 (100.0%)
- Concepts per chunk: [9, 5, 9]
- Lessons per chunk: [1, 1, 2]
- Uncovered chunk indexes: none
- Largest share in one chunk: 39.1%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.5965, 0.2169, 0.1866]
- Actual share per chunk: [0.3913, 0.2174, 0.3913]
- Actual/expected: [0.656, 1.0024, 2.0969]
- Worst concentration ratio: 2.10

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 98.4%
- Worst chunk: 0 at 95.3%
- Chunks under 50% covered: 0
- Lessons routed per segment: [3, 3, 2]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 61 | 95.3% | 0.944 |
| 1 | 2,747 | 28 | 28 | 100.0% | 0.993 |
| 2 | 3,000 | 9 | 9 | 100.0% | 0.986 |
