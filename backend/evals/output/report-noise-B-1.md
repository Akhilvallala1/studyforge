# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 9 |
| Quiz items | 52 |
| Structure problems | 7 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.0962 |
| Grounded, extractive items only | 0.1282 |
| Ungrounded items, all | 39 |
| Ungrounded extractive items | 26 |
| Hallucination candidates | 25 |
| Mean grounding recall | 0.3328 |
| Answerable from lesson | 0.1923 |
| Unanswerable items | 10 |
| Giveaway MCQs | 1 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 1.078 |
| Wall clock s | 571.77 |

## prose-short

Source: text `darwin-origin-short`, 2,498 chars, 1 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 9 | 9 | 1 | 0 | 9 | 9 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 9 | 12,767 | 38,827 | $1.0345 | 61.3 | 78.5 |
| outline | 1 | 984 | 1,544 | $0.0435 | 19.7 | 19.7 |

### Structure

- 3 modules, 9 lessons, 52 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 5, 6, 6, 5]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 7145, min 5262
- Item kinds: {'mcq': 36, 'short': 16}
- Problems: {'duplicate_question': 1, 'empty_concept': 6}

  - `duplicate_question` at module 1 / lesson 3 / item 4: also at module 1 / lesson 2 / item 4
  - `empty_concept` at module 2 / lesson 2 / item 1: Darwin's definition names two operations. What are they, and on what does each operate?
  - `empty_concept` at module 2 / lesson 2 / item 2: According to the passage, what happens to a variation that is neither useful nor injurious?
  - `empty_concept` at module 2 / lesson 2 / item 3: Why does the lesson say the definition sentence is 'parasitic' on the sentences before it?
  - `empty_concept` at module 2 / lesson 2 / item 4: Which premise does Darwin explicitly recall in parenthesis just before asserting that advantaged individuals have the best chance of surviving?
  - `empty_concept` at module 2 / lesson 2 / item 5: The lesson calls the restatement 'Natural selection preserves the species best suited to its conditions' defective. Which flaw does it illustrate?
  - `empty_concept` at module 2 / lesson 2 / item 6: The lesson distinguishes the empirical part of the sentence from the terminological part. Which phrase is purely terminological, and why can it not be false?

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 5/52 answers supported (exact or strong) = 9.6%
- Tiers: {'exact': 1, 'strong': 4, 'partial': 8, 'unsupported': 39}
- Mean best-window recall: 0.333
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 39, 'odd_one_out': 1, 'restatement': 12, 'trivial': 0}
- Extractive items supported: 5/39 = 12.8% (mean window recall 0.376)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 65.0%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 25

  - **module 1 / lesson 1 / item 2** (extractive) novel 80%: It invokes the already-established case of breeders' selection so that the disputed case in nature can be argued by analogy
  - **module 1 / lesson 2 / item 2** (restatement) novel 67%: Because without strong inheritance a favourable peculiarity would die with the individual that had it. Heredity is what carries an advantage into the offspring 
  - **module 1 / lesson 2 / item 3** (extractive) novel 100%: That the entire constitution of the organism proves somewhat mouldable, not just a few parts
  - **module 1 / lesson 2 / item 6** (restatement) novel 61%: Instead of defining natural selection first and then defending it, he asks the reader to 'bear in mind' facts already accepted from domestic breeding — abundant
  - **module 1 / lesson 3 / item 2** (extractive) novel 69%: Because human usefulness is a narrow, arbitrary standard, so if that filter catches variations, nature's far wider set of criteria should catch them too
  - **module 1 / lesson 3 / item 3** (restatement) novel 69%: Because deep time converts rarity into abundance: an event rare in any one generation happens many times across thousands of generations. Darwin needs only an o
  - **module 1 / lesson 3 / item 6** (extractive) novel 70%: It supplies the condition under which a slight advantage is actually cashed out, since without superabundant birth an advantage would be idle
  - **module 2 / lesson 1 / item 1** (extractive) novel 67%: Because overproduction guarantees that a majority must die, which is what converts a tiny difference between individuals into a difference in who leaves descend
  - **module 2 / lesson 1 / item 5** (extractive) novel 71%: He treats the elimination of harmful variation as the surer, more immediate half of the process, while preservation of the useful works more slowly by accumulat
  - **module 2 / lesson 2 / item 3** (extractive) novel 67%: It opens with 'This', which points back to the preservation and destruction just described
  - **module 2 / lesson 2 / item 6** (restatement) novel 73%: 'I call Natural Selection' — it is a stipulation fixing a name for the process already described, so it can only be unhelpful, not false. The empirical work is 
  - **module 2 / lesson 3 / item 2** (restatement) novel 76%: "A fluctuating element" — the character is neither driven toward a fixed form nor weeded out, so it remains unsettled and variable in the population, wobbling w
  - **module 2 / lesson 3 / item 4** (restatement) novel 64%: Because we cannot establish neutrality by inspection: all we observe is that we cannot detect a use for the character, and given how complex and close-fitting t
  - **module 2 / lesson 3 / item 5** (extractive) novel 80%: Its jurisdiction is confined to differences that bear on survival and reproduction, not to every difference between organisms
  - **module 3 / lesson 1 / item 2** (extractive) novel 70%: Because breeders' power is a case his readers already accept, which he can then argue nature exceeds
  - **module 3 / lesson 1 / item 3** (extractive) novel 90%: It turns on success in obtaining mates rather than on survival, and the loser is not killed but leaves few offspring
  - **module 3 / lesson 1 / item 5** (restatement) novel 65%: An intercross is a mating between two distinct individuals of the same species, as opposed to self-fertilisation or habitual close inbreeding. It matters becaus
  - **module 3 / lesson 1 / item 6** (extractive) novel 71%: An advantage appearing in a seed, larva or nestling is preserved just as an adult advantage is, since dying young removes an individual from the species' future
  - **module 3 / lesson 2 / item 1** (extractive) novel 75%: Because crossing with unmodified individuals tends to blend the new character back towards the population average
  - **module 3 / lesson 2 / item 4** (extractive) novel 90%: Lapse of time is not itself a cause of change; it matters only by allowing variations to arise and be accumulated
  - **module 3 / lesson 2 / item 6** (restatement) novel 66%: Any of: it can act only when places in the economy of nature could be better filled, and such openings depend on slow changes in physical conditions, on immigra
  - **module 3 / lesson 3 / item 1** (extractive) novel 75%: Because competition presses hardest between the most similar forms, so descendants that differ most escape rivalry and seize unoccupied places in the economy of
  - **module 3 / lesson 3 / item 2** (extractive) novel 100%: Successful newcomers tend to belong to genera not already represented among the natives, meeting no entrenched rival for the same place
  - **module 3 / lesson 3 / item 3** (restatement) novel 77%: Divergence alone would leave a continuous graded series of forms; extinction removes the connecting links so that the survivors are separated by gaps and appear
  - **module 3 / lesson 3 / item 4** (extractive) novel 94%: Repeated branching at every scale, with most branches dying off, leaves surviving twigs clustered on branches and branches on limbs — genera within families wit

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 1** (The Question Darwin Asks)
  - Q: How does Darwin open Chapter IV?
  - Expected answer: `By posing questions about how the struggle for existence acts on variation, and stating that he thinks selection can act most effectually`
  - Best window recall 0.45, global token recall 0.55
  - Closest source text: `to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 1 / lesson 1 / item 2** (The Question Darwin Asks)
  - Q: What is the rhetorical purpose of Darwin's phrase 'so potent in the hands of man'?
  - Expected answer: `It invokes the already-established case of breeders' selection so that the disputed case in nature can be argued by analogy`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature`

