# StudyForge generation eval

## Headline metrics

| Metric | prose-text | pep8-url |
|---|---|---|
| Lessons | 12 | 0 |
| Quiz items | 72 | 0 |
| Structure problems | 0 | 0 |
| Strict JSON first try | 1 | 1 |
| Hard parse failures | 0 | 1 |
| Grounded (exact+strong) | 0.3889 | 0 |
| Ungrounded items | 25 | 0 |
| Mean grounding recall | 0.6275 | 0 |
| Answerable from lesson | 0.4306 | 0 |
| Unanswerable items | 8 | 0 |
| Giveaway MCQs | 7 | 0 |
| Source chunks covered | 1 | 0 |
| Largest single-chunk share | 0.9167 | 0 |
| Cost USD | 1.4182 | 0.3282 |
| Wall clock s | 615.85 | 68.09 |

## prose-text

Source: text `darwin-origin-excerpt`, 10,637 chars, 2 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 12 | 12 | 0 | 0 | 12 | 12 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 12 | 43,851 | 45,138 | $1.3477 | 49.0 | 57.1 |
| outline | 1 | 3,438 | 2,133 | $0.0705 | 27.2 | 27.2 |

### Structure

- 4 modules, 12 lessons, 72 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 6788, min 5842
- Item kinds: {'mcq': 47, 'short': 25}
- Problems: none

### Grounding (answer vs source document)

- 28/72 answers supported (exact or strong) = 38.9%
- Tiers: {'exact': 8, 'strong': 20, 'partial': 19, 'unsupported': 25}
- Mean best-window recall: 0.628
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

#### Ungrounded items

- **module 1 / lesson 1 / item 1** (From the Struggle for Existence to Selection in Nature)
  - Q: Which of these is NOT one of the premises Darwin assembles in his opening argument for natural selection?
  - Expected answer: `Variations arise specifically because the organism needs them`
  - Best window recall 0.17, global token recall 0.33
  - Closest source text: `plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations`

- **module 1 / lesson 1 / item 3** (From the Struggle for Existence to Selection in Nature)
  - Q: In your own words, state Darwin's central inference in the phrasing he uses, and explain why the qualifiers 'however slight' and 'best chance' matter.
  - Expected answer: `Darwin infers that individuals having any advantage, however slight, over others would have the best chance of surviving and of procreating their kind. 'However slight' matters because it means no dramatic or monstrous variation is required — tiny differences suffice, since the relations of life are close-fitting and finely balanced. 'Best chance' matters because the claim is statistical rather than absolute: an advantaged individual is not guaranteed survival, only better odds, which over thousands of generations is enough to produce large effects.`
  - Best window recall 0.38, global token recall 0.58
  - Closest source text: `shall see that it can act most effectually let it be borne in mind in what an endless number of strange peculiarities our domestic productions and in a lesser degree those under nature vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation`

- **module 1 / lesson 1 / item 5** (From the Struggle for Existence to Selection in Nature)
  - Q: Darwin cites the horticulturist Downing on smooth-skinned versus downy fruits and on purple versus yellow plums. What is the purpose of these examples?
  - Expected answer: `To show that characters botanists call trifling can in fact decide which variety succeeds`
  - Best window recall 0.33, global token recall 0.56
  - Closest source text: `is in a flock of white sheep to destroy every lamb with the faintest trace of black in plants the down on the fruit and the colour of the flesh are considered by botanists as characters of the most trifling`

- **module 1 / lesson 2 / item 3** (The Definition: Preservation and Rejection)
  - Q: Which kind of species does Darwin tentatively offer as a possible example of neutral, fluctuating variation?
  - Expected answer: `Polymorphic species — species in which several distinct forms coexist without one displacing the others, which Darwin suggests ('as perhaps we see') may show variation that selection does not act on.`
  - Best window recall 0.35, global token recall 0.71
  - Closest source text: `and of procreating their kind on the other hand we may feel sure that any variation in the least degree injurious would be rigidly destroyed this preservation of favourable variations and the rejection of injurious variations i call natural selection variations neither useful nor injurious would not`

