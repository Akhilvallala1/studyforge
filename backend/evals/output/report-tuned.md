# StudyForge generation eval

## Headline metrics

| Metric | prose-text |
|---|---|
| Lessons | 10 |
| Quiz items | 60 |
| Structure problems | 6 |
| Strict JSON first try | 0.9167 |
| Hard parse failures | 1 |
| Grounded, all items (old metric) | 0.1833 |
| Grounded, extractive items only | 0.22 |
| Ungrounded items, all | 23 |
| Ungrounded extractive items | 17 |
| Hallucination candidates | 5 |
| Mean grounding recall | 0.5315 |
| Answerable from lesson | 0.3 |
| Unanswerable items | 13 |
| Giveaway MCQs | 1 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.7917 |
| Concentration vs chunk length | 1.0795 |
| Source recall, mean chunk | 0.9487 |
| Source recall, worst chunk | 0.9286 |
| Cost USD | 1.4154 |
| Wall clock s | 666.49 |

## prose-text

Source: text `darwin-origin-excerpt`, 10,637 chars, 2 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 11 | 10 | 0 | 0 | 10 | 10 | 1 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 11 | 42,833 | 45,778 | $1.3586 | 58.7 | 88.0 |
| outline | 1 | 3,436 | 1,583 | $0.0568 | 20.7 | 20.7 |

### Structure

- 4 modules, 10 lessons, 60 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 5, 5, 5, 5, 5, 5, 4, 4, 5]
- Lesson content chars: mean 7459, min 5185
- Item kinds: {'mcq': 40, 'short': 20}
- Problems: {'empty_concept': 6}

  - `empty_concept` at module 1 / lesson 3 / item 1: According to the chapter-summary heading, what is the final thing Darwin claims natural selection explains?
  - `empty_concept` at module 1 / lesson 3 / item 2: The heading names three 'circumstances favourable and unfavourable to Natural Selection'. Which trio is it?
  - `empty_concept` at module 1 / lesson 3 / item 3: Which pair of processes does the heading say acts on 'the descendants from a common parent'?
  - `empty_concept` at module 1 / lesson 3 / item 4: In Darwin's own words in this excerpt, what is natural selection?
  - `empty_concept` at module 1 / lesson 3 / item 5: Which topics from the chapter-summary heading are actually developed in this excerpt?
  - `empty_concept` at module 1 / lesson 3 / item 6: Why does the lesson say intercrossing appears twice in the heading, and what does isolation do about it?

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 11/60 answers supported (exact or strong) = 18.3%
- Tiers: {'exact': 1, 'strong': 10, 'partial': 26, 'unsupported': 23}
- Mean best-window recall: 0.531
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 50, 'odd_one_out': 0, 'restatement': 10, 'trivial': 0}
- Extractive items supported: 11/50 = 22.0% (mean window recall 0.558)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 33.9%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 5

  - **module 2 / lesson 2 / item 2** (extractive) novel 72%: A role or way of making a living within the community — a manner of feeding, breeding or escaping enemies — that some organism could exploit but that no organis
  - **module 2 / lesson 3 / item 5** (extractive) novel 73%: Successful colonists are a filtered sample arriving without their usual enemies onto human-disturbed ground, so the contest with natives is not conducted on equ
  - **module 4 / lesson 1 / item 2** (extractive) novel 91%: It supplies practical evidence that conspicuous colour raises death rates from sight-hunting predators
  - **module 4 / lesson 1 / item 5** (extractive) novel 80%: Traits that seem negligible to human observers may be decisive in the eyes of an organism's enemies
  - **module 4 / lesson 2 / item 3** (extractive) novel 70%: That maintaining a character requires discrimination against even the slightest deviation, repeated consistently

#### Ungrounded extractive items

- **module 1 / lesson 2 / item 4** (The Definition: Preservation of the Favourable, Rejection of the Injurious)
  - Q: Darwin writes that 'unless profitable variations do occur, natural selection can do nothing.' What point is he making?
  - Expected answer: `Selection can only sift variation that already exists; it cannot generate it`
  - Best window recall 0.29, global token recall 0.29
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 2 / lesson 1 / item 4** (A Country Undergoing Physical Change)
  - Q: In Darwin's scenario, why does an island or a country partly surrounded by barriers give natural selection 'free scope for the work of improvement'?
  - Expected answer: `Because intruders cannot enter and seize the newly opened places, so those places can only be filled by natives that happen to be modified`
  - Best window recall 0.42, global token recall 0.50
  - Closest source text: `freely enter we should then have places in the economy of nature which would assuredly be better filled up if some of the original inhabitants were in some manner modified for had the area been open to immigration these same places would have been seized on by intruders`

