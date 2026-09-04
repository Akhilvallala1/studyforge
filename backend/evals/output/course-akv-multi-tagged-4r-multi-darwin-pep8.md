# Two Foundational Texts: Darwin's Natural Selection and Python's PEP 8

> A paired reading course built from two primary sources: the opening of Chapter IV of Darwin's On the Origin of Species, in which natural selection is defined and defended, and the introductory sections of PEP 8, the style guide for Python code. Each lesson works closely from the text itself, tracing how each document states its central principle and applies it.

## How this was generated

- Eval run: `multi-darwin-pep8` (run id `ad872399b9854c379df47e1cd06ef2ee`)
- Source: text `darwin-origin + pep8-style-guide`, 13,639 characters in 3 chunks
- Provider/model: anthropic / `claude-opus-5`
- 7 LLM calls, 19,988 input tokens, 23,340 output tokens, $0.6834, 299s wall clock
- Prompt fingerprint: outline `51268cb63391`, lesson `1e6fc5164c70`

Quiz answers are shown inline on purpose: this file exists so a human can check whether the answers are actually supported by the source.

---

## Module 1: Darwin: The Principle of Natural Selection

### Lesson 1.1: Defining Natural Selection

**Concepts:** Natural selection defined as the preservation of favourable variations and the rejection of injurious ones, The premises of the argument: variation, strong hereditary tendency, and more individuals born than can survive, Neutral variations as a fluctuating element untouched by selection, illustrated by polymorphic species, Selection depends on variation being supplied: 'unless profitable variations do occur, natural selection can do nothing', The comparison between man's selection and nature's in scope, thoroughness, and time

**Written from source segments:** [0]

#### Lesson content

# Defining Natural Selection

Chapter III of the *Origin* left Darwin with a struggle for existence: everywhere, organisms compete for room, food, and survival. Chapter IV opens by asking what that struggle *does* to the variation he has already documented.

> "How will the struggle for existence, discussed too briefly in the last chapter, act in regard to variation? Can the principle of selection, which we have seen is so potent in the hands of man, apply in nature? I think we shall see that it can act most effectually."

Notice the shape of the question. Darwin is not introducing selection from nowhere; he is *transferring* a principle whose power his readers have already conceded in the hands of breeders, and asking whether nature can wield it too.

## The premises he asks us to hold in mind

Darwin builds the argument out of facts he takes to be already established, and he asks the reader to "bear in mind" each one:

1. **Organisms vary.** Domestic productions vary in "an endless number of strange peculiarities," and those under nature vary too — though, he is careful to say, *in a lesser degree*. Under domestication "the whole organisation becomes in some degree plastic."
2. **Variation is inherited.** "How strong the hereditary tendency is." Without heredity, an advantage would die with the individual who had it.
3. **Relations among living things are intricate.** The "mutual relations of all organic beings to each other and to their physical conditions of life" are "infinitely complex and close-fitting." Because the fit is so tight, even a tiny change can matter.
4. **Useful variations do occur.** Variations useful *to man* have undoubtedly occurred — that is a matter of record in the breeder's yard. So why should variations useful *to the organism itself*, in "the great and complex battle of life," never turn up "in the course of thousands of generations"?
5. **More are born than can survive.** This is the pressure that turns a mere difference into a fate: "remembering that many more individuals are born than can possibly survive."

Put these together and the conclusion follows almost by arithmetic. If many more are born than can live, and if some individuals have "any advantage, however slight, over others," then those individuals "would have the best chance of surviving and of procreating their kind." And the mirror case: "any variation in the least degree injurious would be rigidly destroyed."

## The definition

> "This preservation of favourable variations and the rejection of injurious variations, I call Natural Selection."

Two things are worth pausing on.

**It is a two-sided process.** The name covers both the *preservation* of what helps and the *rejection* of what harms. It is not simply a filter that kills the bad, nor simply a reward for the good; it is both at once.

**The threshold is very low.** "Any advantage, however slight"; "in the least degree injurious." Darwin does not require dramatic monstrosities. Because the relations of organisms are so close-fitting, the smallest difference can "turn the nicely-balanced scale in the struggle for life."

## What selection does *not* touch

This is the part readers most often skip, and it is essential to Darwin's honesty about his own principle:

> "Variations neither useful nor injurious would not be affected by natural selection, and would be left a fluctuating element, as perhaps we see in the species called polymorphic."

Selection acts only where a variation makes a difference to survival. A difference that is neither favourable nor injurious is simply invisible to the process. Darwin does not claim it will be eliminated, nor that it must have some hidden use — he says it is left as a **fluctuating element**, drifting free of the principle. His suggested illustration is the *polymorphic* species: species that persist in several distinct forms at once, without any one form being driven out.

So natural selection is a principle with a stated limit. It explains adaptation; it does not claim to explain every character an organism happens to have.

## The condition on which everything depends

One further remark from the chapter sharpens the definition. Selection is not a creative force that manufactures what is needed; it works only on what is offered to it:

> "unless profitable variations do occur, natural selection can do nothing."

A change in the conditions of life is helpful, Darwin says, not because change is inherently improving but because — acting on the reproductive system — it "causes or increases variability," and so gives "a better chance of profitable variations occurring." Selection is the sorting; variation is the supply.

He adds, though, that no *extreme* variability is required. Man gets great results by adding up "mere individual differences" in a given direction; nature can do the same "far more easily, from having incomparably longer time at her disposal."

## Nature versus the breeder

Having defined the principle, Darwin measures nature's version against man's, and finds man's version feeble on every count:

| Man's selection | Nature's selection |
| --- | --- |
| Acts only on "external and visible characters" | Acts on "every internal organ, on every shade of constitutional difference, on the whole machinery of life" |
| Selects "only for his own good" | Selects "only for that of the being which she tends" |
| Seldom exercises a selected character in a fitting way — feeds long- and short-beaked pigeons the same food, exposes long- and short-woolled sheep to the same climate | "Every selected character is fully exercised by her," and the being is placed under well-suited conditions |
| Protects his productions; does not rigidly destroy inferior animals; does not let the most vigorous males struggle for the females | The slightest difference may turn the balance, and so be preserved |
| Often begins from "some half-monstrous form," or something prominent enough to catch his eye | Works on the slightest difference of structure or constitution |
| "How fleeting are the wishes and efforts of man! how short his time!" | Accumulates "during whole geological periods" |