- **module 1 / lesson 1 / item 6** (The Question Darwin Asks)
  - Q: Why does the 'infinitely complex and close-fitting' relations premise matter to Darwin's argument?
  - Expected answer: `Because tight interlocking with other beings and conditions means even a very slight variation can affect an individual's chances`
  - Best window recall 0.15, global token recall 0.38
  - Closest source text: `diversity of inhabitants of any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapte`

- **module 1 / lesson 2 / item 3** (Variation and the Strength of Heredity)
  - Q: What does Darwin mean by saying that under domestication 'the whole organisation becomes in some degree plastic'?
  - Expected answer: `That the entire constitution of the organism proves somewhat mouldable, not just a few parts`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 1 / lesson 2 / item 5** (Variation and the Strength of Heredity)
  - Q: Darwin concedes that wild organisms vary less than domestic ones. What does he offer that keeps this concession from undermining natural selection?
  - Expected answer: `The immense span of time — thousands of generations — over which nature works`
  - Best window recall 0.29, global token recall 0.43
  - Closest source text: `be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations`

- **module 1 / lesson 3 / item 1** (Complex Relations and the Battle of Life)
  - Q: In Darwin's argument, what distinct work is done by the word 'close-fitting' as opposed to 'complex' in describing organic relations?
  - Expected answer: `'Close-fitting' indicates that tolerances are tight, so even slight differences have consequences, while 'complex' indicates that there are many channels through which a variation could matter`
  - Best window recall 0.25, global token recall 0.44
  - Closest source text: `complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and`

