# StudyForge generation eval

## Headline metrics

| Metric | multi-darwin-pep8 |
|---|---|
| Lessons | 7 |
| Quiz items | 41 |
| Structure problems | 1 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.3659 |
| Grounded, extractive items only | 0.3846 |
| Ungrounded items, all | 8 |
| Ungrounded extractive items | 7 |
| Hallucination candidates | 1 |
| Mean grounding recall | 0.6833 |
| Answerable from lesson | 0.5122 |
| Unanswerable items | 7 |
| Giveaway MCQs | 2 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.5333 |
| Concentration vs chunk length | 2.1435 |
| Source recall, mean chunk | 0.9673 |
| Source recall, worst chunk | 0.9375 |
| Cost USD | 0.7962 |
| Wall clock s | 354.76 |

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
| lesson | 7 | 16,342 | 26,060 | $0.7332 | 47.8 | 57.5 |
| outline | 1 | 4,934 | 1,531 | $0.0629 | 20.5 | 20.5 |

### Structure

- 3 modules, 7 lessons, 41 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 5]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 4]
- Lesson content chars: mean 5919, min 5041
- Item kinds: {'mcq': 28, 'short': 13}
- Problems: {'duplicate_question': 1}

  - `duplicate_question` at module 1 / lesson 3 / item 3: also at module 1 / lesson 2 / item 5

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 15/41 answers supported (exact or strong) = 36.6%
- Tiers: {'exact': 4, 'strong': 11, 'partial': 18, 'unsupported': 8}
- Mean best-window recall: 0.683
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 39, 'odd_one_out': 0, 'restatement': 2, 'trivial': 0}
- Extractive items supported: 15/39 = 38.5% (mean window recall 0.688)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 23.0%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 1

  - **module 3 / lesson 1 / item 5** (extractive) novel 64%: It extends beyond visual formatting into how code should be written, and it has been expanded as the language gained new features.

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 1** (From Human Selection to Nature's Selection)
  - Q: Which statement best captures Darwin's own definition of natural selection as given in this passage?
  - Expected answer: `The keeping of variations that help their possessor and the destruction of those that harm it`
  - Best window recall 0.33, global token recall 0.50
  - Closest source text: `not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping`

- **module 1 / lesson 1 / item 3** (From Human Selection to Nature's Selection)
  - Q: In the parenthesis 'remembering that many more individuals are born than can possibly survive', what work is this fact doing in Darwin's argument?
  - Expected answer: `It explains why even a slight advantage should improve an individual's chance of surviving and breeding`
  - Best window recall 0.40, global token recall 0.90
  - Closest source text: `the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving`

- **module 2 / lesson 1 / item 2** (Silent and Insensible Work)
  - Q: Darwin says selection improves each organic being 'in relation to its organic and inorganic conditions of life.' What does this qualification imply?
  - Expected answer: `Improvement is measured against the being's particular surroundings, not by any absolute standard`
  - Best window recall 0.25, global token recall 0.50
  - Closest source text: `comprising the standard library in the main python distribution please see the companion informational pep describing style guidelines for the c code in the c implementation of python this document and pep 257 docstring conventions were adapted from guido s`

- **module 2 / lesson 2 / item 1** (Colour, Concealment, and Trifling Differences)
  - Q: Why does Darwin's argument place such weight on the fact that hawks are guided by eyesight to their prey?
  - Expected answer: `Because a predator that hunts by sight makes an animal's colour a matter of life and death, so tints can be selected`
  - Best window recall 0.15, global token recall 0.46
  - Closest source text: `for appearances except in so far as they may be useful to any being she can act on every internal organ on every shade of constitutional difference on the whole machinery of life man selects only for his own good nature only for that of the being which she tends every selected`

- **module 2 / lesson 2 / item 4** (Colour, Concealment, and Trifling Differences)
  - Q: How does the flock of white sheep answer the objection that only occasional destruction of oddly-coloured animals occurs?
  - Expected answer: `It shows that removing even the few lambs with the faintest trace of black is what keeps the whole flock uniformly white`
  - Best window recall 0.42, global token recall 0.67
  - Closest source text: `once acquired true and constant nor ought we to think that the occasional destruction of an animal of any particular colour would produce little effect we should remember how essential it is in a flock of white sheep to destroy every lamb with the faintest trace of black`

- **module 3 / lesson 1 / item 1** (What PEP 8 Is and What It Covers)
  - Q: PEP 8's Status is listed as "Active" and its Type as "Process". What does this combination tell you about the document?
  - Expected answer: `It describes a process rather than a language change, and it remains in force and continues to be amended over time.`
  - Best window recall 0.20, global token recall 0.40
  - Closest source text: `man can certainly produce great results by adding up in any given direction mere individual differences so could nature but far more easily from having incomparably longer time at her disposal nor do i believe that any great physical change`

- **module 3 / lesson 1 / item 5** (What PEP 8 Is and What It Covers)
  - Q: PEP 8's table of contents includes a section titled "Programming Recommendations", with subsections on Function Annotations and Variable Annotations. What does the presence of this section show about the document's scope?
  - Expected answer: `It extends beyond visual formatting into how code should be written, and it has been expanded as the language gained new features.`
  - Best window recall 0.18, global token recall 0.36
  - Closest source text: `the language itself many projects have their own coding style guidelines in the event of any conflicts such project specific guides take precedence for that project a foolish consistency is the hobgoblin of little minds one of guido s key insights is that code`

### Answerability (answer vs its own lesson content)

- 21/41 answerable from the lesson alone = 51.2%
- Tiers: {'exact': 4, 'strong': 17, 'partial': 13, 'unsupported': 7}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 2

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 1** (From Human Selection to Nature's Selection)
  - Q: Which statement best captures Darwin's own definition of natural selection as given in this passage?
  - Expected answer: `The keeping of variations that help their possessor and the destruction of those that harm it`
  - Best window recall against lesson: 0.17

- **module 1 / lesson 1 / item 3** (From Human Selection to Nature's Selection)
  - Q: In the parenthesis 'remembering that many more individuals are born than can possibly survive', what work is this fact doing in Darwin's argument?
  - Expected answer: `It explains why even a slight advantage should improve an individual's chance of surviving and breeding`
  - Best window recall against lesson: 0.40

- **module 1 / lesson 3 / item 2** (Why Nature Outdoes the Breeder)
  - Q: Darwin says that man 'feeds a long and a short beaked pigeon on the same food' and 'exposes sheep with long and short wool to the same climate.' Which handicap of human selection do these examples illustrate?
  - Expected answer: `That man selects characters but then fails to exercise each one in a fitting manner or place the animal under well-suited conditions`
  - Best window recall against lesson: 0.46

- **module 2 / lesson 1 / item 5** (Silent and Insensible Work)
  - Q: Why does Darwin mention destroying every lamb with the faintest trace of black in a flock of white sheep?
  - Expected answer: `To show that occasional destruction of individuals of a particular colour can have a real effect on a population`
  - Best window recall against lesson: 0.44

- **module 2 / lesson 2 / item 1** (Colour, Concealment, and Trifling Differences)
  - Q: Why does Darwin's argument place such weight on the fact that hawks are guided by eyesight to their prey?
  - Expected answer: `Because a predator that hunts by sight makes an animal's colour a matter of life and death, so tints can be selected`
  - Best window recall against lesson: 0.38

- **module 3 / lesson 1 / item 1** (What PEP 8 Is and What It Covers)
  - Q: PEP 8's Status is listed as "Active" and its Type as "Process". What does this combination tell you about the document?
  - Expected answer: `It describes a process rather than a language change, and it remains in force and continues to be amended over time.`
  - Best window recall against lesson: 0.40

- **module 3 / lesson 1 / item 5** (What PEP 8 Is and What It Covers)
  - Q: PEP 8's table of contents includes a section titled "Programming Recommendations", with subsections on Function Annotations and Variable Annotations. What does the presence of this section show about the document's scope?
  - Expected answer: `It extends beyond visual formatting into how code should be written, and it has been expanded as the language gained new features.`
  - Best window recall against lesson: 0.36

### Concept coverage across the source

- 15/34 concepts anchored to a source chunk (19 unanchored)
- Chunks containing at least one concept: 3/3 (100.0%)
- Concepts per chunk: [8, 1, 6]
- Lessons per chunk: [0, 0, 1]
- Uncovered chunk indexes: none
- Largest share in one chunk: 53.3%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.5965, 0.2169, 0.1866]
- Actual share per chunk: [0.5333, 0.0667, 0.4]
- Actual/expected: [0.8941, 0.3074, 2.1435]
- Worst concentration ratio: 2.14

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 96.7%
- Worst chunk: 0 at 93.8%
- Chunks under 50% covered: 0
- Lessons routed per segment: [3, 2, 2]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 60 | 93.8% | 0.897 |
| 1 | 2,747 | 28 | 27 | 96.4% | 0.945 |
| 2 | 3,000 | 9 | 9 | 100.0% | 0.982 |
