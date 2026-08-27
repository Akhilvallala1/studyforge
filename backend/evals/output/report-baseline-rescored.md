# StudyForge generation eval

## Headline metrics

| Metric | prose-text | pep8-url |
|---|---|---|
| Lessons | 12 | 0 |
| Quiz items | 72 | 0 |
| Structure problems | 0 | 0 |
| Strict JSON first try | 1 | 1 |
| Hard parse failures | 0 | 1 |
| Grounded, all items (old metric) | 0.3889 | 0 |
| Grounded, extractive items only | 0.4828 | 0 |
| Ungrounded items, all | 25 | 0 |
| Ungrounded extractive items | 13 | 0 |
| Hallucination candidates | 5 | 0 |
| Mean grounding recall | 0.6275 | 0 |
| Answerable from lesson | 0.4306 | 0 |
| Unanswerable items | 8 | 0 |
| Giveaway MCQs | 7 | 0 |
| Source chunks covered | 1 | 0 |
| Largest single-chunk share (old metric) | 0.9167 | 0 |
| Concentration vs chunk length | 1.2499 | 0 |
| Source recall, mean chunk | 0.9666 | 0 |
| Source recall, worst chunk | 0.9643 | 0 |
| Cost USD | 1.4182 | 0.3282 |
| Wall clock s | 615.85 | 68.09 |

## prose-text

Source: text `darwin-origin-excerpt`, 10,637 chars, 2 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 12 | 12 | 0 | 0 | 12 | 12 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 12 | 43,851 | 45,138 | $1.3477 | 49.0 | 57.1 |
| outline | 1 | 3,438 | 2,133 | $0.0705 | 27.2 | 27.2 |

### Structure

- 4 modules, 12 lessons, 72 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 6788, min 5842
- Item kinds: {'mcq': 47, 'short': 25}
- Problems: none

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 28/72 answers supported (exact or strong) = 38.9%
- Tiers: {'exact': 8, 'strong': 20, 'partial': 19, 'unsupported': 25}
- Mean best-window recall: 0.628
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 58, 'odd_one_out': 4, 'restatement': 10, 'trivial': 0}
- Extractive items supported: 28/58 = 48.3% (mean window recall 0.700)
- Odd-one-out items: mean share of their distractors found in the source = 100.0%
- Restatement items: mean share of answer words absent from the source = 38.0%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 5

  - **module 3 / lesson 1 / item 6** (odd_one_out) novel 67%: He cannot pass any selected character on to offspring by inheritance
  - **module 3 / lesson 3 / item 2** (extractive) novel 100%: below the threshold of human perception
  - **module 3 / lesson 3 / item 3** (restatement) novel 67%: Because invisibility is what the theory itself predicts: the steps are tiny and the time required is vast, so no observer could see them. Darwin does not rest o
  - **module 3 / lesson 3 / item 6** (extractive) novel 75%: It could be misread as implying a conscious agent, when it means only differential survival and reproduction
  - **module 4 / lesson 1 / item 2** (extractive) novel 62%: An everyday, verifiable observation that a conspicuous colour increases the risk of destruction

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 5** (From the Struggle for Existence to Selection in Nature)
  - Q: Darwin cites the horticulturist Downing on smooth-skinned versus downy fruits and on purple versus yellow plums. What is the purpose of these examples?
  - Expected answer: `To show that characters botanists call trifling can in fact decide which variety succeeds`
  - Best window recall 0.33, global token recall 0.56
  - Closest source text: `is in a flock of white sheep to destroy every lamb with the faintest trace of black in plants the down on the fruit and the colour of the flesh are considered by botanists as characters of the most trifling`

- **module 1 / lesson 2 / item 3** (The Definition: Preservation and Rejection)
  - Q: Which kind of species does Darwin tentatively offer as a possible example of neutral, fluctuating variation?
  - Expected answer: `Polymorphic species — species in which several distinct forms coexist without one displacing the others, which Darwin suggests ('as perhaps we see') may show variation that selection does not act on.`
  - Best window recall 0.35, global token recall 0.71
  - Closest source text: `and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither useful nor injurious would not`

- **module 1 / lesson 2 / item 4** (The Definition: Preservation and Rejection)
  - Q: Darwin writes that 'unless profitable variations do occur, natural selection can do nothing.' What limitation of natural selection does this statement express?
  - Expected answer: `That natural selection cannot create variation; it can only sort or filter the heritable differences that already arise. Its whole power depends on a supply of profitable variation being available.`
  - Best window recall 0.24, global token recall 0.47
  - Closest source text: `conditions of life are supposed to have undergone a change and this would manifestly be favourable to natural selection by giving a better chance of profitable variations occurring and unless profitable variations do occur natural selection can do nothing not that as i believe any extreme amount of `