- **module 1 / lesson 3 / item 2** (Complex Relations and the Battle of Life)
  - Q: Why does Darwin use variations useful to man as the starting point for his inference about variations useful in nature?
  - Expected answer: `Because human usefulness is a narrow, arbitrary standard, so if that filter catches variations, nature's far wider set of criteria should catch them too`
  - Best window recall 0.12, global token recall 0.19
  - Closest source text: `nature vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physica`

- **module 1 / lesson 3 / item 6** (Complex Relations and the Battle of Life)
  - Q: Darwin's parenthesis 'remembering that many more individuals are born than can possibly survive' appears at a precise point in the argument. What role does it play there?
  - Expected answer: `It supplies the condition under which a slight advantage is actually cashed out, since without superabundant birth an advantage would be idle`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight`

- **module 2 / lesson 1 / item 1** (Slight Advantages and Survival)
  - Q: Why does Darwin insert the parenthesis "remembering that many more individuals are born than can possibly survive" at exactly this point in his argument?
  - Expected answer: `Because overproduction guarantees that a majority must die, which is what converts a tiny difference between individuals into a difference in who leaves descendants`
  - Best window recall 0.17, global token recall 0.25
  - Closest source text: `charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between `

- **module 2 / lesson 1 / item 5** (Slight Advantages and Survival)
  - Q: Darwin writes "can we doubt" about favourable variations but "we may feel sure" about injurious ones being rigidly destroyed. What does this difference in wording indicate?
  - Expected answer: `He treats the elimination of harmful variation as the surer, more immediate half of the process, while preservation of the useful works more slowly by accumulation`
  - Best window recall 0.21, global token recall 0.21
  - Closest source text: `any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious vari`

- **module 2 / lesson 2 / item 3** (The Definition in Darwin's Own Words)
  - Q: Why does the lesson say the definition sentence is 'parasitic' on the sentences before it?
  - Expected answer: `It opens with 'This', which points back to the preservation and destruction just described`
  - Best window recall 0.17, global token recall 0.17
  - Closest source text: `any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation`

- **module 2 / lesson 2 / item 5** (The Definition in Darwin's Own Words)
  - Q: The lesson calls the restatement 'Natural selection preserves the species best suited to its conditions' defective. Which flaw does it illustrate?
  - Expected answer: `It shifts the unit acted on from variations among individuals to whole species`
  - Best window recall 0.25, global token recall 0.50
  - Closest source text: `natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species`

- **module 2 / lesson 3 / item 1** (Neutral Variation and Polymorphic Species)
  - Q: According to Darwin's account, what happens to a variation that is neither useful nor injurious?
  - Expected answer: `Natural selection has no purchase on it, so it is left free to vary without direction`
  - Best window recall 0.43, global token recall 0.57
  - Closest source text: `in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither useful nor injurious would not be affected by natural selection and would be left`

- **module 2 / lesson 3 / item 3** (Neutral Variation and Polymorphic Species)
  - Q: Why does Darwin mention polymorphic species at this point in the argument?
  - Expected answer: `They may be a visible case of characters fluctuating because nothing is pressing on them`
  - Best window recall 0.14, global token recall 0.29
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 2 / lesson 3 / item 5** (Neutral Variation and Polymorphic Species)
  - Q: What does the existence of the neutral category reveal about natural selection as an explanatory mechanism?
  - Expected answer: `Its jurisdiction is confined to differences that bear on survival and reproduction, not to every difference between organisms`
  - Best window recall 0.10, global token recall 0.10
  - Closest source text: `gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between`

- **module 3 / lesson 1 / item 2** (Reach of Selection: Trifling Characters, All Ages, Both Sexes—and Sexual Selection)
  - Q: Why does Darwin frame natural selection by comparing it with man's selection?
  - Expected answer: `Because breeders' power is a case his readers already accept, which he can then argue nature exceeds`
  - Best window recall 0.10, global token recall 0.20
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 3 / lesson 1 / item 3** (Reach of Selection: Trifling Characters, All Ages, Both Sexes—and Sexual Selection)
  - Q: How does sexual selection differ from natural selection as the lesson describes it?
  - Expected answer: `It turns on success in obtaining mates rather than on survival, and the loser is not killed but leaves few offspring`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 1 / item 4** (Reach of Selection: Trifling Characters, All Ages, Both Sexes—and Sexual Selection)
  - Q: State the two sides of Darwin's definition of natural selection.
  - Expected answer: `The preservation of favourable variations and the rejection (rigid destruction) of injurious ones — saving the advantageous and destroying the harmful are equal halves of the process.`
  - Best window recall 0.33, global token recall 0.33
  - Closest source text: `remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would b`