Hence, Darwin concludes, we should not wonder that nature's productions are "far 'truer' in character than man's," better adapted to complex conditions, and bear "the stamp of far higher workmanship."

## Summary of the argument

- Organisms vary, and variation is strongly inherited.
- Far more individuals are born than can survive.
- Therefore any slight advantage gives the best chance of surviving and reproducing; any slight injury is rigidly destroyed.
- That preservation-and-rejection *is* natural selection.
- Neutral variations escape it entirely, remaining a fluctuating element.
- Selection can do nothing unless profitable variations arise in the first place.

#### Quiz

1. **In Darwin's own words, what is natural selection?**  
   kind: `mcq` | concept: `Natural selection defined as the preservation of favourable variations and the rejection of injurious ones`  
   - [x] The preservation of favourable variations and the rejection of injurious variations
   - [ ] The tendency of organisms to produce the variations their conditions require
   - [ ] The gradual improvement of every character in every inhabitant of a country
   - [ ] The competition of individuals for mates within a single generation
   **Expected answer:** The preservation of favourable variations and the rejection of injurious variations

2. **According to Darwin, what happens to variations that are neither useful nor injurious?**  
   kind: `mcq` | concept: `Neutral variations as a fluctuating element untouched by selection, illustrated by polymorphic species`  
   - [x] They are left a fluctuating element, unaffected by natural selection
   - [ ] They are slowly destroyed, since nature preserves nothing without a use
   - [ ] They are preserved as reserves for future changes of climate
   - [ ] They become useful once the conditions of life alter sufficiently
   **Expected answer:** They are left a fluctuating element, unaffected by natural selection

3. **Which kind of species does Darwin offer as a possible instance of variations that selection does not touch?**  
   kind: `short` | concept: `Neutral variations as a fluctuating element untouched by selection, illustrated by polymorphic species`  
   **Expected answer:** Polymorphic species — species Darwin says perhaps show neutral variations left as a fluctuating element.

4. **Darwin parenthetically reminds the reader that 'many more individuals are born than can possibly survive.' What work does this fact do in his argument?**  
   kind: `mcq` | concept: `The premises of the argument: variation, strong hereditary tendency, and more individuals born than can survive`  
   - [x] It makes a slight advantage decisive, giving its possessor the best chance of surviving and procreating
   - [ ] It shows that variability must be extreme before selection can operate
   - [ ] It proves that species must go extinct whenever the climate of a country changes
   - [ ] It explains why the hereditary tendency in domestic productions is so strong
   **Expected answer:** It makes a slight advantage decisive, giving its possessor the best chance of surviving and procreating

5. **Darwin says a change in the conditions of life is favourable to natural selection. Why?**  
   kind: `mcq` | concept: `Selection depends on variation being supplied: 'unless profitable variations do occur, natural selection can do nothing'`  
   - [x] Because, by acting on the reproductive system, it causes or increases variability and so improves the chance of profitable variations occurring
   - [ ] Because it directly reshapes organisms in the direction their new surroundings demand
   - [ ] Because it removes the barriers that would otherwise let better-adapted forms immigrate
   - [ ] Because it lengthens the time available to nature for accumulating slight differences
   **Expected answer:** Because, by acting on the reproductive system, it causes or increases variability and so improves the chance of profitable variations occurring

6. **Give one way Darwin says man's selection is weaker than nature's.**  
   kind: `short` | concept: `The comparison between man's selection and nature's in scope, thoroughness, and time`  
   **Expected answer:** Any of: man can act only on external and visible characters while nature acts on every internal organ and shade of constitutional difference; man selects for his own good, nature for the good of the being; man does not exercise each selected character fittingly (same food for long- and short-beaked pigeons, same climate for long- and short-woolled sheep); man protects his productions instead of rigidly destroying inferior animals, and does not let the most vigorous males struggle for the females; man often begins from a half-monstrous or conspicuous form; man's time is short compared with whole geological periods.

---

### Lesson 1.2: Circumstances Favourable to Selection: A Country Under Change

**Concepts:** Natural selection as the preservation of favourable and rejection of injurious variations, with neutral variations left fluctuating, How a physical change alters numerical proportions and thereby disturbs the whole web of inhabitants independently of the change itself, Barriers and isolation as preservers of unfilled 'places in the economy of nature', Changed conditions of life increasing variability by acting on the reproductive system, The argument from 'nicely balanced forces' and naturalised species that no great physical change is necessary

**Written from source segments:** [0]

#### Lesson content

# Circumstances Favourable to Selection: A Country Under Change

## Why Darwin needs a thought experiment

Having defined natural selection as "this preservation of favourable variations and the rejection of injurious variations," Darwin faces a harder question: under what conditions does the process actually get traction? He answers not with a survey of data but with an imagined case. "We shall best understand the probable course of natural selection," he writes, "by taking the case of a country undergoing some physical change, for instance, of climate."

Notice first what the definition leaves out. Variations that are *neither* useful nor injurious "would not be affected by natural selection, and would be left a fluctuating element, as perhaps we see in the species called polymorphic." Selection is not a tidying force that grooms every character; it acts only where a difference makes a difference to survival.

## Step one: the numbers shift, and the shift itself does damage

When the climate changes, Darwin says, "the proportional numbers of its inhabitants would almost immediately undergo a change, and some species might become extinct."

The crucial move comes next. Because the inhabitants of a country are bound together in an "intimate and complex manner," any change in the numerical proportions of *some* inhabitants would "most seriously affect many of the others" — and this happens **independently of the change of climate itself**. The cold is not the only enemy. A species that could tolerate the new temperature perfectly well may still be ruined because the insect that pollinated it has grown scarce, or because a competitor has grown abundant. The physical change is a stone dropped into a web; the ripples do most of the work.

## Step two: open borders versus barriers

Darwin now splits the case in two, and the split is the heart of the lesson.

**If the country is open on its borders,** "new forms would certainly immigrate, and this also would seriously disturb the relations of some of the former inhabitants." He reminds the reader "how powerful the influence of a single introduced tree or mammal has been shown to be" — one immigrant species can reorganise a whole community. But note the consequence for selection: the newly available roles are simply taken over by the newcomers. The natives are not modified; they are displaced.

