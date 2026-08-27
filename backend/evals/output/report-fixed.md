# StudyForge generation eval

## Headline metrics

| Metric | pep8-url | prose-text |
|---|---|---|
| Lessons | 13 | 6 |
| Quiz items | 78 | 34 |
| Structure problems | 10 | 0 |
| Strict JSON first try | 1 | 0.8571 |
| Hard parse failures | 0 | 0 |
| Grounded, all items (old metric) | 0.2692 | 0.0882 |
| Grounded, extractive items only | 0.2857 | 0.1034 |
| Ungrounded items, all | 17 | 19 |
| Ungrounded extractive items | 14 | 15 |
| Hallucination candidates | 0 | 1 |
| Mean grounding recall | 0.6524 | 0.4885 |
| Answerable from lesson | 0.4487 | 0.1176 |
| Unanswerable items | 6 | 13 |
| Giveaway MCQs | 6 | 1 |
| Source chunks covered | 1 | 1 |
| Largest single-chunk share (old metric) | 0.2157 | 0.7143 |
| Concentration vs chunk length | 1.6511 | 1.0716 |
| Source recall, mean chunk | 0.7908 | 0.9453 |
| Source recall, worst chunk | 0.7045 | 0.8906 |
| Cost USD | 1.587 | 0.7972 |
| Wall clock s | 583.58 | 372.52 |

## pep8-url

Source: url `https://peps.python.org/pep-0008/`, 48,597 chars, 8 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 13 | 13 | 13 | 0 | 13 | 13 | 0 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 13 | 52,053 | 47,257 | $1.4417 | 43.1 | 53.0 |
| outline | 1 | 18,817 | 2,050 | $0.1453 | 22.8 | 22.8 |

### Structure

- 4 modules, 13 lessons, 78 quiz items
- Quiz items per lesson: [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6]
- Concepts per lesson: [4, 5, 5, 5, 5, 5, 4, 5, 5, 4, 5, 5, 4]
- Lesson content chars: mean 5625, min 2998
- Item kinds: {'mcq': 52, 'short': 26}
- Problems: {'duplicate_mcq_options': 4, 'empty_concept': 6}

  - `duplicate_mcq_options` at module 2 / lesson 1 / item 1: ['`ham[lower+offset : upper+offset]`', '`ham[lower + offset:upper + offset]`', '`ham[ lower+offset : upper+offset ]`', '`ham[lower+offset :upper+offset]`']
  - `duplicate_mcq_options` at module 2 / lesson 2 / item 1: ["FILES = ('setup.cfg',)", "FILES = 'setup.cfg',", "FILES = ('setup.cfg')", "FILES = ['setup.cfg',]"]
  - `duplicate_mcq_options` at module 3 / lesson 1 / item 6: ['`HTTPServerError`', '`HttpServerError`', '`httpServerError`', '`HTTP_Server_Error`']
  - `empty_concept` at module 3 / lesson 2 / item 1: Which single-character variable names does PEP 8 tell you never to use, and why?
  - `empty_concept` at module 3 / lesson 2 / item 2: You are declaring a contravariant type variable for key types. Which name best follows PEP 8?
  - `empty_concept` at module 3 / lesson 2 / item 3: A function argument would naturally be called `class`, which is a reserved keyword. What does PEP 8 recommend?
  - `empty_concept` at module 3 / lesson 2 / item 4: Inside `class Foo`, an attribute is named `__a`. What does Python's name mangling do, and what does that mean for access from outside?
  - `empty_concept` at module 3 / lesson 2 / item 5: Which naming choice conforms to PEP 8's prescriptive rules?
  - `empty_concept` at module 3 / lesson 2 / item 6: An extension module written in C is wrapped by a higher-level Python module offering a more object-oriented interface. How should the C module be named?
  - `duplicate_mcq_options` at module 4 / lesson 3 / item 1: ["`label: str = '<unknown>'`", "`label : str = '<unknown>'`", "`label:str = '<unknown>'`", "`label: str='<unknown>'`"]

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 21/78 answers supported (exact or strong) = 26.9%
- Tiers: {'exact': 7, 'strong': 14, 'partial': 40, 'unsupported': 17}
- Mean best-window recall: 0.652
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 1

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 70, 'odd_one_out': 1, 'restatement': 7, 'trivial': 0}
- Extractive items supported: 20/70 = 28.6% (mean window recall 0.663)
- Odd-one-out items: mean share of their distractors found in the source = 100.0%
- Restatement items: mean share of answer words absent from the source = 5.5%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 0

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 3** (Why a Style Guide? Consistency and Its Limits)
  - Q: State the insight of Guido's that PEP 8 offers as the underlying justification for its readability rules.
  - Expected answer: `That code is read much more often than it is written, so effort spent making it readable pays off repeatedly.`
  - Best window recall 0.42, global token recall 0.67
  - Closest source text: `have their own coding style guidelines in the event of any conflicts such project specific guides take precedence for that project a foolish consistency is the hobgoblin of little minds one of guido s key insights is that code is read much more often than it is written`

