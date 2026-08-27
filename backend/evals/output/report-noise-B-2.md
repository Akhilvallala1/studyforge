# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 9 |
| Quiz items | 52 |
| Structure problems | 1 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.0962 |
| Grounded, extractive items only | 0.119 |
| Ungrounded items, all | 39 |
| Ungrounded extractive items | 29 |
| Hallucination candidates | 27 |
| Mean grounding recall | 0.3238 |
| Answerable from lesson | 0.1346 |
| Unanswerable items | 11 |
| Giveaway MCQs | 0 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 1.0743 |
| Wall clock s | 570.37 |

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
| lesson | 9 | 12,704 | 38,786 | $1.0332 | 61.4 | 88.5 |
| outline | 1 | 984 | 1,449 | $0.0411 | 17.7 | 17.7 |

### Structure

- 3 modules, 9 lessons, 52 quiz items
- Quiz items per lesson: [6, 5, 6, 6, 6, 6, 5, 6, 6]
- Concepts per lesson: [4, 5, 5, 5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 6963, min 5610
- Item kinds: {'mcq': 36, 'short': 16}
- Problems: {'duplicate_question': 1}

  - `duplicate_question` at module 1 / lesson 3 / item 4: also at module 1 / lesson 1 / item 4

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 5/52 answers supported (exact or strong) = 9.6%
- Tiers: {'exact': 1, 'strong': 4, 'partial': 8, 'unsupported': 39}
- Mean best-window recall: 0.324
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 42, 'odd_one_out': 1, 'restatement': 9, 'trivial': 0}
- Extractive items supported: 5/42 = 11.9% (mean window recall 0.355)
- Odd-one-out items: mean share of their distractors found in the source = 100.0%
- Restatement items: mean share of answer words absent from the source = 68.3%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 27

  - **module 1 / lesson 1 / item 2** (extractive) novel 86%: Without it, an advantageous peculiarity would perish with its owner and nothing could accumulate over generations
  - **module 1 / lesson 1 / item 5** (extractive) novel 82%: It establishes from observed breeding practice that useful variations do arise, making variations useful to the organism itself no improbability
  - **module 1 / lesson 1 / item 6** (restatement) novel 78%: Each individual premise is modest and was largely already accepted by naturalists of the day: that organisms vary, that offspring resemble parents, that far mor
  - **module 1 / lesson 2 / item 2** (extractive) novel 80%: That no part of the organism, internal or external, is exempt from variation, though the change is limited in degree
  - **module 1 / lesson 3 / item 2** (extractive) novel 83%: That the relations are snug enough that even a slight difference in an organism can matter, rather than rattling around without consequence
  - **module 2 / lesson 1 / item 1** (extractive) novel 70%: Because scarcity of surviving places is what converts a small edge into a difference in who actually reproduces
  - **module 2 / lesson 1 / item 6** (extractive) novel 75%: Because tight mutual dependence creates countless narrow margins on which even a small difference could tell
  - **module 2 / lesson 2 / item 3** (extractive) novel 91%: It signals a tentative illustration rather than a demonstrated case, since proving a character has no effect is very hard
  - **module 2 / lesson 2 / item 5** (restatement) novel 72%: Because several forms can be maintained within a species for other reasons as well; persistence is consistent with neutrality but does not by itself demonstrate
  - **module 2 / lesson 2 / item 6** (extractive) novel 67%: It undercuts the caricature, since Darwin allows that some characters may make no difference at all to survival
  - **module 2 / lesson 3 / item 2** (extractive) novel 67%: Nature can act on any difference that affects survival at all, including ones a human eye would never notice or value, and tiny advantages compound over vast nu
  - **module 2 / lesson 3 / item 4** (odd_one_out) novel 71%: That variations arise in the direction the organism's needs require
  - **module 2 / lesson 3 / item 5** (extractive) novel 83%: It supplies a familiar proof that selecting among slight heritable differences can reshape a lineage, which he then extends to nature
  - **module 2 / lesson 3 / item 6** (restatement) novel 77%: Every stage of life — egg, larva, seedling, adult — is exposed to the struggle for existence, and both sexes are, so a variation useful at any age or in either 
  - **module 3 / lesson 1 / item 2** (extractive) novel 89%: It depends on competition for mates, and the loser's penalty is few or no offspring rather than death
  - **module 3 / lesson 1 / item 3** (restatement) novel 76%: Crossing is favourable because it keeps a species uniform, gives crossed offspring vigour, and spreads a new advantageous variation through a population rather 
  - **module 3 / lesson 1 / item 5** (extractive) novel 91%: Hermaphrodites, such as flowers with both stamens and pistils; he argues an occasional cross with a distinct individual is nearly universal
  - **module 3 / lesson 2 / item 1** (extractive) novel 90%: The peculiarity is blended back towards the population average, so the population stays uniform and divergence is retarded
  - **module 3 / lesson 2 / item 3** (extractive) novel 67%: Advantage: isolation checks intercrossing with the unmodified stock, keeps conditions uniform so selection acts in one direction, and excludes better-adapted im
  - **module 3 / lesson 2 / item 4** (extractive) novel 69%: Selection can act only when places in the polity of nature become better fillable, and such openings depend on slow changes of climate, immigration, and the mod
  - **module 3 / lesson 2 / item 5** (restatement) novel 75%: Because competition is severest between the forms that most resemble each other: they need the same food, shelter and conditions, so the improved variety comes 
  - **module 3 / lesson 2 / item 6** (extractive) novel 87%: Small isolated areas yield peculiar endemic forms, but large areas yield forms hardened by severer competition that tend to be dominant and to spread widely
  - **module 3 / lesson 3 / item 1** (extractive) novel 75%: Because competition is sharpest between the most similar forms, so the most divergent descendants escape it and can occupy additional places
  - **module 3 / lesson 3 / item 3** (extractive) novel 86%: A large proportion of naturalised forms belong to genera with no native representatives, since unlike forms meet less competition from residents
  - **module 3 / lesson 3 / item 4** (restatement) novel 76%: Because the forms exterminated first are the ones most like the improved descendants — the parent species and the intermediate varieties — extinction is what re
  - **module 3 / lesson 3 / item 5** (extractive) novel 93%: Because branching descent plus the loss of intermediate forms leaves clusters at several nested levels, so classification records genealogy
  - **module 3 / lesson 3 / item 6** (extractive) novel 90%: The green budding twigs are living species; the dead and broken branches buried in the crust of the earth are extinct groups — orders and families known only as

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 2** (Darwin's Opening Question)
  - Q: According to the lesson, what role does the premise about heredity play in Darwin's chain of reasoning?
  - Expected answer: `Without it, an advantageous peculiarity would perish with its owner and nothing could accumulate over generations`
  - Best window recall 0.14, global token recall 0.14
  - Closest source text: `be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations`

- **module 1 / lesson 1 / item 3** (Darwin's Opening Question)
  - Q: In his own words, how does Darwin define natural selection? Give both halves of the definition.
  - Expected answer: `The preservation of favourable variations and the rejection (rigid destruction) of injurious variations. The definition is two-sided: selection both saves the beneficial and destroys the harmful.`
  - Best window recall 0.40, global token recall 0.40
  - Closest source text: `than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favoura`

- **module 1 / lesson 1 / item 5** (Darwin's Opening Question)
  - Q: Why does Darwin appeal to the fact that variations useful to man have 'undoubtedly occurred'?
  - Expected answer: `It establishes from observed breeding practice that useful variations do arise, making variations useful to the organism itself no improbability`
  - Best window recall 0.18, global token recall 0.18
  - Closest source text: `in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful`

- **module 1 / lesson 2 / item 1** (Variation and the Strength of Heredity)
  - Q: Why does Darwin's concession that species under nature vary only 'in a lesser degree' not defeat his argument?
  - Expected answer: `Because selection requires only some variation together with a great span of generations and a surplus of individuals born`
  - Best window recall 0.36, global token recall 0.55
  - Closest source text: `undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born`

- **module 1 / lesson 2 / item 2** (Variation and the Strength of Heredity)
  - Q: What does Darwin mean when he says that under domestication 'the whole organisation becomes in some degree plastic'?
  - Expected answer: `That no part of the organism, internal or external, is exempt from variation, though the change is limited in degree`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree`

- **module 1 / lesson 2 / item 5** (Variation and the Strength of Heredity)
  - Q: Darwin argues that since variations useful to man have undoubtedly occurred, variations useful to the organism itself should also occur. What makes this inference persuasive?
  - Expected answer: `Usefulness to man is an arbitrary and narrow criterion, so variation that satisfies it should also, over thousands of generations, satisfy the organism's own needs`
  - Best window recall 0.23, global token recall 0.38
  - Closest source text: `each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of gen`

- **module 1 / lesson 3 / item 1** (Complex and Close-Fitting Relations)
  - Q: In Darwin's argument, what work does the premise about 'infinitely complex and close-fitting' relations do?
  - Expected answer: `It makes it plausible that there are many respects in which a variation could turn out useful to a being, so useful variations should sometimes arise`
  - Best window recall 0.40, global token recall 0.50
  - Closest source text: `undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many`

- **module 1 / lesson 3 / item 2** (Complex and Close-Fitting Relations)
  - Q: According to the lesson, what does 'close-fitting' add to 'complex' in Darwin's phrase?
  - Expected answer: `That the relations are snug enough that even a slight difference in an organism can matter, rather than rattling around without consequence`
  - Best window recall 0.08, global token recall 0.17
  - Closest source text: `and in a lesser degree those under nature vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations`

- **module 2 / lesson 1 / item 1** (Preservation and Rejection)
  - Q: Why does Darwin insert the reminder that 'many more individuals are born than can possibly survive' at exactly the point where he claims slight advantages matter?
  - Expected answer: `Because scarcity of surviving places is what converts a small edge into a difference in who actually reproduces`
  - Best window recall 0.10, global token recall 0.20
  - Closest source text: `of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence of character related to the diversity of inhabitants of any small`

- **module 2 / lesson 1 / item 5** (Preservation and Rejection)
  - Q: In Darwin's chain of reasoning, what work is done by the premise that heredity is strong?
  - Expected answer: `Without inheritance, an advantageous variation would die with the individual that happened to have it, so differential survival would leave no lasting mark. Heredity is what allows an advantage to be passed on — Darwin speaks of surviving *and of procreating their kind* — so that selection accumulates across generations.`
  - Best window recall 0.29, global token recall 0.33
  - Closest source text: `way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would ha`

- **module 2 / lesson 1 / item 6** (Preservation and Rejection)
  - Q: Which statement best captures why Darwin's appeal to the 'infinitely complex and close-fitting' relations among organisms supports his argument?
  - Expected answer: `Because tight mutual dependence creates countless narrow margins on which even a small difference could tell`
  - Best window recall 0.08, global token recall 0.17
  - Closest source text: `on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence of character rela`

- **module 2 / lesson 2 / item 3** (Neutral Variation and Polymorphic Species)
  - Q: Why does Darwin's wording — 'as perhaps we see in the species called polymorphic' — matter for how we read his claim?
  - Expected answer: `It signals a tentative illustration rather than a demonstrated case, since proving a character has no effect is very hard`
  - Best window recall 0.09, global token recall 0.09
  - Closest source text: `power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection diverg`

- **module 2 / lesson 2 / item 4** (Neutral Variation and Polymorphic Species)
  - Q: The lesson argues that a trait's neutrality is 'a relation to circumstances, not a fixed label.' What follows from this?
  - Expected answer: `A character that selection currently ignores could become useful or injurious if conditions of life change`
  - Best window recall 0.30, global token recall 0.60
  - Closest source text: `let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful`

- **module 2 / lesson 2 / item 6** (Neutral Variation and Polymorphic Species)
  - Q: How does the third category of variation bear on the caricature that every feature of an organism must be an adaptation?
  - Expected answer: `It undercuts the caricature, since Darwin allows that some characters may make no difference at all to survival`
  - Best window recall 0.22, global token recall 0.22
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 2 / lesson 3 / item 2** (Nature's Selection Compared with Man's)
  - Q: Why does Darwin claim nature has power over 'characters of trifling importance' where a breeder does not?
  - Expected answer: `Nature can act on any difference that affects survival at all, including ones a human eye would never notice or value, and tiny advantages compound over vast numbers and ages`
  - Best window recall 0.11, global token recall 0.17
  - Closest source text: `diversity of inhabitants of any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapte`

- **module 2 / lesson 3 / item 5** (Nature's Selection Compared with Man's)
  - Q: What role does artificial selection play in Darwin's reasoning in Chapter IV?
  - Expected answer: `It supplies a familiar proof that selecting among slight heritable differences can reshape a lineage, which he then extends to nature`
  - Best window recall 0.08, global token recall 0.17
  - Closest source text: `a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature`

- **module 3 / lesson 1 / item 2** (Sexual Selection and Intercrossing)
  - Q: What distinguishes sexual selection from natural selection in the ordinary sense?
  - Expected answer: `It depends on competition for mates, and the loser's penalty is few or no offspring rather than death`
  - Best window recall 0.11, global token recall 0.11
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 3 / lesson 1 / item 4** (Sexual Selection and Intercrossing)
  - Q: Darwin says an advantaged individual has the best chance 'of surviving and of procreating their kind'. Why does the second half of that phrase matter to the theory?
  - Expected answer: `Because a variation is only preserved if it is passed on, so selection is settled in offspring rather than in deaths`
  - Best window recall 0.22, global token recall 0.22
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 3 / lesson 1 / item 5** (Sexual Selection and Intercrossing)
  - Q: Which cases make the claim about 'the generality of intercrosses' worth arguing at length, and what does Darwin conclude about them?
  - Expected answer: `Hermaphrodites, such as flowers with both stamens and pistils; he argues an occasional cross with a distinct individual is nearly universal`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 2 / item 1** (Conditions, Slowness, and Extinction)
  - Q: A favourable variation appears in one individual of a large, freely-interbreeding, wide-ranging population. According to Darwin's reasoning, what is the most likely immediate effect of free intercrossing?
  - Expected answer: `The peculiarity is blended back towards the population average, so the population stays uniform and divergence is retarded`
  - Best window recall 0.10, global token recall 0.10
  - Closest source text: `all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence`

- **module 3 / lesson 2 / item 2** (Conditions, Slowness, and Extinction)
  - Q: Why does Darwin regard a large number of individuals as a highly important element of success for natural selection?
  - Expected answer: `Because the chance that a useful variation turns up in a given period rises with the number of individuals available to vary`
  - Best window recall 0.25, global token recall 0.50
  - Closest source text: `do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation`

- **module 3 / lesson 2 / item 3** (Conditions, Slowness, and Extinction)
  - Q: State one advantage and one disadvantage of isolation for the production of new species, as Darwin presents them.
  - Expected answer: `Advantage: isolation checks intercrossing with the unmodified stock, keeps conditions uniform so selection acts in one direction, and excludes better-adapted immigrants, leaving places open for the old inhabitants to fill. Disadvantage: a small isolated area holds few individuals, so favourable variations appear rarely and modification is correspondingly slow.`
  - Best window recall 0.25, global token recall 0.33
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 3 / lesson 2 / item 4** (Conditions, Slowness, and Extinction)
  - Q: Darwin insists that natural selection acts very slowly. Which reason does the lesson give for this slowness?
  - Expected answer: `Selection can act only when places in the polity of nature become better fillable, and such openings depend on slow changes of climate, immigration, and the modification of other inhabitants`
  - Best window recall 0.25, global token recall 0.31
  - Closest source text: `number of individuals slow action extinction caused by natural selection divergence of character related to the diversity of inhabitants of any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains`

- **module 3 / lesson 2 / item 6** (Conditions, Slowness, and Extinction)
  - Q: On Darwin's account, how do the products of small isolated areas compare with those of large continental areas?
  - Expected answer: `Small isolated areas yield peculiar endemic forms, but large areas yield forms hardened by severer competition that tend to be dominant and to spread widely`
  - Best window recall 0.07, global token recall 0.07
  - Closest source text: `power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow actio`

- **module 3 / lesson 3 / item 1** (Divergence of Character and the Grouping of Organic Beings)
  - Q: According to Darwin's principle of divergence, why do the descendants of one species tend to become unlike one another rather than all improving in the same direction?
  - Expected answer: `Because competition is sharpest between the most similar forms, so the most divergent descendants escape it and can occupy additional places`
  - Best window recall 0.08, global token recall 0.17
  - Closest source text: `excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses `

- **module 3 / lesson 3 / item 2** (Divergence of Character and the Grouping of Organic Beings)
  - Q: What did Darwin's count of plants on a plot of turf three feet by four contribute to the argument?
  - Expected answer: `Twenty species spread over eighteen genera and eight orders showed that a tiny area supports beings of very unlike kinds, as the divergence principle predicts`
  - Best window recall 0.24, global token recall 0.29
  - Closest source text: `of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence of character related to the diversity of inhabitants of any small `

- **module 3 / lesson 3 / item 3** (Divergence of Character and the Grouping of Organic Beings)
  - Q: How does the record of naturalised species support divergence of character?
  - Expected answer: `A large proportion of naturalised forms belong to genera with no native representatives, since unlike forms meet less competition from residents`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 3 / item 5** (Divergence of Character and the Grouping of Organic Beings)
  - Q: On Darwin's view, why does life fall into groups subordinate to groups rather than into a single unbroken series?
  - Expected answer: `Because branching descent plus the loss of intermediate forms leaves clusters at several nested levels, so classification records genealogy`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 3 / item 6** (Divergence of Character and the Grouping of Organic Beings)
  - Q: In the Tree of Life image, what do the green budding twigs and the buried dead branches respectively represent?
  - Expected answer: `The green budding twigs are living species; the dead and broken branches buried in the crust of the earth are extinct groups — orders and families known only as fossils — while the branches below the twigs are the extinct species from which living ones descended.`
  - Best window recall 0.05, global token recall 0.05
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

### Answerability (answer vs its own lesson content)

- 7/52 answerable from the lesson alone = 13.5%
- Tiers: {'exact': 0, 'strong': 7, 'partial': 34, 'unsupported': 11}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 0

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 5** (Darwin's Opening Question)
  - Q: Why does Darwin appeal to the fact that variations useful to man have 'undoubtedly occurred'?
  - Expected answer: `It establishes from observed breeding practice that useful variations do arise, making variations useful to the organism itself no improbability`
  - Best window recall against lesson: 0.36

- **module 1 / lesson 2 / item 3** (Variation and the Strength of Heredity)
  - Q: Why is the strength of the hereditary tendency an indispensable premise, rather than a mere supporting detail?
  - Expected answer: `Because natural selection works by accumulation: without strong heredity a favourable variation would not be passed on, and each generation's preserved differences would be lost instead of building up over time.`
  - Best window recall against lesson: 0.39

- **module 2 / lesson 1 / item 1** (Preservation and Rejection)
  - Q: Why does Darwin insert the reminder that 'many more individuals are born than can possibly survive' at exactly the point where he claims slight advantages matter?
  - Expected answer: `Because scarcity of surviving places is what converts a small edge into a difference in who actually reproduces`
  - Best window recall against lesson: 0.30

- **module 2 / lesson 1 / item 4** (Preservation and Rejection)
  - Q: State the two halves of Darwin's formal definition of natural selection, in your own words.
  - Expected answer: `Natural selection is the preservation of variations that are favourable to their possessor together with the rejection (destruction) of variations that are injurious. Both halves belong to the definition; it is not merely the survival of the better-endowed but also the rigid elimination of the harmed.`
  - Best window recall against lesson: 0.40

- **module 2 / lesson 2 / item 3** (Neutral Variation and Polymorphic Species)
  - Q: Why does Darwin's wording — 'as perhaps we see in the species called polymorphic' — matter for how we read his claim?
  - Expected answer: `It signals a tentative illustration rather than a demonstrated case, since proving a character has no effect is very hard`
  - Best window recall against lesson: 0.45

- **module 2 / lesson 2 / item 5** (Neutral Variation and Polymorphic Species)
  - Q: In the snail example, why does the persistence of three, four, and five-banded shells count only as weak evidence for neutrality?
  - Expected answer: `Because several forms can be maintained within a species for other reasons as well; persistence is consistent with neutrality but does not by itself demonstrate that the character makes no difference to survival or reproduction.`
  - Best window recall against lesson: 0.44

- **module 2 / lesson 2 / item 6** (Neutral Variation and Polymorphic Species)
  - Q: How does the third category of variation bear on the caricature that every feature of an organism must be an adaptation?
  - Expected answer: `It undercuts the caricature, since Darwin allows that some characters may make no difference at all to survival`
  - Best window recall against lesson: 0.33

- **module 2 / lesson 3 / item 2** (Nature's Selection Compared with Man's)
  - Q: Why does Darwin claim nature has power over 'characters of trifling importance' where a breeder does not?
  - Expected answer: `Nature can act on any difference that affects survival at all, including ones a human eye would never notice or value, and tiny advantages compound over vast numbers and ages`
  - Best window recall against lesson: 0.33

- **module 2 / lesson 3 / item 4** (Nature's Selection Compared with Man's)
  - Q: Which of these is NOT one of the premises Darwin asks the reader to bear in mind before concluding that natural selection must act?
  - Expected answer: `That variations arise in the direction the organism's needs require`
  - Best window recall against lesson: 0.29

- **module 3 / lesson 3 / item 2** (Divergence of Character and the Grouping of Organic Beings)
  - Q: What did Darwin's count of plants on a plot of turf three feet by four contribute to the argument?
  - Expected answer: `Twenty species spread over eighteen genera and eight orders showed that a tiny area supports beings of very unlike kinds, as the divergence principle predicts`
  - Best window recall against lesson: 0.47

- **module 3 / lesson 3 / item 5** (Divergence of Character and the Grouping of Organic Beings)
  - Q: On Darwin's view, why does life fall into groups subordinate to groups rather than into a single unbroken series?
  - Expected answer: `Because branching descent plus the loss of intermediate forms leaves clusters at several nested levels, so classification records genealogy`
  - Best window recall against lesson: 0.33

### Concept coverage across the source

- 17/44 concepts anchored to a source chunk (27 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [17]
- Lessons per chunk: [2]
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