**If the country is an island, or partly surrounded by barriers,** "into which new and better adapted forms could not freely enter," the situation reverses. Now there are "places in the economy of nature which would assuredly be better filled up, if some of the original inhabitants were in some manner modified; for, had the area been open to immigration, these same places would have been seized on by intruders." Barriers do not create the vacancies — the change of conditions does that. What barriers do is *keep the vacancies open* long enough for slow modification of the residents to fill them. In such a case, "every slight modification, which in the course of ages chanced to arise," and which better adapted its possessors to the altered conditions, "would tend to be preserved; and natural selection would thus have free scope for the work of improvement."

So isolation is favourable to selection not because isolated organisms vary more, but because isolation removes the rival supply of ready-made adaptations.

## Step three: changed conditions supply the raw material

The changed climate does a second favour. Darwin appeals back to his first chapter: "a change in the conditions of life, by specially acting on the reproductive system, causes or increases variability." So the very event that opens the vacancies also raises the chance of the variations needed to fill them — "and unless profitable variations do occur, natural selection can do nothing."

But he immediately guards against exaggeration: "Not that, as I believe, any extreme amount of variability is necessary." The analogy with breeders does the work here. Man gets "great results by adding up in any given direction mere individual differences"; so can Nature, "but far more easily, from having incomparably longer time at her disposal." Ordinary small differences, accumulated, suffice.

## The twist: none of it is strictly necessary

Having built the scenario, Darwin dismantles its necessity. He does not believe that "any great physical change, as of climate, or any unusual degree of isolation to check immigration, is actually necessary to produce new and unoccupied places for natural selection to fill up."

His reason: "all the inhabitants of each country are struggling together with nicely balanced forces." Where forces are finely balanced, a tiny push tells. "Extremely slight modifications in the structure or habits of one inhabitant would often give it an advantage over others; and still further modifications of the same kind would often still further increase the advantage." The dramatic climate change was a teaching device — a way of making visible a pressure that is always present.

### The proof from naturalised species

A sceptic might reply that in a stable, long-settled country every native is already as good as it can be, leaving nothing for selection to improve. Darwin's rebuttal is an argument from observation, and it is worth following closely:

1. "No country can be named in which all the native inhabitants are now so perfectly adapted to each other and to the physical conditions under which they live, that none of them could anyhow be improved."
2. The evidence: "in all countries, the natives have been so far conquered by naturalised productions, that they have allowed foreigners to take firm possession of the land."
3. The inference: since "foreigners have thus everywhere beaten some of the natives, we may safely conclude that the natives might have been modified with advantage, so as to have better resisted such intruders."

In other words, the fact that introduced species succeed anywhere is a demonstration that the residents were beatable — that room for improvement existed all along, unfilled. Naturalisation is a natural experiment proving imperfection.

## Summary of the argument's shape

| Element of the scenario | What it contributes |
|---|---|
| Change of climate | Alters numerical proportions; ripples through the web independently of the climate itself |
| Barriers / island | Prevents intruders from seizing the vacant places, leaving them for modified natives |
| Changed conditions | Act on the reproductive system, increasing variability and so the supply of profitable variations |
| "Nicely balanced forces" | Shows the whole apparatus is optional: slight modifications always pay |
| Success of naturalised species | Proves no country's natives are beyond improvement |

The rhetorical strategy is characteristic of Darwin: build the most favourable case first so the mechanism is easy to see, then argue that the mechanism does not depend on those favourable conditions at all.

#### Quiz

1. **In Darwin's scenario, why does a change of climate harm species that could themselves tolerate the new climate?**  
   kind: `mcq` | concept: `How a physical change alters numerical proportions and thereby disturbs the whole web of inhabitants independently of the change itself`  
   - [x] Because the shift in numerical proportions of other inhabitants seriously affects them, quite apart from the climate itself
   - [ ] Because climate change acts directly on the reproductive system and sterilises the majority of individuals
   - [ ] Because tolerant species always reproduce too slowly to keep pace with a changing physical environment
   - [ ] Because barriers around the country prevent tolerant species from migrating to more suitable ground
   **Expected answer:** Because the shift in numerical proportions of other inhabitants seriously affects them, quite apart from the climate itself

2. **According to the lesson, what does an island or a barrier-bounded country contribute to the work of natural selection?**  
   kind: `mcq` | concept: `Barriers and isolation as preservers of unfilled 'places in the economy of nature'`  
   - [x] It keeps vacant places from being seized by immigrants, so modified natives can come to fill them
   - [ ] It concentrates the struggle for existence so that far more individuals are born than can survive
   - [ ] It raises the variability of the residents by cutting them off from crossing with outside forms
   - [ ] It removes the need for any change in the conditions of life before modification can begin
   **Expected answer:** It keeps vacant places from being seized by immigrants, so modified natives can come to fill them

3. **Darwin says a change in the conditions of life causes or increases variability. By acting on what, specifically?**  
   kind: `short` | concept: `Changed conditions of life increasing variability by acting on the reproductive system`  
   **Expected answer:** The reproductive system — a change in conditions, by specially acting on the reproductive system, causes or increases variability, giving a better chance of profitable variations occurring.

4. **What evidence does Darwin offer that no country's native inhabitants are so perfectly adapted that none could be improved?**  
   kind: `mcq` | concept: `The argument from 'nicely balanced forces' and naturalised species that no great physical change is necessary`  
   - [x] In all countries, naturalised foreigners have beaten some of the natives and taken firm possession of the land
   - [ ] In all countries, some species have become extinct following recorded changes of climate
   - [ ] In all countries, domestic productions vary in an endless number of strange peculiarities
   - [ ] In all countries, polymorphic species show characters that fluctuate without being selected
   **Expected answer:** In all countries, naturalised foreigners have beaten some of the natives and taken firm possession of the land

5. **How does natural selection treat variations that are neither useful nor injurious?**  
   kind: `mcq` | concept: `Natural selection as the preservation of favourable and rejection of injurious variations, with neutral variations left fluctuating`  
   - [x] They are unaffected by it and left as a fluctuating element, as perhaps in polymorphic species
   - [ ] They are slowly rejected, since only strictly useful characters can be preserved over ages
   - [ ] They are preserved as reserves, becoming useful whenever the conditions of life alter
   - [ ] They are converted into useful characters once the reproductive system is disturbed
   **Expected answer:** They are unaffected by it and left as a fluctuating element, as perhaps in polymorphic species

6. **Why does Darwin claim that no great physical change and no unusual isolation are actually necessary to open up places for natural selection to fill?**  
   kind: `short` | concept: `The argument from 'nicely balanced forces' and naturalised species that no great physical change is necessary`  
   **Expected answer:** Because all the inhabitants of a country are struggling together with nicely balanced forces, so extremely slight modifications in the structure or habits of one inhabitant would often give it an advantage over others, and further modifications of the same kind would increase that advantage.

