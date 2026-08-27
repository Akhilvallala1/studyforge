# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 9 |
| Quiz items | 54 |
| Structure problems | 1 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.1111 |
| Grounded, extractive items only | 0.15 |
| Ungrounded items, all | 44 |
| Ungrounded extractive items | 30 |
| Hallucination candidates | 40 |
| Mean grounding recall | 0.2912 |
| Answerable from lesson | 0.1852 |
| Unanswerable items | 17 |
| Giveaway MCQs | 0 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 1.1159 |
| Wall clock s | 598.24 |

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
| lesson | 9 | 11,463 | 40,677 | $1.0742 | 64.6 | 80.3 |
| outline | 1 | 984 | 1,470 | $0.0417 | 16.8 | 16.8 |

### Structure

- 3 modules, 9 lessons, 54 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 6, 5, 5]
- Lesson content chars: mean 8138, min 5658
- Item kinds: {'mcq': 33, 'short': 21}
- Problems: {'concept_count_out_of_range': 1}

  - `concept_count_out_of_range` at module 3 / lesson 1: 6 concepts

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 6/54 answers supported (exact or strong) = 11.1%
- Tiers: {'exact': 0, 'strong': 6, 'partial': 4, 'unsupported': 44}
- Mean best-window recall: 0.291
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 40, 'odd_one_out': 0, 'restatement': 14, 'trivial': 0}
- Extractive items supported: 6/40 = 15.0% (mean window recall 0.337)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 72.2%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 40

  - **module 1 / lesson 1 / item 5** (extractive) novel 78%: Nature supplies differential reproduction; the breeder's intention or foresight is unnecessary
  - **module 1 / lesson 1 / item 6** (extractive) novel 70%: Because even minute advantages, accumulated over thousands of generations, suffice to produce change
  - **module 1 / lesson 2 / item 1** (extractive) novel 82%: No part of the organism — skeleton, instinct, developmental timing — is exempt from being altered across generations under selection
  - **module 1 / lesson 2 / item 2** (restatement) novel 63%: It concedes the obvious fact that wild populations look more uniform than domestic breeds, preserving Darwin's credibility, while insisting that 'lesser' is not
  - **module 1 / lesson 2 / item 4** (restatement) novel 74%: No. Selection could eliminate the unfit each generation, but with no hereditary link between parent and offspring the next generation's composition would revert
  - **module 1 / lesson 2 / item 5** (extractive) novel 62%: Because selection can only act on the variation available, so a wide and pervasive supply of variability gives selection many dimensions to work on
  - **module 1 / lesson 2 / item 6** (extractive) novel 62%: The pivot is that variations useful to man 'have undoubtedly occurred' — the everyday, uncontested success of breeders. Given that organisms stand in infinitely
  - **module 1 / lesson 3 / item 1** (extractive) novel 70%: It makes it plausible that some undirected variations will happen to be useful, and that even slight ones will matter
  - **module 1 / lesson 3 / item 2** (extractive) novel 61%: It shows selection is a filter rather than a shaper of every detail: it acts only where a variation touches the organism's relations, so indifferent characters 
  - **module 1 / lesson 3 / item 3** (extractive) novel 62%: Because even rare useful variations become an expected occurrence over enormous numbers of trials, and heredity accumulates them
  - **module 1 / lesson 3 / item 4** (extractive) novel 66%: Darwin agrees that most changes will be harmful and says such variations are "rigidly destroyed." His case does not require useful variations to be common, only
  - **module 1 / lesson 3 / item 6** (restatement) novel 77%: Any answer tracing a chain of dependence is acceptable — e.g. Darwin's chain from cats to field-mice to humble-bees to red clover. A slight variation in a clove
  - **module 2 / lesson 1 / item 1** (extractive) novel 83%: It supplies the overproduction premise that makes even slight differences decisive, since some individuals must die regardless
  - **module 2 / lesson 1 / item 3** (restatement) novel 68%: 'Chance' signals that the claim is statistical, not a guarantee: an advantaged individual can still die by accident, and the bias only shows itself across many 
  - **module 2 / lesson 1 / item 5** (restatement) novel 77%: Artificial selection under domestication is a known, demonstrated case in which variation plus heredity plus a selecting agent reshapes organisms. It establishe
  - **module 2 / lesson 1 / item 6** (extractive) novel 80%: The claim that natural selection requires large, conspicuously beneficial novelties to produce change
  - **module 2 / lesson 2 / item 3** (restatement) novel 68%: Because Darwin's theory requires selection to be sensitive to very small differences. If only large advantages or injuries mattered, evolution would depend on r
  - **module 2 / lesson 2 / item 5** (extractive) novel 86%: Selection is probabilistic and genetic drift can carry mildly harmful variants to high frequency, especially in small populations; a variant may also be harmful
  - **module 2 / lesson 2 / item 6** (extractive) novel 80%: Its relation to the specific environment in which the organism lives
  - **module 2 / lesson 3 / item 2** (extractive) novel 62%: As a possible visible case of variation that selection has left untouched and undefined
  - **module 2 / lesson 3 / item 3** (restatement) novel 73%: Darwin hedges because neutrality is very hard to demonstrate. A trait that looks useless to a human observer may in fact matter to mates, predators, or the phys
  - **module 2 / lesson 3 / item 4** (extractive) novel 100%: The neutral theory of molecular evolution, with change driven by genetic drift
  - **module 2 / lesson 3 / item 5** (restatement) novel 85%: Balancing selection: each form may be actively favoured under some circumstance (different habitats, seasons, frequencies, or predator behaviour), so selection 
  - **module 2 / lesson 3 / item 6** (restatement) novel 67%: Natural selection acts only through differences in survival and reproduction. If a variation makes no such difference, there is nothing for selection to grip, s
  - **module 3 / lesson 1 / item 1** (extractive) novel 67%: The penalty in sexual selection is few or no offspring rather than death, since it turns on competition for mates rather than the struggle for existence
  - **module 3 / lesson 1 / item 2** (extractive) novel 70%: That characters which look trifling to us may in fact decide survival, so apparent uselessness reflects our ignorance
  - **module 3 / lesson 1 / item 3** (extractive) novel 88%: Any two of: nature acts on internal organs and every shade of constitutional difference, not just visible traits man values; nature selects for the good of the 
  - **module 3 / lesson 1 / item 4** (restatement) novel 78%: Because every stage of life is exposed to the struggle for existence: larvae, seedlings and young must survive under their own conditions, so structures adapted
  - **module 3 / lesson 1 / item 5** (extractive) novel 65%: It helps by spreading favourable variations and maintaining vigour, but hinders by blending away individual peculiarities and keeping a population uniform — whi
  - **module 3 / lesson 2 / item 1** (extractive) novel 79%: Because repeated crossing with the unmodified majority blends a new variation back into the common stock, keeping the population uniform
  - **module 3 / lesson 2 / item 2** (extractive) novel 74%: A large area supports far more individuals, so favourable variations arise more often in a given time; and competition there is far more severe, so any form tha
  - **module 3 / lesson 2 / item 4** (extractive) novel 62%: That there are places in the economy of nature which can be better filled by modification of the existing inhabitants
  - **module 3 / lesson 2 / item 5** (restatement) novel 70%: Because competition is most severe between forms that are most alike: closely allied varieties and species share nearly the same structure, habits and requireme
  - **module 3 / lesson 2 / item 6** (extractive) novel 89%: That rarity is the ordinary, expected forerunner of extinction, so extinction needs no mysterious special cause
  - **module 3 / lesson 3 / item 1** (extractive) novel 73%: Because differing most from their kin lets them seize places in the economy of nature where competition is less severe
  - **module 3 / lesson 3 / item 2** (extractive) novel 67%: As evidence that a diversified set of forms can be supported on the same area, so divergence is rewarded in nature
  - **module 3 / lesson 3 / item 3** (restatement) novel 84%: It shows that competition is fiercest between very similar forms: a newcomer closely resembling a native meets a well-adapted rival and usually fails, whereas a
  - **module 3 / lesson 3 / item 4** (extractive) novel 85%: It removes the intermediate, less modified links, converting a continuous spread of forms into separated branches with gaps between them
  - **module 3 / lesson 3 / item 5** (restatement) novel 76%: Because classification reflects genealogy. Descendants of a common parent diverge over time, so the degree of resemblance between forms measures how recently th
  - **module 3 / lesson 3 / item 6** (extractive) novel 85%: That divergence is a tendency arising from competition, not an inevitable law, so a form in a confined and stable station may remain little modified

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 3** (The Question Darwin Asks)
  - Q: According to Darwin, what happens to variations that are neither useful nor injurious, and what does he offer as a possible example?
  - Expected answer: `They are not affected by natural selection and remain a fluctuating element in the population; Darwin suggests polymorphic species — those showing several persisting forms — as a possible example.`
  - Best window recall 0.41, global token recall 0.47
  - Closest source text: `and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither useful nor injurious would not`

