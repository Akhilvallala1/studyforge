# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 10 |
| Quiz items | 59 |
| Structure problems | 2 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.2034 |
| Grounded, extractive items only | 0.2683 |
| Ungrounded items, all | 43 |
| Ungrounded extractive items | 27 |
| Hallucination candidates | 26 |
| Mean grounding recall | 0.3981 |
| Answerable from lesson | 0.2203 |
| Unanswerable items | 20 |
| Giveaway MCQs | 1 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 1.0972 |
| Wall clock s | 560.77 |

## prose-short

Source: text `darwin-origin-short`, 2,498 chars, 1 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 10 | 10 | 0 | 0 | 10 | 10 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 10 | 12,627 | 39,893 | $1.0605 | 54.5 | 66.2 |
| outline | 1 | 984 | 1,272 | $0.0367 | 15.8 | 15.8 |

### Structure

- 3 modules, 10 lessons, 59 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 5, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 4, 5, 5, 5, 5, 5, 5, 4, 5]
- Lesson content chars: mean 7157, min 5599
- Item kinds: {'mcq': 34, 'short': 25}
- Problems: {'duplicate_question': 2}

  - `duplicate_question` at module 2 / lesson 1 / item 4: also at module 1 / lesson 1 / item 2
  - `duplicate_question` at module 3 / lesson 1 / item 5: also at module 1 / lesson 1 / item 2

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 12/59 answers supported (exact or strong) = 20.3%
- Tiers: {'exact': 5, 'strong': 7, 'partial': 4, 'unsupported': 43}
- Mean best-window recall: 0.398
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 1

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 41, 'odd_one_out': 1, 'restatement': 17, 'trivial': 0}
- Extractive items supported: 11/41 = 26.8% (mean window recall 0.441)
- Odd-one-out items: mean share of their distractors found in the source = 100.0%
- Restatement items: mean share of answer words absent from the source = 61.3%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 26

  - **module 1 / lesson 1 / item 1** (extractive) novel 83%: The evidence is indirect, so he invites the reader to draw the inference and places the burden on the sceptic to say why the process would not occur
  - **module 1 / lesson 1 / item 3** (restatement) novel 68%: The struggle for existence supplies elimination — more are born than can survive — but without heritable variation it would remove individuals without changing 
  - **module 1 / lesson 1 / item 6** (extractive) novel 69%: He supplies an analogy: since selection demonstrably reshapes domestic organisms, it is not improbable that an analogous process operates in nature
  - **module 1 / lesson 2 / item 6** (extractive) novel 64%: Because the breeder's intention is not the load-bearing part of the analogy. What makes artificial selection work is that variation exists, it is heritable, and
  - **module 1 / lesson 3 / item 4** (extractive) novel 100%: To establish the tempo of the mechanism and defend it against the objection that transformation is never observed
  - **module 1 / lesson 3 / item 5** (restatement) novel 76%: 'Caused' means extinction is not merely something selection tolerates or that happens for unrelated reasons — it is a direct product of the mechanism itself. Im
  - **module 2 / lesson 1 / item 1** (extractive) novel 80%: It admits domesticated forms are more variable while insisting the difference is one of degree, so wild variation still supplies material for selection
  - **module 2 / lesson 1 / item 2** (extractive) novel 100%: The entire structure and constitution of the being, including internal parts, instincts and development
  - **module 2 / lesson 2 / item 2** (restatement) novel 71%: Because tiny increments only accumulate into significant change if they are transmitted faithfully across thousands of generations; weak or unreliable inheritan
  - **module 2 / lesson 2 / item 4** (extractive) novel 71%: The practice of domestic breeding, where fanciers fix peculiarities in a stock
  - **module 2 / lesson 2 / item 5** (restatement) novel 88%: In the neutral case heredity still operates but there is no differential survival to give it direction, so variety is preserved without being steered toward ada
  - **module 2 / lesson 3 / item 4** (extractive) novel 71%: That he is arguing only against improbability, not claiming that useful variations are frequent
  - **module 2 / lesson 3 / item 6** (extractive) novel 80%: That complexity guarantees a variation will be relevant — it will have consequences to be weighed — even if the net effect is uncertain
  - **module 3 / lesson 1 / item 6** (restatement) novel 84%: It asks the reader to concede very little. Darwin does not need useful variations to be common or predictable; he needs only that they arise occasionally. Given
  - **module 3 / lesson 2 / item 1** (extractive) novel 69%: Without a filter removing most individuals before reproduction, a slight advantage would confer no differential success and variation would remain undirected
  - **module 3 / lesson 2 / item 2** (restatement) novel 74%: The favourable case is stated probabilistically: an advantaged individual is not guaranteed to survive, only more likely to, so selection works as a statistical
  - **module 3 / lesson 2 / item 5** (extractive) novel 62%: It shows that natural selection has no grip on traits that make no difference to survival or reproduction; such traits vary without direction. Darwin therefore 
  - **module 3 / lesson 2 / item 6** (extractive) novel 78%: Darwin would accept the observation and deny the inference. Because the advantages selection acts on may be extremely slight, their effects are invisible over t
  - **module 3 / lesson 3 / item 3** (extractive) novel 81%: A slightly harmful variant only lowers average reproductive output, and if its disadvantage is small relative to 1/N it can drift to high frequency anyway
  - **module 3 / lesson 3 / item 5** (extractive) novel 92%: He borrowed it from breeders' artificial selection, which made the process concrete and familiar; the drawback is that it suggests a choosing agent with foresig
  - **module 3 / lesson 3 / item 6** (restatement) novel 63%: Because selection is comparative: preservation of the favourable only produces sharpening adaptation if the injurious is simultaneously eliminated. If harmful v
  - **module 3 / lesson 4 / item 2** (restatement) novel 72%: Because Darwin cannot actually verify that the differing forms of a polymorphic species are indifferent to the struggle for existence. He offers polymorphism as
  - **module 3 / lesson 4 / item 3** (extractive) novel 67%: It marks a boundary where the mechanism does not apply, so the theory does not explain everything and can therefore be tested
  - **module 3 / lesson 4 / item 4** (extractive) novel 87%: Persistent polymorphism is consistent with neutrality but does not establish it. The two forms could be actively maintained by selection — for instance through 
  - **module 3 / lesson 4 / item 5** (extractive) novel 92%: Selected characters tend toward uniformity as the favoured form spreads; neutral characters remain variable and unresolved
  - **module 3 / lesson 4 / item 6** (extractive) novel 73%: It foreshadows the neutral theory of molecular evolution (Kimura, 1968), which holds that most change at the molecular level is neither advantageous nor harmful

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 1** (From the Struggle for Existence to Variation)
  - Q: Darwin opens Chapter IV with questions rather than a flat assertion. Which best explains the rhetorical purpose of this framing?
  - Expected answer: `The evidence is indirect, so he invites the reader to draw the inference and places the burden on the sceptic to say why the process would not occur`
  - Best window recall 0.08, global token recall 0.08
  - Closest source text: `organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur`