---

### Lesson 1.3: Nature's Selection Compared with Man's

**Concepts:** Man selects only external and visible characters, while nature acts on every internal organ and shade of constitutional difference, Man selects for his own good; nature preserves only what benefits the being itself, The breeder fails to exercise selected characters under fitting conditions and shelters inferior individuals from the struggle, The argument from time: fleeting human wishes versus accumulation over whole geological periods, Natural selection can do nothing unless profitable variations occur

**Written from source segments:** [0]

#### Lesson content

# Nature's Selection Compared with Man's

By the middle of Chapter IV, Darwin has already defined natural selection: "This preservation of favourable variations and the rejection of injurious variations, I call Natural Selection." He has also reminded us that variations which are *neither* useful nor injurious would not be affected by selection at all, and "would be left a fluctuating element, as perhaps we see in the species called polymorphic."

Now he does something rhetorically clever. Instead of arguing that natural selection is *like* the breeder's art, he argues that the breeder is a feeble imitation of it. The whole passage is built as a point-by-point comparison in which man loses every point.

## The opening question

> "As man can produce and certainly has produced a great result by his methodical and unconscious means of selection, what may not nature effect?"

The form of the argument matters. Darwin is not asking his reader to believe in a new and untested power. He is asking: given that a *weak* version of this process demonstrably remakes pigeons, dogs and cabbages, what should we expect from a far stronger version?

## Point one: what each can see and act on

Man "can act only on external and visible characters." He selects what catches the eye — plumage, size, the shape of a beak.

Nature "cares nothing for appearances, except in so far as they may be useful to any being." Appearance is not excluded, but it counts only where it *does* something. And nature's reach is total: "She can act on every internal organ, on every shade of constitutional difference, on the whole machinery of life." A slight improvement in a liver, a gut, a tolerance for cold — invisible to a breeder, but not invisible to the struggle for life.

## Point two: for whose benefit

> "Man selects only for his own good; Nature only for that of the being which she tends."

This is a compressed and important claim. A fat, short-legged sheep may be excellent for its owner and poor for itself. Nothing preserved by natural selection can be of that kind, because the only thing that preserves it is the advantage it gives its possessor in surviving and leaving offspring.

## Point three: exercise and fitting conditions

Under nature, "every selected character is fully exercised by her; and the being is placed under well-suited conditions of life." Under domestication, Darwin gives a list of failures, and it is worth reading as a catalogue of the breeder's carelessness:

- Man "keeps the natives of many climates in the same country."
- "He feeds a long and a short beaked pigeon on the same food."
- "He does not exercise a long-backed or long-legged quadruped in any peculiar manner."
- "He exposes sheep with long and short wool to the same climate."

In each case the character is selected but never put to the test of the conditions that would make it advantageous. The breeder produces the beak without producing the food it suits.

## Point four: the rigour of the sifting

Man "does not allow the most vigorous males to struggle for the females." He "does not rigidly destroy all inferior animals, but protects during each varying season, as far as lies in his power, all his productions." The breeder is, in effect, constantly cancelling the selection he is trying to perform, by sheltering exactly the individuals nature would have removed.

## Point five: how small a difference can count

Man "often begins his selection by some half-monstrous form; or at least by some modification prominent enough to catch his eye, or to be plainly useful to him." His threshold of notice is coarse.

"Under nature, the slightest difference of structure or constitution may well turn the nicely-balanced scale in the struggle for life, and so be preserved." Because the inhabitants of a country are "struggling together with nicely balanced forces," differences far too small for a breeder to spot are still large enough to decide who survives.

## Point six: time

> "How fleeting are the wishes and efforts of man! how short his time! and consequently how poor will his products be, compared with those accumulated by nature during whole geological periods."

Darwin has already used this asymmetry earlier in the chapter: no extreme variability is needed, because "as man can certainly produce great results by adding up in any given direction mere individual differences, so could Nature, but far more easily, from having incomparably longer time at her disposal." Notice that the fickleness of human *wishes* is part of the point, not just the shortness of human lives — a fashion in fanciers changes, while the pressures of life do not.

One limit is stated plainly, though: "unless profitable variations do occur, natural selection can do nothing." Time and rigour give nature its advantage, but neither creates the variation on which selection works.

## The conclusion: higher workmanship

All six points converge on a single rhetorical question:

> "Can we wonder, then, that nature's productions should be far 'truer' in character than man's productions; that they should be infinitely better adapted to the most complex conditions of life, and should plainly bear the stamp of far higher workmanship?"

The word *workmanship* is doing deliberate work. Darwin borrows the language of design — of the watchmaker whose skill is read off from the watch — and reassigns it to a process with no designer at all. Adaptation, on this reading, is not evidence of a craftsman; it is what you get when a blind sifting is applied to the whole machinery of life, for the good of the being itself, over whole geological periods.

## A caution about the metaphor

"Nature only for that of the being which she tends" personifies nature as a careful breeder. Darwin's own earlier definition shows what the personification stands in for: nothing tends anything. Favourable variations are preserved because their possessors survive and reproduce; injurious ones are "rigidly destroyed" because their possessors do not. The nurse, the shepherd and the workman are figures of speech for a bookkeeping of births and deaths.

#### Quiz

1. **According to the lesson, why does Darwin say nature's selection can reach characters that a breeder's cannot?**  
   kind: `mcq` | concept: `Man selects only external and visible characters, while nature acts on every internal organ and shade of constitutional difference`  
   - [x] Because nature can act on every internal organ and every shade of constitutional difference, not merely on what is visible
   - [ ] Because nature produces variations directly in the reproductive organs, whereas man must wait for them to appear
   - [ ] Because nature preserves variations that are neither useful nor injurious, which man discards as worthless
   - [ ] Because nature works on whole populations at once, while man can only examine one animal at a time
   **Expected answer:** Because nature can act on every internal organ and every shade of constitutional difference, not merely on what is visible

2. **Darwin lists the breeder feeding a long-beaked and a short-beaked pigeon on the same food, and exposing long- and short-woolled sheep to the same climate. What point are these examples meant to make?**  
   kind: `mcq` | concept: `The breeder fails to exercise selected characters under fitting conditions`  
   - [x] That the breeder selects a character without ever exercising it under the conditions that would suit it
   - [ ] That the breeder unknowingly selects for hardiness rather than for the character he intends
   - [ ] That domestic animals vary less than wild ones because their conditions are kept uniform
   - [ ] That characters selected by man tend to disappear again within a few generations
   **Expected answer:** That the breeder selects a character without ever exercising it under the conditions that would suit it