- **module 1 / lesson 1 / item 5** (The Question Darwin Asks)
  - Q: Darwin argues by analogy from the breeder to nature. What crucial element of the breeder's activity does he claim nature supplies, and what element does he show to be unnecessary?
  - Expected answer: `Nature supplies differential reproduction; the breeder's intention or foresight is unnecessary`
  - Best window recall 0.11, global token recall 0.22
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 1 / lesson 1 / item 6** (The Question Darwin Asks)
  - Q: Why does Darwin emphasise advantages that are 'slight' rather than large?
  - Expected answer: `Because even minute advantages, accumulated over thousands of generations, suffice to produce change`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations`

- **module 1 / lesson 2 / item 1** (Variation, Heredity, and Plasticity)
  - Q: When Darwin writes that 'under domestication... the whole organisation becomes in some degree plastic,' what does he mean?
  - Expected answer: `No part of the organism — skeleton, instinct, developmental timing — is exempt from being altered across generations under selection`
  - Best window recall 0.09, global token recall 0.18
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all`

- **module 1 / lesson 2 / item 3** (Variation, Heredity, and Plasticity)
  - Q: Darwin says variations 'neither useful nor injurious' would be left 'a fluctuating element'. What does this concession accomplish?
  - Expected answer: `It admits that some characters are invisible to selection, so the theory does not claim all traits are adaptations, and it offers an explanation for polymorphic species`
  - Best window recall 0.25, global token recall 0.33
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both`

- **module 1 / lesson 2 / item 5** (Variation, Heredity, and Plasticity)
  - Q: Darwin stresses that domestic productions vary in an 'endless number of strange peculiarities' rather than merely in size or colour. Why does the strangeness and breadth of variation matter to his case?
  - Expected answer: `Because selection can only act on the variation available, so a wide and pervasive supply of variability gives selection many dimensions to work on`
  - Best window recall 0.23, global token recall 0.31
  - Closest source text: `diversity of inhabitants of any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapte`

- **module 1 / lesson 2 / item 6** (Variation, Heredity, and Plasticity)
  - Q: Reconstruct the step in Darwin's reasoning that moves from the breeder's experience to nature. What admitted fact does he use as his pivot, and what would a sceptic have to believe in order to reject the inference?
  - Expected answer: `The pivot is that variations useful to man 'have undoubtedly occurred' — the everyday, uncontested success of breeders. Given that organisms stand in infinitely complex relations to their conditions of life, there are countless ways a slight variation could also be useful to the organism itself. To reject the inference, a sceptic would have to believe something arbitrary: that variation conveniently throws up features useful to humans but never any useful to the organism in its own struggle for existence.`
  - Best window recall 0.35, global token recall 0.38
  - Closest source text: `grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature i think we shall see that it can act most effectually let it be b`

- **module 1 / lesson 3 / item 1** (The Web of Mutual Relations)
  - Q: In Darwin's argument, what is the chief work done by the claim that mutual relations are "infinitely complex and close-fitting"?
  - Expected answer: `It makes it plausible that some undirected variations will happen to be useful, and that even slight ones will matter`
  - Best window recall 0.20, global token recall 0.30
  - Closest source text: `let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful`

- **module 1 / lesson 3 / item 2** (The Web of Mutual Relations)
  - Q: Darwin says variations "neither useful nor injurious" would be "left a fluctuating element." What does this concession show about the scope of natural selection?
  - Expected answer: `It shows selection is a filter rather than a shaper of every detail: it acts only where a variation touches the organism's relations, so indifferent characters escape it and may persist in several forms — which is what Darwin suspects we see in polymorphic species. Darwin is therefore not committed to every trait being an adaptation.`
  - Best window recall 0.18, global token recall 0.32
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 1 / lesson 3 / item 3** (The Web of Mutual Relations)
  - Q: Why is the phrase "in the course of thousands of generations" essential to Darwin's reasoning?
  - Expected answer: `Because even rare useful variations become an expected occurrence over enormous numbers of trials, and heredity accumulates them`
  - Best window recall 0.15, global token recall 0.15
  - Closest source text: `be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations use`