- **module 1 / lesson 2 / item 4** (The Definition: Preservation and Rejection)
  - Q: Darwin writes that 'unless profitable variations do occur, natural selection can do nothing.' What limitation of natural selection does this statement express?
  - Expected answer: `That natural selection cannot create variation; it can only sort or filter the heritable differences that already arise. Its whole power depends on a supply of profitable variation being available.`
  - Best window recall 0.24, global token recall 0.47
  - Closest source text: `conditions of life are supposed to have undergone a change and this would manifestly be favourable to natural selection by giving a better chance of profitable variations occurring and unless profitable variations do occur natural selection can do nothing not that as i believe any extreme amount of `

- **module 1 / lesson 2 / item 5** (The Definition: Preservation and Rejection)
  - Q: Which of these is NOT one of the premises Darwin uses to build up to his definition of natural selection?
  - Expected answer: `Only large, monstrous variations are capable of giving an advantage`
  - Best window recall 0.33, global token recall 0.67
  - Closest source text: `the reproductive system causes or increases variability and in the foregoing case the conditions of life are supposed to have undergone a change and this would manifestly be favourable to natural selection by giving a better chance of profitable variations`

- **module 1 / lesson 2 / item 6** (The Definition: Preservation and Rejection)
  - Q: Darwin contrasts nature with the human breeder, who 'does not rigidly destroy all inferior animals.' What point about natural selection is he making?
  - Expected answer: `That the negative half of selection — the constant destruction of injurious variation — operates in nature without mercy or lapse`
  - Best window recall 0.27, global token recall 0.73
  - Closest source text: `the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature`

- **module 2 / lesson 1 / item 2** (A Country Undergoing Physical Change)
  - Q: Explain in your own words what Darwin means when he says that changes in numerical proportions affect many inhabitants 'independently of the change of climate itself'.
  - Expected answer: `He means there are two causal channels. Besides the climate acting directly on an organism, the climate alters the abundance of other species, and because all inhabitants are intimately and complexly bound together, those altered numbers alone can seriously affect a species — even one that would have been perfectly comfortable in the new climate.`
  - Best window recall 0.32, global token recall 0.54
  - Closest source text: `as perhaps we see in the species called polymorphic we shall best understand the probable course of natural selection by taking the case of a country undergoing some physical change for instance of climate the proportional numbers of its inhabitants would almost immediately undergo a change and some`

- **module 2 / lesson 2 / item 2** (Immigration, Barriers, and Places in the Economy of Nature)
  - Q: In an open country undergoing physical change, what happens to newly opened places in the economy of nature, and why does this limit natural selection's work on the natives?
  - Expected answer: `New forms immigrate freely and seize those places at once; because the vacancy is filled by arrival rather than by modification, the original inhabitants get no opportunity to be slowly remade to occupy the role.`
  - Best window recall 0.40, global token recall 0.50
  - Closest source text: `to be but in the case of an island or of a country partly surrounded by barriers into which new and better adapted forms could not freely enter we should then have places in the economy of nature which would assuredly be better filled up if some of the original inhabitants were in some manner modifi`

- **module 2 / lesson 3 / item 5** (Variability, Time, and the Test of Naturalised Species)
  - Q: Which of the following is NOT one of Darwin's stated contrasts between man's selection and Nature's?
  - Expected answer: `Man works only on plants, while Nature works only on animals`
  - Best window recall 0.33, global token recall 0.67
  - Closest source text: `organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation can the principle of selection which we have seen is so potent in the hands of man apply in nature`

- **module 3 / lesson 1 / item 5** (What Man Can and Cannot Select)
  - Q: Why, in Darwin's account, does the breeder tend to begin from 'half-monstrous' forms?
  - Expected answer: `Because he must notice a variation before he can act on it, so only prominent or plainly useful modifications catch his eye`
  - Best window recall 0.45, global token recall 0.73
  - Closest source text: `animals but protects during each varying season as far as lies in his power all his productions he often begins his selection by some half monstrous form or at least by some modification prominent enough to catch his eye or to be plainly useful`

