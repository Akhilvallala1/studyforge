# StudyForge generation eval

## Headline metrics

| Metric | prose-text |
|---|---|
| Lessons | 11 |
| Quiz items | 65 |
| Structure problems | 2 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.5231 |
| Grounded, extractive items only | 0.5517 |
| Ungrounded items, all | 10 |
| Ungrounded extractive items | 9 |
| Hallucination candidates | 0 |
| Mean grounding recall | 0.7576 |
| Answerable from lesson | 0.5231 |
| Unanswerable items | 5 |
| Giveaway MCQs | 4 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.871 |
| Concentration vs chunk length | 1.1876 |
| Source recall, mean chunk | 0.9922 |
| Source recall, worst chunk | 0.9844 |
| Cost USD | 1.3789 |
| Wall clock s | 598.41 |

## prose-text

Source: text `darwin-origin-excerpt`, 10,637 chars, 2 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 11 | 11 | 0 | 0 | 11 | 11 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 11 | 43,555 | 43,687 | $1.3099 | 52.0 | 63.2 |
| outline | 1 | 3,436 | 2,072 | $0.0690 | 26.0 | 26.0 |

### Structure

- 4 modules, 11 lessons, 65 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 5, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 5, 5, 4, 5, 5]
- Lesson content chars: mean 6543, min 5514
- Item kinds: {'mcq': 43, 'short': 22}
- Problems: {'duplicate_question': 2}

  - `duplicate_question` at module 1 / lesson 2 / item 2: also at module 1 / lesson 1 / item 2
  - `duplicate_question` at module 4 / lesson 1 / item 5: also at module 3 / lesson 3 / item 4

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 34/65 answers supported (exact or strong) = 52.3%
- Tiers: {'exact': 3, 'strong': 31, 'partial': 21, 'unsupported': 10}
- Mean best-window recall: 0.758
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 58, 'odd_one_out': 0, 'restatement': 7, 'trivial': 0}
- Extractive items supported: 32/58 = 55.2% (mean window recall 0.764)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 14.6%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 0

#### Ungrounded extractive items

- **module 1 / lesson 2 / item 4** (The Definition: Preservation of the Favourable, Rejection of the Injurious)
  - Q: A reader concludes: "Since botanists call the down on a fruit a character of the most trifling importance, it must be one of Darwin's indifferent variations, untouched by selection." How does the lesson answer this?
  - Expected answer: `Whether a character is favourable, injurious or indifferent depends on its consequences in the struggle for life, not on how important it seems to us — Downing found smooth-skinned fruits suffer far more from the curculio than downy ones`
  - Best window recall 0.38, global token recall 0.67
  - Closest source text: `an excellent horticulturist downing that in the united states smooth skinned fruits suffer far more from a beetle a curculio than those with down that purple plums suffer far more from a certain disease than yellow plums whereas another disease attacks yellow fleshed peaches far more than those with`