- **module 1 / lesson 1 / item 6** (Why a Style Guide? Consistency and Its Limits)
  - Q: PEP 8 singles out one thing you must never do merely to comply with the PEP. What is it?
  - Expected answer: `Break backwards compatibility. Style compliance never justifies breaking existing users of the code.`
  - Best window recall 0.36, global token recall 0.73
  - Closest source text: `important however know when to be inconsistent sometimes style guide recommendations just aren t applicable when in doubt use your best judgment look at other examples and decide what looks best and don t hesitate to ask in particular do not break backwards compatibility`

- **module 1 / lesson 2 / item 1** (Indentation and Continuation Lines)
  - Q: Which requirement applies specifically to a hanging indent?
  - Expected answer: `No arguments may appear on the first line, and the wrapped lines must be indented further to mark themselves as continuations`
  - Best window recall 0.40, global token recall 0.70
  - Closest source text: `continuation lines should align wrapped elements either vertically using python s implicit line joining inside parentheses brackets and braces or using a hanging indent 1 when using a hanging indent the following should be considered there should be no arguments`

- **module 1 / lesson 2 / item 2** (Indentation and Continuation Lines)
  - Q: Why does PEP 8 suggest an extra indentation level for the parameters of a `def` that uses a hanging indent?
  - Expected answer: `Because a plain 4-space indent would be indistinguishable from the function's own body`
  - Best window recall 0.44, global token recall 0.89
  - Closest source text: `long enough to require that it be written across multiple lines it s worth noting that the combination of a two character keyword i e if plus a single space plus an opening parenthesis creates a natural 4 space indent`

- **module 2 / lesson 1 / item 3** (Whitespace Pet Peeves and Operator Spacing)
  - Q: What does PEP 8 say about choosing between single and double quotes for ordinary strings?
  - Expected answer: `It states no preference; choose a rule and apply it consistently, switching quote styles only to avoid backslash-escaping a quote inside the string.`
  - Best window recall 0.29, global token recall 0.71
  - Closest source text: `version 0 1 author cardinal biggles import os import sys string quotes in python single quoted strings and double quoted strings are the same this pep does not make a recommendation for this pick a rule and stick to it when a string contains single or double quote characters however use the other on`

- **module 2 / lesson 1 / item 5** (Whitespace Pet Peeves and Operator Spacing)
  - Q: According to the lesson, when may you legitimately use more than the uniform single space around a binary operator to show grouping, as in `hypot2 = x*x + y*y`?
  - Expected answer: `Never — you must never exceed one space; the grouping is shown by removing spaces around the higher-priority operators instead.`
  - Best window recall 0.46, global token recall 0.69
  - Closest source text: `single space on either side assignment augmented assignment etc comparisons lt gt lt gt in not in is is not booleans and or not if operators with different priorities are used consider adding whitespace around the operators with the lowest priority ies use your own judgment however never use more th`

- **module 2 / lesson 2 / item 2** (Trailing Commas and Writing Good Comments)
  - Q: Why does PEP 8 recommend a trailing comma after the final item when each item is on its own line?
  - Expected answer: `Adding a later item then changes only one line in a version-control diff`
  - Best window recall 0.44, global token recall 0.78
  - Closest source text: `often helpful when a version control system is used when a list of values arguments or imported items is expected to be extended over time the pattern is to put each value etc on a line by itself always adding`

