# StudyForge generation eval

## Headline metrics

| Metric | prose-short |
|---|---|
| Lessons | 8 |
| Quiz items | 48 |
| Structure problems | 1 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.1667 |
| Grounded, extractive items only | 0.2286 |
| Ungrounded items, all | 36 |
| Ungrounded extractive items | 24 |
| Hallucination candidates | 25 |
| Mean grounding recall | 0.3384 |
| Answerable from lesson | 0.2292 |
| Unanswerable items | 15 |
| Giveaway MCQs | 0 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 1 |
| Concentration vs chunk length | 1 |
| Source recall, mean chunk | 1 |
| Source recall, worst chunk | 1 |
| Cost USD | 0.9109 |
| Wall clock s | 467.76 |

## prose-short

Source: text `darwin-origin-short`, 2,498 chars, 1 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 8 | 8 | 0 | 0 | 8 | 8 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 8 | 10,221 | 33,003 | $0.8762 | 56.6 | 72.6 |
| outline | 1 | 984 | 1,190 | $0.0347 | 14.8 | 14.8 |

### Structure

- 3 modules, 8 lessons, 48 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 7667, min 6199
- Item kinds: {'mcq': 30, 'short': 18}
- Problems: {'duplicate_question': 1}

  - `duplicate_question` at module 3 / lesson 1 / item 2: also at module 2 / lesson 3 / item 3

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 8/48 answers supported (exact or strong) = 16.7%
- Tiers: {'exact': 1, 'strong': 7, 'partial': 4, 'unsupported': 36}
- Mean best-window recall: 0.338
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 35, 'odd_one_out': 0, 'restatement': 13, 'trivial': 0}
- Extractive items supported: 8/35 = 22.9% (mean window recall 0.374)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 65.4%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 25

  - **module 1 / lesson 1 / item 2** (extractive) novel 82%: Because it bridges from something his readers already accept to the contested claim, shifting the question to who does the selecting
  - **module 1 / lesson 2 / item 1** (extractive) novel 70%: Because establishing that intercrossing is universal sets up intercrossing as one of the main obstacles selection must overcome
  - **module 1 / lesson 2 / item 2** (extractive) novel 70%: It depends on a struggle between males for females, where failure means few or no offspring rather than death
  - **module 1 / lesson 2 / item 3** (restatement) novel 83%: Divergence generates ever more diversified descendants, which on its own would yield a continuous graded series of forms. Extinction removes the intermediate an
  - **module 1 / lesson 2 / item 5** (extractive) novel 79%: It establishes the timescale the rest of the argument needs. Selection accumulates only infinitesimally small modifications and can act only as places in the ec
  - **module 1 / lesson 2 / item 6** (extractive) novel 75%: Mechanism and reach; factual premise about intercrossing; conditions and tempo; consequences
  - **module 2 / lesson 1 / item 1** (extractive) novel 82%: Because artificial selection was already accepted by his readers, so he only has to argue that a familiar cause extends further than assumed
  - **module 2 / lesson 1 / item 6** (extractive) novel 86%: A probabilistic argument from accepted premises about variation, heredity, and time
  - **module 2 / lesson 2 / item 2** (restatement) novel 79%: Variation supplies the novelty on which selection acts, while heredity preserves and accumulates any advantage across generations. They pull against each other 
  - **module 2 / lesson 2 / item 4** (extractive) novel 84%: He lacked any correct mechanism of inheritance — no particulate theory, no genes. Under the assumed model of blending inheritance, a new favourable variation wo
  - **module 2 / lesson 2 / item 6** (extractive) novel 80%: To show that variation throws up unforeseen novelties rather than a limited, predictable set of options
  - **module 2 / lesson 3 / item 2** (restatement) novel 73%: A variation is not useful in the abstract; it is useful only insofar as it improves an organism's standing in some relation it already occupies — to a predator,
  - **module 2 / lesson 3 / item 4** (restatement) novel 81%: Many contemporaries treated the environment as essentially physical — climate, soil, elevation — acting directly on organisms. By stressing relations to other o
  - **module 2 / lesson 3 / item 5** (extractive) novel 62%: It means even slight differences in an organism register in its relations, so small variations can matter — and departures are usually for the worse
  - **module 3 / lesson 1 / item 3** (restatement) novel 69%: Because selection is a statistical process about odds, not a guarantee for any individual: a better-adapted organism can still die by chance. The theory only re
  - **module 3 / lesson 1 / item 4** (extractive) novel 75%: It makes it hard to deny that variation can be useful, since breeders have demonstrably found variations useful to human purposes
  - **module 3 / lesson 1 / item 5** (restatement) novel 76%: The definition comes after the premises have already forced the conclusion. Given heritable variation, occasional useful variations, and more births than surviv
  - **module 3 / lesson 1 / item 6** (extractive) novel 80%: Advantages would not be passed on, so any edge would die with the individual
  - **module 3 / lesson 2 / item 2** (restatement) novel 76%: Because without rejection, injurious variations would accumulate alongside favourable ones and the population would not move consistently in one direction. Pres
  - **module 3 / lesson 2 / item 3** (extractive) novel 78%: That preservation is probabilistic and only a tendency, while elimination of the harmful is treated as near-certain
  - **module 3 / lesson 2 / item 4** (extractive) novel 88%: 'Selection' imports the analogy with animal breeding, a process readers already accept and can observe, lending borrowed credibility to an invisible process. 'N
  - **module 3 / lesson 3 / item 2** (extractive) novel 73%: Because with no selective pressure directing it, the variation is free to persist and vary without converging on one form
  - **module 3 / lesson 3 / item 3** (restatement) novel 67%: Polymorphic species are species that appear in several distinct forms at once, unusually variable in some characters and hard for naturalists to classify. Darwi
  - **module 3 / lesson 3 / item 5** (restatement) novel 69%: A principle that could explain every feature of every organism would predict nothing and could not be tested. By stating that selection acts only where a variat
  - **module 3 / lesson 3 / item 6** (extractive) novel 67%: Neutrality depends on the organism's particular conditions of life, not on the trait alone

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 2** (The Chapter's Argument in Miniature)
  - Q: Why does Darwin open Chapter IV by comparing natural selection with man's selection?
  - Expected answer: `Because it bridges from something his readers already accept to the contested claim, shifting the question to who does the selecting`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 1 / lesson 1 / item 4** (The Chapter's Argument in Miniature)
  - Q: The heading's clauses about 'characters of trifling importance' and action 'at all ages and on both sexes' serve mainly to establish:
  - Expected answer: `The scope of natural selection — that nothing in an organism's life is exempt from it`
  - Best window recall 0.38, global token recall 0.50
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 1 / lesson 1 / item 6** (The Chapter's Argument in Miniature)
  - Q: The final clause of the heading — 'Explains the Grouping of all organic beings' — indicates that Darwin's ultimate aim in Chapter IV is to:
  - Expected answer: `Show that natural selection, via divergence and extinction, accounts for the nested pattern of life that taxonomists had described but not explained`
  - Best window recall 0.31, global token recall 0.46
  - Closest source text: `s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of indivi`

- **module 1 / lesson 2 / item 1** (The Topics Darwin Promises to Cover)
  - Q: Why does Darwin place "the generality of intercrosses between individuals of the same species" before the section on circumstances favourable and unfavourable to natural selection?
  - Expected answer: `Because establishing that intercrossing is universal sets up intercrossing as one of the main obstacles selection must overcome`
  - Best window recall 0.20, global token recall 0.20
  - Closest source text: `s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing`

- **module 1 / lesson 2 / item 2** (The Topics Darwin Promises to Cover)
  - Q: According to the lesson, what distinguishes sexual selection from natural selection as Darwin frames it?
  - Expected answer: `It depends on a struggle between males for females, where failure means few or no offspring rather than death`
  - Best window recall 0.10, global token recall 0.20
  - Closest source text: `gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between`

- **module 1 / lesson 2 / item 5** (The Topics Darwin Promises to Cover)
  - Q: What argumentative work does the brief topic "slow action" do, positioned as it is between the section on favourable circumstances and the sections on extinction and divergence?
  - Expected answer: `It establishes the timescale the rest of the argument needs. Selection accumulates only infinitesimally small modifications and can act only as places in the economy of nature open up, so its results are invisible in a human lifetime — which answers the objection that we never observe new species forming. It also bridges conditions and consequences, since extinction and divergence are cumulative outcomes requiring vast stretches of time.`
  - Best window recall 0.18, global token recall 0.21
  - Closest source text: `selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of int`

- **module 1 / lesson 2 / item 6** (The Topics Darwin Promises to Cover)
  - Q: The lesson describes the chapter heading as moving through four stages. Which sequence matches Darwin's plan?
  - Expected answer: `Mechanism and reach; factual premise about intercrossing; conditions and tempo; consequences`
  - Best window recall 0.12, global token recall 0.25
  - Closest source text: `s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing`

- **module 2 / lesson 1 / item 1** (Darwin's Opening Question)
  - Q: Why does Darwin frame his central claim as a question about whether *man's* principle of selection can apply in nature, rather than simply asserting a new natural law?
  - Expected answer: `Because artificial selection was already accepted by his readers, so he only has to argue that a familiar cause extends further than assumed`
  - Best window recall 0.09, global token recall 0.09
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all`

- **module 2 / lesson 1 / item 5** (Darwin's Opening Question)
  - Q: Why does Darwin emphasise that the mutual relations of organic beings are 'infinitely complex and close-fitting'?
  - Expected answer: `Because tight fit between an organism and its conditions means even slight differences can have real consequences`
  - Best window recall 0.08, global token recall 0.25
  - Closest source text: `excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses `

- **module 2 / lesson 1 / item 6** (Darwin's Opening Question)
  - Q: Darwin's inference that useful variations must sometimes arise in nature is best described as:
  - Expected answer: `A probabilistic argument from accepted premises about variation, heredity, and time`
  - Best window recall 0.14, global token recall 0.14
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 2 / lesson 2 / item 1** (Variation, Plasticity, and Heredity)
  - Q: Why does Darwin insist on adding the clause "and, in a lesser degree, those under nature" rather than simply pointing to the spectacular variation of domestic breeds?
  - Expected answer: `Because his argument moves by analogy from domestication to nature, and it collapses if wild organisms do not also vary`
  - Best window recall 0.30, global token recall 0.30
  - Closest source text: `it can act most effectually let it be borne in mind in what an endless number of strange peculiarities our domestic productions and in a lesser degree those under nature vary and how strong the hereditary tendency is under domestication`

- **module 2 / lesson 2 / item 4** (Variation, Plasticity, and Heredity)
  - Q: Darwin treats the strength of the hereditary tendency as an established fact. What did he lack, and what later objection did that gap expose his theory to?
  - Expected answer: `He lacked any correct mechanism of inheritance — no particulate theory, no genes. Under the assumed model of blending inheritance, a new favourable variation would be halved each generation by crossing and swamped before selection could accumulate it (the objection pressed by Fleeming Jenkin). Mendelian, particulate inheritance later resolved the difficulty because such factors do not dilute.`
  - Best window recall 0.10, global token recall 0.10
  - Closest source text: `project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals of the same species circum`

- **module 2 / lesson 2 / item 5** (Variation, Plasticity, and Heredity)
  - Q: At the end of this premise-setting passage, what has Darwin NOT yet established?
  - Expected answer: `That some variations are useful in nature and that anything acts to preserve them`
  - Best window recall 0.33, global token recall 0.50
  - Closest source text: `let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful`

- **module 2 / lesson 2 / item 6** (Variation, Plasticity, and Heredity)
  - Q: Why does Darwin emphasise the *strangeness* of domestic peculiarities, not merely their quantity?
  - Expected answer: `To show that variation throws up unforeseen novelties rather than a limited, predictable set of options`
  - Best window recall 0.10, global token recall 0.10
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 2 / lesson 3 / item 1** (Complex and Close-Fitting Relations)
  - Q: Why does Darwin insert the claim about 'infinitely complex and close-fitting' relations before arguing that useful variations occur in nature?
  - Expected answer: `Because the complexity of relations supplies many distinct dimensions in which a variation could be an advantage, making 'useful' variations unsurprising`
  - Best window recall 0.31, global token recall 0.46
  - Closest source text: `occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any`

- **module 2 / lesson 3 / item 5** (Complex and Close-Fitting Relations)
  - Q: Which statement best captures the significance of the word 'close-fitting' in Darwin's phrase, as distinct from 'complex'?
  - Expected answer: `It means even slight differences in an organism register in its relations, so small variations can matter — and departures are usually for the worse`
  - Best window recall 0.15, global token recall 0.31
  - Closest source text: `may be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations`

- **module 2 / lesson 3 / item 6** (Complex and Close-Fitting Relations)
  - Q: A student says: 'Darwin argues that because organisms need certain traits to fit their complex relations, the needed variations arise.' What is wrong with this reading?
  - Expected answer: `It reverses Darwin's logic. The complexity of relations does not summon or direct variation; variation is taken as given, copious and heritable, from the evidence of domestication. The relations merely ensure that among the many undirected variations, some will happen to confer an advantage in one relation or another — and those are then preserved while injurious ones are destroyed.`
  - Best window recall 0.22, global token recall 0.31
  - Closest source text: `in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each bei`

- **module 3 / lesson 1 / item 4** (Advantage, However Slight)
  - Q: What role does the analogy with domestic breeding play in the argument?
  - Expected answer: `It makes it hard to deny that variation can be useful, since breeders have demonstrably found variations useful to human purposes`
  - Best window recall 0.25, global token recall 0.25
  - Closest source text: `the best chance of surviving and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither u`

- **module 3 / lesson 1 / item 6** (Advantage, However Slight)
  - Q: If heredity were removed from Darwin's chain of premises while everything else stayed the same, what would fail?
  - Expected answer: `Advantages would not be passed on, so any edge would die with the individual`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 2 / item 3** (Naming the Principle)
  - Q: Darwin writes that advantaged individuals have 'the best chance of surviving' but that injurious variations 'would be rigidly destroyed'. What does this difference in register convey?
  - Expected answer: `That preservation is probabilistic and only a tendency, while elimination of the harmful is treated as near-certain`
  - Best window recall 0.11, global token recall 0.22
  - Closest source text: `shall see that it can act most effectually let it be borne in mind in what an endless number of strange peculiarities our domestic productions and in a lesser degree those under nature vary and how strong the hereditary tendency`

- **module 3 / lesson 2 / item 4** (Naming the Principle)
  - Q: What rhetorical work does the word 'selection' do, and what corrective work does 'natural' do?
  - Expected answer: `'Selection' imports the analogy with animal breeding, a process readers already accept and can observe, lending borrowed credibility to an invisible process. 'Natural' removes the selector: it marks that the process operates impersonally, without intention, and contrasts with the contrived 'artificial' case.`
  - Best window recall 0.08, global token recall 0.08
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 3 / lesson 3 / item 2** (The Neutral Case and Polymorphic Species)
  - Q: Why does Darwin say neutral variation would be 'fluctuating' rather than simply lost from the species?
  - Expected answer: `Because with no selective pressure directing it, the variation is free to persist and vary without converging on one form`
  - Best window recall 0.09, global token recall 0.18
  - Closest source text: `to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 3 / lesson 3 / item 4** (The Neutral Case and Polymorphic Species)
  - Q: Darwin writes 'as PERHAPS we see in the species called polymorphic.' What does this hedge indicate about the status of his claim?
  - Expected answer: `The logical point about neutral variation is certain, but the identification of polymorphic species as examples of it is a tentative empirical suggestion`
  - Best window recall 0.17, global token recall 0.25
  - Closest source text: `injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither useful nor injurious would not be affected by natural selection and would be left a fluctuating element as perhaps we see in the speci`

- **module 3 / lesson 3 / item 6** (The Neutral Case and Polymorphic Species)
  - Q: A shell-banding pattern in snails is neutral in one habitat but affects predation in another. What does this show about neutrality?
  - Expected answer: `Neutrality depends on the organism's particular conditions of life, not on the trait alone`
  - Best window recall 0.22, global token recall 0.33
  - Closest source text: `said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life`

### Answerability (answer vs its own lesson content)

- 11/48 answerable from the lesson alone = 22.9%
- Tiers: {'exact': 1, 'strong': 10, 'partial': 22, 'unsupported': 15}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 0

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 2** (The Chapter's Argument in Miniature)
  - Q: Why does Darwin open Chapter IV by comparing natural selection with man's selection?
  - Expected answer: `Because it bridges from something his readers already accept to the contested claim, shifting the question to who does the selecting`
  - Best window recall against lesson: 0.27

- **module 1 / lesson 1 / item 4** (The Chapter's Argument in Miniature)
  - Q: The heading's clauses about 'characters of trifling importance' and action 'at all ages and on both sexes' serve mainly to establish:
  - Expected answer: `The scope of natural selection — that nothing in an organism's life is exempt from it`
  - Best window recall against lesson: 0.38

- **module 1 / lesson 2 / item 3** (The Topics Darwin Promises to Cover)
  - Q: Explain why extinction must be discussed alongside divergence of character if Darwin is to account for the grouping of organic beings.
  - Expected answer: `Divergence generates ever more diversified descendants, which on its own would yield a continuous graded series of forms. Extinction removes the intermediate and less successful forms — especially the closely allied ones that compete most severely — so that what remains is a set of distinct groups nested within larger groups. Only the two together produce the discontinuous, hierarchical pattern that classification records.`
  - Best window recall against lesson: 0.39

- **module 2 / lesson 1 / item 1** (Darwin's Opening Question)
  - Q: Why does Darwin frame his central claim as a question about whether *man's* principle of selection can apply in nature, rather than simply asserting a new natural law?
  - Expected answer: `Because artificial selection was already accepted by his readers, so he only has to argue that a familiar cause extends further than assumed`
  - Best window recall against lesson: 0.36

- **module 2 / lesson 1 / item 6** (Darwin's Opening Question)
  - Q: Darwin's inference that useful variations must sometimes arise in nature is best described as:
  - Expected answer: `A probabilistic argument from accepted premises about variation, heredity, and time`
  - Best window recall against lesson: 0.43

- **module 2 / lesson 2 / item 5** (Variation, Plasticity, and Heredity)
  - Q: At the end of this premise-setting passage, what has Darwin NOT yet established?
  - Expected answer: `That some variations are useful in nature and that anything acts to preserve them`
  - Best window recall against lesson: 0.33

- **module 2 / lesson 2 / item 6** (Variation, Plasticity, and Heredity)
  - Q: Why does Darwin emphasise the *strangeness* of domestic peculiarities, not merely their quantity?
  - Expected answer: `To show that variation throws up unforeseen novelties rather than a limited, predictable set of options`
  - Best window recall against lesson: 0.30

- **module 2 / lesson 3 / item 2** (Complex and Close-Fitting Relations)
  - Q: In two or three sentences, explain what Darwin means by saying that usefulness is relational rather than a property of a variation on its own.
  - Expected answer: `A variation is not useful in the abstract; it is useful only insofar as it improves an organism's standing in some relation it already occupies — to a predator, a competitor, a pollinator, a drought. The same change could be an advantage in one relational context and a liability in another, so usefulness must always be assessed against the particular web of relations the being is embedded in.`
  - Best window recall against lesson: 0.47

- **module 2 / lesson 3 / item 4** (Complex and Close-Fitting Relations)
  - Q: The phrase 'mutual relations of all organic beings to each other' marks a departure from a common view of Darwin's contemporaries. What was that view, and why does his emphasis matter?
  - Expected answer: `Many contemporaries treated the environment as essentially physical — climate, soil, elevation — acting directly on organisms. By stressing relations to other organisms, Darwin makes the chief environment of any being consist largely of other living things, which are themselves changing. This makes the environment dynamic rather than fixed and multiplies the ways a slight advantage can matter.`
  - Best window recall against lesson: 0.39

- **module 2 / lesson 3 / item 5** (Complex and Close-Fitting Relations)
  - Q: Which statement best captures the significance of the word 'close-fitting' in Darwin's phrase, as distinct from 'complex'?
  - Expected answer: `It means even slight differences in an organism register in its relations, so small variations can matter — and departures are usually for the worse`
  - Best window recall against lesson: 0.38

- **module 2 / lesson 3 / item 6** (Complex and Close-Fitting Relations)
  - Q: A student says: 'Darwin argues that because organisms need certain traits to fit their complex relations, the needed variations arise.' What is wrong with this reading?
  - Expected answer: `It reverses Darwin's logic. The complexity of relations does not summon or direct variation; variation is taken as given, copious and heritable, from the evidence of domestication. The relations merely ensure that among the many undirected variations, some will happen to confer an advantage in one relation or another — and those are then preserved while injurious ones are destroyed.`
  - Best window recall against lesson: 0.31

- **module 3 / lesson 2 / item 3** (Naming the Principle)
  - Q: Darwin writes that advantaged individuals have 'the best chance of surviving' but that injurious variations 'would be rigidly destroyed'. What does this difference in register convey?
  - Expected answer: `That preservation is probabilistic and only a tendency, while elimination of the harmful is treated as near-certain`
  - Best window recall against lesson: 0.33

- **module 3 / lesson 3 / item 2** (The Neutral Case and Polymorphic Species)
  - Q: Why does Darwin say neutral variation would be 'fluctuating' rather than simply lost from the species?
  - Expected answer: `Because with no selective pressure directing it, the variation is free to persist and vary without converging on one form`
  - Best window recall against lesson: 0.36

- **module 3 / lesson 3 / item 5** (The Neutral Case and Polymorphic Species)
  - Q: Explain why admitting that some variations escape natural selection makes Darwin's theory stronger rather than weaker.
  - Expected answer: `A principle that could explain every feature of every organism would predict nothing and could not be tested. By stating that selection acts only where a variation affects survival or reproduction, Darwin makes a definite causal claim with observable consequences: traits that matter should be relatively uniform and fitted to conditions, while indifferent traits should stay variable. That contrast can be checked against nature.`
  - Best window recall against lesson: 0.42

- **module 3 / lesson 3 / item 6** (The Neutral Case and Polymorphic Species)
  - Q: A shell-banding pattern in snails is neutral in one habitat but affects predation in another. What does this show about neutrality?
  - Expected answer: `Neutrality depends on the organism's particular conditions of life, not on the trait alone`
  - Best window recall against lesson: 0.44

### Concept coverage across the source

- 11/40 concepts anchored to a source chunk (29 unanchored)
- Chunks containing at least one concept: 1/1 (100.0%)
- Concepts per chunk: [11]
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
- Lessons routed per segment: [8]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 2,498 | 19 | 19 | 100.0% | 1.000 |