- **module 1 / lesson 3 / item 4** (The Web of Mutual Relations)
  - Q: A critic objects: "If the fit between organism and conditions is so close, surely almost any change would be harmful — so tight fitting tells against Darwin, not for him." How does Darwin's argument survive this?
  - Expected answer: `Darwin agrees that most changes will be harmful and says such variations are "rigidly destroyed." His case does not require useful variations to be common, only that they occur sometimes; the harmful ones are eliminated and cost the argument nothing, while the useful ones are preserved and accumulate. Close fit simply makes the filter sensitive in both directions, which is exactly what selection requires.`
  - Best window recall 0.22, global token recall 0.31
  - Closest source text: `in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each bei`

- **module 2 / lesson 1 / item 1** (Advantage, However Slight)
  - Q: In Darwin's sentence, what role does the parenthetical reminder that 'many more individuals are born than can possibly survive' play in the argument?
  - Expected answer: `It supplies the overproduction premise that makes even slight differences decisive, since some individuals must die regardless`
  - Best window recall 0.17, global token recall 0.17
  - Closest source text: `some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight`

- **module 2 / lesson 1 / item 6** (Advantage, However Slight)
  - Q: Which of the following would Darwin's phrase 'however slight' most directly contradict?
  - Expected answer: `The claim that natural selection requires large, conspicuously beneficial novelties to produce change`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 2 / lesson 2 / item 5** (Preservation and Rejection)
  - Q: Give one reason modern biology regards 'rigidly destroyed' as an overstatement, and state the more careful version of the claim.
  - Expected answer: `Selection is probabilistic and genetic drift can carry mildly harmful variants to high frequency, especially in small populations; a variant may also be harmful in one context but not another. The careful version is that variants reducing reproductive success tend to decline in frequency over many generations in sufficiently large populations.`
  - Best window recall 0.11, global token recall 0.14
  - Closest source text: `improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individua`