- **module 2 / lesson 2 / item 4** (Trailing Commas and Writing Good Comments)
  - Q: A comment begins with the name of a variable called `retries`. What does PEP 8 say about capitalization here?
  - Expected answer: `Leave it as `retries`, because the case of an identifier must never be altered`
  - Best window recall 0.43, global token recall 0.57
  - Closest source text: `comments always make a priority of keeping the comments up to date when the code changes comments should be complete sentences the first word should be capitalized unless it is an identifier that begins with a lower case letter never`

- **module 3 / lesson 1 / item 2** (Naming Styles and Underscore Conventions)
  - Q: Why does PEP 8 call `_single_leading_underscore` a *weak* internal-use indicator?
  - Expected answer: `Because the only real behavior it triggers is exclusion from `from M import *`; an explicit import of the name still succeeds`
  - Best window recall 0.27, global token recall 0.73
  - Closest source text: `object and function names are prefixed with a module name in addition the following special forms using leading or trailing underscores are recognized these can generally be combined with any case convention single leading underscore weak internal use indicator e g from m import`

- **module 3 / lesson 1 / item 5** (Naming Styles and Underscore Conventions)
  - Q: State the overriding principle PEP 8 gives for names that are visible as public parts of an API.
  - Expected answer: `They should follow conventions that reflect usage rather than implementation — the name should describe what a caller does with the thing, not how it happens to be built internally.`
  - Best window recall 0.46, global token recall 0.85
  - Closest source text: `standards new modules and packages including third party frameworks should be written to these standards but where an existing library has a different style internal consistency is preferred overriding principle names that are visible to the user as public parts of the api should follow conventions `

- **module 4 / lesson 2 / item 1** (Idiomatic Statements and Return Values)
  - Q: Why does PEP 8 prefer `with conn.begin_transaction():` over `with conn:` when the connection's `__enter__`/`__exit__` manage a transaction?
  - Expected answer: `A named method makes it explicit that the context manager does something beyond closing the connection, which `with conn:` hides`
  - Best window recall 0.42, global token recall 0.75
  - Closest source text: `resources correct with conn begin transaction do stuff in transaction conn wrong with conn do stuff in transaction conn the latter example doesn t provide any information to indicate that the enter and exit methods are doing something other than closing the connection after a transaction being expli`

- **module 4 / lesson 2 / item 3** (Idiomatic Statements and Return Values)
  - Q: Rewrite `def bar(x):` so it follows PEP 8's rule on consistent returns, given that it currently does a bare `return` when `x < 0` and `return math.sqrt(x)` otherwise. State the change and the reason in one or two sentences.
  - Expected answer: `Change the bare `return` to `return None`, so that every return statement in the function returns an expression. Since one return carries a value, the value-less return must state `None` explicitly, making it clear the author intended that branch rather than forgetting a case.`
  - Best window recall 0.42, global token recall 0.83
  - Closest source text: `than acquire and release resources correct with conn begin transaction do stuff in transaction conn wrong with conn do stuff in transaction conn the latter example doesn t provide any information to indicate that the enter and exit methods are doing something other than closing the connection after `

- **module 4 / lesson 2 / item 5** (Idiomatic Statements and Return Values)
  - Q: PEP 8 calls `if greeting is True:` *worse* than `if greeting == True:`. What is the reasoning?
  - Expected answer: ``is True` requires the exact `True` singleton, so other truthy values such as `1` or a non-empty list fail the test`
  - Best window recall 0.25, global token recall 0.75
  - Closest source text: `is another thing do something also see the discussion of whether to break before or after binary operators below the closing brace bracket parenthesis on multiline constructs may either line up under the first non whitespace character of the last line of list as in my list 1`

- **module 4 / lesson 2 / item 6** (Idiomatic Statements and Return Values)
  - Q: A reviewer sees `if type(obj) is type(1):` and `if foo[:3] == 'bar':`. Which replacements does PEP 8 recommend, and what is the practical advantage of each?
  - Expected answer: `Use `isinstance(obj, int)` instead of the type comparison — it reads better and also accepts subclasses, which direct type identity rejects. Use `foo.startswith('bar')` instead of the slice — it is cleaner and less error prone, since the slice length can drift out of sync with the literal being compared.`
  - Best window recall 0.46, global token recall 0.75
  - Closest source text: `def bar x if x lt 0 return return math sqrt x use startswith and endswith instead of string slicing to check for prefixes or suffixes startswith and endswith are cleaner and less error prone correct if foo startswith bar wrong if foo 3 bar object type comparisons should always use isinstance instead`