3. **In Darwin's contrast, whose good does each kind of selection serve?**  
   kind: `short` | concept: `Man selects for his own good; nature preserves only what benefits the being itself`  
   **Expected answer:** Man selects only for his own good; nature selects only for the good of the being which she tends — so nothing can be preserved under nature unless it benefits its possessor.

4. **Which statement best captures the difference in the *size* of difference that each kind of selection can act on?**  
   kind: `mcq` | concept: `Nature can act on the slightest difference of structure or constitution`  
   - [x] Man often starts from a half-monstrous or eye-catching form, while under nature the slightest difference may turn the nicely-balanced scale
   - [ ] Man can detect differences finer than nature can, but lacks the time to accumulate them
   - [ ] Both act only on differences large enough to be plainly useful, but nature repeats the process more often
   - [ ] Nature acts only on large modifications, since slight ones are swamped by the struggle for existence
   **Expected answer:** Man often starts from a half-monstrous or eye-catching form, while under nature the slightest difference may turn the nicely-balanced scale

5. **Darwin grants one strict limit on the power of natural selection even with all of geological time available. What is it?**  
   kind: `short` | concept: `Natural selection can do nothing unless profitable variations occur`  
   **Expected answer:** Unless profitable variations actually occur, natural selection can do nothing — selection preserves and rejects variations but does not create them.

6. **What does Darwin conclude from the whole comparison between nature's selection and man's?**  
   kind: `mcq` | concept: `The argument from time and the resulting higher workmanship of natural productions`  
   - [x] That nature's productions are 'truer' in character and bear the stamp of far higher workmanship than man's
   - [ ] That man's productions, being deliberately aimed at a goal, are more perfectly adapted than nature's
   - [ ] That domestic and natural selection produce results of much the same quality by different routes
   - [ ] That man's short time is compensated for by his methodical and conscious choice of parents
   **Expected answer:** That nature's productions are 'truer' in character and bear the stamp of far higher workmanship than man's

---

### Lesson 1.4: Selection Acting on Characters of Trifling Importance

**Concepts:** Natural selection as continuous, cumulative, and imperceptible scrutiny of every variation, Protective colouring as evidence that apparently trifling characters affect survival, Selection by sight-hunting predators (hawks, the white pigeon warning) and the analogy of culling black-traced lambs from a white flock, Downing's observations on fruit down and flesh colour: advantage is relative to particular enemies, not absolute, Reasoning from differences that matter under cultivation to their greater force in the struggle of nature

**Written from source segments:** [1]

#### Lesson content

# Selection Acting on Characters of Trifling Importance

## The daily and hourly scrutiny

Darwin asks us to picture natural selection not as a rare, dramatic event but as a continuous audit of living things:

> "It may be said that natural selection is daily and hourly scrutinising, throughout the world, every variation, even the slightest; rejecting that which is bad, preserving and adding up all that is good; silently and insensibly working, whenever and wherever opportunity offers, at the improvement of each organic being in relation to its organic and inorganic conditions of life."

Three features of this picture matter.

1. **Its scope is total.** *Every* variation, even the slightest, is examined — not just the obviously useful ones.
2. **Its action is cumulative.** Bad variations are rejected; good ones are "preserved and added up." The adding up is what turns tiny differences into large ones over time.
3. **Its pace is imperceptible.** The work is "silent and insensible." We see nothing of the changes while they are in progress. Only when "the hand of time has marked the long lapse of ages" do we notice anything — and even then our view into past geological ages is so imperfect that all we can say is that the forms of life are now different from what they formerly were.

Note also the standard by which variations are judged: improvement is always **relative to conditions of life**, both organic (enemies, competitors, food) and inorganic (climate, soil). There is no absolute scale of "better."

## The problem: does selection reach trivial characters?

Natural selection can act only through and for the good of each being. So a natural objection arises: surely there are characters too small to matter — a shade of colour, a bit of fuzz on a fruit skin — that selection simply cannot touch. Darwin's answer is that characters "which we are apt to consider as of very trifling importance" may be acted on all the same. Our sense of what is trifling is not a reliable guide to what is trifling *in nature*.

He supports this with two lines of evidence: colouring in animals, and the humble characters of cultivated fruit.

## Evidence I: protective colouring

Darwin lines up cases in which an animal's tint matches its surroundings:

| Organism | Colour | Background |
|---|---|---|
| Leaf-eating insects | green | foliage |
| Bark-feeding insects | mottled-grey | bark |
| Alpine ptarmigan | white in winter | snow |
| Red-grouse | the colour of heather | heather |
| Black-grouse | the colour of peaty earth | peat |

The correspondence is too regular to be accidental; "we must believe that these tints are of service to these birds and insects in preserving them from danger."

The argument is then tightened for the grouse. Grouse, if not destroyed at some period of their lives, would increase in countless numbers — so destruction is happening on a large scale. They are known to suffer largely from birds of prey. And crucially, **hawks are guided by eyesight to their prey**. If the killing agent hunts by sight, then colour is exactly the sort of character that killing can sort on.

The clinching observation is a practical one from human experience: on parts of the Continent, people are warned not to keep white pigeons, as being the most liable to destruction. A conspicuous colour has a measurable cost even in a dovecote. Given all this, Darwin sees no reason to doubt that natural selection might be most effective both in *giving* the proper colour to each kind of grouse and in *keeping* that colour, once acquired, true and constant.

## Evidence II: the flock of white sheep

One might still object that the occasional loss of an oddly coloured animal is too infrequent to matter. Darwin answers with a breeder's analogy: recall "how essential it is in a flock of white sheep to destroy every lamb with the faintest trace of black."

The point is about the power of *consistent* elimination of a slight deviation. A trace of black is a trifling character; yet destroying every lamb that shows one is what keeps a flock white. If a breeder's culling of faint traces has that power, so can nature's.

## Evidence III: down and flesh-colour in fruit

Botanists consider the down on a fruit and the colour of its flesh to be characters of the most trifling importance. Yet Darwin cites the excellent American horticulturist **Downing** for three observations from the United States:

- **Smooth-skinned fruits suffer far more from a beetle, a curculio, than those with down.**
- **Purple plums suffer far more from a certain disease than yellow plums.**
- **Another disease attacks yellow-fleshed peaches far more than those with other coloured flesh.**