- **module 2 / lesson 2 / item 6** (Preservation and Rejection)
  - Q: According to the moth illustration, what determines whether a given variation counts as favourable or injurious?
  - Expected answer: `Its relation to the specific environment in which the organism lives`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 2 / lesson 3 / item 2** (The Neutral Case and Polymorphic Species)
  - Q: Why does Darwin cite polymorphic species in this passage?
  - Expected answer: `As a possible visible case of variation that selection has left untouched and undefined`
  - Best window recall 0.25, global token recall 0.38
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 2 / lesson 3 / item 4** (The Neutral Case and Polymorphic Species)
  - Q: Which modern idea is the closest descendant of Darwin's 'fluctuating element'?
  - Expected answer: `The neutral theory of molecular evolution, with change driven by genetic drift`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 1 / item 1** (Reach of Selection: Trifling Characters, All Ages, Both Sexes, and Sexual Selection)
  - Q: According to Darwin, what is the essential difference between natural selection and sexual selection?
  - Expected answer: `The penalty in sexual selection is few or no offspring rather than death, since it turns on competition for mates rather than the struggle for existence`
  - Best window recall 0.25, global token recall 0.33
  - Closest source text: `natural selection divergence of character related to the diversity of inhabitants of any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the strugg`

- **module 3 / lesson 1 / item 2** (Reach of Selection: Trifling Characters, All Ages, Both Sexes, and Sexual Selection)
  - Q: Darwin cites downy versus smooth-skinned fruit and the black pigs of Virginia that survive eating paint-root. What general point are these examples making?
  - Expected answer: `That characters which look trifling to us may in fact decide survival, so apparent uselessness reflects our ignorance`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 3 / lesson 1 / item 3** (Reach of Selection: Trifling Characters, All Ages, Both Sexes, and Sexual Selection)
  - Q: State two ways in which Darwin argues that nature's selection is more powerful than a human breeder's selection.
  - Expected answer: `Any two of: nature acts on internal organs and every shade of constitutional difference, not just visible traits man values; nature selects for the good of the organism itself rather than for man's use or fancy; nature tests variations under the exact conditions the organism must live in; nature works over immense periods of time whereas man's efforts are short and fleeting; nature is always at work, silently and insensibly, wherever opportunity offers.`
  - Best window recall 0.10, global token recall 0.12
  - Closest source text: `and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the princi`

