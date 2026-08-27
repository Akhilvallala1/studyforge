# StudyForge generation eval

## Headline metrics

| Metric | prose-text |
|---|---|
| Lessons | 11 |
| Quiz items | 65 |
| Structure problems | 0 |
| Strict JSON first try | 1 |
| Hard parse failures | 0 |
| Grounded, all items (old metric) | 0.4154 |
| Grounded, extractive items only | 0.4727 |
| Ungrounded items, all | 20 |
| Ungrounded extractive items | 16 |
| Hallucination candidates | 1 |
| Mean grounding recall | 0.6439 |
| Answerable from lesson | 0.4462 |
| Unanswerable items | 10 |
| Giveaway MCQs | 3 |
| Source chunks covered | 1 |
| Largest single-chunk share (old metric) | 0.75 |
| Concentration vs chunk length | 1.0227 |
| Source recall, mean chunk | 0.9922 |
| Source recall, worst chunk | 0.9844 |
| Cost USD | 1.3344 |
| Wall clock s | 605.67 |

## prose-text

Source: text `darwin-origin-excerpt`, 10,637 chars, 2 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 11 | 11 | 0 | 0 | 11 | 11 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 11 | 43,356 | 42,149 | $1.2705 | 52.9 | 61.6 |
| outline | 1 | 3,436 | 1,868 | $0.0639 | 23.4 | 23.4 |

### Structure