- **module 1 / lesson 1 / item 4** (From the Struggle for Existence to Variation)
  - Q: Darwin's phrase 'how infinitely complex and close-fitting are the mutual relations of all organic beings' does what work in the argument?
  - Expected answer: `It explains why even a slight variation can affect an individual's chance of surviving`
  - Best window recall 0.44, global token recall 0.67
  - Closest source text: `more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation`

- **module 1 / lesson 1 / item 6** (From the Struggle for Existence to Variation)
  - Q: What role does the human breeder play in Darwin's opening argument?
  - Expected answer: `He supplies an analogy: since selection demonstrably reshapes domestic organisms, it is not improbable that an analogous process operates in nature`
  - Best window recall 0.23, global token recall 0.31
  - Closest source text: `act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature i think we shall see that it can act most effectually let it be borne in mind in what an endless number of strange peculiarities our domestic`

- **module 1 / lesson 2 / item 1** (Can Selection Apply in Nature?)
  - Q: How does Darwin answer his own question about whether the principle of selection can apply in nature?
  - Expected answer: `He states at once that he thinks it can act most effectually, then argues for it`
  - Best window recall 0.40, global token recall 0.40
  - Closest source text: `in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature i think we shall see that it can act most effectually`

- **module 1 / lesson 2 / item 5** (Can Selection Apply in Nature?)
  - Q: What work does Darwin's claim that the mutual relations of organic beings are 'infinitely complex and close-fitting' do in his argument?
  - Expected answer: `It explains why there are enormously many ways a variation could turn out to be useful, widening the criterion beyond usefulness to man`
  - Best window recall 0.25, global token recall 0.42
  - Closest source text: `the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man`