### Answerability (answer vs its own lesson content)

- 35/78 answerable from the lesson alone = 44.9%
- Tiers: {'exact': 8, 'strong': 27, 'partial': 37, 'unsupported': 6}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 6

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 5** (Why a Style Guide? Consistency and Its Limits)
  - Q: Which of these is NOT one of the reasons PEP 8 gives for ignoring a particular guideline?
  - Expected answer: `The developer finds the recommended form personally unattractive`
  - Best window recall against lesson: 0.17

- **module 2 / lesson 1 / item 3** (Whitespace Pet Peeves and Operator Spacing)
  - Q: What does PEP 8 say about choosing between single and double quotes for ordinary strings?
  - Expected answer: `It states no preference; choose a rule and apply it consistently, switching quote styles only to avoid backslash-escaping a quote inside the string.`
  - Best window recall against lesson: 0.21

- **module 2 / lesson 2 / item 4** (Trailing Commas and Writing Good Comments)
  - Q: A comment begins with the name of a variable called `retries`. What does PEP 8 say about capitalization here?
  - Expected answer: `Leave it as `retries`, because the case of an identifier must never be altered`
  - Best window recall against lesson: 0.43

- **module 3 / lesson 1 / item 2** (Naming Styles and Underscore Conventions)
  - Q: Why does PEP 8 call `_single_leading_underscore` a *weak* internal-use indicator?
  - Expected answer: `Because the only real behavior it triggers is exclusion from `from M import *`; an explicit import of the name still succeeds`
  - Best window recall against lesson: 0.45

- **module 3 / lesson 2 / item 6** (Prescriptive Naming Rules by Kind of Name)
  - Q: An extension module written in C is wrapped by a higher-level Python module offering a more object-oriented interface. How should the C module be named?
  - Expected answer: `With a leading underscore, e.g. `_socket`, while the Python wrapper keeps the plain name`
  - Best window recall against lesson: 0.45

- **module 4 / lesson 2 / item 1** (Idiomatic Statements and Return Values)
  - Q: Why does PEP 8 prefer `with conn.begin_transaction():` over `with conn:` when the connection's `__enter__`/`__exit__` manage a transaction?
  - Expected answer: `A named method makes it explicit that the context manager does something beyond closing the connection, which `with conn:` hides`
  - Best window recall against lesson: 0.42

### Concept coverage across the source

- 51/61 concepts anchored to a source chunk (10 unanchored)
- Chunks containing at least one concept: 8/8 (100.0%)
- Concepts per chunk: [11, 7, 6, 4, 5, 6, 5, 7]
- Lessons per chunk: [2, 0, 1, 1, 0, 1, 0, 1]
- Uncovered chunk indexes: none
- Largest share in one chunk: 21.6%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.1306, 0.1683, 0.1213, 0.0711, 0.0958, 0.1691, 0.1229, 0.1208]
- Actual share per chunk: [0.2157, 0.1373, 0.1176, 0.0784, 0.098, 0.1176, 0.098, 0.1373]
- Actual/expected: [1.6511, 0.8155, 0.9695, 1.1029, 1.0231, 0.6956, 0.798, 1.1362]
- Worst concentration ratio: 1.65

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 79.1%
- Worst chunk: 6 at 70.5%
- Chunks under 50% covered: 0
- Lessons routed per segment: [2, 3, 2, 2, 3, 3, 2, 2]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 6,500 | 33 | 27 | 81.8% | 0.809 |
| 1 | 8,000 | 64 | 54 | 84.4% | 0.806 |
| 2 | 6,082 | 24 | 17 | 70.8% | 0.747 |
| 3 | 3,319 | 22 | 17 | 77.3% | 0.800 |
| 4 | 4,720 | 29 | 27 | 93.1% | 0.848 |
| 5 | 8,000 | 61 | 46 | 75.4% | 0.717 |
| 6 | 5,848 | 44 | 31 | 70.5% | 0.748 |
| 7 | 6,118 | 34 | 27 | 79.4% | 0.756 |

## prose-text

Source: text `darwin-origin-excerpt`, 10,637 chars, 2 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 6 | 6 | 0 | 0 | 6 | 6 | 0 |
| outline | 1 | 0 | 1 | 1 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 6 | 23,490 | 25,246 | $0.7486 | 59.4 | 65.4 |
| outline | 1 | 3,586 | 1,227 | $0.0486 | 16.2 | 16.2 |