- **module 2 / lesson 2 / item 2** (Open Borders, Islands, and Places in the Economy of Nature)
  - Q: What does Darwin mean by a "place in the economy of nature"?
  - Expected answer: `A role or way of making a living within the community — a manner of feeding, breeding or escaping enemies — that some organism could exploit but that no organism currently occupies. It is an opportunity, not a patch of ground.`
  - Best window recall 0.11, global token recall 0.22
  - Closest source text: `adapted forms could not freely enter we should then have places in the economy of nature which would assuredly be better filled up if some of the original inhabitants were in some manner modified for had the area been open to immigration these same places would have been seized on by intruders in su`

- **module 2 / lesson 3 / item 3** (Variability, Nicely Balanced Forces, and Naturalised Intruders)
  - Q: What work does the phrase 'nicely balanced forces' do in Darwin's argument?
  - Expected answer: `It supports the idea that extremely slight modifications can be decisive, so improvement is possible without any external upheaval`
  - Best window recall 0.30, global token recall 0.50
  - Closest source text: `necessary to produce new and unoccupied places for natural selection to fill up by modifying and improving some of the varying inhabitants for as all the inhabitants of each country are struggling together with nicely balanced forces extremely slight modifications`

- **module 2 / lesson 3 / item 5** (Variability, Nicely Balanced Forces, and Naturalised Intruders)
  - Q: Which of the following is the strongest objection to Darwin's use of naturalisation as evidence?
  - Expected answer: `Successful colonists are a filtered sample arriving without their usual enemies onto human-disturbed ground, so the contest with natives is not conducted on equal terms`
  - Best window recall 0.07, global token recall 0.13
  - Closest source text: `advantage over others and still further modifications of the same kind would often still further increase the advantage no country can be named in which all the native inhabitants are now so perfectly adapted to each other and to the physical conditions under which they live that none of them could `

- **module 3 / lesson 1 / item 2** (What Man Can and Cannot Do)
  - Q: According to the lesson, what is nature's relation to outward appearance?
  - Expected answer: `Nature attends to appearance only so far as it is useful to the being, as with a grouse's protective colouring`
  - Best window recall 0.33, global token recall 0.56
  - Closest source text: `produced a great result by his methodical and unconscious means of selection what may not nature effect man can act only on external and visible characters nature cares nothing for appearances except in so far as they may be useful`

- **module 3 / lesson 1 / item 4** (What Man Can and Cannot Do)
  - Q: Darwin notes that man 'does not rigidly destroy all inferior animals, but protects during each varying season, as far as lies in his power, all his productions.' What is the consequence?
  - Expected answer: `Selection under domestication is leaky, since inferior variants survive to breed, whereas natural selection rejects them`
  - Best window recall 0.18, global token recall 0.55
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all`

- **module 3 / lesson 2 / item 2** (Nature as a Superior Selector)
  - Q: Darwin complains that man 'feeds a long and a short beaked pigeon on the same food' and 'exposes sheep with long and short wool to the same climate.' What defect in human selection are these examples meant to illustrate?
  - Expected answer: `That the breeder never puts the character he has selected to use in conditions fitted to it`
  - Best window recall 0.38, global token recall 0.38
  - Closest source text: `on the whole machinery of life man selects only for his own good nature only for that of the being which she tends every selected character is fully exercised by her and the being is placed under well suited conditions`

- **module 3 / lesson 2 / item 5** (Nature as a Superior Selector)
  - Q: Downing's observations on American fruit — that smooth-skinned fruits suffer more from the curculio beetle, and purple plums more from a certain disease than yellow ones — serve what purpose in Darwin's argument?
  - Expected answer: `They show that characters botanists call trifling can decide which variety survives, and would do so still more forcibly in the wild`
  - Best window recall 0.27, global token recall 0.55
  - Closest source text: `remember how essential it is in a flock of white sheep to destroy every lamb with the faintest trace of black in plants the down on the fruit and the colour of the flesh are considered by botanists as characters of the most trifling`

- **module 4 / lesson 1 / item 1** (Colour and Concealment in Insects and Birds)
  - Q: According to the lesson, why is the alpine ptarmigan's white winter plumage a particularly telling example?
  - Expected answer: `Because the colour changes with the season, so it tracks the background rather than being a fixed family trait`
  - Best window recall 0.10, global token recall 0.30
  - Closest source text: `manner he exposes sheep with long and short wool to the same climate he does not allow the most vigorous males to struggle for the females he does not rigidly destroy all inferior animals but protects during each varying season`

- **module 4 / lesson 1 / item 2** (Colour and Concealment in Insects and Birds)
  - Q: What role does the warning against keeping white pigeons play in Darwin's argument?
  - Expected answer: `It supplies practical evidence that conspicuous colour raises death rates from sight-hunting predators`
  - Best window recall 0.09, global token recall 0.09
  - Closest source text: `being yet characters and structures which we are apt to consider as of very trifling importance may thus be acted on when we see leaf eating insects green and bark feeders mottled grey the alpine ptarmigan white in winter the red grouse the colour`

- **module 4 / lesson 1 / item 4** (Colour and Concealment in Insects and Birds)
  - Q: Darwin mentions the flock of white sheep in which every lamb with the faintest trace of black is destroyed. What objection is this analogy meant to answer?
  - Expected answer: `That the occasional destruction of oddly coloured individuals is too rare to have any real effect`
  - Best window recall 0.38, global token recall 0.62
  - Closest source text: `giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant nor ought we to think that the occasional destruction of an animal of any particular colour would produce little effect`

- **module 4 / lesson 1 / item 5** (Colour and Concealment in Insects and Birds)
  - Q: Which statement best captures the lesson's point about 'characters of trifling importance'?
  - Expected answer: `Traits that seem negligible to human observers may be decisive in the eyes of an organism's enemies`
  - Best window recall 0.10, global token recall 0.20
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 4 / lesson 1 / item 6** (Colour and Concealment in Insects and Birds)
  - Q: Besides giving grouse their proper colour in the first place, what second job does Darwin say natural selection performs with respect to that colour?
  - Expected answer: `It keeps the colour true and constant once acquired, by continually removing individuals that deviate from it.`
  - Best window recall 0.44, global token recall 0.67
  - Closest source text: `most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant`