- **module 1 / lesson 2 / item 6** (Can Selection Apply in Nature?)
  - Q: A critic objects that the analogy with breeding fails because the breeder has intentions and nature has none. How does Darwin's argument answer this?
  - Expected answer: `Because the breeder's intention is not the load-bearing part of the analogy. What makes artificial selection work is that variation exists, it is heritable, and some variants reproduce while others do not — all impersonal facts that also hold in nature, and the last of them holds more severely there because of the struggle for existence.`
  - Best window recall 0.21, global token recall 0.29
  - Closest source text: `compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolatio`

- **module 1 / lesson 3 / item 4** (Reading the Chapter Summary Heading)
  - Q: Why does Darwin include 'Slow action' as a separate item in his chapter heading?
  - Expected answer: `To establish the tempo of the mechanism and defend it against the objection that transformation is never observed`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 2 / lesson 1 / item 1** (Variation Under Domestication and in Nature)
  - Q: When Darwin writes that domestic productions vary in an endless number of strange peculiarities "and, in a lesser degree, those under nature," what is the significance of the qualifying clause for his argument?
  - Expected answer: `It admits domesticated forms are more variable while insisting the difference is one of degree, so wild variation still supplies material for selection`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature i think we shall see that it can act most effectually let it be borne in mind in what an endless number of strange peculiarities our domestic productions and in `

- **module 2 / lesson 1 / item 2** (Variation Under Domestication and in Nature)
  - Q: In Darwin's phrase "under domestication... the whole organisation becomes in some degree plastic," what does "the whole organisation" refer to?
  - Expected answer: `The entire structure and constitution of the being, including internal parts, instincts and development`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 2 / lesson 2 / item 1** (The Strength of Heredity)
  - Q: If variation existed but were not inherited at all, what would happen to Darwin's mechanism?
  - Expected answer: `Selection would still operate, but any advantage would die with the individual and no cumulative change would occur`
  - Best window recall 0.22, global token recall 0.33
  - Closest source text: `the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage`

- **module 2 / lesson 2 / item 4** (The Strength of Heredity)
  - Q: What evidence had Darwin already laid out that lets him simply ask readers to 'bear in mind' how strong the hereditary tendency is?
  - Expected answer: `The practice of domestic breeding, where fanciers fix peculiarities in a stock`
  - Best window recall 0.29, global token recall 0.29
  - Closest source text: `have seen is so potent in the hands of man apply in nature i think we shall see that it can act most effectually let it be borne in mind in what an endless number of strange peculiarities our domestic`

- **module 2 / lesson 3 / item 1** (Complex and Close-Fitting Relations)
  - Q: What logical work does the premise about 'infinitely complex and close-fitting' relations do in Darwin's argument?
  - Expected answer: `It bridges from man's selection to nature by making it plausible that variations useful to the organism itself sometimes occur`
  - Best window recall 0.38, global token recall 0.62
  - Closest source text: `mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometim`

- **module 2 / lesson 3 / item 3** (Complex and Close-Fitting Relations)
  - Q: A student says: 'Because the environment is so complex, it pressures organisms into producing the variations they need.' What is wrong with this?
  - Expected answer: `The complex relations do not produce variations; they only determine whether a variation that has arisen is favourable, injurious, or indifferent`
  - Best window recall 0.36, global token recall 0.55
  - Closest source text: `having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations`