- **module 1 / lesson 3 / item 6** (The Chapter's Roadmap)
  - Q: Which statement about sexual selection is supported by the excerpt and its heading?
  - Expected answer: `It is listed as a topic in its own right, and is hinted at when Darwin notes that man does not let the most vigorous males struggle for the females`
  - Best window recall 0.33, global token recall 0.58
  - Closest source text: `a short beaked pigeon on the same food he does not exercise a long backed or long legged quadruped in any peculiar manner he exposes sheep with long and short wool to the same climate he does not allow the most vigorous males to struggle for the females`

- **module 2 / lesson 3 / item 4** (Why No Great Change Is Actually Necessary)
  - Q: What role does the scenario of a country undergoing a change of climate, or an island closed to immigration, play in Darwin's argument?
  - Expected answer: `It is the case in which selection is most easily understood, though Darwin then denies such conditions are necessary`
  - Best window recall 0.33, global token recall 0.67
  - Closest source text: `the conditions of life by specially acting on the reproductive system causes or increases variability and in the foregoing case the conditions of life are supposed to have undergone a change and this would manifestly be favourable to natural selection`

- **module 3 / lesson 1 / item 1** (What Man Can and Cannot Do)
  - Q: According to Darwin, what can nature act upon that man's selection cannot reach?
  - Expected answer: `The inward workings of a creature — its organs, its constitution, the whole machinery of life`
  - Best window recall 0.38, global token recall 0.50
  - Closest source text: `external and visible characters nature cares nothing for appearances except in so far as they may be useful to any being she can act on every internal organ on every shade of constitutional difference on the whole machinery of life`

- **module 3 / lesson 1 / item 2** (What Man Can and Cannot Do)
  - Q: Darwin points out that the breeder feeds a long-beaked and a short-beaked pigeon on the same food, and exposes long-woolled and short-woolled sheep to the same climate. What single failing do these two examples illustrate?
  - Expected answer: `The breeder alters the animal without placing it under conditions that would actually test the altered character`
  - Best window recall 0.22, global token recall 0.56
  - Closest source text: `seized on by intruders in such case every slight modification which in the course of ages chanced to arise and which in any way favoured the individuals of any of the species by better adapting them to their altered conditions`

- **module 4 / lesson 1 / item 1** (Colour and Concealment in Insects and Birds)
  - Q: Why does Darwin bring up the fact that hawks are guided by eyesight to their prey?
  - Expected answer: `Because it establishes that a difference in an animal's colour can translate into a difference in its chance of being killed`
  - Best window recall 0.22, global token recall 0.56
  - Closest source text: `that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant nor ought we to think that the occasional destruction of an animal`

- **module 4 / lesson 1 / item 2** (Colour and Concealment in Insects and Birds)
  - Q: According to the lesson, what are people warned about on parts of the Continent, and what does Darwin use this to show?
  - Expected answer: `They are warned not to keep white pigeons, as being the most liable to destruction. Darwin uses this as independent, practical evidence that predators hunt by sight and that a conspicuous colour makes a bird more likely to be killed.`
  - Best window recall 0.35, global token recall 0.40
  - Closest source text: `from danger grouse if not destroyed at some period of their lives would increase in countless numbers they are known to suffer largely from birds of prey and hawks are guided by eyesight to their prey so much so that on parts of the continent persons are warned not to keep white pigeons as being the`

- **module 4 / lesson 1 / item 3** (Colour and Concealment in Insects and Birds)
  - Q: What is Darwin's point in mentioning that in a flock of white sheep it is essential to destroy every lamb with the faintest trace of black?
  - Expected answer: `That a small but steady removal of odd individuals is enough to keep a colour true and constant`
  - Best window recall 0.30, global token recall 0.70
  - Closest source text: `most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant`

- **module 4 / lesson 2 / item 1** (Small Differences, Large Consequences: Sheep, Plums, and Peaches)
  - Q: Why does Darwin bring up the flock of white sheep?
  - Expected answer: `To show that occasional destruction of individuals of a particular colour, repeated in each generation, has a real effect on a population`
  - Best window recall 0.45, global token recall 0.55
  - Closest source text: `be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant nor ought we to think that the occasional destruction of an animal of any particular colour would produce little effect`

### Answerability (answer vs its own lesson content)

- 34/65 answerable from the lesson alone = 52.3%
- Tiers: {'exact': 4, 'strong': 30, 'partial': 26, 'unsupported': 5}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 4

#### Items not answerable from their lesson

- **module 2 / lesson 3 / item 4** (Why No Great Change Is Actually Necessary)
  - Q: What role does the scenario of a country undergoing a change of climate, or an island closed to immigration, play in Darwin's argument?
  - Expected answer: `It is the case in which selection is most easily understood, though Darwin then denies such conditions are necessary`
  - Best window recall against lesson: 0.44

- **module 3 / lesson 1 / item 2** (What Man Can and Cannot Do)
  - Q: Darwin points out that the breeder feeds a long-beaked and a short-beaked pigeon on the same food, and exposes long-woolled and short-woolled sheep to the same climate. What single failing do these two examples illustrate?
  - Expected answer: `The breeder alters the animal without placing it under conditions that would actually test the altered character`
  - Best window recall against lesson: 0.44

- **module 3 / lesson 1 / item 4** (What Man Can and Cannot Do)
  - Q: Where does man's selection typically begin, and how does this differ from nature's?
  - Expected answer: `With a half-monstrous form or some change striking enough to catch his eye, whereas nature can seize on the faintest difference`
  - Best window recall against lesson: 0.46

- **module 3 / lesson 3 / item 3** (Daily and Hourly Scrutiny: The Invisibility of Slow Change)
  - Q: Why does Darwin bring up the practice of destroying every lamb with the faintest trace of black in a flock of white sheep?
  - Expected answer: `To answer the thought that the occasional destruction of an animal of a particular colour would produce little effect`
  - Best window recall against lesson: 0.30

- **module 4 / lesson 1 / item 1** (Colour and Concealment in Insects and Birds)
  - Q: Why does Darwin bring up the fact that hawks are guided by eyesight to their prey?
  - Expected answer: `Because it establishes that a difference in an animal's colour can translate into a difference in its chance of being killed`
  - Best window recall against lesson: 0.44

### Concept coverage across the source

- 31/54 concepts anchored to a source chunk (23 unanchored)
- Chunks containing at least one concept: 2/2 (100.0%)
- Concepts per chunk: [27, 4]
- Lessons per chunk: [3, 0]
- Uncovered chunk indexes: none
- Largest share in one chunk: 87.1%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.7334, 0.2666]
- Actual share per chunk: [0.871, 0.129]
- Actual/expected: [1.1876, 0.4839]
- Worst concentration ratio: 1.19

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 99.2%
- Worst chunk: 0 at 98.4%
- Chunks under 50% covered: 0
- Lessons routed per segment: [11, 11]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 63 | 98.4% | 0.966 |
| 1 | 2,747 | 28 | 28 | 100.0% | 0.980 |