Notice that the second and third points pull in opposite directions with respect to colour: yellow is an advantage in plums against one disease, and a liability in peaches against another. There is no universally good colour — only colours that are good against particular enemies. This is the "in relation to its conditions of life" clause made concrete.

Darwin then draws the conclusion by strengthening the case: these differences show up *with all the aids of art* — under cultivation, where the grower props up his trees, controls competitors, and fights off pests. If the differences still make a great difference under such sheltered conditions, then in a state of nature, where trees must struggle with other trees and with a host of enemies, "such differences would effectually settle which variety, whether a smooth or downy, a yellow or purple fleshed fruit, should succeed."

## The shape of the argument

It is worth extracting the reasoning pattern, because Darwin uses it repeatedly:

1. Identify a character everyone agrees is trivial.
2. Show that it nonetheless correlates with a difference in rate of destruction (by hawks, curculios, diseases).
3. Recall that destruction is enormous — grouse would otherwise increase in countless numbers.
4. Conclude that a small, repeated bias in survival, scrutinised daily and hourly and added up over ages, is enough to fix the character.

The conclusion is not that every trivial character *is* selected, but that we are in no position to declare any character beyond selection's reach.

#### Quiz

1. **According to Darwin, why do we see nothing of natural selection's changes while they are in progress?**  
   kind: `mcq` | concept: `Natural selection as continuous, cumulative, and imperceptible scrutiny of every variation`  
   - [x] Because it works silently and insensibly, and only the long lapse of ages makes its effects visible
   - [ ] Because it acts only during rare crises such as famines, which observers seldom witness
   - [ ] Because its effects are confined to internal structures that leave no outward mark
   - [ ] Because the variations it acts on arise faster than they can be recorded by naturalists
   **Expected answer:** Because it works silently and insensibly, and only the long lapse of ages makes its effects visible

2. **In Darwin's list of protective tints, what colour does he assign to the black-grouse's surroundings, and what to the red-grouse's?**  
   kind: `mcq` | concept: `Protective colouring as evidence that apparently trifling characters affect survival`  
   - [x] The black-grouse matches peaty earth; the red-grouse matches heather
   - [ ] The black-grouse matches heather; the red-grouse matches peaty earth
   - [ ] The black-grouse matches bark; the red-grouse matches winter snow
   - [ ] The black-grouse matches winter snow; the red-grouse matches mottled-grey bark
   **Expected answer:** The black-grouse matches peaty earth; the red-grouse matches heather

3. **What role does the warning against keeping white pigeons play in Darwin's argument?**  
   kind: `mcq` | concept: `Selection by sight-hunting predators (hawks, the white pigeon warning) and the analogy of culling black-traced lambs from a white flock`  
   - [x] It gives everyday evidence that conspicuous colour raises the risk of destruction by sight-hunting predators
   - [ ] It shows that domesticated birds lose the protective colouring their wild relatives retain
   - [ ] It shows that breeders unconsciously select for colour without intending any change
   - [ ] It gives evidence that white plumage is physically weaker and more prone to disease
   **Expected answer:** It gives everyday evidence that conspicuous colour raises the risk of destruction by sight-hunting predators

4. **State the three observations Darwin credits to Downing about fruit in the United States.**  
   kind: `short` | concept: `Downing's observations on fruit down and flesh colour: advantage is relative to particular enemies, not absolute`  
   **Expected answer:** Smooth-skinned fruits suffer far more from a beetle, a curculio, than downy ones; purple plums suffer far more from a certain disease than yellow plums; and another disease attacks yellow-fleshed peaches far more than peaches with other coloured flesh.

5. **Darwin notes that the fruit differences make a great difference even 'with all the aids of art.' What does he infer from this?**  
   kind: `mcq` | concept: `Reasoning from differences that matter under cultivation to their greater force in the struggle of nature`  
   - [x] That in nature, where trees struggle with other trees and a host of enemies, such differences would settle which variety succeeds
   - [ ] That cultivation exaggerates differences which would be negligible among wild trees
   - [ ] That art can preserve varieties which natural selection would otherwise have destroyed long ago
   - [ ] That the same varieties would prosper in nature, since enemies are fewer outside orchards
   **Expected answer:** That in nature, where trees struggle with other trees and a host of enemies, such differences would settle which variety succeeds

6. **What point does the flock of white sheep illustrate?**  
   kind: `mcq` | concept: `Selection by sight-hunting predators (hawks, the white pigeon warning) and the analogy of culling black-traced lambs from a white flock`  
   - [x] That consistently destroying every individual with the faintest deviation is enough to keep a trifling character constant
   - [ ] That a character can spread through a flock even when no individuals are ever destroyed
   - [ ] That sheep breeders select for wool quality rather than colour, so colour drifts at random
   - [ ] That black lambs are hardier than white ones and would prevail if left unchecked
   **Expected answer:** That consistently destroying every individual with the faintest deviation is enough to keep a trifling character constant

---

## Module 2: PEP 8: A Style Guide for Python Code

### Lesson 2.1: What PEP 8 Is and What It Covers

**Concepts:** PEP 8's status, authorship and Process type, The scope of PEP 8: standard library Python code, with C code and docstrings delegated elsewhere, Origin in Guido's style essay plus Barry's guide, shared with PEP 257, Readability and the precedence of project-specific guides, The structure of the guide: layout, whitespace, comments, naming, programming recommendations, annotations

**Written from source segments:** [2]

#### Lesson content

# What PEP 8 Is and What It Covers

## The document's identity

PEP 8 is titled **"Style Guide for Python Code"**. Its header tells you a lot before you read a single guideline:

| Field | Value |
|---|---|
| Author | Guido van Rossum, Barry Warsaw, Alyssa Coghlan |
| Status | Active |
| Type | Process |
| Created | 05-Jul-2001 |
| Post-History | 05-Jul-2001, 01-Aug-2013 |

Two of those fields are worth pausing on. The type is **Process**, not Standards Track — PEP 8 does not change the Python language, it describes how people working on Python should do something. And the status is **Active** rather than Final: as the introduction says, "This style guide evolves over time as additional conventions are identified and past conventions are rendered obsolete by changes in the language itself." A document about a moving language cannot itself stand still.

## What it is a style guide *for*

The opening sentence is narrower than most people remember:

> This document gives coding conventions for the Python code comprising the standard library in the main Python distribution.