- **module 3 / lesson 1 / item 5** (Reach of Selection: Trifling Characters, All Ages, Both Sexes, and Sexual Selection)
  - Q: Darwin argues at length that an occasional cross between two individuals is nearly universal, even among hermaphrodites. How does this fact cut both ways for natural selection?
  - Expected answer: `It helps by spreading favourable variations and maintaining vigour, but hinders by blending away individual peculiarities and keeping a population uniform — which is why isolation can favour selection`
  - Best window recall 0.18, global token recall 0.29
  - Closest source text: `species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selecti`

- **module 3 / lesson 2 / item 1** (Favourable and Unfavourable Circumstances)
  - Q: Why did Darwin regard free intercrossing over a wide area as generally unfavourable to the formation of new varieties?
  - Expected answer: `Because repeated crossing with the unmodified majority blends a new variation back into the common stock, keeping the population uniform`
  - Best window recall 0.14, global token recall 0.14
  - Closest source text: `character related to the diversity of inhabitants of any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too b`

- **module 3 / lesson 2 / item 2** (Favourable and Unfavourable Circumstances)
  - Q: Darwin thought a large, continuous area was in the long run more important than a small isolated one for producing dominant, widely diffused species. Give the two main reasons he offers.
  - Expected answer: `A large area supports far more individuals, so favourable variations arise more often in a given time; and competition there is far more severe, so any form that survives has been tested against many rivals and tends to beat the narrowly adapted products of small isolated regions.`
  - Best window recall 0.15, global token recall 0.22
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 3 / lesson 2 / item 3** (Favourable and Unfavourable Circumstances)
  - Q: Which statement best captures why the number of individuals matters so much to natural selection?
  - Expected answer: `Selection can only sort among variations that actually occur, and more individuals means more chances for a favourable variation to appear in a given time`
  - Best window recall 0.36, global token recall 0.43
  - Closest source text: `that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rej`

- **module 3 / lesson 2 / item 4** (Favourable and Unfavourable Circumstances)
  - Q: According to Darwin, natural selection acts only when certain conditions obtain, which is one reason it is so slow. What condition does he name?
  - Expected answer: `That there are places in the economy of nature which can be better filled by modification of the existing inhabitants`
  - Best window recall 0.12, global token recall 0.25
  - Closest source text: `on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence of character related to the diversity of inhabit`

- **module 3 / lesson 2 / item 6** (Favourable and Unfavourable Circumstances)
  - Q: Darwin writes that to admit species generally become rare before becoming extinct, yet to marvel when they cease to exist, is like admitting sickness precedes death but being astonished when the patient dies. What point is this analogy making?
  - Expected answer: `That rarity is the ordinary, expected forerunner of extinction, so extinction needs no mysterious special cause`
  - Best window recall 0.11, global token recall 0.11
  - Closest source text: `trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction`

- **module 3 / lesson 3 / item 1** (Divergence of Character and the Grouping of Organic Beings)
  - Q: According to the principle of divergence of character, why do the most divergent descendants of a common parent tend to be favoured?
  - Expected answer: `Because differing most from their kin lets them seize places in the economy of nature where competition is less severe`
  - Best window recall 0.09, global token recall 0.09
  - Closest source text: `the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature`

- **module 3 / lesson 3 / item 2** (Divergence of Character and the Grouping of Organic Beings)
  - Q: A plot of ground sown with several distinct genera of grasses yields more plants and a greater weight of herbage than a plot sown with a single species. How does Darwin use this fact?
  - Expected answer: `As evidence that a diversified set of forms can be supported on the same area, so divergence is rewarded in nature`
  - Best window recall 0.22, global token recall 0.33
  - Closest source text: `intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence of character related to the diversity of inhabitants of any small are`

- **module 3 / lesson 3 / item 4** (Divergence of Character and the Grouping of Organic Beings)
  - Q: What role does extinction play alongside divergence in explaining classification?
  - Expected answer: `It removes the intermediate, less modified links, converting a continuous spread of forms into separated branches with gaps between them`
  - Best window recall 0.08, global token recall 0.08
  - Closest source text: `chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on th`

- **module 3 / lesson 3 / item 6** (Divergence of Character and the Grouping of Organic Beings)
  - Q: In Darwin's diagram, one species (F) persists through all the periods almost unchanged. What does this illustrate?
  - Expected answer: `That divergence is a tendency arising from competition, not an inevitable law, so a form in a confined and stable station may remain little modified`
  - Best window recall 0.08, global token recall 0.15
  - Closest source text: `s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of indivi`