- **module 4 / lesson 2 / item 2** (Small Differences, Large Consequences)
  - Q: Why does Darwin think the orchard evidence is stronger, not weaker, for his case about wild plants?
  - Expected answer: `Because the effects appear even under cultivation's protections, so in nature, amid competing trees and many enemies, they would be greater still`
  - Best window recall 0.20, global token recall 0.47
  - Closest source text: `disease than yellow plums whereas another disease attacks yellow fleshed peaches far more than those with other coloured flesh if with all the aids of art these slight differences make a great difference in cultivating the several varieties assuredly in a state of nature where the trees would have t`

- **module 4 / lesson 2 / item 3** (Small Differences, Large Consequences)
  - Q: What point is Darwin making with the remark about destroying every lamb with the faintest trace of black in a flock of white sheep?
  - Expected answer: `That maintaining a character requires discrimination against even the slightest deviation, repeated consistently`
  - Best window recall 0.20, global token recall 0.30
  - Closest source text: `it may be said that natural selection is daily and hourly scrutinising throughout the world every variation even the slightest rejecting that which is bad preserving and adding up all that is good silently and insensibly working whenever and wherever`

- **module 4 / lesson 2 / item 5** (Small Differences, Large Consequences)
  - Q: Why does Darwin bring up the warning, on parts of the Continent, against keeping white pigeons?
  - Expected answer: `To show that hawks hunt by eyesight, so that mere colour is under constant lethal scrutiny`
  - Best window recall 0.22, global token recall 0.56
  - Closest source text: `these birds and insects in preserving them from danger grouse if not destroyed at some period of their lives would increase in countless numbers they are known to suffer largely from birds of prey and hawks are guided by eyesight`

### Answerability (answer vs its own lesson content)

- 18/60 answerable from the lesson alone = 30.0%
- Tiers: {'exact': 1, 'strong': 17, 'partial': 29, 'unsupported': 13}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 1

#### Items not answerable from their lesson

- **module 1 / lesson 2 / item 4** (The Definition: Preservation of the Favourable, Rejection of the Injurious)
  - Q: Darwin writes that 'unless profitable variations do occur, natural selection can do nothing.' What point is he making?
  - Expected answer: `Selection can only sift variation that already exists; it cannot generate it`
  - Best window recall against lesson: 0.43

- **module 1 / lesson 2 / item 5** (The Definition: Preservation of the Favourable, Rejection of the Injurious)
  - Q: Why do Darwin's examples of grouse colouring and of downy versus smooth-skinned fruit complicate his category of variations that are 'neither useful nor injurious'?
  - Expected answer: `Because they show that characters we judge to be of trifling importance — plumage tint, down on a fruit, flesh colour — often turn out to affect survival, through predation by hawks or attack by beetles and disease. The neutral category is real, but our ability to decide what belongs in it is unreliable.`
  - Best window recall against lesson: 0.43

- **module 2 / lesson 1 / item 4** (A Country Undergoing Physical Change)
  - Q: In Darwin's scenario, why does an island or a country partly surrounded by barriers give natural selection 'free scope for the work of improvement'?
  - Expected answer: `Because intruders cannot enter and seize the newly opened places, so those places can only be filled by natives that happen to be modified`
  - Best window recall against lesson: 0.42

