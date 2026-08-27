# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 9 |
| Quiz items | 52 |
| Structure problems | 2 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.1923 |
| Grounded, extractive items only | 0.2632 |
| Ungrounded items, all | 39 |
| Ungrounded extractive items | 26 |
| Hallucination candidates | 29 |
| Mean grounding recall | 0.3495 |
| Answerable from lesson | 0.2115 |
| Unanswerable items | 17 |
| Giveaway MCQs | 1 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 1.062 |
| Wall clock s | 554.05 |

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
| lesson | 9 | 11,440 | 38,638 | $1.0232 | 59.8 | 74.8 |
| outline | 1 | 984 | 1,356 | $0.0388 | 16.1 | 16.1 |

### Structure

- 3 modules, 9 lessons, 52 quiz items
- Quiz items per lesson: [6, 5, 6, 6, 6, 6, 6, 5, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 5, 4, 5]
- Lesson content chars: mean 7740, min 6023
- Item kinds: {'mcq': 29, 'short': 23}
- Problems: {'duplicate_question': 2}

  - `duplicate_question` at module 1 / lesson 2 / item 1: also at module 1 / lesson 1 / item 2
  - `duplicate_question` at module 2 / lesson 1 / item 5: also at module 1 / lesson 1 / item 2

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 10/52 answers supported (exact or strong) = 19.2%
- Tiers: {'exact': 1, 'strong': 9, 'partial': 3, 'unsupported': 39}
- Mean best-window recall: 0.350
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 38, 'odd_one_out': 0, 'restatement': 14, 'trivial': 0}
- Extractive items supported: 10/38 = 26.3% (mean window recall 0.386)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 63.1%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 29

  - **module 1 / lesson 1 / item 4** (extractive) novel 67%: To make it plausible that some variations will happen to be useful to their possessor
  - **module 1 / lesson 1 / item 5** (extractive) novel 71%: It is useful because it undeniably demonstrates the power of accumulated selection to transform organisms. It is imperfect because the breeder has intentions, a
  - **module 1 / lesson 1 / item 6** (extractive) novel 86%: Because he frames his task as building plausibility from premises his readers already concede, not as reporting a direct observation of species formation
  - **module 1 / lesson 2 / item 3** (restatement) novel 67%: 'Chance' signals a statistical claim about probabilities across many individuals over many generations, not a guarantee for any single individual — an advantage
  - **module 1 / lesson 2 / item 5** (extractive) novel 62%: He argues that since variations useful to breeders have undoubtedly occurred, it is not improbable that variations useful to the organism itself would also occu
  - **module 1 / lesson 3 / item 1** (extractive) novel 70%: Because selection acts on differences in survival and reproduction, and neutral variants create no such difference
  - **module 1 / lesson 3 / item 3** (extractive) novel 79%: Darwin identified the logical possibility that selection ignores some variation, but had no mechanism (random change in finite populations) to describe what hap
  - **module 1 / lesson 3 / item 4** (restatement) novel 62%: Because our failure to identify a function reflects our ignorance, not the trait's irrelevance. Darwin himself stresses natural selection's power over 'characte
  - **module 1 / lesson 3 / item 5** (extractive) novel 83%: The same variant may be neutral in one environment and advantageous or harmful in another, so neutral variation also acts as a reservoir for future selection
  - **module 1 / lesson 3 / item 6** (extractive) novel 65%: It prevents the theory from becoming an unfalsifiable claim that every character must be useful. By allowing that some characters are outside selection's reach,
  - **module 2 / lesson 1 / item 1** (extractive) novel 67%: That variation touches an enormous range of different characters, giving selection abundant and varied raw material
  - **module 2 / lesson 1 / item 3** (extractive) novel 67%: The idea that species possess fixed essential natures beyond which they cannot be modified
  - **module 2 / lesson 1 / item 4** (restatement) novel 65%: He adds "how strong the hereditary tendency is." Variation alone would be useless to selection if peculiarities were not passed to offspring; heredity is what m
  - **module 2 / lesson 2 / item 2** (extractive) novel 68%: Because organisms are entangled with many other beings and conditions at every point of life, there are countless relations a slight variation could bear upon. 
  - **module 2 / lesson 2 / item 5** (extractive) novel 69%: He means that changed conditions of life seem to loosen the organism so that variation appears in many parts at once, yielding an abundance of strange peculiari
  - **module 2 / lesson 2 / item 6** (restatement) novel 62%: That many more individuals are born than can possibly survive. This superabundance is essential because it guarantees that a sorting actually takes place: if al
  - **module 2 / lesson 3 / item 1** (extractive) novel 90%: It guarantees that heavy elimination occurs automatically, so no conscious chooser is needed for sorting to happen
  - **module 2 / lesson 3 / item 2** (restatement) novel 63%: He includes it to mark a genuine limit on the theory — natural selection does not account for every trait, only those that bear on advantage or injury. He uses 
  - **module 2 / lesson 3 / item 4** (restatement) novel 84%: Because a weak premise is easy to grant and hard to dispute. Darwin does not need useful variations to be frequent or dramatic; given an enormous span of genera
  - **module 2 / lesson 3 / item 6** (extractive) novel 77%: Destruction of the injurious follows directly from the crushing surplus of births — it requires nothing but the arithmetic of elimination. Preservation of the f
  - **module 3 / lesson 1 / item 4** (extractive) novel 100%: The loser suffers few or no offspring rather than death
  - **module 3 / lesson 1 / item 5** (restatement) novel 70%: Because selection acts at all ages of the life cycle, not only on adults. A heritable variation expressed in the larval stage that improves the larva's survival
  - **module 3 / lesson 2 / item 2** (extractive) novel 71%: Advantage: isolation checks immigration of better-adapted competitors and prevents swamping by intercrossing with the parent stock, leaving open places for the 
  - **module 3 / lesson 2 / item 4** (restatement) novel 73%: He means time is not itself a cause of change: species do not become modified simply because they are old, and no accumulation occurs unless variations arise an
  - **module 3 / lesson 2 / item 5** (extractive) novel 64%: A large open continental area, because it holds many individuals and keeps competition severe
  - **module 3 / lesson 3 / item 2** (restatement) novel 73%: Because the struggle for existence is fiercest between the most closely allied forms: near relatives compete for the same food, habitat and resources, so any ad
  - **module 3 / lesson 3 / item 3** (extractive) novel 78%: Naturalised species succeed most often when they belong to genera not already represented in the country
  - **module 3 / lesson 3 / item 4** (restatement) novel 63%: It shows that a given area supports more total life when its inhabitants are structurally diverse, because differently built organisms exploit different places 
  - **module 3 / lesson 3 / item 6** (extractive) novel 80%: There would be a continuous gradation of forms with no gaps, so no natural boundaries between species, genera or families; every division would be arbitrary. Th

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 4** (The Question Darwin Poses)
  - Q: Why does Darwin ask his reader to 'bear in mind' the infinitely complex and close-fitting relations of organic beings to each other and to their conditions of life?
  - Expected answer: `To make it plausible that some variations will happen to be useful to their possessor`
  - Best window recall 0.33, global token recall 0.33
  - Closest source text: `let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful`