- **module 3 / lesson 1 / item 6** (Reach of Selection: Trifling Characters, All Ages, Both Sexes—and Sexual Selection)
  - Q: Which statement best captures Darwin's claim that selection acts 'at all ages'?
  - Expected answer: `An advantage appearing in a seed, larva or nestling is preserved just as an adult advantage is, since dying young removes an individual from the species' future`
  - Best window recall 0.07, global token recall 0.14
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 3 / lesson 2 / item 1** (Favourable and Unfavourable Circumstances)
  - Q: Why does Darwin regard free intercrossing as generally unfavourable to the fixing of a new local peculiarity?
  - Expected answer: `Because crossing with unmodified individuals tends to blend the new character back towards the population average`
  - Best window recall 0.17, global token recall 0.17
  - Closest source text: `of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused `

- **module 3 / lesson 2 / item 2** (Favourable and Unfavourable Circumstances)
  - Q: According to the lesson, what is the chief disadvantage of a small isolated area for natural selection?
  - Expected answer: `It supports few individuals, so favourable variations arise rarely and competition is less severe`
  - Best window recall 0.22, global token recall 0.33
  - Closest source text: `natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable`

- **module 3 / lesson 2 / item 4** (Favourable and Unfavourable Circumstances)
  - Q: How does the lesson describe Darwin's treatment of time as a factor?
  - Expected answer: `Lapse of time is not itself a cause of change; it matters only by allowing variations to arise and be accumulated`
  - Best window recall 0.10, global token recall 0.10
  - Closest source text: `plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations`

- **module 3 / lesson 2 / item 5** (Favourable and Unfavourable Circumstances)
  - Q: Which forms does the lesson say suffer most from the extinction caused by natural selection?
  - Expected answer: `The parent form, the intermediate varieties, and the most closely allied species`
  - Best window recall 0.14, global token recall 0.29
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 3 / lesson 3 / item 1** (Divergence of Character and the Grouping of Organic Beings)
  - Q: According to the lesson, why does natural selection tend to push the descendants of one species further apart in character?
  - Expected answer: `Because competition presses hardest between the most similar forms, so descendants that differ most escape rivalry and seize unoccupied places in the economy of nature`
  - Best window recall 0.12, global token recall 0.19
  - Closest source text: `both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence of character related`

- **module 3 / lesson 3 / item 2** (Divergence of Character and the Grouping of Organic Beings)
  - Q: What pattern in the naturalisation of introduced species is offered as evidence for divergence of character?
  - Expected answer: `Successful newcomers tend to belong to genera not already represented among the natives, meeting no entrenched rival for the same place`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 3 / item 4** (Divergence of Character and the Grouping of Organic Beings)
  - Q: How does the branching-tree picture account for the fact that living things fall into groups subordinate to groups?
  - Expected answer: `Repeated branching at every scale, with most branches dying off, leaves surviving twigs clustered on branches and branches on limbs — genera within families within orders`
  - Best window recall 0.06, global token recall 0.06
  - Closest source text: `undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individual`

### Answerability (answer vs its own lesson content)

