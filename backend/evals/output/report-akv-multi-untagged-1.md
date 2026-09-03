# StudyForge generation eval

## Headline metrics

| Metric | multi-darwin-pep8 |
|---|---|
| Lessons | 7 |
| Quiz items | 42 |
| Structure problems | 6 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.4524 |
| Grounded, extractive items only | 0.4872 |
| Ungrounded items, all | 7 |
| Ungrounded extractive items | 6 |
| Hallucination candidates | 0 |
| Mean grounding recall | 0.7345 |
| Answerable from lesson | 0.4524 |
| Unanswerable items | 3 |
| Giveaway MCQs | 2 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.4583 |
| Concentration vs chunk length | 1.7862 |
| Source recall, mean chunk | 0.9687 |
| Source recall, worst chunk | 0.9062 |
| Cost USD | 0.7942 |
| Wall clock s | 357.37 |

## multi-darwin-pep8

Source: text `darwin-origin + pep8-style-guide`, 13,639 chars, 3 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 7 | 7 | 0 | 0 | 7 | 7 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 7 | 16,380 | 26,011 | $0.7322 | 48.1 | 66.9 |
| outline | 1 | 4,934 | 1,493 | $0.0620 | 20.8 | 20.8 |

### Structure

- 3 modules, 7 lessons, 42 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 4]
- Lesson content chars: mean 6022, min 3755
- Item kinds: {'short': 13, 'mcq': 29}
- Problems: {'empty_concept': 6}

  - `empty_concept` at module 3 / lesson 1 / item 1: According to PEP 8's own header, what Type of PEP is it?
  - `empty_concept` at module 3 / lesson 1 / item 2: PEP 8's Introduction says the document gives coding conventions for which body of code?
  - `empty_concept` at module 3 / lesson 1 / item 3: A project you join has a house style guide that conflicts with PEP 8 on a particular point. According to PEP 8's Introduction, which guide applies within that project, and why?
  - `empty_concept` at module 3 / lesson 1 / item 4: Which statement about PEP 8's companion documents is accurate?
  - `empty_concept` at module 3 / lesson 1 / item 5: Why does PEP 8 describe itself as a guide that changes over time?
  - `empty_concept` at module 3 / lesson 1 / item 6: From which earlier writings were PEP 8 and PEP 257 adapted?

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 19/42 answers supported (exact or strong) = 45.2%
- Tiers: {'exact': 8, 'strong': 11, 'partial': 16, 'unsupported': 7}
- Mean best-window recall: 0.734
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 2

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 39, 'odd_one_out': 0, 'restatement': 3, 'trivial': 0}
- Extractive items supported: 19/39 = 48.7% (mean window recall 0.754)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 22.9%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 0

#### Ungrounded extractive items

- **module 1 / lesson 3 / item 2** (Nature's Selection Compared with Man's)
  - Q: Darwin says that nature 'cares nothing for appearances' — but he adds a qualification. What is it?
  - Expected answer: `Appearances matter in so far as they may be useful to any being; a visible character that helps the creature survive will still be selected.`
  - Best window recall 0.36, global token recall 0.73
  - Closest source text: `produce and certainly has produced a great result by his methodical and unconscious means of selection what may not nature effect man can act only on external and visible characters nature cares nothing for appearances except in so far as they may be useful`

- **module 1 / lesson 3 / item 4** (Nature's Selection Compared with Man's)
  - Q: Complete Darwin's contrast: 'Man selects only for his own good; Nature only for ___.'
  - Expected answer: `that of the being which she tends (i.e. the good of the organism itself).`
  - Best window recall 0.40, global token recall 0.60
  - Closest source text: `useful to any being she can act on every internal organ on every shade of constitutional difference on the whole machinery of life man selects only for his own good nature only for that of the being which she tends`

- **module 2 / lesson 1 / item 1** (Daily and Hourly Scrutiny)
  - Q: In Darwin's famous sentence, what two operations does natural selection perform on variations?
  - Expected answer: `It rejects what is bad, and preserves and adds up all that is good`
  - Best window recall 0.40, global token recall 0.40
  - Closest source text: `it may be said that natural selection is daily and hourly scrutinising throughout the world every variation even the slightest rejecting that which is bad preserving and adding up all that is good silently and insensibly working whenever and wherever`

- **module 2 / lesson 2 / item 1** (Colour, Down, and Other Trifles)
  - Q: Why does Darwin specifically mention that hawks are guided by eyesight to their prey?
  - Expected answer: `Because it establishes that the chief enemy of grouse can be deceived by plumage colour, giving selection something to act on`
  - Best window recall 0.33, global token recall 0.42
  - Closest source text: `much so that on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse`

- **module 2 / lesson 2 / item 2** (Colour, Down, and Other Trifles)
  - Q: According to the lesson, what is the point of the example of the flock of white sheep?
  - Expected answer: `That the occasional removal of a slightly deviating individual is enough to keep a character true and constant`
  - Best window recall 0.30, global token recall 0.70
  - Closest source text: `no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant nor ought we to think that the occasional`

- **module 2 / lesson 2 / item 4** (Colour, Down, and Other Trifles)
  - Q: Darwin notes that a disease attacks yellow-fleshed peaches more than others, while yellow plums resist a disease better than purple ones. What does this pair of facts show?
  - Expected answer: `That advantage is relative to the particular enemy, so no colour is simply superior`
  - Best window recall 0.29, global token recall 0.43
  - Closest source text: `might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant nor ought we to think that the occasional destruction of an animal of any particular`

### Answerability (answer vs its own lesson content)

- 19/42 answerable from the lesson alone = 45.2%
- Tiers: {'exact': 7, 'strong': 12, 'partial': 20, 'unsupported': 3}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 2

#### Items not answerable from their lesson

- **module 1 / lesson 3 / item 4** (Nature's Selection Compared with Man's)
  - Q: Complete Darwin's contrast: 'Man selects only for his own good; Nature only for ___.'
  - Expected answer: `that of the being which she tends (i.e. the good of the organism itself).`
  - Best window recall against lesson: 0.40

- **module 2 / lesson 1 / item 1** (Daily and Hourly Scrutiny)
  - Q: In Darwin's famous sentence, what two operations does natural selection perform on variations?
  - Expected answer: `It rejects what is bad, and preserves and adds up all that is good`
  - Best window recall against lesson: 0.40

- **module 2 / lesson 1 / item 5** (Daily and Hourly Scrutiny)
  - Q: Downing reported that in the United States smooth-skinned fruits suffer far more from a certain beetle than downy ones. What conclusion does Darwin draw from this and similar cases?
  - Expected answer: `That since these differences already tell with all the aids of art, in nature they would effectually settle which variety succeeds`
  - Best window recall against lesson: 0.45

### Concept coverage across the source

- 24/34 concepts anchored to a source chunk (10 unanchored)
- Chunks containing at least one concept: 3/3 (100.0%)
- Concepts per chunk: [11, 5, 8]
- Lessons per chunk: [2, 0, 1]
- Uncovered chunk indexes: none
- Largest share in one chunk: 45.8%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.5965, 0.2169, 0.1866]
- Actual share per chunk: [0.4583, 0.2083, 0.3333]
- Actual/expected: [0.7684, 0.9606, 1.7862]
- Worst concentration ratio: 1.79

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 96.9%
- Worst chunk: 0 at 90.6%
- Chunks under 50% covered: 0
- Lessons routed per segment: [3, 2, 2]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 58 | 90.6% | 0.906 |
| 1 | 2,747 | 28 | 28 | 100.0% | 0.945 |
| 2 | 3,000 | 9 | 9 | 100.0% | 0.986 |