- **module 2 / lesson 3 / item 4** (Complex and Close-Fitting Relations)
  - Q: Darwin says that in a world of complex relations, useful variations 'should sometimes occur in the course of thousands of generations.' What does the word 'sometimes' concede?
  - Expected answer: `That he is arguing only against improbability, not claiming that useful variations are frequent`
  - Best window recall 0.29, global token recall 0.29
  - Closest source text: `let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful`

- **module 2 / lesson 3 / item 6** (Complex and Close-Fitting Relations)
  - Q: In the flowering-date example, an earlier-flowering variant gains better pollination and escapes a seed weevil and late drought, but risks April frost. What does this example primarily illustrate?
  - Expected answer: `That complexity guarantees a variation will be relevant — it will have consequences to be weighed — even if the net effect is uncertain`
  - Best window recall 0.10, global token recall 0.10
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 3 / lesson 1 / item 1** (Useful Variations in the Battle of Life)
  - Q: Darwin argues that variations useful to each being 'should sometimes occur in the course of thousands of generations.' What rhetorical strategy underlies this claim?
  - Expected answer: `An argument from probability and analogy: since variations useful to man undoubtedly occur, it would be improbable that none is useful to the organism itself`
  - Best window recall 0.46, global token recall 0.46
  - Closest source text: `mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometim`

- **module 3 / lesson 1 / item 3** (Useful Variations in the Battle of Life)
  - Q: What role does the parenthetical reminder 'remembering that many more individuals are born than can possibly survive' play in Darwin's inference?
  - Expected answer: `It guarantees that most individuals must die anyway, so any slight advantage biases who survives to reproduce`
  - Best window recall 0.33, global token recall 0.33
  - Closest source text: `and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight`

- **module 3 / lesson 2 / item 1** (Slight Advantage and the Chance of Survival)
  - Q: Darwin places the phrase 'many more individuals are born than can possibly survive' in a parenthesis. Why is this premise essential rather than incidental to his conclusion?
  - Expected answer: `Without a filter removing most individuals before reproduction, a slight advantage would confer no differential success and variation would remain undirected`
  - Best window recall 0.31, global token recall 0.31
  - Closest source text: `of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any va`

- **module 3 / lesson 2 / item 3** (Slight Advantage and the Chance of Survival)
  - Q: According to the lesson, what allows Darwin to claim that an advantage 'however slight' is sufficient to reshape a population?
  - Expected answer: `Small biases repeated every generation compound over thousands of generations`
  - Best window recall 0.25, global token recall 0.38
  - Closest source text: `be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations`

- **module 3 / lesson 2 / item 5** (Slight Advantage and the Chance of Survival)
  - Q: Darwin writes that variations 'neither useful nor injurious' would be 'left a fluctuating element.' What does this qualification reveal about the scope of his theory?
  - Expected answer: `It shows that natural selection has no grip on traits that make no difference to survival or reproduction; such traits vary without direction. Darwin therefore does not claim that every feature of an organism is adaptive, and he cites polymorphic species as possible cases. This anticipates the modern idea of neutral variation and drift.`
  - Best window recall 0.17, global token recall 0.24
  - Closest source text: `complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and`

- **module 3 / lesson 2 / item 6** (Slight Advantage and the Chance of Survival)
  - Q: A critic objects: 'I have watched a population of beetles for ten years and seen no evolutionary change; therefore natural selection does not operate.' Using the lesson, give Darwin's likely reply.
  - Expected answer: `Darwin would accept the observation and deny the inference. Because the advantages selection acts on may be extremely slight, their effects are invisible over ten years and only become substantial across thousands of generations. The theory positively predicts that change will be too slow to observe casually, so failure to see change in a decade is exactly what one should expect, not evidence against the mechanism.`
  - Best window recall 0.14, global token recall 0.19
  - Closest source text: `physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occu`