- **module 1 / lesson 1 / item 5** (The Question Darwin Poses)
  - Q: In what way is the analogy with the breeder both useful and imperfect for Darwin's argument?
  - Expected answer: `It is useful because it undeniably demonstrates the power of accumulated selection to transform organisms. It is imperfect because the breeder has intentions, a target, a short timescale, and selects for traits useful to himself, none of which apply in nature; the rest of the chapter works to show the principle still holds — indeed acts more effectually — once the intentional selector is removed.`
  - Best window recall 0.21, global token recall 0.24
  - Closest source text: `on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action exti`

- **module 1 / lesson 1 / item 6** (The Question Darwin Poses)
  - Q: Why does Darwin open the chapter with questions and the hedged phrase 'I think we shall see that it can act most effectually', rather than a flat assertion?
  - Expected answer: `Because he frames his task as building plausibility from premises his readers already concede, not as reporting a direct observation of species formation`
  - Best window recall 0.07, global token recall 0.07
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 1 / lesson 2 / item 5** (Preservation and Rejection: Darwin's Definition)
  - Q: How does Darwin use the example of variations useful to man under domestication to support his case for natural selection, and where does the analogy break down?
  - Expected answer: `He argues that since variations useful to breeders have undoubtedly occurred, it is not improbable that variations useful to the organism itself would also occur over thousands of generations; if breeders can accumulate such variations, nature can too. The analogy breaks down because the breeder selects deliberately toward a chosen standard, whereas nature has no purpose or foresight — the only 'standard' is whatever happens to aid survival and reproduction in an organism's particular conditions, and the process is correspondingly slower and undirected.`
  - Best window recall 0.26, global token recall 0.28
  - Closest source text: `regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature i think we shall see that it can act most effectually let it be borne in mind in what an endless number of strange peculiarities our domestic productions and in a lesser degree thos`

- **module 1 / lesson 3 / item 1** (Neutral Variation and Polymorphic Species)
  - Q: According to Darwin's own definition, why does natural selection leave neutral variations unaffected?
  - Expected answer: `Because selection acts on differences in survival and reproduction, and neutral variants create no such difference`
  - Best window recall 0.10, global token recall 0.10
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 1 / lesson 3 / item 3** (Neutral Variation and Polymorphic Species)
  - Q: A student says: 'Darwin's clause about neutral variation shows he already had the theory of genetic drift.' What is the most accurate correction?
  - Expected answer: `Darwin identified the logical possibility that selection ignores some variation, but had no mechanism (random change in finite populations) to describe what happens to it`
  - Best window recall 0.14, global token recall 0.21
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 1 / lesson 3 / item 5** (Neutral Variation and Polymorphic Species)
  - Q: Which statement best captures the claim that neutrality is context-dependent?
  - Expected answer: `The same variant may be neutral in one environment and advantageous or harmful in another, so neutral variation also acts as a reservoir for future selection`
  - Best window recall 0.17, global token recall 0.17
  - Closest source text: `any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 1 / lesson 3 / item 6** (Neutral Variation and Polymorphic Species)
  - Q: How does admitting a category of neutral variation strengthen rather than weaken Darwin's theory?
  - Expected answer: `It prevents the theory from becoming an unfalsifiable claim that every character must be useful. By allowing that some characters are outside selection's reach, Darwin makes 'this trait is an adaptation' a testable claim that could be wrong, and turns the usefulness of a trait into a question for investigation rather than an assumption.`
  - Best window recall 0.19, global token recall 0.23
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 2 / lesson 1 / item 1** (Variability Under Domestication and in Nature)
  - Q: When Darwin writes that domestic productions vary in an "endless number of strange peculiarities," what is the main force of the phrase for his argument?
  - Expected answer: `That variation touches an enormous range of different characters, giving selection abundant and varied raw material`
  - Best window recall 0.17, global token recall 0.25
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both`

- **module 2 / lesson 1 / item 3** (Variability Under Domestication and in Nature)
  - Q: What doctrine does the claim that "the whole organisation becomes in some degree plastic" most directly work against?
  - Expected answer: `The idea that species possess fixed essential natures beyond which they cannot be modified`
  - Best window recall 0.11, global token recall 0.11
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 2 / lesson 2 / item 1** (Heredity and the Complex Web of Relations)
  - Q: Why does Darwin's argument require that the hereditary tendency be strong?
  - Expected answer: `Because without inheritance, an individual's advantage would die with it and could not accumulate in the population`
  - Best window recall 0.12, global token recall 0.25
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 2 / lesson 2 / item 2** (Heredity and the Complex Web of Relations)
  - Q: How does the complexity and 'close-fitting' character of organic relations support, rather than undermine, the plausibility of useful variations?
  - Expected answer: `Because organisms are entangled with many other beings and conditions at every point of life, there are countless relations a slight variation could bear upon. The more numerous and tight the dependencies, the more ways a trifling change — in a nectary's depth, a seed coat, a coat colour, a flowering date — can tip the balance of survival. A tight, many-stranded web multiplies the opportunities for a variation to be advantageous.`
  - Best window recall 0.19, global token recall 0.24
  - Closest source text: `nature vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physica`

- **module 2 / lesson 2 / item 5** (Heredity and the Complex Web of Relations)
  - Q: What does Darwin mean by saying that under domestication 'the whole organisation becomes in some degree plastic', and what role does this play in his argument?
  - Expected answer: `He means that changed conditions of life seem to loosen the organism so that variation appears in many parts at once, yielding an abundance of strange peculiarities. Its role is evidential and material: it shows how much variation can be available as raw material for selection. Plasticity supplies the variety, heredity fixes it, and selection chooses among it. It does not mean organisms are moulded at will in a single generation.`
  - Best window recall 0.17, global token recall 0.20
  - Closest source text: `descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature i think we shall se`

- **module 2 / lesson 3 / item 1** (From Variations Useful to Man to Variations Useful in Nature)
  - Q: In Darwin's argument, what does the fact that 'many more individuals are born than can possibly survive' contribute that the analogy with human breeding cannot supply on its own?
  - Expected answer: `It guarantees that heavy elimination occurs automatically, so no conscious chooser is needed for sorting to happen`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 2 / lesson 3 / item 5** (From Variations Useful to Man to Variations Useful in Nature)
  - Q: Why does Darwin emphasise the 'infinitely complex and close-fitting' mutual relations among organic beings before drawing his analogy?
  - Expected answer: `Because this web of relations supplies the standard by which a variation counts as 'useful' in nature, playing the role the breeder's taste plays under domestication`
  - Best window recall 0.19, global token recall 0.38
  - Closest source text: `it be borne in mind in what an endless number of strange peculiarities our domestic productions and in a lesser degree those under nature vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degree plastic let it be borne`

- **module 2 / lesson 3 / item 6** (From Variations Useful to Man to Variations Useful in Nature)
  - Q: Darwin says he 'may feel sure' that injurious variations would be rigidly destroyed, but phrases the occurrence of useful variations more cautiously as a question. What accounts for this difference in confidence?
  - Expected answer: `Destruction of the injurious follows directly from the crushing surplus of births — it requires nothing but the arithmetic of elimination. Preservation of the favourable additionally requires that a genuinely advantageous variation happen to arise in the first place, which is a matter of chance and therefore stated more tentatively.`
  - Best window recall 0.19, global token recall 0.19
  - Closest source text: `then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that man`

- **module 3 / lesson 1 / item 2** (Scope and Reach of Selection)
  - Q: Which contrast best captures Darwin's claim that natural selection is more powerful than man's selection?
  - Expected answer: `Man selects only external characters useful or pleasing to himself, while nature scrutinises the whole organisation for the being's own good over vast time`
  - Best window recall 0.25, global token recall 0.44
  - Closest source text: `potent in the hands of man apply in nature i think we shall see that it can act most effectually let it be borne in mind in what an endless number of strange peculiarities our domestic productions and in a lesser degree those under nature vary and how strong the hereditary tendency is under domestic`

- **module 3 / lesson 1 / item 4** (Scope and Reach of Selection)
  - Q: How does sexual selection differ from natural selection in what the loser suffers?
  - Expected answer: `The loser suffers few or no offspring rather than death`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 1 / item 6** (Scope and Reach of Selection)
  - Q: A peacock's train makes flight harder and the bird more visible to predators. Which explanation fits Darwin's framework?
  - Expected answer: `It arises through sexual selection: the reproductive advantage from female preference outweighs the survival cost`
  - Best window recall 0.18, global token recall 0.36
  - Closest source text: `iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual`

- **module 3 / lesson 2 / item 1** (Conditions Favourable and Unfavourable)
  - Q: According to Darwin, why does free intercrossing tend to retard the formation of a new variety?
  - Expected answer: `Because a new favourable character is diluted by breeding with unmodified individuals, keeping the species uniform`
  - Best window recall 0.36, global token recall 0.36
  - Closest source text: `power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection diverg`

- **module 3 / lesson 2 / item 2** (Conditions Favourable and Unfavourable)
  - Q: Darwin treats isolation as favourable in some respects and unfavourable in others. Name one advantage and one disadvantage of isolation for the production of new species.
  - Expected answer: `Advantage: isolation checks immigration of better-adapted competitors and prevents swamping by intercrossing with the parent stock, leaving open places for the residents to fill (it may also give uniform physical conditions). Disadvantage: an isolated area is usually small, supporting few individuals, so favourable variations appear rarely, and competition is less severe, so the resulting forms tend to lose when they meet continental forms.`
  - Best window recall 0.17, global token recall 0.27
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 3 / lesson 2 / item 3** (Conditions Favourable and Unfavourable)
  - Q: Why does Darwin regard a large number of individuals as 'a highly important element of success' for a species undergoing modification?
  - Expected answer: `Large numbers supply more raw variation in any given period, so selection has more to act on`
  - Best window recall 0.33, global token recall 0.33
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 3 / lesson 2 / item 5** (Conditions Favourable and Unfavourable)
  - Q: On Darwin's reasoning, which region is more likely to produce dominant forms that spread widely over the world?
  - Expected answer: `A large open continental area, because it holds many individuals and keeps competition severe`
  - Best window recall 0.18, global token recall 0.27
  - Closest source text: `on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence of character related to the diversity of inhabit`

- **module 3 / lesson 3 / item 3** (Divergence, Extinction, and the Grouping of Organic Beings)
  - Q: Which observation did Darwin use as evidence connected with naturalisation to support the principle of divergence?
  - Expected answer: `Naturalised species succeed most often when they belong to genera not already represented in the country`
  - Best window recall 0.11, global token recall 0.11
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 3 / lesson 3 / item 5** (Divergence, Extinction, and the Grouping of Organic Beings)
  - Q: Darwin claims his theory explains why organic beings fall into 'groups subordinate to groups.' Which pairing of causes produces this pattern?
  - Expected answer: `Divergence produces branching lineages, and extinction of intermediate and parent forms produces the gaps between them`
  - Best window recall 0.30, global token recall 0.40
  - Closest source text: `all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence`

- **module 3 / lesson 3 / item 6** (Divergence, Extinction, and the Grouping of Organic Beings)
  - Q: If no ancestral or intermediate forms had ever gone extinct, what would happen to the practice of biological classification?
  - Expected answer: `There would be a continuous gradation of forms with no gaps, so no natural boundaries between species, genera or families; every division would be arbitrary. The distinctness of the groups we recognise depends on the loss of the intermediate links.`
  - Best window recall 0.15, global token recall 0.15
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

### Answerability (answer vs its own lesson content)

- 11/52 answerable from the lesson alone = 21.2%
- Tiers: {'exact': 1, 'strong': 10, 'partial': 24, 'unsupported': 17}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 1

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 6** (The Question Darwin Poses)
  - Q: Why does Darwin open the chapter with questions and the hedged phrase 'I think we shall see that it can act most effectually', rather than a flat assertion?
  - Expected answer: `Because he frames his task as building plausibility from premises his readers already concede, not as reporting a direct observation of species formation`
  - Best window recall against lesson: 0.29

- **module 1 / lesson 2 / item 5** (Preservation and Rejection: Darwin's Definition)
  - Q: How does Darwin use the example of variations useful to man under domestication to support his case for natural selection, and where does the analogy break down?
  - Expected answer: `He argues that since variations useful to breeders have undoubtedly occurred, it is not improbable that variations useful to the organism itself would also occur over thousands of generations; if breeders can accumulate such variations, nature can too. The analogy breaks down because the breeder selects deliberately toward a chosen standard, whereas nature has no purpose or foresight — the only 'standard' is whatever happens to aid survival and reproduction in an organism's particular conditions, and the process is correspondingly slower and undirected.`
  - Best window recall against lesson: 0.49

- **module 1 / lesson 3 / item 2** (Neutral Variation and Polymorphic Species)
  - Q: What did Darwin mean by 'the species called polymorphic', and why did he mention them in this passage?
  - Expected answer: `He meant species (such as Rubus, Rosa, Hieracium, and some Crustacea) that vary so extensively and confusingly that taxonomists cannot agree on their limits. He mentions them as a possible ('perhaps') example of characters that are neither useful nor injurious, and which have therefore been left free to fluctuate because selection has not constrained them.`
  - Best window recall against lesson: 0.46

- **module 2 / lesson 1 / item 1** (Variability Under Domestication and in Nature)
  - Q: When Darwin writes that domestic productions vary in an "endless number of strange peculiarities," what is the main force of the phrase for his argument?
  - Expected answer: `That variation touches an enormous range of different characters, giving selection abundant and varied raw material`
  - Best window recall against lesson: 0.33

- **module 2 / lesson 1 / item 3** (Variability Under Domestication and in Nature)
  - Q: What doctrine does the claim that "the whole organisation becomes in some degree plastic" most directly work against?
  - Expected answer: `The idea that species possess fixed essential natures beyond which they cannot be modified`
  - Best window recall against lesson: 0.44

- **module 2 / lesson 1 / item 4** (Variability Under Domestication and in Nature)
  - Q: Darwin pairs the fact of variation with a second fact in the same sentence. What is it, and why is the pairing necessary?
  - Expected answer: `He adds "how strong the hereditary tendency is." Variation alone would be useless to selection if peculiarities were not passed to offspring; heredity is what makes selected differences cumulative across generations rather than transient.`
  - Best window recall against lesson: 0.45

- **module 2 / lesson 3 / item 1** (From Variations Useful to Man to Variations Useful in Nature)
  - Q: In Darwin's argument, what does the fact that 'many more individuals are born than can possibly survive' contribute that the analogy with human breeding cannot supply on its own?
  - Expected answer: `It guarantees that heavy elimination occurs automatically, so no conscious chooser is needed for sorting to happen`
  - Best window recall against lesson: 0.30

- **module 2 / lesson 3 / item 4** (From Variations Useful to Man to Variations Useful in Nature)
  - Q: Darwin says variations useful in nature need only 'sometimes occur in the course of thousands of generations', and that an advantage may be 'however slight'. Why does making these claims so weak actually strengthen his overall argument?
  - Expected answer: `Because a weak premise is easy to grant and hard to dispute. Darwin does not need useful variations to be frequent or dramatic; given an enormous span of generations and a constant surplus of births, even rare and tiny advantages accumulate. Asking little of the reader while deriving a large conclusion makes the argument robust against objection.`
  - Best window recall against lesson: 0.24

- **module 2 / lesson 3 / item 5** (From Variations Useful to Man to Variations Useful in Nature)
  - Q: Why does Darwin emphasise the 'infinitely complex and close-fitting' mutual relations among organic beings before drawing his analogy?
  - Expected answer: `Because this web of relations supplies the standard by which a variation counts as 'useful' in nature, playing the role the breeder's taste plays under domestication`
  - Best window recall against lesson: 0.44

- **module 2 / lesson 3 / item 6** (From Variations Useful to Man to Variations Useful in Nature)
  - Q: Darwin says he 'may feel sure' that injurious variations would be rigidly destroyed, but phrases the occurrence of useful variations more cautiously as a question. What accounts for this difference in confidence?
  - Expected answer: `Destruction of the injurious follows directly from the crushing surplus of births — it requires nothing but the arithmetic of elimination. Preservation of the favourable additionally requires that a genuinely advantageous variation happen to arise in the first place, which is a matter of chance and therefore stated more tentatively.`
  - Best window recall against lesson: 0.27

- **module 3 / lesson 1 / item 4** (Scope and Reach of Selection)
  - Q: How does sexual selection differ from natural selection in what the loser suffers?
  - Expected answer: `The loser suffers few or no offspring rather than death`
  - Best window recall against lesson: 0.40

- **module 3 / lesson 1 / item 6** (Scope and Reach of Selection)
  - Q: A peacock's train makes flight harder and the bird more visible to predators. Which explanation fits Darwin's framework?
  - Expected answer: `It arises through sexual selection: the reproductive advantage from female preference outweighs the survival cost`
  - Best window recall against lesson: 0.36

- **module 3 / lesson 2 / item 3** (Conditions Favourable and Unfavourable)
  - Q: Why does Darwin regard a large number of individuals as 'a highly important element of success' for a species undergoing modification?
  - Expected answer: `Large numbers supply more raw variation in any given period, so selection has more to act on`
  - Best window recall against lesson: 0.44

- **module 3 / lesson 2 / item 4** (Conditions Favourable and Unfavourable)
  - Q: Darwin writes that 'the mere lapse of time does nothing, either for or against natural selection.' Explain what he means and why long geological periods still matter to his argument.
  - Expected answer: `He means time is not itself a cause of change: species do not become modified simply because they are old, and no accumulation occurs unless variations arise and are selected. Long periods matter only because they provide the opportunity — the room — for slight favourable variations to appear, be preserved, and accumulate, since the process acts extremely slowly.`
  - Best window recall against lesson: 0.42

- **module 3 / lesson 2 / item 5** (Conditions Favourable and Unfavourable)
  - Q: On Darwin's reasoning, which region is more likely to produce dominant forms that spread widely over the world?
  - Expected answer: `A large open continental area, because it holds many individuals and keeps competition severe`
  - Best window recall against lesson: 0.45

- **module 3 / lesson 3 / item 3** (Divergence, Extinction, and the Grouping of Organic Beings)
  - Q: Which observation did Darwin use as evidence connected with naturalisation to support the principle of divergence?
  - Expected answer: `Naturalised species succeed most often when they belong to genera not already represented in the country`
  - Best window recall against lesson: 0.44

- **module 3 / lesson 3 / item 4** (Divergence, Extinction, and the Grouping of Organic Beings)
  - Q: A small plot of turf is found to contain many species drawn from many different genera and orders, rather than many species of one genus. Explain how Darwin uses this as evidence for divergence of character.
  - Expected answer: `It shows that a given area supports more total life when its inhabitants are structurally diverse, because differently built organisms exploit different places in the economy of nature and compete less directly. If diversity pays in a square yard of turf, then over generations natural selection will favour the most divergent descendants of a common parent, since they escape competition with their own relatives.`
  - Best window recall against lesson: 0.39

### Concept coverage across the source

- 16/44 concepts anchored to a source chunk (28 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [16]
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
| 0 | 2,498 | 19 | 19 | 100.0% | 0.954 |