- **module 1 / lesson 2 / item 6** (The Definition: Preservation and Rejection)
  - Q: Darwin contrasts nature with the human breeder, who 'does not rigidly destroy all inferior animals.' What point about natural selection is he making?
  - Expected answer: `That the negative half of selection — the constant destruction of injurious variation — operates in nature without mercy or lapse`
  - Best window recall 0.27, global token recall 0.73
  - Closest source text: `the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature`

- **module 3 / lesson 1 / item 5** (What Man Can and Cannot Select)
  - Q: Why, in Darwin's account, does the breeder tend to begin from 'half-monstrous' forms?
  - Expected answer: `Because he must notice a variation before he can act on it, so only prominent or plainly useful modifications catch his eye`
  - Best window recall 0.45, global token recall 0.73
  - Closest source text: `animals but protects during each varying season as far as lies in his power all his productions he often begins his selection by some half monstrous form or at least by some modification prominent enough to catch his eye or to be plainly useful`

- **module 3 / lesson 3 / item 2** (Daily and Hourly Scrutiny: The Invisibility of Slow Change)
  - Q: In the passage, 'insensibly' means that natural selection works
  - Expected answer: `below the threshold of human perception`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 3 / item 6** (Daily and Hourly Scrutiny: The Invisibility of Slow Change)
  - Q: Why did Darwin's personification of natural selection as 'scrutinising' cause him later trouble?
  - Expected answer: `It could be misread as implying a conscious agent, when it means only differential survival and reproduction`
  - Best window recall 0.12, global token recall 0.12
  - Closest source text: `the natives we may safely conclude that the natives might have been modified with advantage so as to have better resisted such intruders as man can produce and certainly has produced a great result by his methodical and unconscious means`

- **module 4 / lesson 1 / item 1** (Colour and Concealment in Animals)
  - Q: Why is the detail that hawks 'are guided by eyesight to their prey' essential to Darwin's argument about grouse colour?
  - Expected answer: `Because a visually hunting predator makes colour a cause of survival or death, so selection can act on it`
  - Best window recall 0.18, global token recall 0.27
  - Closest source text: `any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act`

- **module 4 / lesson 1 / item 2** (Colour and Concealment in Animals)
  - Q: According to the lesson, what does the warning on the Continent against keeping white pigeons contribute to Darwin's case?
  - Expected answer: `An everyday, verifiable observation that a conspicuous colour increases the risk of destruction`
  - Best window recall 0.25, global token recall 0.38
  - Closest source text: `on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour`

- **module 4 / lesson 2 / item 4** (Small Differences, Large Consequences in Plants)
  - Q: Darwin says that nature 'cares nothing for appearances, except in so far as they may be useful to any being.' What does this imply about calling the down on fruit a 'trifling' character?
  - Expected answer: `It shows that 'trifling' reflects our judgement of appearance, not a proven lack of consequence for survival`
  - Best window recall 0.11, global token recall 0.11
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 4 / lesson 2 / item 6** (Small Differences, Large Consequences in Plants)
  - Q: How does the plant example extend Darwin's earlier animal-colour examples (green leaf-eating insects, white ptarmigan, heather-coloured grouse)?
  - Expected answer: `It shows the mechanism can be susceptibility to a beetle or disease rather than concealment from a predator's eye, and rests on independent testimony from a practical horticulturist`
  - Best window recall 0.20, global token recall 0.33
  - Closest source text: `the down on the fruit and the colour of the flesh are considered by botanists as characters of the most trifling importance yet we hear from an excellent horticulturist downing that in the united states smooth skinned fruits suffer far more from a beetle a curculio than those with down that purple p`

- **module 4 / lesson 3 / item 2** (Why Occasional Destruction Matters)
  - Q: Why does the objection that 'occasional destruction would produce little effect' fail?
  - Expected answer: `Because the deficit is inherited and repeated, so tiny per-generation effects add up over many generations`
  - Best window recall 0.18, global token recall 0.18
  - Closest source text: `useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many`

- **module 4 / lesson 3 / item 3** (Why Occasional Destruction Matters)
  - Q: Darwin says natural selection does two jobs with grouse colour. Name both.
  - Expected answer: `It gives the proper colour to each kind of grouse (origination), and it keeps that colour true and constant once acquired (maintenance, by continually pruning away new deviations).`
  - Best window recall 0.44, global token recall 0.56
  - Closest source text: `eyesight to their prey so much so that on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping th`

