# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 7 |
| Quiz items | 41 |
| Structure problems | 0 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.1951 |
| Grounded, extractive items only | 0.2286 |
| Ungrounded items, all | 26 |
| Ungrounded extractive items | 20 |
| Hallucination candidates | 14 |
| Mean grounding recall | 0.4298 |
| Answerable from lesson | 0.3171 |
| Unanswerable items | 11 |
| Giveaway MCQs | 0 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 0.7973 |
| Wall clock s | 409.86 |

## prose-short

Source: text `darwin-origin-short`, 2,498 chars, 1 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 7 | 7 | 0 | 0 | 7 | 7 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 7 | 10,037 | 28,454 | $0.7615 | 56.4 | 76.2 |
| outline | 1 | 984 | 1,235 | $0.0358 | 15.0 | 15.0 |

### Structure

- 3 modules, 7 lessons, 41 quiz items
- Quiz items per lesson: [6, 6, 6, 5, 6, 6, 6]
- Concepts per lesson: [4, 5, 5, 5, 5, 4, 5]
- Lesson content chars: mean 6844, min 5799
- Item kinds: {'mcq': 28, 'short': 13}
- Problems: none

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 8/41 answers supported (exact or strong) = 19.5%
- Tiers: {'exact': 0, 'strong': 8, 'partial': 7, 'unsupported': 26}
- Mean best-window recall: 0.430
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 35, 'odd_one_out': 1, 'restatement': 5, 'trivial': 0}
- Extractive items supported: 8/35 = 22.9% (mean window recall 0.456)
- Odd-one-out items: mean share of their distractors found in the source = 100.0%
- Restatement items: mean share of answer words absent from the source = 55.5%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 14

  - **module 1 / lesson 2 / item 2** (extractive) novel 70%: He answers almost immediately, at the very start: 'I think we shall see that it can act most effectually.' The answer comes before the evidence, so the rest of 
  - **module 1 / lesson 2 / item 6** (extractive) novel 80%: Because the passage is built as an argument whose conclusion follows once variation, heredity and overproduction are granted
  - **module 2 / lesson 1 / item 1** (extractive) novel 85%: He is conceding an obvious fact his critics would raise anyway, and he compensates for it later with appeals to vast time and vast numbers of individuals
  - **module 2 / lesson 1 / item 2** (extractive) novel 67%: Favourable peculiarities would appear and disappear without accumulating, so no form of selection could build anything up
  - **module 2 / lesson 1 / item 4** (extractive) novel 73%: It supplies an undisputed fact from which he infers that variations useful to the organism itself must also sometimes arise, since variation is not aimed at hum
  - **module 2 / lesson 1 / item 5** (extractive) novel 83%: An empirical generalisation drawn from breeding practice, requiring only that offspring resemble parents more than chance, with no mechanism supplied
  - **module 2 / lesson 2 / item 1** (extractive) novel 75%: It establishes that the fit between organism and environment is tight enough that even a slight variation can tip an outcome
  - **module 2 / lesson 2 / item 2** (restatement) novel 64%: Because each organism stands at the intersection of a great many relations at once (food, predators, competitors, climate, timing), there are many more points a
  - **module 2 / lesson 2 / item 3** (extractive) novel 81%: Whether thicker fur counts as an advantage depends on the conditions the animal actually faces, so the same variation may help in one setting and harm in anothe
  - **module 2 / lesson 2 / item 4** (extractive) novel 74%: Man selects on a short and arbitrary list of criteria, so if useful variations arise even by that narrow standard, they should arise more readily against nature
  - **module 2 / lesson 3 / item 2** (extractive) novel 64%: It places the burden on an objector to show why such variations could not occur, while committing Darwin only to a modest possibility
  - **module 2 / lesson 3 / item 6** (extractive) novel 89%: It names a process whose components have already been granted, rather than proving a new claim
  - **module 3 / lesson 1 / item 5** (restatement) novel 64%: Darwin claims only that the advantaged individual has the *best chance* of surviving and procreating. It is a probabilistic statement about tendencies across ma
  - **module 3 / lesson 2 / item 3** (extractive) novel 62%: They may be visible cases of indifferent variation, where selection is not adjudicating between the forms

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 4** (The Chapter's Own Table of Contents)
  - Q: The summary lists 'its power on characters of trifling importance' among natural selection's powers. Why is this a meaningful contrast with what a human breeder does?
  - Expected answer: `Because a breeder selects for differences he can perceive and values, while nature can act on differences too slight for us to notice, given the close-fitting relations among organic beings`
  - Best window recall 0.39, global token recall 0.44
  - Closest source text: `act most effectually let it be borne in mind in what an endless number of strange peculiarities our domestic productions and in a lesser degree those under nature vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degre`

- **module 1 / lesson 2 / item 1** (The Question Darwin Poses)
  - Q: The second of Darwin's two opening questions asks whether the principle of selection can apply in nature. What does that question presuppose has already been established?
  - Expected answer: `That selection in the hands of human breeders is powerful`
  - Best window recall 0.40, global token recall 0.40
  - Closest source text: `explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands`

- **module 1 / lesson 2 / item 2** (The Question Darwin Poses)
  - Q: How does Darwin answer his own opening questions, and where in the chapter does he do it?
  - Expected answer: `He answers almost immediately, at the very start: 'I think we shall see that it can act most effectually.' The answer comes before the evidence, so the rest of the chapter functions as the argument supporting a conclusion already announced.`
  - Best window recall 0.25, global token recall 0.25
  - Closest source text: `of any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variat`

- **module 1 / lesson 2 / item 3** (The Question Darwin Poses)
  - Q: What role does the premise that the mutual relations of organic beings are 'infinitely complex and close-fitting' play in Darwin's reasoning?
  - Expected answer: `It makes it plausible that many small differences will have some consequence for a being's survival`
  - Best window recall 0.12, global token recall 0.38
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 1 / lesson 2 / item 6** (The Question Darwin Poses)
  - Q: Why does the lesson say that a reader who wants to resist Darwin should attack his premises rather than his examples?
  - Expected answer: `Because the passage is built as an argument whose conclusion follows once variation, heredity and overproduction are granted`
  - Best window recall 0.10, global token recall 0.10
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 2 / lesson 1 / item 1** (Variation and Hereditary Tendency)
  - Q: Why does Darwin add the qualifier "and, in a lesser degree, those under nature" when describing how organisms vary?
  - Expected answer: `He is conceding an obvious fact his critics would raise anyway, and he compensates for it later with appeals to vast time and vast numbers of individuals`
  - Best window recall 0.08, global token recall 0.08
  - Closest source text: `iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the genera`

- **module 2 / lesson 1 / item 2** (Variation and Hereditary Tendency)
  - Q: In the lesson's terms, what would follow if the hereditary tendency were absent or negligible?
  - Expected answer: `Favourable peculiarities would appear and disappear without accumulating, so no form of selection could build anything up`
  - Best window recall 0.22, global token recall 0.33
  - Closest source text: `natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable`

- **module 2 / lesson 1 / item 4** (Variation and Hereditary Tendency)
  - Q: Darwin writes that "variations useful to man have undoubtedly occurred." What work does this observation do in his argument?
  - Expected answer: `It supplies an undisputed fact from which he infers that variations useful to the organism itself must also sometimes arise, since variation is not aimed at human purposes`
  - Best window recall 0.20, global token recall 0.27
  - Closest source text: `mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being `

- **module 2 / lesson 1 / item 5** (Variation and Hereditary Tendency)
  - Q: According to the lesson, what is the status of Darwin's claim about the hereditary tendency?
  - Expected answer: `An empirical generalisation drawn from breeding practice, requiring only that offspring resemble parents more than chance, with no mechanism supplied`
  - Best window recall 0.08, global token recall 0.08
  - Closest source text: `great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance`

- **module 2 / lesson 1 / item 6** (Variation and Hereditary Tendency)
  - Q: What does Darwin say becomes of variations that are neither useful nor injurious, and what does this reveal about the scope of natural selection?
  - Expected answer: `He says they "would not be affected by natural selection, and would be left a fluctuating element," as perhaps in the species called polymorphic. This shows that selection does not grip all variation: it acts only on the portion that makes a difference to survival, while neutral variation simply fluctuates.`
  - Best window recall 0.48, global token recall 0.48
  - Closest source text: `more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed th`

- **module 2 / lesson 2 / item 1** (The Web of Mutual Relations)
  - Q: According to the lesson, what does the word 'close-fitting' contribute to Darwin's argument that 'complex' does not already supply?
  - Expected answer: `It establishes that the fit between organism and environment is tight enough that even a slight variation can tip an outcome`
  - Best window recall 0.17, global token recall 0.25
  - Closest source text: `do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation`

- **module 2 / lesson 2 / item 3** (The Web of Mutual Relations)
  - Q: The lesson says utility is 'relational, not intrinsic.' Which statement best expresses that idea?
  - Expected answer: `Whether thicker fur counts as an advantage depends on the conditions the animal actually faces, so the same variation may help in one setting and harm in another`
  - Best window recall 0.12, global token recall 0.19
  - Closest source text: `complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and`

- **module 2 / lesson 2 / item 4** (The Web of Mutual Relations)
  - Q: How does the complexity premise strengthen Darwin's move from 'variations useful to man have undoubtedly occurred' to variations useful in nature?
  - Expected answer: `Man selects on a short and arbitrary list of criteria, so if useful variations arise even by that narrow standard, they should arise more readily against nature's far more numerous standards`
  - Best window recall 0.21, global token recall 0.26
  - Closest source text: `domestic productions and in a lesser degree those under nature vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations `

- **module 2 / lesson 3 / item 1** (From Useful to Man to Useful in Nature)
  - Q: Why does Darwin describe the standard 'useful in some way to each being in the great and complex battle of life' as a broader criterion than 'useful to man'?
  - Expected answer: `Because the countless close-fitting relations of a being to its conditions create far more ways in which a variation could turn out advantageous than human purposes do`
  - Best window recall 0.29, global token recall 0.36
  - Closest source text: `degree those under nature vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other a`

- **module 2 / lesson 3 / item 2** (From Useful to Man to Useful in Nature)
  - Q: What is the rhetorical effect of phrasing the key claim as 'Can it, then, be thought improbable...?' rather than as a flat assertion?
  - Expected answer: `It places the burden on an objector to show why such variations could not occur, while committing Darwin only to a modest possibility`
  - Best window recall 0.18, global token recall 0.27
  - Closest source text: `other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur`

- **module 2 / lesson 3 / item 6** (From Useful to Man to Useful in Nature)
  - Q: The passage moves from an undoubted fact through two questions to a definition. What does the final step ('This preservation of favourable variations and the rejection of injurious variations, I call Natural Selection') actually accomplish?
  - Expected answer: `It names a process whose components have already been granted, rather than proving a new claim`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 1 / item 1** (Advantage, Survival, and Procreation)
  - Q: Why does Darwin insert the parenthesis "remembering that many more individuals are born than can possibly survive" into his key sentence?
  - Expected answer: `Because scarcity of places means individuals compete, so even a slight comparative advantage decides who survives and breeds`
  - Best window recall 0.23, global token recall 0.23
  - Closest source text: `other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage how`

- **module 3 / lesson 1 / item 4** (Advantage, Survival, and Procreation)
  - Q: Darwin writes that the advantaged individual has "the best chance of surviving and of procreating their kind." Why is the second clause essential rather than redundant?
  - Expected answer: `Because an individual that survives but leaves no offspring transmits nothing, so descendants are what the argument requires`
  - Best window recall 0.10, global token recall 0.10
  - Closest source text: `isolation number of individuals slow action extinction caused by natural selection divergence of character related to the diversity of inhabitants of any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants`

- **module 3 / lesson 2 / item 3** (The Definition and Its Limits)
  - Q: Why does Darwin mention polymorphic species right after defining natural selection?
  - Expected answer: `They may be visible cases of indifferent variation, where selection is not adjudicating between the forms`
  - Best window recall 0.25, global token recall 0.38
  - Closest source text: `gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between`

- **module 3 / lesson 2 / item 6** (The Definition and Its Limits)
  - Q: Which statement about Darwin's definition is accurate as presented in the lesson?
  - Expected answer: `Its currency is both surviving and procreating, not survival alone`
  - Best window recall 0.40, global token recall 0.40
  - Closest source text: `thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating`

### Answerability (answer vs its own lesson content)

- 13/41 answerable from the lesson alone = 31.7%
- Tiers: {'exact': 0, 'strong': 13, 'partial': 17, 'unsupported': 11}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 0

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 5** (The Chapter's Own Table of Contents)
  - Q: What role does the plasticity of organisms under domestication play in the opening argument of Chapter IV?
  - Expected answer: `It establishes that organisms are variable rather than fixed. Since variations useful to man have undoubtedly occurred under domestication, and since nature varies too (though in a lesser degree) amid infinitely complex relations among beings, Darwin infers that variations useful to the organisms themselves must sometimes occur.`
  - Best window recall against lesson: 0.43

- **module 1 / lesson 2 / item 6** (The Question Darwin Poses)
  - Q: Why does the lesson say that a reader who wants to resist Darwin should attack his premises rather than his examples?
  - Expected answer: `Because the passage is built as an argument whose conclusion follows once variation, heredity and overproduction are granted`
  - Best window recall against lesson: 0.30

- **module 2 / lesson 1 / item 1** (Variation and Hereditary Tendency)
  - Q: Why does Darwin add the qualifier "and, in a lesser degree, those under nature" when describing how organisms vary?
  - Expected answer: `He is conceding an obvious fact his critics would raise anyway, and he compensates for it later with appeals to vast time and vast numbers of individuals`
  - Best window recall against lesson: 0.31

- **module 2 / lesson 1 / item 2** (Variation and Hereditary Tendency)
  - Q: In the lesson's terms, what would follow if the hereditary tendency were absent or negligible?
  - Expected answer: `Favourable peculiarities would appear and disappear without accumulating, so no form of selection could build anything up`
  - Best window recall against lesson: 0.22

- **module 2 / lesson 2 / item 1** (The Web of Mutual Relations)
  - Q: According to the lesson, what does the word 'close-fitting' contribute to Darwin's argument that 'complex' does not already supply?
  - Expected answer: `It establishes that the fit between organism and environment is tight enough that even a slight variation can tip an outcome`
  - Best window recall against lesson: 0.42

- **module 2 / lesson 2 / item 3** (The Web of Mutual Relations)
  - Q: The lesson says utility is 'relational, not intrinsic.' Which statement best expresses that idea?
  - Expected answer: `Whether thicker fur counts as an advantage depends on the conditions the animal actually faces, so the same variation may help in one setting and harm in another`
  - Best window recall against lesson: 0.25

- **module 2 / lesson 3 / item 2** (From Useful to Man to Useful in Nature)
  - Q: What is the rhetorical effect of phrasing the key claim as 'Can it, then, be thought improbable...?' rather than as a flat assertion?
  - Expected answer: `It places the burden on an objector to show why such variations could not occur, while committing Darwin only to a modest possibility`
  - Best window recall against lesson: 0.45

- **module 2 / lesson 3 / item 6** (From Useful to Man to Useful in Nature)
  - Q: The passage moves from an undoubted fact through two questions to a definition. What does the final step ('This preservation of favourable variations and the rejection of injurious variations, I call Natural Selection') actually accomplish?
  - Expected answer: `It names a process whose components have already been granted, rather than proving a new claim`
  - Best window recall against lesson: 0.22

- **module 3 / lesson 1 / item 1** (Advantage, Survival, and Procreation)
  - Q: Why does Darwin insert the parenthesis "remembering that many more individuals are born than can possibly survive" into his key sentence?
  - Expected answer: `Because scarcity of places means individuals compete, so even a slight comparative advantage decides who survives and breeds`
  - Best window recall against lesson: 0.31

- **module 3 / lesson 1 / item 6** (Advantage, Survival, and Procreation)
  - Q: Which of the following was NOT among the premises Darwin restates in support of his inference?
  - Expected answer: `A known mechanism by which hereditary variations are physically transmitted to offspring`
  - Best window recall against lesson: 0.29

- **module 3 / lesson 2 / item 5** (The Definition and Its Limits)
  - Q: State two of the premises Darwin lays out before naming natural selection, and explain why both are necessary.
  - Expected answer: `Any two of: variation is abundant; variation is heritable; the mutual relations of organisms are infinitely complex and close-fitting, so small changes can matter; some variations will therefore be useful to their possessors; many more individuals are born than can survive. Heritability is needed or an advantage would not be passed on; overproduction is needed or there would be no differential survival to sort the variants; complexity of relations is needed to make it plausible that variations are useful in some way.`
  - Best window recall against lesson: 0.49

### Concept coverage across the source

- 15/33 concepts anchored to a source chunk (18 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [15]
- Lessons per chunk: [1]
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
- Lessons routed per segment: [7]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 2,498 | 19 | 19 | 100.0% | 1.000 |
