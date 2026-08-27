# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 9 |
| Quiz items | 53 |
| Structure problems | 3 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.5094 |
| Grounded, extractive items only | 0.5745 |
| Ungrounded items, all | 15 |
| Ungrounded extractive items | 11 |
| Hallucination candidates | 6 |
| Mean grounding recall | 0.6986 |
| Answerable from lesson | 0.6415 |
| Unanswerable items | 6 |
| Giveaway MCQs | 3 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 0.9646 |
| Wall clock s | 471.38 |

## prose-short

Source: text `darwin-origin-short`, 2,498 chars, 1 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 9 | 9 | 0 | 0 | 9 | 9 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 9 | 13,132 | 34,229 | $0.9214 | 50.5 | 56.2 |
| outline | 1 | 984 | 1,533 | $0.0432 | 17.1 | 17.1 |

### Structure

- 3 modules, 9 lessons, 53 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6, 5, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 6315, min 5501
- Item kinds: {'mcq': 35, 'short': 18}
- Problems: {'duplicate_question': 3}

  - `duplicate_question` at module 1 / lesson 2 / item 4: also at module 1 / lesson 1 / item 3
  - `duplicate_question` at module 2 / lesson 1 / item 4: also at module 1 / lesson 1 / item 3
  - `duplicate_question` at module 3 / lesson 3 / item 4: also at module 2 / lesson 2 / item 3

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 27/53 answers supported (exact or strong) = 50.9%
- Tiers: {'exact': 6, 'strong': 21, 'partial': 11, 'unsupported': 15}
- Mean best-window recall: 0.699
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 47, 'odd_one_out': 1, 'restatement': 5, 'trivial': 0}
- Extractive items supported: 27/47 = 57.4% (mean window recall 0.731)
- Odd-one-out items: mean share of their distractors found in the source = 100.0%
- Restatement items: mean share of answer words absent from the source = 47.8%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 6

  - **module 1 / lesson 1 / item 1** (extractive) novel 78%: Both are treated as already established in earlier chapters, so the new question is what happens when they are combined
  - **module 1 / lesson 1 / item 6** (restatement) novel 79%: No. He answers almost immediately, saying 'I think we shall see that it can act most effectually,' and then builds the supporting argument afterwards. Stating t
  - **module 1 / lesson 3 / item 1** (extractive) novel 71%: Because the many tight relations give a chance peculiarity numerous ways of bearing on a being's chances, so almost any change may touch something that matters
  - **module 1 / lesson 3 / item 6** (extractive) novel 73%: It shows that variation is not confined in advance to a few channels, so selection is offered raw material in every direction
  - **module 2 / lesson 1 / item 6** (extractive) novel 80%: It shifts the burden onto the doubter, inviting a reader who has granted the premises to draw the conclusion himself
  - **module 2 / lesson 3 / item 6** (extractive) novel 92%: It makes the claim specific to a defined class of differences, rather than a claim that explains every feature and predicts nothing

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 1** (Darwin's Opening Question)
  - Q: According to the lesson, why does Darwin refer to the struggle for existence and to man's power of selection in his opening two questions?
  - Expected answer: `Both are treated as already established in earlier chapters, so the new question is what happens when they are combined`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 1 / lesson 1 / item 4** (Darwin's Opening Question)
  - Q: Darwin asks the reader to bear in mind that the mutual relations of organic beings to each other and to their conditions of life are 'infinitely complex and close-fitting.' What role does this premise play in his argument?
  - Expected answer: `It makes it plausible that a slight variation could turn out to be useful in some way in the battle of life`
  - Best window recall 0.44, global token recall 0.67
  - Closest source text: `each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle`

- **module 1 / lesson 2 / item 3** (Variation, Heredity, and Plasticity)
  - Q: In Darwin's own words, what does he name 'Natural Selection'?
  - Expected answer: `The preservation of favourable variations and the rejection of injurious variations. It is a two-sided process — both the keeping of useful variations and the destruction of harmful ones — not survival alone.`
  - Best window recall 0.40, global token recall 0.40
  - Closest source text: `survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and`

- **module 1 / lesson 3 / item 1** (The Web of Mutual Relations)
  - Q: In Darwin's argument, why does the complexity of mutual relations make useful variations more likely rather than less?
  - Expected answer: `Because the many tight relations give a chance peculiarity numerous ways of bearing on a being's chances, so almost any change may touch something that matters`
  - Best window recall 0.12, global token recall 0.24
  - Closest source text: `relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occu`

- **module 1 / lesson 3 / item 6** (The Web of Mutual Relations)
  - Q: Darwin says that under domestication "the whole organisation becomes in some degree plastic." What role does this remark play in his argument?
  - Expected answer: `It shows that variation is not confined in advance to a few channels, so selection is offered raw material in every direction`
  - Best window recall 0.18, global token recall 0.18
  - Closest source text: `to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 2 / lesson 1 / item 1** (Building the Inference Step by Step)
  - Q: In Darwin's argument, what role does the parenthetical reminder that "many more individuals are born than can possibly survive" play?
  - Expected answer: `It supplies the condition under which even a slight advantage translates into a better chance of surviving and breeding`
  - Best window recall 0.40, global token recall 0.40
  - Closest source text: `the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving`

- **module 2 / lesson 1 / item 6** (Building the Inference Step by Step)
  - Q: Darwin phrases his key steps as questions — "Can it, then, be thought improbable...?" and "can we doubt...?" What is the effect of this phrasing?
  - Expected answer: `It shifts the burden onto the doubter, inviting a reader who has granted the premises to draw the conclusion himself`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 2 / lesson 3 / item 5** (Neutral Variation and Polymorphic Species)
  - Q: In the snail example, what changes when banded shells become slightly harder for a thrush to spot?
  - Expected answer: `Banding is no longer neutral: it now confers a slight advantage, so banded individuals have the best chance of surviving and procreating, and the trait moves out of the fluctuating category and comes under the action of selection.`
  - Best window recall 0.45, global token recall 0.50
  - Closest source text: `are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation o`

- **module 2 / lesson 3 / item 6** (Neutral Variation and Polymorphic Species)
  - Q: Why does admitting a class of variation beyond selection's reach strengthen rather than weaken Darwin's argument?
  - Expected answer: `It makes the claim specific to a defined class of differences, rather than a claim that explains every feature and predicts nothing`
  - Best window recall 0.08, global token recall 0.08
  - Closest source text: `selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence of character related to the diversity of inhabitants of any small area and to naturalisation action of natural selection through divergence of character and extinction on the `

- **module 3 / lesson 1 / item 6** (Scope and Reach of Selection)
  - Q: What does Darwin say about the mutual relations of organic beings to each other and to their physical conditions of life?
  - Expected answer: `That they are infinitely complex and close-fitting — one of the things he asks the reader to bear in mind before concluding that useful variations could arise and be selected.`
  - Best window recall 0.44, global token recall 0.44
  - Closest source text: `vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical condi`

- **module 3 / lesson 3 / item 5** (Divergence of Character and the Grouping of Organic Beings)
  - Q: In the chapter summary, how is extinction presented in relation to natural selection?
  - Expected answer: `As something caused by natural selection, listed among its consequences`
  - Best window recall 0.43, global token recall 0.43
  - Closest source text: `importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused`

### Answerability (answer vs its own lesson content)

- 34/53 answerable from the lesson alone = 64.2%
- Tiers: {'exact': 5, 'strong': 29, 'partial': 13, 'unsupported': 6}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 3

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 1** (Darwin's Opening Question)
  - Q: According to the lesson, why does Darwin refer to the struggle for existence and to man's power of selection in his opening two questions?
  - Expected answer: `Both are treated as already established in earlier chapters, so the new question is what happens when they are combined`
  - Best window recall against lesson: 0.22

- **module 1 / lesson 1 / item 4** (Darwin's Opening Question)
  - Q: Darwin asks the reader to bear in mind that the mutual relations of organic beings to each other and to their conditions of life are 'infinitely complex and close-fitting.' What role does this premise play in his argument?
  - Expected answer: `It makes it plausible that a slight variation could turn out to be useful in some way in the battle of life`
  - Best window recall against lesson: 0.44

- **module 1 / lesson 1 / item 6** (Darwin's Opening Question)
  - Q: Does Darwin withhold his answer to the opening questions until the end of the chapter? Explain briefly.
  - Expected answer: `No. He answers almost immediately, saying 'I think we shall see that it can act most effectually,' and then builds the supporting argument afterwards. Stating the conclusion first and demonstrating it later is characteristic of his method.`
  - Best window recall against lesson: 0.47

- **module 1 / lesson 3 / item 1** (The Web of Mutual Relations)
  - Q: In Darwin's argument, why does the complexity of mutual relations make useful variations more likely rather than less?
  - Expected answer: `Because the many tight relations give a chance peculiarity numerous ways of bearing on a being's chances, so almost any change may touch something that matters`
  - Best window recall against lesson: 0.47

- **module 2 / lesson 1 / item 1** (Building the Inference Step by Step)
  - Q: In Darwin's argument, what role does the parenthetical reminder that "many more individuals are born than can possibly survive" play?
  - Expected answer: `It supplies the condition under which even a slight advantage translates into a better chance of surviving and breeding`
  - Best window recall against lesson: 0.40

- **module 3 / lesson 1 / item 6** (Scope and Reach of Selection)
  - Q: What does Darwin say about the mutual relations of organic beings to each other and to their physical conditions of life?
  - Expected answer: `That they are infinitely complex and close-fitting — one of the things he asks the reader to bear in mind before concluding that useful variations could arise and be selected.`
  - Best window recall against lesson: 0.38

### Concept coverage across the source

- 32/45 concepts anchored to a source chunk (13 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [32]
- Lessons per chunk: [3]
- Uncovered chunk indexes: none
- Largest share in one chunk: 100.0%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [1.0]
- Actual share per chunk: [1.0]
- Actual/expected: [1.0]
- Worst concentration ratio: 1.00

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 100.0%
- Worst chunk: 0 at 100.0%
- Chunks under 50% covered: 0
- Lessons routed per segment: [9]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 2,498 | 19 | 19 | 100.0% | 1.000 |