### Answerability (answer vs its own lesson content)

- 31/72 answerable from the lesson alone = 43.1%
- Tiers: {'exact': 9, 'strong': 22, 'partial': 33, 'unsupported': 8}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 7

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 1** (From the Struggle for Existence to Selection in Nature)
  - Q: Which of these is NOT one of the premises Darwin assembles in his opening argument for natural selection?
  - Expected answer: `Variations arise specifically because the organism needs them`
  - Best window recall against lesson: 0.33

- **module 1 / lesson 1 / item 5** (From the Struggle for Existence to Selection in Nature)
  - Q: Darwin cites the horticulturist Downing on smooth-skinned versus downy fruits and on purple versus yellow plums. What is the purpose of these examples?
  - Expected answer: `To show that characters botanists call trifling can in fact decide which variety succeeds`
  - Best window recall against lesson: 0.33

- **module 1 / lesson 2 / item 5** (The Definition: Preservation and Rejection)
  - Q: Which of these is NOT one of the premises Darwin uses to build up to his definition of natural selection?
  - Expected answer: `Only large, monstrous variations are capable of giving an advantage`
  - Best window recall against lesson: 0.33

- **module 3 / lesson 1 / item 6** (What Man Can and Cannot Select)
  - Q: Which of the following is NOT one of the limitations on man's selection listed in this lesson?
  - Expected answer: `He cannot pass any selected character on to offspring by inheritance`
  - Best window recall against lesson: 0.33

- **module 3 / lesson 3 / item 5** (Daily and Hourly Scrutiny: The Invisibility of Slow Change)
  - Q: Why does the lesson say the phrase 'adding up all that is good' is especially important in the famous passage?
  - Expected answer: `Because it shows selection is cumulative rather than a one-off filter: slight advantageous variations are preserved and accumulated across generations, so individually imperceptible steps can build up into large change over geological time.`
  - Best window recall against lesson: 0.30

- **module 4 / lesson 1 / item 1** (Colour and Concealment in Animals)
  - Q: Why is the detail that hawks 'are guided by eyesight to their prey' essential to Darwin's argument about grouse colour?
  - Expected answer: `Because a visually hunting predator makes colour a cause of survival or death, so selection can act on it`
  - Best window recall against lesson: 0.45

- **module 4 / lesson 2 / item 4** (Small Differences, Large Consequences in Plants)
  - Q: Darwin says that nature 'cares nothing for appearances, except in so far as they may be useful to any being.' What does this imply about calling the down on fruit a 'trifling' character?
  - Expected answer: `It shows that 'trifling' reflects our judgement of appearance, not a proven lack of consequence for survival`
  - Best window recall against lesson: 0.22

- **module 4 / lesson 3 / item 2** (Why Occasional Destruction Matters)
  - Q: Why does the objection that 'occasional destruction would produce little effect' fail?
  - Expected answer: `Because the deficit is inherited and repeated, so tiny per-generation effects add up over many generations`
  - Best window recall against lesson: 0.45

### Concept coverage across the source

- 24/60 concepts anchored to a source chunk (36 unanchored)
- Chunks containing at least one concept: 2/2 (100.0%)
- Concepts per chunk: [22, 2]
- Lessons per chunk: [2, 0]
- Uncovered chunk indexes: none
- Largest share in one chunk: 91.7%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.7334, 0.2666]
- Actual share per chunk: [0.9167, 0.0833]
- Actual/expected: [1.2499, 0.3125]
- Worst concentration ratio: 1.25

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 96.7%
- Worst chunk: 1 at 96.4%
- Chunks under 50% covered: 0
- Lessons routed per segment: [0, 0]
- Segments with no lesson: n/a (routing off)

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 62 | 96.9% | 0.968 |
| 1 | 2,747 | 28 | 27 | 96.4% | 0.952 |

## pep8-url

**Generation failed:** `ValueError: No JSON object in model response: 'python\\ndef processRecord(rec):\\n    ...\\n'`

Source: url `https://peps.python.org/pep-0008/`, 48,597 chars, 8 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 1 | 1 | 1 | 0 | 0 | 0 | 1 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 1 | 18,834 | 2,929 | $0.1674 | 36.4 | 36.4 |
| outline | 1 | 18,639 | 2,704 | $0.1608 | 31.7 | 31.7 |