So its home territory is the standard library. It has become the de facto style guide for Python code everywhere, but its stated audience is the code shipped with CPython itself. That framing matters when PEP 8 later declines to legislate on some question: it is writing rules for one particular (very large) codebase, not for the universe.

It also makes the limits of its authority explicit:

> Many projects have their own coding style guidelines. In the event of any conflicts, such project-specific guides take precedence for that project.

So PEP 8 is not the top of the hierarchy in your own project — your project's guide is.

## Its neighbours

PEP 8 deliberately does not cover everything about writing Python-related code. It points to two sibling documents:

- **A companion informational PEP** describing style guidelines for the **C code in the C implementation of Python**. PEP 8 is about the Python-language half of CPython; the C half has its own guide.
- **PEP 257 (Docstring Conventions)**, which handles docstrings. PEP 8 has a short "Documentation Strings" subsection, but the detailed conventions live in PEP 257.

The reason PEP 8 and PEP 257 read like siblings is that they are: both "were adapted from Guido's original Python Style Guide essay, with some additions from Barry's style guide." One essay was split and grown into two PEPs.

## The guiding motive

Immediately after the introduction comes a section with a borrowed title, "A Foolish Consistency is the Hobgoblin of Little Minds." It states the insight the whole document rests on:

> One of Guido's key insights is that code is read much more often than it is written.

The guidelines exist to improve **readability** and to make code consistent across the wide spectrum of Python code — echoing PEP 20's "Readability counts". The section then ranks consistency: consistency with this style guide is important, consistency within a project is more important, and consistency within one module or function is more important still. The rules are means to an end, not the end.

## The table of contents as a map

Reading the contents list is the fastest way to see what the guide considers a style question at all:

1. **Introduction** and **A Foolish Consistency is the Hobgoblin of Little Minds** — scope, and when to ignore the rules.
2. **Code Lay-out** — the largest mechanical section: Indentation, Tabs or Spaces?, Maximum Line Length, Should a Line Break Before or After a Binary Operator?, Blank Lines, Source File Encoding, Imports, Module Level Dunder Names.
3. **String Quotes**.
4. **Whitespace in Expressions and Statements** — split into Pet Peeves and Other Recommendations.
5. **When to Use Trailing Commas**.
6. **Comments** — Block Comments, Inline Comments, Documentation Strings.
7. **Naming Conventions** — an Overriding Principle, then a *descriptive* catalogue of naming styles, then *prescriptive* conventions for packages and modules, classes, type variables, exceptions, globals, functions and variables, arguments, methods and instance variables, constants, plus Designing for Inheritance; then Public and Internal Interfaces.
8. **Programming Recommendations** — including Function Annotations and Variable Annotations.
9. **References** and **Copyright**.

Notice the shape of that list. It runs from the purely visual (where to put spaces and line breaks), through the semi-semantic (what to call things), to the genuinely behavioural ("Programming Recommendations" advises on how to write code, not just how to format it). Notice too the distinction drawn inside Naming Conventions between *descriptive* — here are the naming styles that exist and what to call them — and *prescriptive* — here is which style to use where. And annotations get their own subsections at the end, a reminder that the guide grew to cover language features added long after 2001.

## Takeaways

- PEP 8 is an Active, Process-type PEP from 2001, authored by van Rossum, Warsaw and Coghlan, still evolving.
- Its stated scope is the Python code of the standard library; C code and docstrings are delegated to a companion C style PEP and to PEP 257.
- Its justification is that code is read far more often than written, and a project's own guide outranks it.
- Its coverage runs from layout and whitespace through comments and naming to programming recommendations and annotations.

#### Quiz

1. **According to PEP 8's introduction, what body of code does the document give coding conventions for?**  
   kind: `mcq` | concept: `The scope of PEP 8: standard library Python code, with C code and docstrings delegated elsewhere`  
   - [x] The Python code comprising the standard library in the main Python distribution
   - [ ] All Python code published on the Python Package Index
   - [ ] Every file in the CPython source tree, both Python and C
   - [ ] Teaching material and example code used in Python tutorials
   **Expected answer:** The Python code comprising the standard library in the main Python distribution

2. **Which PEP does PEP 8 identify as covering docstring conventions, having been adapted from the same original essay?**  
   kind: `short` | concept: `Origin in Guido's style essay plus Barry's guide, shared with PEP 257`  
   **Expected answer:** PEP 257 (Docstring Conventions)

3. **What does PEP 8 say happens when its advice conflicts with a project's own coding style guidelines?**  
   kind: `mcq` | concept: `Readability and the precedence of project-specific guides`  
   - [x] The project-specific guide takes precedence for that project
   - [ ] PEP 8 takes precedence, since it is an Active Process PEP
   - [ ] The conflict must be resolved by filing an amendment to PEP 8
   - [ ] Whichever rule produces shorter lines should be followed
   **Expected answer:** The project-specific guide takes precedence for that project

4. **PEP 8's status is 'Active' and its type is 'Process'. Which reading of these fields matches what the document says about itself?**  
   kind: `mcq` | concept: `PEP 8's status, authorship and Process type`  
   - [x] It is a still-evolving document about how work on Python should be done, rather than a change to the language
   - [ ] It is a finished specification that adds new syntax rules enforced by the interpreter
   - [ ] It is a draft awaiting approval before the conventions become binding
   - [ ] It is a historical record of conventions that have since been superseded
   **Expected answer:** It is a still-evolving document about how work on Python should be done, rather than a change to the language

5. **Which of these topics does the source material list as belonging to PEP 8's 'Code Lay-out' section?**  
   kind: `mcq` | concept: `The structure of the guide: layout, whitespace, comments, naming, programming recommendations, annotations`  
   - [x] Whether a line should break before or after a binary operator
   - [ ] Whether to use single or double quotes for strings
   - [ ] Which naming style to use for type variables
   - [ ] When it is appropriate to use a trailing comma
   **Expected answer:** Whether a line should break before or after a binary operator

6. **What insight of Guido's does PEP 8 name as the reason its readability guidelines matter?**  
   kind: `short` | concept: `Readability and the precedence of project-specific guides`  
   **Expected answer:** That code is read much more often than it is written

---

### Lesson 2.2: A Foolish Consistency Is the Hobgoblin of Little Minds