### Structure

- 2 modules, 6 lessons, 34 quiz items
- Quiz items per lesson: [6, 5, 6, 6, 6, 5]
- Concepts per lesson: [5, 5, 5, 5, 5, 5]
- Lesson content chars: mean 7357, min 6426
- Item kinds: {'mcq': 23, 'short': 11}
- Problems: none

### Grounding (answer vs source document)

**Uncorrected, every non-trivial answer scored by token overlap:**

- 3/34 answers supported (exact or strong) = 8.8%
- Tiers: {'exact': 1, 'strong': 2, 'partial': 12, 'unsupported': 19}
- Mean best-window recall: 0.489
- Trivial answers excluded from scoring: 0
- Low-signal answers (under 2 content tokens): 0

**Corrected.** Odd-one-out MCQs have deliberately false answers and restatement questions ask for a paraphrase, so neither can be scored by looking for its answer in the source. They are split out and scored on their own terms:

- Item classes: {'extractive': 29, 'odd_one_out': 0, 'restatement': 5, 'trivial': 0}
- Extractive items supported: 3/29 = 10.3% (mean window recall 0.507)
- Odd-one-out items: mean share of their distractors found in the source = 0.0%
- Restatement items: mean share of answer words absent from the source = 35.0%
- Hallucination candidates (low window recall AND over 60% novel vocabulary): 1

  - **module 2 / lesson 2 / item 2** (extractive) novel 64%: Everyday practical experience that colour alone measurably alters how often an animal is taken by predators

#### Ungrounded extractive items

- **module 1 / lesson 1 / item 4** (From the Struggle for Existence to a Principle of Selection)
  - Q: Darwin writes that 'unless profitable variations do occur, natural selection can do nothing.' What does this show about how he conceives selection?
  - Expected answer: `Selection sifts variation that arises independently; it does not itself generate novelty`
  - Best window recall 0.25, global token recall 0.50
  - Closest source text: `natural selection through divergence of character and extinction on the descendants from a common parent explains the grouping of all organic beings how will the struggle for existence discussed too briefly in the last chapter act in regard to variation`

- **module 1 / lesson 1 / item 6** (From the Struggle for Existence to a Principle of Selection)
  - Q: What role does the premise about the 'infinitely complex and close-fitting' mutual relations of organic beings play in the argument?
  - Expected answer: `It makes it plausible that some variation will be useful, since a being interacts with its world in countless ways, and it explains why a change to one species disturbs many others`
  - Best window recall 0.25, global token recall 0.62
  - Closest source text: `inhabitants would almost immediately undergo a change and some species might become extinct we may conclude from what we have seen of the intimate and complex manner in which the inhabitants of each country are bound together that any change in the numerical proportions of some of the inhabitants in`

- **module 1 / lesson 2 / item 2** (Changing Conditions, Islands, and Places in the Economy of Nature)
  - Q: Why does Darwin insist that shifts in numerical proportions matter 'independently of the change of climate itself'?
  - Expected answer: `Because the inhabitants are bound together so intimately that a species can be gravely affected through its neighbours without feeling the physical change directly`
  - Best window recall 0.43, global token recall 0.57
  - Closest source text: `taking the case of a country undergoing some physical change for instance of climate the proportional numbers of its inhabitants would almost immediately undergo a change and some species might become extinct we may conclude from what we have seen of the intimate and complex manner in which the inha`

- **module 1 / lesson 3 / item 1** (Nature Compared with Man as a Selector)
  - Q: According to Darwin, why can natural selection act on characters that a human breeder could never notice?
  - Expected answer: `Because nature registers only the survival consequences of a difference, so internal organs and constitutional shades are sifted as readily as visible ones`
  - Best window recall 0.36, global token recall 0.36
  - Closest source text: `produced a great result by his methodical and unconscious means of selection what may not nature effect man can act only on external and visible characters nature cares nothing for appearances except in so far as they may be useful to any being she can act on every internal organ on every shade of c`