- 4 modules, 11 lessons, 65 quiz items
- Quiz items per lesson: [6, 6, 6, 5, 6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [5, 5, 4, 5, 5, 5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 6507, min 5221
- Item kinds: {'mcq': 44, 'short': 21}
- Problems: none

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 27/65 answers supported (exact or strong) = 41.5%
- Tiers: {'exact': 4, 'strong': 23, 'partial': 18, 'unsupported': 20}
- Mean best-window recall: 0.644
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 55, 'odd_one_out': 0, 'restatement': 10, 'trivial': 0}
- Extractive items supported: 26/55 = 47.3% (mean window recall 0.664)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 24.6%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 1

  - **module 4 / lesson 1 / item 2** (extractive) novel 73%: It supplies everyday evidence that hawks hunt by sight, so conspicuous colouring gets an animal killed

#### Ungrounded extractive items

- **module 1 / lesson 2 / item 5** (Preservation and Rejection: The Definition)
  - Q: Darwin reasons that since variations useful to man have undoubtedly occurred, variations useful to the being itself should also occur. What makes this step an argument from a lesser case to a greater one, as the lesson presents it?
  - Expected answer: `Because human purposes in breeding are narrow and arbitrary and the breeder's time is short, whereas variations useful in the being's own "great and complex battle of life" have thousands of generations in which to arise; so if the narrower case is a fact, the broader one should be at least as likely.`
  - Best window recall 0.33, global token recall 0.59
  - Closest source text: `organic beings to each other and to their physical conditions of life can it then be thought improbable seeing that variations useful to man have undoubtedly occurred that other variations useful in some way to each being in the great and complex battle of life should sometimes occur in the course o`

- **module 1 / lesson 2 / item 6** (Preservation and Rejection: The Definition)
  - Q: Why does Darwin cite the warning, given in parts of the Continent, against keeping white pigeons?
  - Expected answer: `To show that hawks hunt by eyesight, so that colour is no trifle but a matter of life and death`
  - Best window recall 0.22, global token recall 0.44
  - Closest source text: `these birds and insects in preserving them from danger grouse if not destroyed at some period of their lives would increase in countless numbers they are known to suffer largely from birds of prey and hawks are guided by eyesight`

- **module 1 / lesson 3 / item 5** (Variations That Are Neither Useful Nor Injurious)
  - Q: Darwin cites the horticulturist Downing on plums and peaches. What does that evidence show about characters botanists call trifling?
  - Expected answer: `Such characters, like fruit down and flesh colour, are tied to susceptibility to particular beetles and diseases, and so are far from indifferent`
  - Best window recall 0.42, global token recall 0.50
  - Closest source text: `particular colour would produce little effect we should remember how essential it is in a flock of white sheep to destroy every lamb with the faintest trace of black in plants the down on the fruit and the colour of the flesh are considered by botanists as characters`

- **module 2 / lesson 1 / item 1** (A Country Undergoing Physical Change)
  - Q: According to Darwin, what is the first effect of a change in a country's climate?
  - Expected answer: `The relative abundances of the various inhabitants are altered almost at once`
  - Best window recall 0.33, global token recall 0.50
  - Closest source text: `we see in the species called polymorphic we shall best understand the probable course of natural selection by taking the case of a country undergoing some physical change for instance of climate the proportional numbers of its inhabitants would almost`

- **module 2 / lesson 1 / item 3** (A Country Undergoing Physical Change)
  - Q: Why does Darwin remind the reader of "how powerful the influence of a single introduced tree or mammal has been shown to be"?
  - Expected answer: `To supply a demonstrated case showing that even one species can profoundly reorganise a region's life`
  - Best window recall 0.17, global token recall 0.50
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both`

- **module 2 / lesson 2 / item 1** (Open Borders, Islands, and Places in the Economy of Nature)
  - Q: In Darwin's scenario, why does an island or barrier-bounded country favour the modification of its original inhabitants?
  - Expected answer: `Vacant places cannot be taken by better-adapted arrivals, so they are left to be filled by residents that happen to vary favourably`
  - Best window recall 0.31, global token recall 0.46
  - Closest source text: `single introduced tree or mammal has been shown to be but in the case of an island or of a country partly surrounded by barriers into which new and better adapted forms could not freely enter we should then have places in the economy of nature which would assuredly be better filled`

- **module 2 / lesson 2 / item 6** (Open Borders, Islands, and Places in the Economy of Nature)
  - Q: What does Darwin mean by saying natural selection would have 'free scope for the work of improvement' in an isolated area?
  - Expected answer: `Slight favourable modifications are left free to be preserved because no ready-made intruder pre-empts the openings they would fit`
  - Best window recall 0.21, global token recall 0.43
  - Closest source text: `places would have been seized on by intruders in such case every slight modification which in the course of ages chanced to arise and which in any way favoured the individuals of any of the species by better adapting them to their altered conditions would tend to be preserved and natural selection w`

- **module 3 / lesson 1 / item 1** (What Man Can and Cannot Do)
  - Q: Darwin says man 'feeds a long and a short beaked pigeon on the same food.' What defect in human selection is this meant to illustrate?
  - Expected answer: `That the breeder produces a difference in structure without supplying the conditions that would make that structure count for anything`
  - Best window recall 0.22, global token recall 0.44
  - Closest source text: `power all his productions he often begins his selection by some half monstrous form or at least by some modification prominent enough to catch his eye or to be plainly useful to him under nature the slightest difference of structure`

- **module 3 / lesson 1 / item 6** (What Man Can and Cannot Do)
  - Q: Why does Darwin conclude that nature's productions are 'truer' in character and better adapted than man's?
  - Expected answer: `Because every limitation he lists belongs to the breeder rather than to selection itself, so removing them leaves nothing to keep the results small`
  - Best window recall 0.20, global token recall 0.47
  - Closest source text: `case the conditions of life are supposed to have undergone a change and this would manifestly be favourable to natural selection by giving a better chance of profitable variations occurring and unless profitable variations do occur natural selection can do nothing not that as i believe any extreme a`

- **module 3 / lesson 2 / item 1** (Nature's Advantages: Scope, Fitness, and Time)
  - Q: Darwin writes that man 'feeds a long and a short beaked pigeon on the same food' and 'exposes sheep with long and short wool to the same climate.' What defect in human selection do these examples illustrate?
  - Expected answer: `The breeder fails to place each selected character in conditions where it is actually exercised and tested`
  - Best window recall 0.44, global token recall 0.56
  - Closest source text: `on the whole machinery of life man selects only for his own good nature only for that of the being which she tends every selected character is fully exercised by her and the being is placed under well suited conditions`

- **module 3 / lesson 2 / item 5** (Nature's Advantages: Scope, Fitness, and Time)
  - Q: Which statement best describes the logical character of Darwin's comparison between nature's selection and man's?
  - Expected answer: `It is an argument a fortiori: the reader who grants the power of domestic breeding must grant nature the greater power`
  - Best window recall 0.20, global token recall 0.30
  - Closest source text: `have seen is so potent in the hands of man apply in nature i think we shall see that it can act most effectually let it be borne in mind in what an endless number of strange peculiarities our domestic`

- **module 3 / lesson 3 / item 2** (Silent and Insensible Work)
  - Q: Darwin writes that selection works at the improvement of each being "in relation to its organic and inorganic conditions of life." What does this qualification establish?
  - Expected answer: `That improvement is measured against a being's living and physical surroundings, not against an absolute standard`
  - Best window recall 0.11, global token recall 0.33
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance`

- **module 3 / lesson 3 / item 6** (Silent and Insensible Work)
  - Q: Darwin mentions that in parts of the Continent people are warned not to keep white pigeons. What is this fact meant to support?
  - Expected answer: `That hawks are guided to their prey by eyesight, so conspicuous colour is dangerous — which supports the claim that the tints of grouse and insects serve to preserve them from danger and could be produced and kept constant by natural selection.`
  - Best window recall 0.45, global token recall 0.65
  - Closest source text: `leaf eating insects green and bark feeders mottled grey the alpine ptarmigan white in winter the red grouse the colour of heather and the black grouse that of peaty earth we must believe that these tints are of service to these birds and insects in preserving them from danger grouse if not destroyed`

- **module 4 / lesson 1 / item 2** (Colour and Concealment in Animals)
  - Q: Why does Darwin mention that on parts of the Continent people are warned not to keep white pigeons?
  - Expected answer: `It supplies everyday evidence that hawks hunt by sight, so conspicuous colouring gets an animal killed`
  - Best window recall 0.09, global token recall 0.18
  - Closest source text: `believe that these tints are of service to these birds and insects in preserving them from danger grouse if not destroyed at some period of their lives would increase in countless numbers they are known to suffer largely from birds of prey and hawks`

- **module 4 / lesson 1 / item 4** (Colour and Concealment in Animals)
  - Q: What point does the example of a flock of white sheep serve in Darwin's argument?
  - Expected answer: `That destroying even the faintly off-coloured individuals is enough to keep a whole population true to a colour`
  - Best window recall 0.25, global token recall 0.67
  - Closest source text: `are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true`

- **module 4 / lesson 2 / item 3** (Small Differences, Large Consequences in Plants)
  - Q: What point is Darwin making with the remark that in a flock of white sheep it is essential to destroy every lamb with the faintest trace of black?
  - Expected answer: `That the repeated elimination of even slightly deviant individuals produces large cumulative results`
  - Best window recall 0.10, global token recall 0.30
  - Closest source text: `ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sexes sexual selection on the generality of intercrosses between individuals`

### Answerability (answer vs its own lesson content)

- 29/65 answerable from the lesson alone = 44.6%
- Tiers: {'exact': 5, 'strong': 24, 'partial': 26, 'unsupported': 10}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 3

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 6** (The Question Darwin Sets Himself)
  - Q: Why does the phrase 'however slight' matter to Darwin's argument about individuals with an advantage?
  - Expected answer: `Because his argument does not depend on large or monstrous variations: it needs only that some individuals possess any advantage at all, however small, combined with the fact that many more individuals are born than can possibly survive. Slight everyday differences are therefore enough for selection to work on.`
  - Best window recall against lesson: 0.48

- **module 1 / lesson 3 / item 5** (Variations That Are Neither Useful Nor Injurious)
  - Q: Darwin cites the horticulturist Downing on plums and peaches. What does that evidence show about characters botanists call trifling?
  - Expected answer: `Such characters, like fruit down and flesh colour, are tied to susceptibility to particular beetles and diseases, and so are far from indifferent`
  - Best window recall against lesson: 0.42

- **module 2 / lesson 1 / item 1** (A Country Undergoing Physical Change)
  - Q: According to Darwin, what is the first effect of a change in a country's climate?
  - Expected answer: `The relative abundances of the various inhabitants are altered almost at once`
  - Best window recall against lesson: 0.33

- **module 2 / lesson 2 / item 1** (Open Borders, Islands, and Places in the Economy of Nature)
  - Q: In Darwin's scenario, why does an island or barrier-bounded country favour the modification of its original inhabitants?
  - Expected answer: `Vacant places cannot be taken by better-adapted arrivals, so they are left to be filled by residents that happen to vary favourably`
  - Best window recall against lesson: 0.31

- **module 2 / lesson 2 / item 6** (Open Borders, Islands, and Places in the Economy of Nature)
  - Q: What does Darwin mean by saying natural selection would have 'free scope for the work of improvement' in an isolated area?
  - Expected answer: `Slight favourable modifications are left free to be preserved because no ready-made intruder pre-empts the openings they would fit`
  - Best window recall against lesson: 0.29

- **module 3 / lesson 1 / item 6** (What Man Can and Cannot Do)
  - Q: Why does Darwin conclude that nature's productions are 'truer' in character and better adapted than man's?
  - Expected answer: `Because every limitation he lists belongs to the breeder rather than to selection itself, so removing them leaves nothing to keep the results small`
  - Best window recall against lesson: 0.33

- **module 3 / lesson 3 / item 2** (Silent and Insensible Work)
  - Q: Darwin writes that selection works at the improvement of each being "in relation to its organic and inorganic conditions of life." What does this qualification establish?
  - Expected answer: `That improvement is measured against a being's living and physical surroundings, not against an absolute standard`
  - Best window recall against lesson: 0.44

- **module 3 / lesson 3 / item 6** (Silent and Insensible Work)
  - Q: Darwin mentions that in parts of the Continent people are warned not to keep white pigeons. What is this fact meant to support?
  - Expected answer: `That hawks are guided to their prey by eyesight, so conspicuous colour is dangerous — which supports the claim that the tints of grouse and insects serve to preserve them from danger and could be produced and kept constant by natural selection.`
  - Best window recall against lesson: 0.35

- **module 4 / lesson 1 / item 2** (Colour and Concealment in Animals)
  - Q: Why does Darwin mention that on parts of the Continent people are warned not to keep white pigeons?
  - Expected answer: `It supplies everyday evidence that hawks hunt by sight, so conspicuous colouring gets an animal killed`
  - Best window recall against lesson: 0.36

- **module 4 / lesson 1 / item 4** (Colour and Concealment in Animals)
  - Q: What point does the example of a flock of white sheep serve in Darwin's argument?
  - Expected answer: `That destroying even the faintly off-coloured individuals is enough to keep a whole population true to a colour`
  - Best window recall against lesson: 0.42

### Concept coverage across the source

- 28/54 concepts anchored to a source chunk (26 unanchored)
- Chunks containing at least one concept: 2/2 (100.0%)
- Concepts per chunk: [21, 7]
- Lessons per chunk: [3, 0]
- Uncovered chunk indexes: none
- Largest share in one chunk: 75.0%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.7334, 0.2666]
- Actual share per chunk: [0.75, 0.25]
- Actual/expected: [1.0227, 0.9376]
- Worst concentration ratio: 1.02

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 99.2%
- Worst chunk: 0 at 98.4%
- Chunks under 50% covered: 0
- Lessons routed per segment: [11, 11]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 63 | 98.4% | 0.980 |
| 1 | 2,747 | 28 | 28 | 100.0% | 0.974 |