### Answerability (answer vs its own lesson content)

- 10/54 answerable from the lesson alone = 18.5%
- Tiers: {'exact': 0, 'strong': 10, 'partial': 27, 'unsupported': 17}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 0

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 4** (The Question Darwin Asks)
  - Q: Why is the fact that 'many more individuals are born than can possibly survive' essential to Darwin's opening argument?
  - Expected answer: `Because it means not all offspring can live to reproduce, so any slight heritable advantage translates into a better chance of surviving and leaving offspring. Without superabundant birth there would be no differential survival for variation to act through, and the chain of reasoning would collapse.`
  - Best window recall against lesson: 0.22

- **module 1 / lesson 1 / item 6** (The Question Darwin Asks)
  - Q: Why does Darwin emphasise advantages that are 'slight' rather than large?
  - Expected answer: `Because even minute advantages, accumulated over thousands of generations, suffice to produce change`
  - Best window recall against lesson: 0.30

- **module 1 / lesson 2 / item 6** (Variation, Heredity, and Plasticity)
  - Q: Reconstruct the step in Darwin's reasoning that moves from the breeder's experience to nature. What admitted fact does he use as his pivot, and what would a sceptic have to believe in order to reject the inference?
  - Expected answer: `The pivot is that variations useful to man 'have undoubtedly occurred' — the everyday, uncontested success of breeders. Given that organisms stand in infinitely complex relations to their conditions of life, there are countless ways a slight variation could also be useful to the organism itself. To reject the inference, a sceptic would have to believe something arbitrary: that variation conveniently throws up features useful to humans but never any useful to the organism in its own struggle for existence.`
  - Best window recall against lesson: 0.49

- **module 1 / lesson 3 / item 6** (The Web of Mutual Relations)
  - Q: Give one concrete example of the kind of interlocking relation Darwin has in mind, and explain how it would make a slight variation in an organism consequential.
  - Expected answer: `Any answer tracing a chain of dependence is acceptable — e.g. Darwin's chain from cats to field-mice to humble-bees to red clover. A slight variation in a clover's corolla length would alter how easily bees can reach its nectar, which alters pollination and seed set, which alters its representation in the next generation. Because the character sits at a tight interface with another organism, even a small change registers in survival and reproduction.`
  - Best window recall against lesson: 0.39

- **module 2 / lesson 1 / item 1** (Advantage, However Slight)
  - Q: In Darwin's sentence, what role does the parenthetical reminder that 'many more individuals are born than can possibly survive' play in the argument?
  - Expected answer: `It supplies the overproduction premise that makes even slight differences decisive, since some individuals must die regardless`
  - Best window recall against lesson: 0.42

- **module 2 / lesson 1 / item 3** (Advantage, However Slight)
  - Q: Darwin writes that an advantaged individual would have 'the best chance of surviving and of procreating their kind.' Explain why the word 'chance' matters, and why 'procreating' is not redundant with 'surviving'.
  - Expected answer: `'Chance' signals that the claim is statistical, not a guarantee: an advantaged individual can still die by accident, and the bias only shows itself across many individuals and generations. 'Procreating' is essential because mere survival accomplishes nothing for the theory unless the individual leaves offspring that inherit the advantage — reproduction, not longevity, is what propagates the variation.`
  - Best window recall against lesson: 0.41

- **module 2 / lesson 1 / item 6** (Advantage, However Slight)
  - Q: Which of the following would Darwin's phrase 'however slight' most directly contradict?
  - Expected answer: `The claim that natural selection requires large, conspicuously beneficial novelties to produce change`
  - Best window recall against lesson: 0.30

- **module 2 / lesson 2 / item 3** (Preservation and Rejection)
  - Q: Why does the lesson call the phrase 'in the least degree injurious' a 'load-bearing claim' rather than mere rhetoric?
  - Expected answer: `Because Darwin's theory requires selection to be sensitive to very small differences. If only large advantages or injuries mattered, evolution would depend on rare large variations; by making even slight differences consequential, Darwin allows complex structures to be built by the accumulation of many small steps.`
  - Best window recall against lesson: 0.46

- **module 2 / lesson 2 / item 6** (Preservation and Rejection)
  - Q: According to the moth illustration, what determines whether a given variation counts as favourable or injurious?
  - Expected answer: `Its relation to the specific environment in which the organism lives`
  - Best window recall against lesson: 0.40