- **module 1 / lesson 3 / item 3** (Nature Compared with Man as a Selector)
  - Q: In Darwin's contrast, whose good does each selector serve?
  - Expected answer: `Man selects only for his own good, whereas nature selects only for the good of the being which she tends — since a variation can be preserved under nature only by advantaging its possessor.`
  - Best window recall 0.45, global token recall 0.73
  - Closest source text: `as they may be useful to any being she can act on every internal organ on every shade of constitutional difference on the whole machinery of life man selects only for his own good nature only for that of the being which she tends`

- **module 2 / lesson 1 / item 5** (Daily and Hourly Scrutiny: Selection Beyond Human Perception)
  - Q: Why does Darwin cite Downing's observations on downy versus smooth-skinned fruits and purple versus yellow plums?
  - Expected answer: `To show that characters botanists call trifling can decide which variety survives, so selection's reach extends to the slightest differences`
  - Best window recall 0.29, global token recall 0.64
  - Closest source text: `on the origin of species chapter iv natural selection excerpt charles darwin 1859 public domain via project gutenberg ebook 1228 chapter iv natural selection natural selection its power compared with man s selection its power on characters of trifling importance its power at all ages and on both sex`

- **module 2 / lesson 1 / item 6** (Daily and Hourly Scrutiny: Selection Beyond Human Perception)
  - Q: What point is Darwin making with the flock of white sheep in which every lamb with the faintest trace of black must be destroyed?
  - Expected answer: `That occasional, small-scale destruction is nevertheless enough to keep a character true and constant`
  - Best window recall 0.40, global token recall 0.90
  - Closest source text: `reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant nor ought we to think that the occasional destruction`

- **module 2 / lesson 2 / item 1** (Colour, Concealment, and the Case of the Grouse)
  - Q: In Darwin's argument about grouse, why is the fact that 'hawks are guided by eyesight to their prey' essential rather than incidental?
  - Expected answer: `It establishes that a difference in visibility translates into a difference in the chance of being killed, which is what lets colour be selected at all`
  - Best window recall 0.22, global token recall 0.44
  - Closest source text: `any being she can act on every internal organ on every shade of constitutional difference on the whole machinery of life man selects only for his own good nature only for that of the being which she tends every selected`

- **module 2 / lesson 2 / item 2** (Colour, Concealment, and the Case of the Grouse)
  - Q: What does the warning against keeping white pigeons on parts of the Continent contribute to the argument?
  - Expected answer: `Everyday practical experience that colour alone measurably alters how often an animal is taken by predators`
  - Best window recall 0.18, global token recall 0.27
  - Closest source text: `no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant nor ought we to think that the occasional destruction of an animal`

- **module 2 / lesson 2 / item 3** (Colour, Concealment, and the Case of the Grouse)
  - Q: In the analogy of the flock of white sheep, what does the practice of destroying every lamb with the faintest trace of black illustrate?
  - Expected answer: `That a small but unfailing rate of removal, repeated over generations, is enough to keep a character uniform`
  - Best window recall 0.20, global token recall 0.50
  - Closest source text: `of intercrosses between individuals of the same species circumstances favourable and unfavourable to natural selection namely intercrossing isolation number of individuals slow action extinction caused by natural selection divergence of character related to the diversity of inhabitants of any small`

- **module 2 / lesson 2 / item 4** (Colour, Concealment, and the Case of the Grouse)
  - Q: The lesson distinguishes two things natural selection does for grouse colour. Name both.
  - Expected answer: `It originates the proper colour by favouring each slight improvement in matching the habitat, and it maintains that colour true and constant afterwards by continually destroying deviants.`
  - Best window recall 0.27, global token recall 0.40
  - Closest source text: `so much so that on parts of the continent persons are warned not to keep white pigeons as being the most liable to destruction hence i can see no reason to doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acq`

- **module 2 / lesson 2 / item 5** (Colour, Concealment, and the Case of the Grouse)
  - Q: Darwin notes that in cultivated fruit, smooth-skinned varieties suffer more from the curculio beetle than downy ones. What does he conclude about a state of nature?
  - Expected answer: `Such differences would tell even more strongly, since no gardener's art protects the trees from their enemies`
  - Best window recall 0.36, global token recall 0.64
  - Closest source text: `other coloured flesh if with all the aids of art these slight differences make a great difference in cultivating the several varieties assuredly in a state of nature where the trees would have to struggle with other trees and with a host of enemies`