- **module 3 / lesson 3 / item 3** (Preservation, Rejection, and the Naming of a Principle)
  - Q: The lesson argues that Darwin's phrase 'rigidly destroyed' overstates his case. Which consideration best supports that criticism?
  - Expected answer: `A slightly harmful variant only lowers average reproductive output, and if its disadvantage is small relative to 1/N it can drift to high frequency anyway`
  - Best window recall 0.06, global token recall 0.06
  - Closest source text: `man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of in`

- **module 3 / lesson 3 / item 5** (Preservation, Rejection, and the Naming of a Principle)
  - Q: Why did Darwin choose the word 'selection', and what is the chief drawback of that choice?
  - Expected answer: `He borrowed it from breeders' artificial selection, which made the process concrete and familiar; the drawback is that it suggests a choosing agent with foresight`
  - Best window recall 0.08, global token recall 0.08
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 3 / lesson 4 / item 3** (The Neutral Case and Polymorphic Species)
  - Q: Why does explicitly acknowledging a neutral category strengthen rather than weaken Darwin's theory?
  - Expected answer: `It marks a boundary where the mechanism does not apply, so the theory does not explain everything and can therefore be tested`
  - Best window recall 0.11, global token recall 0.11
  - Closest source text: `of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply`

- **module 3 / lesson 4 / item 4** (The Neutral Case and Polymorphic Species)
  - Q: A species of beetle shows two shell colours in equal proportions across many generations. A naturalist concludes this must be neutral variation. What is wrong with this inference?
  - Expected answer: `Persistent polymorphism is consistent with neutrality but does not establish it. The two forms could be actively maintained by selection — for instance through heterozygote advantage (balancing selection), through frequency-dependent selection where the rarer form is favoured by predator search images, or because different forms are favoured in different patches or seasons. Stable coexistence of forms can be a product of selection, not an absence of it.`
  - Best window recall 0.06, global token recall 0.10
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 3 / lesson 4 / item 5** (The Neutral Case and Polymorphic Species)
  - Q: Which contrast in observable pattern does Darwin's distinction predict?
  - Expected answer: `Selected characters tend toward uniformity as the favoured form spreads; neutral characters remain variable and unresolved`
  - Best window recall 0.08, global token recall 0.08
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both`

- **module 3 / lesson 4 / item 6** (The Neutral Case and Polymorphic Species)
  - Q: In what sense does Darwin's remark about neutral variation anticipate twentieth-century evolutionary biology?
  - Expected answer: `It foreshadows the neutral theory of molecular evolution (Kimura, 1968), which holds that most change at the molecular level is neither advantageous nor harmful and that its frequency is governed by random genetic drift rather than selection. Darwin's 'fluctuating element' is the same basic idea — variation whose fate is not determined by usefulness — though without the population-genetic mathematics.`
  - Best window recall 0.15, global token recall 0.21
  - Closest source text: `thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more i`

### Answerability (answer vs its own lesson content)

- 13/59 answerable from the lesson alone = 22.0%
- Tiers: {'exact': 3, 'strong': 10, 'partial': 26, 'unsupported': 20}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 1

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 4** (From the Struggle for Existence to Variation)
  - Q: Darwin's phrase 'how infinitely complex and close-fitting are the mutual relations of all organic beings' does what work in the argument?
  - Expected answer: `It explains why even a slight variation can affect an individual's chance of surviving`
  - Best window recall against lesson: 0.33

- **module 1 / lesson 1 / item 6** (From the Struggle for Existence to Variation)
  - Q: What role does the human breeder play in Darwin's opening argument?
  - Expected answer: `He supplies an analogy: since selection demonstrably reshapes domestic organisms, it is not improbable that an analogous process operates in nature`
  - Best window recall against lesson: 0.31

- **module 1 / lesson 2 / item 2** (Can Selection Apply in Nature?)
  - Q: Why is the premise that 'many more individuals are born than can possibly survive' essential to the argument, rather than merely a supporting detail?
  - Expected answer: `Because it supplies the filter through which a slight advantage becomes a difference in survival. If every individual born survived and reproduced, variation and heredity alone would produce no sorting; overproduction guarantees that some must fail, so any advantage, however slight, improves the chance of surviving and procreating.`
  - Best window recall against lesson: 0.48

