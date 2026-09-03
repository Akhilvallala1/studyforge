# StudyForge generation eval

## Headline metrics

| Metric | multi-darwin-pep8 |
|---|---|
| Lessons | 9 |
| Quiz items | 54 |
| Structure problems | 7 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.4815 |
| Grounded, extractive items only | 0.5 |
| Ungrounded items, all | 10 |
| Ungrounded extractive items | 7 |
| Hallucination candidates | 0 |
| Mean grounding recall | 0.7306 |
| Answerable from lesson | 0.5185 |
| Unanswerable items | 8 |
| Giveaway MCQs | 3 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.5 |
| Concentration vs chunk length | 1.9486 |
| Source recall, mean chunk | 0.9844 |
| Source recall, worst chunk | 0.9531 |
| Cost USD | 0.9814 |
| Wall clock s | 445.26 |

## multi-darwin-pep8

Source: text `darwin-origin + pep8-style-guide`, 13,639 chars, 3 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 9 | 9 | 2 | 0 | 9 | 9 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 9 | 19,916 | 32,346 | $0.9082 | 46.6 | 59.5 |
| outline | 1 | 4,934 | 1,941 | $0.0732 | 25.5 | 25.5 |

### Structure

- 3 modules, 9 lessons, 54 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [4, 5, 5, 4, 5, 5, 4, 5, 4]
- Lesson content chars: mean 5928, min 4283
- Item kinds: {'mcq': 37, 'short': 17}
- Problems: {'duplicate_question': 1, 'empty_concept': 6}

  - `duplicate_question` at module 1 / lesson 2 / item 4: also at module 1 / lesson 1 / item 2
  - `empty_concept` at module 3 / lesson 1 / item 1: According to its metadata, what Type and Status is PEP 8?
  - `empty_concept` at module 3 / lesson 1 / item 2: A team's internal coding guide contradicts a recommendation in PEP 8. According to PEP 8 itself, which applies to that team's code?
  - `empty_concept` at module 3 / lesson 1 / item 3: Name the three authors listed on PEP 8.
  - `empty_concept` at module 3 / lesson 1 / item 4: Which document does PEP 8's Introduction point readers to for style guidelines covering the C code in the C implementation of Python?
  - `empty_concept` at module 3 / lesson 1 / item 5: PEP 8 states that both it and PEP 257 (Docstring Conventions) were adapted from what earlier source?
  - `empty_concept` at module 3 / lesson 1 / item 6: Why does PEP 8 describe itself as a document that evolves over time?

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 26/54 answers supported (exact or strong) = 48.1%
- Tiers: {'exact': 7, 'strong': 19, 'partial': 18, 'unsupported': 10}
- Mean best-window recall: 0.731
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 50, 'odd_one_out': 0, 'restatement': 4, 'trivial': 0}
- Extractive items supported: 25/50 = 50.0% (mean window recall 0.753)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 27.0%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 0

#### Ungrounded extractive items

- **module 2 / lesson 1 / item 3** (Daily and Hourly Scrutiny: Selection and Deep Time)
  - Q: Why does Darwin mention that hawks are guided by eyesight to their prey?
  - Expected answer: `It establishes that visibility is the trait under selection, making colour a matter of life and death for grouse`
  - Best window recall 0.30, global token recall 0.40
  - Closest source text: `persons are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse`

- **module 2 / lesson 2 / item 1** (Characters of Trifling Importance)
  - Q: Why does Darwin bring up the warning, given on parts of the Continent, against keeping white pigeons?
  - Expected answer: `It shows that hawks locate prey by eyesight, so conspicuous colour really does invite destruction`
  - Best window recall 0.40, global token recall 0.50
  - Closest source text: `to suffer largely from birds of prey and hawks are guided by eyesight to their prey so much so that on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction`

- **module 2 / lesson 2 / item 6** (Characters of Trifling Importance)
  - Q: In Darwin's account, why do we see nothing of natural selection's work as it happens?
  - Expected answer: `It works silently and insensibly, becoming visible only after the long lapse of ages, and even then our view of past ages is imperfect`
  - Best window recall 0.46, global token recall 0.85
  - Closest source text: `good silently and insensibly working whenever and wherever opportunity offers at the improvement of each organic being in relation to its organic and inorganic conditions of life we see nothing of these slow changes in progress until the hand of time has marked the long lapse of ages and then so imp`

- **module 2 / lesson 3 / item 2** (Downy Fruit and Purple Plums: Evidence from Cultivation)
  - Q: Why does Darwin think evidence drawn from cultivated orchards strengthens rather than weakens his case about a state of nature?
  - Expected answer: `Because orchards are the mildest conditions a tree can face, so a difference that still tells there would tell far more where trees struggle with rivals and enemies`
  - Best window recall 0.33, global token recall 0.53
  - Closest source text: `disease than yellow plums whereas another disease attacks yellow fleshed peaches far more than those with other coloured flesh if with all the aids of art these slight differences make a great difference in cultivating the several varieties assuredly in a state of nature where the trees would have t`

- **module 2 / lesson 3 / item 3** (Downy Fruit and Purple Plums: Evidence from Cultivation)
  - Q: What point is Darwin making with the flock of white sheep in which every lamb with the faintest trace of black is destroyed?
  - Expected answer: `That occasional destruction of individuals bearing a particular character is not a trivial force: culling the few black-traced lambs is exactly what keeps the whole flock white, so nature's occasional destruction of oddly coloured animals could likewise govern a population's character.`
  - Best window recall 0.24, global token recall 0.56
  - Closest source text: `that on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true `