- **module 2 / lesson 2 / item 6** (Colour, Concealment, and the Case of the Grouse)
  - Q: What is the significance of the red-grouse being the colour of heather while the black-grouse is the colour of peaty earth?
  - Expected answer: `Each colour corresponds to the particular background of that species' own life, which suggests concealment rather than coincidence`
  - Best window recall 0.20, global token recall 0.40
  - Closest source text: `might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant nor ought we to think that the occasional destruction of an animal of any particular`

- **module 2 / lesson 3 / item 2** (Down, Colour, and Disease in Fruit: Trifles That Decide Survival)
  - Q: Darwin's three examples from Downing include one about plums and one about peaches. Why does he point out that these two cases work in opposite directions with respect to the colour yellow?
  - Expected answer: `Because it shows the advantage of a trait depends on which particular enemy is present, not on any universal virtue of a colour`
  - Best window recall 0.18, global token recall 0.27
  - Closest source text: `doubt that natural selection might be most effective in giving the proper colour to each kind of grouse and in keeping that colour when once acquired true and constant nor ought we to think that the occasional destruction of an animal of any particular`

- **module 2 / lesson 3 / item 5** (Down, Colour, and Disease in Fruit: Trifles That Decide Survival)
  - Q: Does Darwin's argument imply that every character of an organism must be adaptive? Answer with reference to what he says about variations that are neither useful nor injurious.
  - Expected answer: `No. Darwin holds that variations neither useful nor injurious would not be affected by natural selection and would be left a fluctuating element. The Downing examples are meant to show that our judgements about which characters are inert are often mistaken — not that every trait must have a use.`
  - Best window recall 0.42, global token recall 0.62
  - Closest source text: `thousands of generations if such do occur can we doubt remembering that many more individuals are born than can possibly survive that individuals having any advantage however slight over others would have the best chance of surviving and of procreating their kind on the other hand we may feel sure t`

### Answerability (answer vs its own lesson content)

- 4/34 answerable from the lesson alone = 11.8%
- Tiers: {'exact': 1, 'strong': 3, 'partial': 17, 'unsupported': 13}
- Giveaway MCQs (correct option quoted verbatim, no distractor is): 1

#### Items not answerable from their lesson

- **module 1 / lesson 1 / item 3** (From the Struggle for Existence to a Principle of Selection)
  - Q: Why is the strength of heredity an indispensable premise in Darwin's argument, and not just a supporting detail?
  - Expected answer: `Because without transmission to offspring, an individual's advantage would die with it. Only if offspring tend to resemble parents can a favourable variation be passed on and accumulated across generations, so heredity is what lets differential survival have any lasting effect.`
  - Best window recall against lesson: 0.45

- **module 1 / lesson 1 / item 4** (From the Struggle for Existence to a Principle of Selection)
  - Q: Darwin writes that 'unless profitable variations do occur, natural selection can do nothing.' What does this show about how he conceives selection?
  - Expected answer: `Selection sifts variation that arises independently; it does not itself generate novelty`
  - Best window recall against lesson: 0.38

- **module 1 / lesson 2 / item 2** (Changing Conditions, Islands, and Places in the Economy of Nature)
  - Q: Why does Darwin insist that shifts in numerical proportions matter 'independently of the change of climate itself'?
  - Expected answer: `Because the inhabitants are bound together so intimately that a species can be gravely affected through its neighbours without feeling the physical change directly`
  - Best window recall against lesson: 0.43

- **module 1 / lesson 3 / item 1** (Nature Compared with Man as a Selector)
  - Q: According to Darwin, why can natural selection act on characters that a human breeder could never notice?
  - Expected answer: `Because nature registers only the survival consequences of a difference, so internal organs and constitutional shades are sifted as readily as visible ones`
  - Best window recall against lesson: 0.43

- **module 1 / lesson 3 / item 3** (Nature Compared with Man as a Selector)
  - Q: In Darwin's contrast, whose good does each selector serve?
  - Expected answer: `Man selects only for his own good, whereas nature selects only for the good of the being which she tends — since a variation can be preserved under nature only by advantaging its possessor.`
  - Best window recall against lesson: 0.45

- **module 2 / lesson 1 / item 4** (Daily and Hourly Scrutiny: Selection Beyond Human Perception)
  - Q: Darwin says selection would leave variations that are neither useful nor injurious untouched. Why does this matter for understanding the 'scrutiny' image?
  - Expected answer: `It shows the scrutiny is not a general improver of everything: selection only acts where a variation makes a difference to survival or reproduction. Neutral variations are left as a fluctuating element, as perhaps seen in polymorphic species, so the personified 'scrutiny' is really just differential survival, not an inspecting agent perfecting organisms in the abstract.`
  - Best window recall against lesson: 0.45