- **module 3 / lesson 1 / item 6** (What Man Can and Cannot Select)
  - Q: Which of the following is NOT one of the limitations on man's selection listed in this lesson?
  - Expected answer: `He cannot pass any selected character on to offspring by inheritance`
  - Best window recall 0.33, global token recall 0.33
  - Closest source text: `being she can act on every internal organ on every shade of constitutional difference on the whole machinery of life man selects only for his own good nature only for that of the being which she tends every selected character`

- **module 3 / lesson 3 / item 2** (Daily and Hourly Scrutiny: The Invisibility of Slow Change)
  - Q: In the passage, 'insensibly' means that natural selection works
  - Expected answer: `below the threshold of human perception`
  - Best window recall 0.00, global token recall 0.00
  - Closest source text: ``

- **module 3 / lesson 3 / item 3** (Daily and Hourly Scrutiny: The Invisibility of Slow Change)
  - Q: The lesson argues that the invisibility of natural selection is a strength of Darwin's case rather than an excuse. Briefly explain why.
  - Expected answer: `Because invisibility is what the theory itself predicts: the steps are tiny and the time required is vast, so no observer could see them. Darwin does not rest on direct observation but on two checkable legs — the mechanism (variation, heredity, overproduction, and the demonstrated power of cumulative selection under domestication) is observable now, and the outcome (that life has changed) is observable in the rocks. Like a river cutting a valley, an unwatched process can still be inferred from a known mechanism plus its cumulative product.`
  - Best window recall 0.13, global token recall 0.27
  - Closest source text: `it may be said that natural selection is daily and hourly scrutinising throughout the world every variation even the slightest rejecting that which is bad preserving and adding up all that is good silently and insensibly working whenever and wherever opportunity offers at the improvement of each org`

- **module 3 / lesson 3 / item 5** (Daily and Hourly Scrutiny: The Invisibility of Slow Change)
  - Q: Why does the lesson say the phrase 'adding up all that is good' is especially important in the famous passage?
  - Expected answer: `Because it shows selection is cumulative rather than a one-off filter: slight advantageous variations are preserved and accumulated across generations, so individually imperceptible steps can build up into large change over geological time.`
  - Best window recall 0.22, global token recall 0.43
  - Closest source text: `in any given direction mere individual differences so could nature but far more easily from having incomparably longer time at her disposal nor do i believe that any great physical change as of climate or any unusual degree of isolation to check immigration is actually necessary to produce new and u`

- **module 3 / lesson 3 / item 6** (Daily and Hourly Scrutiny: The Invisibility of Slow Change)
  - Q: Why did Darwin's personification of natural selection as 'scrutinising' cause him later trouble?
  - Expected answer: `It could be misread as implying a conscious agent, when it means only differential survival and reproduction`
  - Best window recall 0.12, global token recall 0.12
  - Closest source text: `the natives we may safely conclude that the natives might have been modified with advantage so as to have better resisted such intruders as man can produce and certainly has produced a great result by his methodical and unconscious means`

- **module 4 / lesson 1 / item 1** (Colour and Concealment in Animals)
  - Q: Why is the detail that hawks 'are guided by eyesight to their prey' essential to Darwin's argument about grouse colour?
  - Expected answer: `Because a visually hunting predator makes colour a cause of survival or death, so selection can act on it`
  - Best window recall 0.18, global token recall 0.27
  - Closest source text: `any small area and to naturalisation action of natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act`

- **module 4 / lesson 1 / item 2** (Colour and Concealment in Animals)
  - Q: According to the lesson, what does the warning on the Continent against keeping white pigeons contribute to Darwin's case?
  - Expected answer: `An everyday, verifiable observation that a conspicuous colour increases the risk of destruction`
  - Best window recall 0.25, global token recall 0.38
  - Closest source text: `on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour`