- **module 2 / lesson 3 / item 4** (Downy Fruit and Purple Plums: Evidence from Cultivation)
  - Q: Darwin mentions that on parts of the Continent people are warned not to keep white pigeons. What does this detail support?
  - Expected answer: `That predators such as hawks are guided by eyesight, making conspicuous colouring dangerous`
  - Best window recall 0.38, global token recall 0.38
  - Closest source text: `these birds and insects in preserving them from danger grouse if not destroyed at some period of their lives would increase in countless numbers they are known to suffer largely from birds of prey and hawks are guided by eyesight`

- **module 2 / lesson 3 / item 6** (Downy Fruit and Purple Plums: Evidence from Cultivation)
  - Q: Which statement best describes the pattern in Downing's three reported cases?
  - Expected answer: `A given colour or texture helps against one enemy and can hurt against another, so no variety is superior across the board`
  - Best window recall 0.15, global token recall 0.46
  - Closest source text: `project specific guides take precedence for that project a foolish consistency is the hobgoblin of little minds one of guido s key insights is that code is read much more often than it is written the guidelines provided here are intended to improve the readability of code and make it consistent acro`

### Answerability (answer vs its own lesson content)

- 28/54 answerable from the lesson alone = 51.9%
- Tiers: {'exact': 6, 'strong': 22, 'partial': 18, 'unsupported': 8}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 3

#### Items not answerable from their lesson

- **module 1 / lesson 3 / item 2** (Nature's Selection Compared with Man's)
  - Q: Darwin says man 'feeds a long and a short beaked pigeon on the same food' and 'exposes sheep with long and short wool to the same climate.' What limitation of human selection do these examples illustrate?
  - Expected answer: `That man selects characters without exercising each one in a peculiar and fitting manner, or placing the being under well-suited conditions`
  - Best window recall against lesson: 0.42

- **module 2 / lesson 1 / item 3** (Daily and Hourly Scrutiny: Selection and Deep Time)
  - Q: Why does Darwin mention that hawks are guided by eyesight to their prey?
  - Expected answer: `It establishes that visibility is the trait under selection, making colour a matter of life and death for grouse`
  - Best window recall against lesson: 0.40

- **module 2 / lesson 1 / item 5** (Daily and Hourly Scrutiny: Selection and Deep Time)
  - Q: In Downing's American observations, which fruits suffered far more from the beetle known as a curculio?
  - Expected answer: `Smooth-skinned fruits, as compared with those bearing down`
  - Best window recall against lesson: 0.20

- **module 2 / lesson 2 / item 1** (Characters of Trifling Importance)
  - Q: Why does Darwin bring up the warning, given on parts of the Continent, against keeping white pigeons?
  - Expected answer: `It shows that hawks locate prey by eyesight, so conspicuous colour really does invite destruction`
  - Best window recall against lesson: 0.40

- **module 2 / lesson 3 / item 2** (Downy Fruit and Purple Plums: Evidence from Cultivation)
  - Q: Why does Darwin think evidence drawn from cultivated orchards strengthens rather than weakens his case about a state of nature?
  - Expected answer: `Because orchards are the mildest conditions a tree can face, so a difference that still tells there would tell far more where trees struggle with rivals and enemies`
  - Best window recall against lesson: 0.33

- **module 2 / lesson 3 / item 4** (Downy Fruit and Purple Plums: Evidence from Cultivation)
  - Q: Darwin mentions that on parts of the Continent people are warned not to keep white pigeons. What does this detail support?
  - Expected answer: `That predators such as hawks are guided by eyesight, making conspicuous colouring dangerous`
  - Best window recall against lesson: 0.25

- **module 2 / lesson 3 / item 6** (Downy Fruit and Purple Plums: Evidence from Cultivation)
  - Q: Which statement best describes the pattern in Downing's three reported cases?
  - Expected answer: `A given colour or texture helps against one enemy and can hurt against another, so no variety is superior across the board`
  - Best window recall against lesson: 0.46

- **module 3 / lesson 2 / item 6** (A Foolish Consistency: Readability and Project Precedence)
  - Q: You join a project whose written style guide mandates `mixedCase` method names throughout its codebase. Following the lesson's reasoning, what should you do when adding a new method, and why?
  - Expected answer: `Use mixedCase, matching the project. The project-specific guide takes precedence in a conflict, and mixing two naming styles in one file hurts the readability that the rule was meant to protect.`
  - Best window recall against lesson: 0.40

### Concept coverage across the source

- 22/41 concepts anchored to a source chunk (19 unanchored)
- Chunks containing at least one concept: 3/3 (100.0%)
- Concepts per chunk: [11, 3, 8]
- Lessons per chunk: [0, 0, 1]
- Uncovered chunk indexes: none
- Largest share in one chunk: 50.0%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.5965, 0.2169, 0.1866]
- Actual share per chunk: [0.5, 0.1364, 0.3636]
- Actual/expected: [0.8382, 0.6288, 1.9486]
- Worst concentration ratio: 1.95

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 98.4%
- Worst chunk: 0 at 95.3%
- Chunks under 50% covered: 0
- Lessons routed per segment: [3, 3, 3]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 61 | 95.3% | 0.923 |
| 1 | 2,747 | 28 | 28 | 100.0% | 0.966 |
| 2 | 3,000 | 9 | 9 | 100.0% | 1.000 |