- **module 2 / lesson 3 / item 3** (The Neutral Case and Polymorphic Species)
  - Q: Darwin writes 'as perhaps we see in the species called polymorphic.' Explain why the word 'perhaps' is appropriate here, giving at least one reason a seemingly neutral character might not truly be neutral.
  - Expected answer: `Darwin hedges because neutrality is very hard to demonstrate. A trait that looks useless to a human observer may in fact matter to mates, predators, or the physical conditions of life (Darwin stresses our ignorance of these relations); it may be correlated in development with a trait that is under selection; or it may be neutral only under present conditions and become useful or injurious if conditions change. So polymorphism is consistent with neutrality but does not prove it.`
  - Best window recall against lesson: 0.39

- **module 2 / lesson 3 / item 5** (The Neutral Case and Polymorphic Species)
  - Q: A biologist finds a species with two persistent colour forms and concludes, following Darwin, that colour must be selectively neutral. What alternative explanation should be considered, and why?
  - Expected answer: `Balancing selection: each form may be actively favoured under some circumstance (different habitats, seasons, frequencies, or predator behaviour), so selection maintains both rather than ignoring them. Persistent polymorphism can therefore be a product of selection rather than of its absence, so the observation of many forms alone does not establish neutrality.`
  - Best window recall against lesson: 0.31

- **module 3 / lesson 1 / item 2** (Reach of Selection: Trifling Characters, All Ages, Both Sexes, and Sexual Selection)
  - Q: Darwin cites downy versus smooth-skinned fruit and the black pigs of Virginia that survive eating paint-root. What general point are these examples making?
  - Expected answer: `That characters which look trifling to us may in fact decide survival, so apparent uselessness reflects our ignorance`
  - Best window recall against lesson: 0.30

- **module 3 / lesson 2 / item 3** (Favourable and Unfavourable Circumstances)
  - Q: Which statement best captures why the number of individuals matters so much to natural selection?
  - Expected answer: `Selection can only sort among variations that actually occur, and more individuals means more chances for a favourable variation to appear in a given time`
  - Best window recall against lesson: 0.43

- **module 3 / lesson 2 / item 6** (Favourable and Unfavourable Circumstances)
  - Q: Darwin writes that to admit species generally become rare before becoming extinct, yet to marvel when they cease to exist, is like admitting sickness precedes death but being astonished when the patient dies. What point is this analogy making?
  - Expected answer: `That rarity is the ordinary, expected forerunner of extinction, so extinction needs no mysterious special cause`
  - Best window recall against lesson: 0.22

- **module 3 / lesson 3 / item 1** (Divergence of Character and the Grouping of Organic Beings)
  - Q: According to the principle of divergence of character, why do the most divergent descendants of a common parent tend to be favoured?
  - Expected answer: `Because differing most from their kin lets them seize places in the economy of nature where competition is less severe`
  - Best window recall against lesson: 0.36

- **module 3 / lesson 3 / item 3** (Divergence of Character and the Grouping of Organic Beings)
  - Q: Naturalised plants and animals in a new country tend to belong disproportionately to genera that are not already represented among the natives. Explain in a sentence or two what this shows about competition and divergence.
  - Expected answer: `It shows that competition is fiercest between very similar forms: a newcomer closely resembling a native meets a well-adapted rival and usually fails, whereas a strikingly unlike form finds an unoccupied place in the economy of nature and can establish itself. This supports the claim that being different from one's nearest competitors is advantageous — the core of divergence.`
  - Best window recall against lesson: 0.41

- **module 3 / lesson 3 / item 5** (Divergence of Character and the Grouping of Organic Beings)
  - Q: On Darwin's view, why do organic beings fall into 'groups subordinate to groups' rather than into a single unbroken series?
  - Expected answer: `Because classification reflects genealogy. Descendants of a common parent diverge over time, so the degree of resemblance between forms measures how recently they shared an ancestor; species within a genus branched off recently, orders long ago. Extinction of the intermediate branches leaves the gaps that make the nested groups definable rather than a continuous series.`
  - Best window recall against lesson: 0.46

### Concept coverage across the source

- 8/46 concepts anchored to a source chunk (38 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [8]
- Lessons per chunk: [0]
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
| 0 | 2,498 | 19 | 19 | 100.0% | 0.981 |