- **module 1 / lesson 2 / item 5** (Can Selection Apply in Nature?)
  - Q: What work does Darwin's claim that the mutual relations of organic beings are 'infinitely complex and close-fitting' do in his argument?
  - Expected answer: `It explains why there are enormously many ways a variation could turn out to be useful, widening the criterion beyond usefulness to man`
  - Best window recall against lesson: 0.42

- **module 1 / lesson 3 / item 4** (Reading the Chapter Summary Heading)
  - Q: Why does Darwin include 'Slow action' as a separate item in his chapter heading?
  - Expected answer: `To establish the tempo of the mechanism and defend it against the objection that transformation is never observed`
  - Best window recall against lesson: 0.44

- **module 1 / lesson 3 / item 5** (Reading the Chapter Summary Heading)
  - Q: The heading says 'Extinction caused by Natural Selection.' Why is the word 'caused' significant, and which organisms does Darwin expect to be displaced most severely?
  - Expected answer: `'Caused' means extinction is not merely something selection tolerates or that happens for unrelated reasons — it is a direct product of the mechanism itself. Improved forms outcompete and displace less-improved ones, and competition is fiercest between the closest relatives, so an organism's nearest kin are the most likely to be driven extinct. This is what leaves gaps between groups in the resulting classification.`
  - Best window recall against lesson: 0.49

- **module 2 / lesson 1 / item 1** (Variation Under Domestication and in Nature)
  - Q: When Darwin writes that domestic productions vary in an endless number of strange peculiarities "and, in a lesser degree, those under nature," what is the significance of the qualifying clause for his argument?
  - Expected answer: `It admits domesticated forms are more variable while insisting the difference is one of degree, so wild variation still supplies material for selection`
  - Best window recall against lesson: 0.47

- **module 2 / lesson 1 / item 4** (Variation Under Domestication and in Nature)
  - Q: According to Darwin, what happens to variations that are neither useful nor injurious?
  - Expected answer: `They are unaffected by natural selection and remain a fluctuating element, as perhaps in polymorphic species`
  - Best window recall against lesson: 0.44

- **module 2 / lesson 2 / item 1** (The Strength of Heredity)
  - Q: If variation existed but were not inherited at all, what would happen to Darwin's mechanism?
  - Expected answer: `Selection would still operate, but any advantage would die with the individual and no cumulative change would occur`
  - Best window recall against lesson: 0.44

- **module 2 / lesson 2 / item 2** (The Strength of Heredity)
  - Q: Why does the smallness of the advantages Darwin invokes ('any advantage, however slight') make the *strength* of heredity especially important?
  - Expected answer: `Because tiny increments only accumulate into significant change if they are transmitted faithfully across thousands of generations; weak or unreliable inheritance would let noise wash out a slight advantage before it could add up.`
  - Best window recall against lesson: 0.48

- **module 2 / lesson 3 / item 6** (Complex and Close-Fitting Relations)
  - Q: In the flowering-date example, an earlier-flowering variant gains better pollination and escapes a seed weevil and late drought, but risks April frost. What does this example primarily illustrate?
  - Expected answer: `That complexity guarantees a variation will be relevant — it will have consequences to be weighed — even if the net effect is uncertain`
  - Best window recall against lesson: 0.40

- **module 3 / lesson 1 / item 3** (Useful Variations in the Battle of Life)
  - Q: What role does the parenthetical reminder 'remembering that many more individuals are born than can possibly survive' play in Darwin's inference?
  - Expected answer: `It guarantees that most individuals must die anyway, so any slight advantage biases who survives to reproduce`
  - Best window recall against lesson: 0.44

- **module 3 / lesson 1 / item 4** (Useful Variations in the Battle of Life)
  - Q: Darwin's definition of natural selection has two halves. State both, and explain why including the second half matters.
  - Expected answer: `Natural selection is 'the preservation of favourable variations and the rejection of injurious variations'. Including the rejection half matters because selection is not only a creative accumulator: it also acts as a filter that rigidly destroys any variation 'in the least degree injurious'. Without this, harmful variations would accumulate alongside useful ones and no directional improvement would result.`
  - Best window recall against lesson: 0.43