- 10/52 answerable from the lesson alone = 19.2%
- Tiers: {'exact': 1, 'strong': 9, 'partial': 32, 'unsupported': 10}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 1

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 6** (The Question Darwin Asks)
  - Q: Why does the 'infinitely complex and close-fitting' relations premise matter to Darwin's argument?
  - Expected answer: `Because tight interlocking with other beings and conditions means even a very slight variation can affect an individual's chances`
  - Best window recall against lesson: 0.31

- **module 1 / lesson 2 / item 2** (Variation and the Strength of Heredity)
  - Q: Why is the strength of the hereditary tendency an indispensable premise, rather than a mere supporting detail?
  - Expected answer: `Because without strong inheritance a favourable peculiarity would die with the individual that had it. Heredity is what carries an advantage into the offspring and lets slight advantages accumulate across generations; variation alone would produce differences that never persist or add up.`
  - Best window recall against lesson: 0.46

- **module 1 / lesson 2 / item 3** (Variation and the Strength of Heredity)
  - Q: What does Darwin mean by saying that under domestication 'the whole organisation becomes in some degree plastic'?
  - Expected answer: `That the entire constitution of the organism proves somewhat mouldable, not just a few parts`
  - Best window recall against lesson: 0.29

- **module 1 / lesson 2 / item 6** (Variation and the Strength of Heredity)
  - Q: Describe the rhetorical strategy Darwin uses at the start of Chapter IV, and why he uses it.
  - Expected answer: `Instead of defining natural selection first and then defending it, he asks the reader to 'bear in mind' facts already accepted from domestic breeding — abundant strange variation, strong heredity, plasticity of the whole organisation — and adds the complexity of organic relations. He then poses the conclusion as a question, so the reader draws the inference himself. Premises borrowed from familiar barnyard experience are used to license a conclusion about all of nature.`
  - Best window recall against lesson: 0.37

- **module 1 / lesson 3 / item 5** (Complex Relations and the Battle of Life)
  - Q: Which of the following is NOT part of what the 'complex relations' argument claims?
  - Expected answer: `That the complexity of an organism's needs calls forth the variations required to meet them`
  - Best window recall against lesson: 0.33

- **module 2 / lesson 1 / item 6** (Slight Advantages and Survival)
  - Q: Name the two facts about organisms Darwin asks the reader to "bear in mind" before he draws his inference, and explain why the second one is indispensable.
  - Expected answer: `That organisms vary (endlessly under domestication, less so in nature) and that the hereditary tendency is strong. Heredity is indispensable because an advantage that could not be passed to offspring would die with the individual and could never accumulate across generations.`
  - Best window recall against lesson: 0.38

- **module 2 / lesson 2 / item 3** (The Definition in Darwin's Own Words)
  - Q: Why does the lesson say the definition sentence is 'parasitic' on the sentences before it?
  - Expected answer: `It opens with 'This', which points back to the preservation and destruction just described`
  - Best window recall against lesson: 0.33

- **module 2 / lesson 3 / item 1** (Neutral Variation and Polymorphic Species)
  - Q: According to Darwin's account, what happens to a variation that is neither useful nor injurious?
  - Expected answer: `Natural selection has no purchase on it, so it is left free to vary without direction`
  - Best window recall against lesson: 0.43

- **module 3 / lesson 3 / item 1** (Divergence of Character and the Grouping of Organic Beings)
  - Q: According to the lesson, why does natural selection tend to push the descendants of one species further apart in character?
  - Expected answer: `Because competition presses hardest between the most similar forms, so descendants that differ most escape rivalry and seize unoccupied places in the economy of nature`
  - Best window recall against lesson: 0.38

- **module 3 / lesson 3 / item 3** (Divergence of Character and the Grouping of Organic Beings)
  - Q: In two or three sentences, explain the part extinction plays in producing distinct, well-defined groups, and say why intermediate forms are especially vulnerable.
  - Expected answer: `Divergence alone would leave a continuous graded series of forms; extinction removes the connecting links so that the survivors are separated by gaps and appear as distinct groups. Intermediate forms are especially vulnerable because they resemble both diverging extremes and so compete with both, and because they tend to exist in smaller numbers in the intermediate zone, which makes them liable to be exterminated by their own more successful relatives.`
  - Best window recall against lesson: 0.43

### Concept coverage across the source

- 17/45 concepts anchored to a source chunk (28 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [17]
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
- Lessons routed per segment: [9]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 2,498 | 19 | 19 | 100.0% | 1.000 |