- **module 4 / lesson 1 / item 3** (Colour and Concealment in Animals)
  - Q: Darwin says natural selection may be effective both in 'giving' the proper colour and in 'keeping' it true and constant. Explain the difference between these two roles.
  - Expected answer: `'Giving' is directional: over generations the better-matched individuals survive more often and the population shifts toward the background tint. 'Keeping' is stabilising: once a good match exists, any individual departing from it is preferentially destroyed, so variation is continually removed and the colour stays uniform.`
  - Best window recall 0.18, global token recall 0.43
  - Closest source text: `to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of `

- **module 4 / lesson 1 / item 5** (Colour and Concealment in Animals)
  - Q: Why is the ptarmigan being white *in winter* (rather than always white) a particularly telling example?
  - Expected answer: `Because the seasonal change shows that what is useful is the match with the background, not whiteness in itself; a fixed tendency to be white would not switch on and off with the arrival of snow.`
  - Best window recall 0.12, global token recall 0.31
  - Closest source text: `vary and how strong the hereditary tendency is under domestication it may be truly said that the whole organisation becomes in some degree plastic let it be borne in mind how infinitely complex and close fitting are the mutual relations of all organic beings to each other and to their physical condi`

- **module 4 / lesson 2 / item 3** (Small Differences, Large Consequences in Plants)
  - Q: Explain the structure of Darwin's a fortiori inference from the orchard to the state of nature. Why is the cultivated case the harder case for his thesis?
  - Expected answer: `In cultivation the grower shelters the trees with all the aids of art, dampening the consequences of any weakness; yet even so, down and colour make a great difference between varieties. If the differences tell under such protective conditions, then in nature — where trees struggle with other trees and a host of enemies and far more are born than can survive — the same differences would decisively settle which variety succeeds. Cultivation is the harder case precisely because human care is expected to mask such small disadvantages.`
  - Best window recall 0.40, global token recall 0.57
  - Closest source text: `to think that the occasional destruction of an animal of any particular colour would produce little effect we should remember how essential it is in a flock of white sheep to destroy every lamb with the faintest trace of black in plants the down on the fruit and the colour of the flesh are considere`

- **module 4 / lesson 2 / item 4** (Small Differences, Large Consequences in Plants)
  - Q: Darwin says that nature 'cares nothing for appearances, except in so far as they may be useful to any being.' What does this imply about calling the down on fruit a 'trifling' character?
  - Expected answer: `It shows that 'trifling' reflects our judgement of appearance, not a proven lack of consequence for survival`
  - Best window recall 0.11, global token recall 0.11
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 4 / lesson 2 / item 6** (Small Differences, Large Consequences in Plants)
  - Q: How does the plant example extend Darwin's earlier animal-colour examples (green leaf-eating insects, white ptarmigan, heather-coloured grouse)?
  - Expected answer: `It shows the mechanism can be susceptibility to a beetle or disease rather than concealment from a predator's eye, and rests on independent testimony from a practical horticulturist`
  - Best window recall 0.20, global token recall 0.33
  - Closest source text: `the down on the fruit and the colour of the flesh are considered by botanists as characters of the most trifling importance yet we hear from an excellent horticulturist downing that in the united states smooth skinned fruits suffer far more from a beetle a curculio than those with down that purple p`

- **module 4 / lesson 3 / item 2** (Why Occasional Destruction Matters)
  - Q: Why does the objection that 'occasional destruction would produce little effect' fail?
  - Expected answer: `Because the deficit is inherited and repeated, so tiny per-generation effects add up over many generations`
  - Best window recall 0.18, global token recall 0.18
  - Closest source text: `useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course of thousands of generations if such do occur can we doubt remembering that many`

- **module 4 / lesson 3 / item 3** (Why Occasional Destruction Matters)
  - Q: Darwin says natural selection does two jobs with grouse colour. Name both.
  - Expected answer: `It gives the proper colour to each kind of grouse (origination), and it keeps that colour true and constant once acquired (maintenance, by continually pruning away new deviations).`
  - Best window recall 0.44, global token recall 0.56
  - Closest source text: `eyesight to their prey so much so that on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping th`