- **module 2 / lesson 1 / item 5** (Daily and Hourly Scrutiny: Selection Beyond Human Perception)
  - Q: Why does Darwin cite Downing's observations on downy versus smooth-skinned fruits and purple versus yellow plums?
  - Expected answer: `To show that characters botanists call trifling can decide which variety survives, so selection's reach extends to the slightest differences`
  - Best window recall against lesson: 0.43

- **module 2 / lesson 1 / item 6** (Daily and Hourly Scrutiny: Selection Beyond Human Perception)
  - Q: What point is Darwin making with the flock of white sheep in which every lamb with the faintest trace of black must be destroyed?
  - Expected answer: `That occasional, small-scale destruction is nevertheless enough to keep a character true and constant`
  - Best window recall against lesson: 0.30

- **module 2 / lesson 2 / item 1** (Colour, Concealment, and the Case of the Grouse)
  - Q: In Darwin's argument about grouse, why is the fact that 'hawks are guided by eyesight to their prey' essential rather than incidental?
  - Expected answer: `It establishes that a difference in visibility translates into a difference in the chance of being killed, which is what lets colour be selected at all`
  - Best window recall against lesson: 0.22

- **module 2 / lesson 2 / item 2** (Colour, Concealment, and the Case of the Grouse)
  - Q: What does the warning against keeping white pigeons on parts of the Continent contribute to the argument?
  - Expected answer: `Everyday practical experience that colour alone measurably alters how often an animal is taken by predators`
  - Best window recall against lesson: 0.36

- **module 2 / lesson 2 / item 3** (Colour, Concealment, and the Case of the Grouse)
  - Q: In the analogy of the flock of white sheep, what does the practice of destroying every lamb with the faintest trace of black illustrate?
  - Expected answer: `That a small but unfailing rate of removal, repeated over generations, is enough to keep a character uniform`
  - Best window recall against lesson: 0.40

- **module 2 / lesson 2 / item 5** (Colour, Concealment, and the Case of the Grouse)
  - Q: Darwin notes that in cultivated fruit, smooth-skinned varieties suffer more from the curculio beetle than downy ones. What does he conclude about a state of nature?
  - Expected answer: `Such differences would tell even more strongly, since no gardener's art protects the trees from their enemies`
  - Best window recall against lesson: 0.45

- **module 2 / lesson 3 / item 2** (Down, Colour, and Disease in Fruit: Trifles That Decide Survival)
  - Q: Darwin's three examples from Downing include one about plums and one about peaches. Why does he point out that these two cases work in opposite directions with respect to the colour yellow?
  - Expected answer: `Because it shows the advantage of a trait depends on which particular enemy is present, not on any universal virtue of a colour`
  - Best window recall against lesson: 0.45

### Concept coverage across the source

- 14/30 concepts anchored to a source chunk (16 unanchored)
- Chunks containing at least one concept: 2/2 (100.0%)
- Concepts per chunk: [10, 4]
- Lessons per chunk: [1, 0]
- Uncovered chunk indexes: none
- Largest share in one chunk: 71.4%

Raw shares are not comparable across chunks of different sizes. Actual share over expected share (by chunk length) is: 1.0 means balanced.

- Expected share per chunk: [0.7334, 0.2666]
- Actual share per chunk: [0.7143, 0.2857]
- Actual/expected: [0.974, 1.0716]
- Worst concentration ratio: 1.07

### Source coverage (document sentences reaching the course)

Measured from the source side, so chunk length cancels out: what share of each chunk's substantial sentences is said anywhere in the course.

- Mean chunk recall: 94.5%
- Worst chunk: 0 at 89.1%
- Chunks under 50% covered: 0
- Lessons routed per segment: [6, 6]
- Segments with no lesson: []

| Chunk | Chars | Sentences | Covered | Recall | Mean sentence recall |
|---|---|---|---|---|---|
| 0 | 7,888 | 64 | 57 | 89.1% | 0.891 |
| 1 | 2,747 | 28 | 28 | 100.0% | 0.971 |