- **module 2 / lesson 3 / item 2** (Variability, Nicely Balanced Forces, and Naturalised Intruders)
  - Q: Darwin writes that 'unless profitable variations do occur, natural selection can do nothing.' Explain in a sentence or two why this admission is important to the logic of his theory.
  - Expected answer: `Because natural selection is a sorting process rather than a creative one: it can only preserve and accumulate variations that already exist, so the theory depends on an independent supply of variation. Darwin correctly identified this dependency even though his proposed source of variation (the reproductive system disturbed by changed conditions) was largely wrong.`
  - Best window recall against lesson: 0.45

- **module 2 / lesson 3 / item 3** (Variability, Nicely Balanced Forces, and Naturalised Intruders)
  - Q: What work does the phrase 'nicely balanced forces' do in Darwin's argument?
  - Expected answer: `It supports the idea that extremely slight modifications can be decisive, so improvement is possible without any external upheaval`
  - Best window recall against lesson: 0.30

- **module 3 / lesson 2 / item 5** (Nature as a Superior Selector)
  - Q: Downing's observations on American fruit — that smooth-skinned fruits suffer more from the curculio beetle, and purple plums more from a certain disease than yellow ones — serve what purpose in Darwin's argument?
  - Expected answer: `They show that characters botanists call trifling can decide which variety survives, and would do so still more forcibly in the wild`
  - Best window recall against lesson: 0.27

- **module 3 / lesson 2 / item 6** (Nature as a Superior Selector)
  - Q: Darwin says man 'often begins his selection by some half-monstrous form; or at least by some modification prominent enough to catch his eye.' State the contrast he draws with nature on this point.
  - Expected answer: `Under nature the slightest difference of structure or constitution may turn the nicely-balanced scale in the struggle for life and so be preserved — nature acts on differences far too small to attract a breeder's notice, rather than requiring a conspicuous or striking modification to start from.`
  - Best window recall against lesson: 0.42

- **module 4 / lesson 1 / item 1** (Colour and Concealment in Insects and Birds)
  - Q: According to the lesson, why is the alpine ptarmigan's white winter plumage a particularly telling example?
  - Expected answer: `Because the colour changes with the season, so it tracks the background rather than being a fixed family trait`
  - Best window recall against lesson: 0.40

- **module 4 / lesson 1 / item 4** (Colour and Concealment in Insects and Birds)
  - Q: Darwin mentions the flock of white sheep in which every lamb with the faintest trace of black is destroyed. What objection is this analogy meant to answer?
  - Expected answer: `That the occasional destruction of oddly coloured individuals is too rare to have any real effect`
  - Best window recall against lesson: 0.12

- **module 4 / lesson 1 / item 5** (Colour and Concealment in Insects and Birds)
  - Q: Which statement best captures the lesson's point about 'characters of trifling importance'?
  - Expected answer: `Traits that seem negligible to human observers may be decisive in the eyes of an organism's enemies`
  - Best window recall against lesson: 0.40

- **module 4 / lesson 1 / item 6** (Colour and Concealment in Insects and Birds)
  - Q: Besides giving grouse their proper colour in the first place, what second job does Darwin say natural selection performs with respect to that colour?
  - Expected answer: `It keeps the colour true and constant once acquired, by continually removing individuals that deviate from it.`
  - Best window recall against lesson: 0.44

- **module 4 / lesson 2 / item 2** (Small Differences, Large Consequences)
  - Q: Why does Darwin think the orchard evidence is stronger, not weaker, for his case about wild plants?
  - Expected answer: `Because the effects appear even under cultivation's protections, so in nature, amid competing trees and many enemies, they would be greater still`
  - Best window recall against lesson: 0.40

- **module 4 / lesson 2 / item 6** (Small Differences, Large Consequences)
  - Q: Darwin says natural selection could both give and keep the proper colour of each kind of grouse. What is the significance of putting it in those two parts?
  - Expected answer: `It shows that origination and maintenance are the same process at different moments: the same continual rejection of slightly disadvantageous variants that first establishes an advantageous colour also holds it true and constant afterwards.`
  - Best window recall against lesson: 0.42

### Concept coverage across the source

- 24/48 concepts anchored to a source chunk (24 unanchored)
- Chunks containing at least one concept: 2/2 (100.0%)
- Concepts per chunk: [19, 5]
- Lessons per chunk: [2, 1]
- Uncovered chunk indexes: none
- Largest share in one chunk: 79.2%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.7334, 0.2666]
- Actual share per chunk: [0.7917, 0.2083]
- Actual/expected: [1.0795, 0.7814]
- Worst concentration ratio: 1.08

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 94.9%
- Worst chunk: 1 at 92.9%
- Chunks under 50% covered: 0
- Lessons routed per segment: [10, 10]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 62 | 96.9% | 0.963 |
| 1 | 2,747 | 28 | 26 | 92.9% | 0.895 |