### Answerability (answer vs its own lesson content)

- 31/72 answerable from the lesson alone = 43.1%
- Tiers: {'exact': 9, 'strong': 22, 'partial': 33, 'unsupported': 8}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 7

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 1** (From the Struggle for Existence to Selection in Nature)
  - Q: Which of these is NOT one of the premises Darwin assembles in his opening argument for natural selection?
  - Expected answer: `Variations arise specifically because the organism needs them`
  - Best window recall against lesson: 0.33

- **module 1 / lesson 1 / item 5** (From the Struggle for Existence to Selection in Nature)
  - Q: Darwin cites the horticulturist Downing on smooth-skinned versus downy fruits and on purple versus yellow plums. What is the purpose of these examples?
  - Expected answer: `To show that characters botanists call trifling can in fact decide which variety succeeds`
  - Best window recall against lesson: 0.33

- **module 1 / lesson 2 / item 5** (The Definition: Preservation and Rejection)
  - Q: Which of these is NOT one of the premises Darwin uses to build up to his definition of natural selection?
  - Expected answer: `Only large, monstrous variations are capable of giving an advantage`
  - Best window recall against lesson: 0.33

- **module 3 / lesson 1 / item 6** (What Man Can and Cannot Select)
  - Q: Which of the following is NOT one of the limitations on man's selection listed in this lesson?
  - Expected answer: `He cannot pass any selected character on to offspring by inheritance`
  - Best window recall against lesson: 0.33

- **module 3 / lesson 3 / item 5** (Daily and Hourly Scrutiny: The Invisibility of Slow Change)
  - Q: Why does the lesson say the phrase 'adding up all that is good' is especially important in the famous passage?
  - Expected answer: `Because it shows selection is cumulative rather than a one-off filter: slight advantageous variations are preserved and accumulated across generations, so individually imperceptible steps can build up into large change over geological time.`
  - Best window recall against lesson: 0.30

- **module 4 / lesson 1 / item 1** (Colour and Concealment in Animals)
  - Q: Why is the detail that hawks 'are guided by eyesight to their prey' essential to Darwin's argument about grouse colour?
  - Expected answer: `Because a visually hunting predator makes colour a cause of survival or death, so selection can act on it`
  - Best window recall against lesson: 0.45

- **module 4 / lesson 2 / item 4** (Small Differences, Large Consequences in Plants)
  - Q: Darwin says that nature 'cares nothing for appearances, except in so far as they may be useful to any being.' What does this imply about calling the down on fruit a 'trifling' character?
  - Expected answer: `It shows that 'trifling' reflects our judgement of appearance, not a proven lack of consequence for survival`
  - Best window recall against lesson: 0.22

- **module 4 / lesson 3 / item 2** (Why Occasional Destruction Matters)
  - Q: Why does the objection that 'occasional destruction would produce little effect' fail?
  - Expected answer: `Because the deficit is inherited and repeated, so tiny per-generation effects add up over many generations`
  - Best window recall against lesson: 0.45

### Concept coverage across the source

- 24/60 concepts anchored to a source chunk (36 unanchored)
- Chunks containing at least one concept: 2/2 (100.0%)
- Concepts per chunk: [22, 2]
- Lessons per chunk: [2, 0]
- Uncovered chunk indexes: none
- Largest share in one chunk: 91.7%

## pep8-url

**Generation failed:** `ValueError: No JSON object in model response: 'python\\ndef processRecord(rec):\\n    ...\\n'`

Source: url `https://peps.python.org/pep-0008/`, 48,597 chars, 8 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 1 | 1 | 1 | 0 | 0 | 0 | 1 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 1 | 18,834 | 2,929 | $0.1674 | 36.4 | 36.4 |
| outline | 1 | 18,639 | 2,704 | $0.1608 | 31.7 | 31.7 |