**Concepts:** Code is read more often than it is written, so readability is the governing goal, The layered priority of consistency: module or function, then project, then style guide, Project-specific style guides take precedence over PEP 8 in case of conflict, PEP 8's scope and provenance: standard library conventions adapted from Guido's essay, The style guide evolves as conventions are identified or made obsolete by language changes

**Written from source segments:** [2]

#### Lesson content

# A Foolish Consistency Is the Hobgoblin of Little Minds

PEP 8 opens with a title borrowed from Emerson, and it is not decoration. Before the guide tells you anything about indentation, line length, or naming, it tells you *why* any of it matters and *when* it can be set aside. This lesson is about that governing principle.

## The insight underneath everything

> One of Guido's key insights is that code is read much more often than it is written.

Every rule that follows in PEP 8 is downstream of this one observation. You type a function once. You, your reviewer, the person debugging it at 2 a.m. three years from now, and the tooling that greps through it will all *read* it many times over. So the guidelines exist "to improve the readability of code and make it consistent across the wide spectrum of Python code."

PEP 8 backs this up by citing PEP 20, the *Zen of Python*: **"Readability counts."** That is the whole justification. A style rule that made code harder to read would be self-defeating.

A quick illustration of what "written once, read many times" buys you:

```python
# Written fast, read slowly
def p(l, t): return [x for x in l if x[1] > t]

# Written slightly slower, read instantly
def filter_above_threshold(readings, threshold):
    return [r for r in readings if r.value > threshold]
```

Both cost you a few seconds to type. Only one costs you nothing to understand later.

## The scope of the document

PEP 8 is explicit about what it covers: "coding conventions for the Python code comprising the standard library in the main Python distribution." There is a companion informational PEP for the *C* code in the C implementation of Python, and PEP 257 covers docstring conventions. Both PEP 8 and PEP 257 were adapted from Guido's original Python Style Guide essay, with additions from Barry Warsaw's style guide.

So, strictly speaking, this is the standard library's house style. It became the de facto style for the wider Python world because it is good and because it is public — not because it was ever imposed on your project.

## Consistency in layers

Here is the part people quote most:

- Consistency with **this style guide** is important.
- Consistency within a **project** is more important.
- Consistency within **one module or function** is the most important.

Read that as a widening set of priorities, with the *narrowest* scope winning. If you are editing a module that has used a particular convention throughout, matching that module beats matching the rest of the project; matching the project beats matching PEP 8 in the abstract. The reason is exactly the readability principle: a reader working inside one file is jarred most by inconsistency inside that file.

In practice this means: when you land in unfamiliar code, read before you reformat. A PEP 8-correct edit dropped into a module that does things another way can make the module *less* readable than leaving it alone, or than following local custom.

## Project guidelines take precedence

The introduction says it directly:

> Many projects have their own coding style guidelines. In the event of any conflicts, such project-specific guides take precedence for that project.

This is not grudging permission — it is the stated rule. If your employer's guide says something different from PEP 8, your employer's guide wins *for that project*. PEP 8 does not claim authority over code it does not govern.

## The guide is a moving target

One more piece of humility from the introduction:

> This style guide evolves over time as additional conventions are identified and past conventions are rendered obsolete by changes in the language itself.

Two distinct forces are named there. New conventions get *identified* as the community works out what reads well. And old conventions become *obsolete* when the language itself changes — a recommendation written for a Python that no longer exists stops making sense.

Put together with the layered consistency rule and the precedence of project guides, the message is clear: PEP 8 is a well-argued default, not a law. Its authority rests entirely on whether following it makes code easier to read.

## Takeaways

1. Optimise for the reader, because reading happens far more often than writing.
2. "Readability counts" (PEP 20) is the tie-breaker for any style question.
3. Consistency is layered: module/function beats project beats the style guide.
4. Project-specific guides win over PEP 8 within their project.
5. The guide changes as conventions are found and as the language moves on.

#### Quiz

1. **A project you have joined documents a style rule that directly contradicts PEP 8. According to PEP 8's introduction, what should you do?**  
   kind: `mcq` | concept: `Project-specific style guides take precedence over PEP 8 in case of conflict`  
   - [x] Follow the project's guideline, since project-specific guides take precedence for that project
   - [ ] Follow PEP 8, since it defines the conventions for the main Python distribution
   - [ ] Follow whichever rule produces fewer changes to the existing files
   - [ ] Follow PEP 8 for new files and the project's rule only when editing old ones
   **Expected answer:** Follow the project's guideline, since project-specific guides take precedence for that project

2. **In one sentence, state the insight of Guido's that PEP 8 identifies as the reason its guidelines exist.**  
   kind: `short` | concept: `Code is read more often than it is written, so readability is the governing goal`  
   **Expected answer:** That code is read much more often than it is written, so the guidelines aim to improve readability.

3. **Which ordering of consistency does PEP 8 give, from most important to least?**  
   kind: `mcq` | concept: `The layered priority of consistency: module or function, then project, then style guide`  
   - [x] Within one module or function, then within a project, then with the style guide
   - [ ] With the style guide, then within a project, then within one module or function
   - [ ] Within a project, then within one module or function, then with the style guide
   - [ ] With the style guide, then within one module or function, then within a project
   **Expected answer:** Within one module or function, then within a project, then with the style guide

4. **PEP 8 says the style guide evolves over time. Which pair of reasons does it give?**  
   kind: `mcq` | concept: `The style guide evolves as conventions are identified or made obsolete by language changes`  
   - [x] Additional conventions are identified, and past conventions are made obsolete by changes in the language itself
   - [ ] New authors join the PEP, and older authors withdraw their earlier recommendations
   - [ ] Large projects publish their own guides, and the most popular of those rules are absorbed
   - [ ] Automated formatting tools change, and the guide is updated to match what they produce
   **Expected answer:** Additional conventions are identified, and past conventions are made obsolete by changes in the language itself

5. **Which document does PEP 8 quote for the line "Readability counts"?**  
   kind: `short` | concept: `Code is read more often than it is written, so readability is the governing goal`  
   **Expected answer:** PEP 20 (the Zen of Python).

6. **What body of code does PEP 8 state that it gives coding conventions for?**  
   kind: `mcq` | concept: `PEP 8's scope and provenance: standard library conventions adapted from Guido's essay`  
   - [x] The Python code comprising the standard library in the main Python distribution
   - [ ] All Python code published on the Python Package Index
   - [ ] Both the Python and the C code in the CPython implementation
   - [ ] Any Python code intended to be read by more than one developer
   **Expected answer:** The Python code comprising the standard library in the main Python distribution

---