- **module 3 / lesson 1 / item 6** (Useful Variations in the Battle of Life)
  - Q: Darwin says useful variations should 'sometimes' occur over 'thousands of generations'. Why is this modest phrasing a strength rather than a weakness of his argument?
  - Expected answer: `It asks the reader to concede very little. Darwin does not need useful variations to be common or predictable; he needs only that they arise occasionally. Given the enormous spans of time available and the fact that heredity preserves what appears, even rare useful variations can accumulate. Overclaiming frequency would expose the argument to easy refutation, whereas the modest claim is nearly impossible to deny.`
  - Best window recall against lesson: 0.27

- **module 3 / lesson 2 / item 1** (Slight Advantage and the Chance of Survival)
  - Q: Darwin places the phrase 'many more individuals are born than can possibly survive' in a parenthesis. Why is this premise essential rather than incidental to his conclusion?
  - Expected answer: `Without a filter removing most individuals before reproduction, a slight advantage would confer no differential success and variation would remain undirected`
  - Best window recall against lesson: 0.31

- **module 3 / lesson 2 / item 2** (Slight Advantage and the Chance of Survival)
  - Q: Darwin says favourable variations give an individual 'the best chance' of surviving, but that injurious variations 'would be rigidly destroyed.' Explain the significance of this difference in wording.
  - Expected answer: `The favourable case is stated probabilistically: an advantaged individual is not guaranteed to survive, only more likely to, so selection works as a statistical bias across many individuals and generations. The injurious case is stated absolutely because in a world where most individuals die before breeding, a disadvantage is a near-certain route to elimination over the long run. The asymmetry shows that selection is a two-sided filter and that elimination is the surer and swifter half of it.`
  - Best window recall against lesson: 0.46

- **module 3 / lesson 2 / item 6** (Slight Advantage and the Chance of Survival)
  - Q: A critic objects: 'I have watched a population of beetles for ten years and seen no evolutionary change; therefore natural selection does not operate.' Using the lesson, give Darwin's likely reply.
  - Expected answer: `Darwin would accept the observation and deny the inference. Because the advantages selection acts on may be extremely slight, their effects are invisible over ten years and only become substantial across thousands of generations. The theory positively predicts that change will be too slow to observe casually, so failure to see change in a decade is exactly what one should expect, not evidence against the mechanism.`
  - Best window recall against lesson: 0.36

- **module 3 / lesson 3 / item 4** (Preservation, Rejection, and the Naming of a Principle)
  - Q: The lesson notes a 'stylistic tell' in Darwin's paragraph: an asymmetry between how he describes the fate of favourable variations and the fate of injurious ones. Describe it.
  - Expected answer: `For favourable variations Darwin hedges probabilistically — advantaged individuals have 'the best chance of surviving' — whereas for injurious ones he speaks in absolutes: they 'would be rigidly destroyed.' The same statistical process is described cautiously in one clause and deterministically in the other.`
  - Best window recall against lesson: 0.38

- **module 3 / lesson 3 / item 5** (Preservation, Rejection, and the Naming of a Principle)
  - Q: Why did Darwin choose the word 'selection', and what is the chief drawback of that choice?
  - Expected answer: `He borrowed it from breeders' artificial selection, which made the process concrete and familiar; the drawback is that it suggests a choosing agent with foresight`
  - Best window recall against lesson: 0.38

- **module 3 / lesson 4 / item 3** (The Neutral Case and Polymorphic Species)
  - Q: Why does explicitly acknowledging a neutral category strengthen rather than weaken Darwin's theory?
  - Expected answer: `It marks a boundary where the mechanism does not apply, so the theory does not explain everything and can therefore be tested`
  - Best window recall against lesson: 0.44

### Concept coverage across the source

- 18/48 concepts anchored to a source chunk (30 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [18]
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
- Lessons routed per segment: [10]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 2,498 | 19 | 19 | 100.0% | 1.000 |
