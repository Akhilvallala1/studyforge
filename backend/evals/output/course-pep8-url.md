# PEP 8: Writing Readable, Idiomatic Python

> A guided tour of PEP 8, the official style guide for Python code. Working section by section through the PEP, this course covers its guiding philosophy, code layout and indentation rules, whitespace and comment conventions, naming standards, interface design, and the programming and annotation recommendations that shape idiomatic Python.

## How this was generated

- Eval run: `pep8-url` (run id `34c8037ba343472783cb6f657ddfda21`)
- Source: url `https://peps.python.org/pep-0008/`, 48,597 characters in 8 chunks
- Provider/model: anthropic / `claude-opus-5`
- 14 LLM calls, 70,870 input tokens, 49,307 output tokens, $1.5870, 584s wall clock
- Prompt fingerprint: outline `1f4a89050a37`, lesson `f575bed1be67`

Quiz answers are shown inline on purpose: this file exists so a human can check whether the answers are actually supported by the source.

---

## Module 1: Philosophy and Code Layout

### Lesson 1.1: Why a Style Guide? Consistency and Its Limits

**Concepts:** PEP 8's scope, status, and origin in Guido's style essay alongside PEP 257, Code is read more often than it is written as the rationale for style rules, The hierarchy of consistency: function/module > project > PEP 8, Legitimate reasons to ignore a guideline, including the ban on breaking backwards compatibility

**Written from source segments:** [0]

#### Lesson content

# Why a Style Guide? Consistency and Its Limits

Before we look at a single rule about indentation or naming, it's worth understanding what PEP 8 actually *is*, who it was written for, and — perhaps most importantly — when you are supposed to ignore it.

## What PEP 8 is

PEP 8 is titled *Style Guide for Python Code*. It was created on 5 July 2001 by Guido van Rossum, Barry Warsaw, and Alyssa Coghlan, and it carries the status **Active** with the type **Process**. "Active" matters: PEP 8 is not a finished historical document. As the PEP itself says, the guide *evolves over time as additional conventions are identified and past conventions are rendered obsolete by changes in the language itself*. A rule you learned in 2005 may have been softened, replaced, or dropped.

Its stated scope is narrower than most people assume:

> This document gives coding conventions for the Python code comprising the standard library in the main Python distribution.

So, strictly speaking, PEP 8 is the house style of CPython's standard library. It became the default style of the wider Python world by adoption and habit, not by decree. The C code in the CPython implementation is governed by a separate companion informational PEP, not by PEP 8.

### Its relatives

- **PEP 257 (Docstring Conventions)** is a companion document. Both PEP 8 and PEP 257 were adapted from **Guido's original Python Style Guide essay**, with some additions from **Barry Warsaw's style guide**. So the two PEPs are siblings drawn from a common ancestor, not one derived from the other.
- **PEP 20** (*The Zen of Python*) supplies the slogan PEP 8 leans on: "Readability counts".

## The core insight: code is read more often than it is written

The justification for the whole document fits in one sentence: *one of Guido's key insights is that code is read much more often than it is written.* You type a function once; you, your reviewers, and whoever maintains it in three years will read it dozens of times. Every rule in PEP 8 is an attempt to spend a little effort at writing time to save a lot of effort at reading time.

This also gives you a test for applying any rule: **does following it here make the code easier to read?** If a rule is making a particular piece of code harder to read, the rule is failing at the job it exists to do.

## The hierarchy of consistency

PEP 8 states an explicit ordering, and it is the most quoted passage in the document:

> Consistency with this style guide is important. **Consistency within a project is more important. Consistency within one module or function is the most important.**

Read as a ladder, from weakest to strongest claim:

| Level | Priority |
|---|---|
| PEP 8 itself | Important |
| The project you are working in | More important |
| The single module or function you are editing | Most important |

The practical consequence: if you drop a PEP 8-perfect function into a module written in a different but internally coherent style, you have made that module *worse*, because the reader now has to switch gears mid-file. The introduction says the same thing from the project angle: many projects have their own coding style guidelines, and **in the event of any conflicts, such project-specific guides take precedence for that project.**

This is why the relevant section is titled *"A Foolish Consistency is the Hobgoblin of Little Minds"* (a line borrowed from Emerson). Mechanical, context-blind rule-following is not the goal.

## When to be inconsistent

PEP 8 tells you outright: *know when to be inconsistent — sometimes style guide recommendations just aren't applicable.* When in doubt, use your best judgment, look at other examples, decide what looks best, and don't hesitate to ask.

One prohibition is stated with unusual force:

> In particular: **do not break backwards compatibility just to comply with this PEP!**

If a public function has a badly named parameter, renaming it to satisfy PEP 8 breaks every caller that used it as a keyword argument. Style never outranks not breaking your users.

The PEP then lists four other good reasons to ignore a particular guideline:

1. **Readability loss.** When applying the guideline would make the code less readable — even for someone who is used to reading PEP 8-compliant code. (Note that qualifier: the excuse is not "I personally find it ugly"; the standard is the experienced reader.)
2. **Surrounding code already breaks it**, perhaps for historic reasons — although the PEP adds that this is also an opportunity to clean up someone else's mess, in true XP style.
3. **The code predates the guideline** and there is no other reason to be modifying that code. Don't churn a file just to restyle it.
4. **Older-Python compatibility.** When the code must keep running on older versions of Python that don't support the feature the style guide recommends.

Notice what is *not* on the list: "I don't like it", "my editor does it differently", or "it was faster to type". The exemptions are all grounded in readability, history, or compatibility.

## A worked example

Suppose you're adding a helper to a module whose existing functions all use a two-space indent and `mixedCase` names, written in 2003:

```python
# legacy_parser.py  (written long ago, still in production)
def parseHeader(rawText):
  fields = rawText.split(':')
  return fields

# Your new helper — which version belongs here?

# Option A: strict PEP 8
def parse_body(raw_text):
    return raw_text.splitlines()

# Option B: matches the module
def parseBody(rawText):
  return rawText.splitlines()
```

By the hierarchy, consistency *within the module* is the most important level, so Option B is defensible and arguably preferred: reason 2 above applies directly. Option A is not "wrong" either — the PEP explicitly frames legacy style as an opportunity to clean up. What would be clearly wrong is rewriting the entire module's public function names to snake_case in a patch that was supposed to add one helper: that hits reason 3 (code predating the guideline, with no other reason to modify it) and risks breaking backwards compatibility for anyone importing `parseHeader`.

## Takeaway

PEP 8 is a tool for making code readable, aimed originally at the standard library, subordinate to your project's guide and to the local coherence of the file you're in, and explicitly overridable when readability, history, or compatibility demand it. Learn the rules well enough to know what you're deviating from — and then use judgment.

#### Quiz

1. **According to PEP 8's own ordering, which kind of consistency ranks highest?**  
   kind: `mcq` | concept: `The hierarchy of consistency: function/module > project > PEP 8`  
   - [x] Consistency within a single module or function
   - [ ] Consistency with PEP 8's published rules
   - [ ] Consistency across the whole project's codebase
   - [ ] Consistency with the CPython standard library's style
   **Expected answer:** Consistency within a single module or function

2. **What does PEP 8 say happens when a project's own coding style guidelines conflict with PEP 8?**  
   kind: `mcq` | concept: `The hierarchy of consistency: function/module > project > PEP 8`  
   - [x] The project-specific guide takes precedence for that project
   - [ ] PEP 8 wins, since it is an Active Process PEP
   - [ ] The conflict must be resolved in favour of whichever rule is newer
   - [ ] Both are ignored and the author uses personal judgment instead
   **Expected answer:** The project-specific guide takes precedence for that project

3. **State the insight of Guido's that PEP 8 offers as the underlying justification for its readability rules.**  
   kind: `short` | concept: `Code is read more often than it is written as the rationale for style rules`  
   **Expected answer:** That code is read much more often than it is written, so effort spent making it readable pays off repeatedly.

4. **Which statement about PEP 8's origins and relatives is accurate?**  
   kind: `mcq` | concept: `PEP 8's scope, status, and origin in Guido's style essay alongside PEP 257`  
   - [x] PEP 8 and PEP 257 were both adapted from Guido's original style guide essay, with additions from Barry Warsaw's guide
   - [ ] PEP 257 was derived from PEP 8 after PEP 8 was finalised in 2001
   - [ ] PEP 8 covers both the Python and the C code of the CPython implementation
   - [ ] PEP 8 was frozen on publication so that the standard library's style would never shift
   **Expected answer:** PEP 8 and PEP 257 were both adapted from Guido's original style guide essay, with additions from Barry Warsaw's guide

5. **Which of these is NOT one of the reasons PEP 8 gives for ignoring a particular guideline?**  
   kind: `mcq` | concept: `Legitimate reasons to ignore a guideline, including the ban on breaking backwards compatibility`  
   - [x] The developer finds the recommended form personally unattractive
   - [ ] Following the guideline would make the code less readable to someone used to PEP 8 code
   - [ ] The code must stay compatible with older Python versions lacking the recommended feature
   - [ ] The code predates the guideline and there is no other reason to modify it
   **Expected answer:** The developer finds the recommended form personally unattractive

6. **PEP 8 singles out one thing you must never do merely to comply with the PEP. What is it?**  
   kind: `short` | concept: `Legitimate reasons to ignore a guideline, including the ban on breaking backwards compatibility`  
   **Expected answer:** Break backwards compatibility. Style compliance never justifies breaking existing users of the code.

---

### Lesson 1.2: Indentation and Continuation Lines

**Concepts:** 4-space indentation with spaces rather than tabs, Vertical alignment with the opening delimiter vs. hanging indents, Extra indentation to distinguish continuation lines from a nested suite (def parameters, multi-line if conditions), Two acceptable placements for the closing bracket of a multiline construct, Implicit line joining inside brackets preferred over backslash continuation

**Written from source segments:** [0, 1]

#### Lesson content

# Indentation and Continuation Lines

## The basic rule

**Use 4 spaces per indentation level.** Spaces are the preferred indentation method; tabs should only be used to stay consistent with code that is already indented with tabs. Python itself disallows mixing tabs and spaces for indentation.

```python
def greet(name):
    if name:
        print(f"Hello, {name}")
```

## Continuation lines: two strategies

When an expression is too long for one line, you break it inside parentheses, brackets or braces (Python's *implicit line joining*). PEP 8 gives you two acceptable ways to indent the wrapped part:

1. **Vertical alignment with the opening delimiter** — the continuation lines start in the column just after the opening `(`, `[` or `{`.
2. **Hanging indent** — nothing follows the opening delimiter on the first line, and the wrapped elements are indented on the lines below.

### Aligned with the opening delimiter

```python
# Correct:
foo = long_function_name(var_one, var_two,
                         var_three, var_four)
```

Here `var_three` sits directly under `var_one`, right after the `(`.

### Hanging indent

With a hanging indent, two things must be true:

- **There are no arguments on the first line.**
- **Further indentation is used** so the continuation clearly distinguishes itself from surrounding code.

```python
# Correct: hanging indents should add a level.
foo = long_function_name(
    var_one, var_two,
    var_three, var_four)
```

For a `def`, the body of the function is itself indented 4 spaces, so a plain 4-space hanging indent for the parameters would look identical to the body. Add an *extra* level so the parameters stand apart:

```python
# Correct: add 4 more spaces to distinguish arguments from the rest.
def long_function_name(
        var_one, var_two, var_three,
        var_four):
    print(var_one)
```

### The two classic mistakes

```python
# Wrong: arguments on the first line are forbidden
# when not using vertical alignment.
foo = long_function_name(var_one, var_two,
    var_three, var_four)

# Wrong: further indentation required, as the parameters are
# not distinguishable from the function body.
def long_function_name(
    var_one, var_two, var_three,
    var_four):
    print(var_one)
```

### The 4-space rule is optional here

For *continuation lines only*, the 4-space rule is optional — a hanging indent may use some other amount:

```python
# Optional: hanging indents *may* be indented to other than 4 spaces.
foo = long_function_name(
  var_one, var_two,
  var_three, var_four)
```

This relaxation applies to continuation lines, not to ordinary block indentation, which stays at 4 spaces.

## The multi-line `if`-statement problem

`if` is a two-character keyword, plus a space, plus `(` — which naturally puts continuation lines of the condition at column 4. That is exactly where the indented suite inside the `if` will also land, creating a visual conflict. PEP 8 **takes no explicit position** on how (or whether) to resolve this. Acceptable options include, but are not limited to:

```python
# No extra indentation.
if (this_is_one_thing and
        that_is_another_thing):
    do_something()
```

Wait — more precisely, the plainest form is:

```python
# No extra indentation.
if (this_is_one_thing and
    that_is_another_thing):
    do_something()

# Add a comment, which will provide some distinction in editors
# supporting syntax highlighting.
if (this_is_one_thing and
    that_is_another_thing):
    # Since both conditions are true, we can frobnicate.
    do_something()

# Add some extra indentation on the conditional continuation line.
if (this_is_one_thing
        and that_is_another_thing):
    do_something()
```

All three are acceptable; pick one and be consistent locally.

## Where to put the closing bracket

The closing brace/bracket/parenthesis of a multiline construct may go in either of two places:

**Lined up under the first non-whitespace character of the last line:**

```python
my_list = [
    1, 2, 3,
    4, 5, 6,
    ]
result = some_function_that_takes_arguments(
    'a', 'b', 'c',
    'd', 'e', 'f',
    )
```

**Or lined up under the first character of the line that starts the construct:**

```python
my_list = [
    1, 2, 3,
    4, 5, 6,
]
result = some_function_that_takes_arguments(
    'a', 'b', 'c',
    'd', 'e', 'f',
)
```

Both are sanctioned by PEP 8. Choose one style and apply it consistently.

## Backslashes versus implicit continuation

The preferred way to wrap a long line is implied continuation inside parentheses, brackets and braces — in preference to a backslash. Backslashes are still occasionally appropriate; for instance, multiple `with`-statements could not use implicit continuation before Python 3.10, and `assert` statements are another such case. Whenever you do use a backslash, indent the continued line appropriately.

```python
with open('/path/to/some/file/you/want/to/read') as file_1, \
     open('/path/to/some/file/being/written', 'w') as file_2:
    file_2.write(file_1.read())
```

## Summary checklist

- 4 spaces per indentation level; spaces over tabs.
- Either align with the opening delimiter, or use a hanging indent — never mix the two by leaving arguments on the first line and then under-indenting the rest.
- With a hanging indent in a `def`, add an extra level so parameters don't blend into the body.
- Multi-line `if` conditions: PEP 8 leaves the choice to you; comment, extra indent, or nothing.
- Closing bracket: under the first content character of the last line, or under the start of the opening line.

#### Quiz

1. **Which requirement applies specifically to a hanging indent?**  
   kind: `mcq` | concept: `Vertical alignment with the opening delimiter vs. hanging indents`  
   - [x] No arguments may appear on the first line, and the wrapped lines must be indented further to mark themselves as continuations
   - [ ] The wrapped lines must start in the column immediately after the opening delimiter
   - [ ] Exactly one argument must be left on the first line so readers can see the call's shape
   - [ ] The closing delimiter must sit on the same line as the final argument
   **Expected answer:** No arguments may appear on the first line, and the wrapped lines must be indented further to mark themselves as continuations

2. **Why does PEP 8 suggest an extra indentation level for the parameters of a `def` that uses a hanging indent?**  
   kind: `mcq` | concept: `Extra indentation to distinguish continuation lines from a nested suite (def parameters, multi-line if conditions)`  
   - [x] Because a plain 4-space indent would be indistinguishable from the function's own body
   - [ ] Because the interpreter raises an IndentationError when parameters sit at 4 spaces
   - [ ] Because parameter lists are exempt from the 79-character line limit and need the room
   - [ ] Because the closing parenthesis can only be aligned if the parameters are at 8 spaces
   **Expected answer:** Because a plain 4-space indent would be indistinguishable from the function's own body

3. **What position does PEP 8 take on visually distinguishing a long multi-line `if` condition from the suite nested inside it?**  
   kind: `mcq` | concept: `Extra indentation to distinguish continuation lines from a nested suite (def parameters, multi-line if conditions)`  
   - [x] It takes no explicit position and lists several acceptable options, such as adding a comment or extra indentation
   - [ ] It requires the continuation lines of the condition to be indented 8 spaces so the suite stays at 4
   - [ ] It requires the condition to be assigned to a temporary variable before the `if`
   - [ ] It requires breaking before the boolean operator and aligning the operator under the `if`
   **Expected answer:** It takes no explicit position and lists several acceptable options, such as adding a comment or extra indentation

4. **Name the two placements PEP 8 allows for the closing bracket of a multiline list or call.**  
   kind: `short` | concept: `Two acceptable placements for the closing bracket of a multiline construct`  
   **Expected answer:** It may line up under the first non-whitespace character of the last line of the construct, or under the first character of the line that starts the multiline construct.

5. **Which statement about the 4-space rule is accurate?**  
   kind: `mcq` | concept: `4-space indentation with spaces rather than tabs`  
   - [x] It is optional for continuation lines, so a hanging indent may use some other amount
   - [ ] It applies to continuation lines but block bodies may use any consistent width
   - [ ] It is optional everywhere as long as one file uses a single width throughout
   - [ ] It is mandatory everywhere, including hanging indents, with no exceptions
   **Expected answer:** It is optional for continuation lines, so a hanging indent may use some other amount

6. **According to the lesson, what is the preferred way to wrap a long line, and when might a backslash still be appropriate?**  
   kind: `short` | concept: `Implicit line joining inside brackets preferred over backslash continuation`  
   **Expected answer:** The preferred way is Python's implied line continuation inside parentheses, brackets and braces. Backslashes are still sometimes appropriate, for example for multiple `with`-statements before Python 3.10 and for `assert` statements; the continued line should be indented appropriately.

---

### Lesson 1.3: Line Length, Line Breaks, and Blank Lines

**Concepts:** Spaces as the preferred indentation, with tabs only for consistency with existing code, The 79-character code limit and 72-character docstring/comment limit, and their rationale, Implied line continuation inside brackets preferred over backslashes, Knuth's rule: break before binary operators in new code, Two blank lines around top-level definitions, one around methods

**Written from source segments:** [1]

#### Lesson content

# Line Length, Line Breaks, and Blank Lines

This lesson covers the parts of PEP 8 that shape the *physical layout* of a source file: what character you indent with, how long a line may be, where to break it, and how much vertical whitespace to leave between definitions.

---

## Tabs or Spaces?

- **Spaces are the preferred indentation method.**
- Tabs should be used *solely* to remain consistent with code that is already indented with tabs. If you inherit a tab-indented file, don't half-convert it.
- Python itself **disallows mixing tabs and spaces** for indentation — this is a language-level error, not just a style rule.

The practical takeaway: new code gets spaces (four per level), and you never mix the two within one file.

---

## Maximum Line Length

Two different limits apply, depending on what's on the line:

| Content | Limit |
|---|---|
| Code | **79 characters** |
| Docstrings and comments (flowing prose) | **72 characters** |

### Why bother in an age of wide monitors?

The rationale is about *tools and eyes*, not about terminals from 1980:

- A narrow required editor width lets you keep **several files open side by side**.
- It works well with **code review tools that show two versions in adjacent columns**.
- **Default wrapping in most tools disrupts the visual structure of the code**, making it harder to understand. The limits are set to avoid wrapping in an editor 80 columns wide, *even when* the tool spends the final column on a marker glyph for wrapped lines.
- Some web-based viewers offer no dynamic wrapping at all — long lines just get cut off or force horizontal scrolling.

### The team escape hatch

For code maintained exclusively or primarily by a team that can agree on it, it is okay to raise the code limit **up to 99 characters** — but **comments and docstrings must still wrap at 72**. The prose limit does not move.

The Python standard library is deliberately conservative: 79 for code, 72 for docstrings and comments, no exceptions.

---

## Breaking Long Lines: Implied Continuation vs. Backslashes

The **preferred** way to wrap a long line is Python's *implied line continuation* inside parentheses, brackets, and braces. If an expression isn't already inside a bracket, you can wrap it in parentheses to get the same effect. This is preferred over the backslash.

```python
# Correct: implied continuation inside parentheses
income = (gross_wages
          + taxable_interest
          - ira_deduction)
```

Backslashes are still occasionally appropriate. Before Python 3.10, long multiple `with`-statements could not use implicit continuation, so a backslash was the accepted solution:

```python
with open('/path/to/some/file/you/want/to/read') as file_1, \
     open('/path/to/some/file/being/written', 'w') as file_2:
    file_2.write(file_1.read())
```

`assert` statements are another such case. Whichever mechanism you use, **indent the continued line appropriately** so the reader can see it is a continuation and not a new statement.

### Where the closing bracket goes

On a multiline construct, the closing brace/bracket/parenthesis may either line up under the first non-whitespace character of the last line, or under the first character of the line that *starts* the construct:

```python
my_list = [
    1, 2, 3,
    4, 5, 6,
    ]          # under the first non-whitespace char of the last line

my_list = [
    1, 2, 3,
    4, 5, 6,
]              # under the first char of the starting line
```

Both are acceptable; pick one and be consistent.

---

## Break Before or After a Binary Operator?

For decades the recommendation was to break **after** the operator. That hurts readability in two ways: the operators end up scattered across different columns, and each operator is separated from its right-hand operand by a line break. The eye has to work to see which terms are added and which are subtracted:

```python
# Wrong:
# operators sit far away from their operands
income = (gross_wages +
          taxable_interest +
          (dividends - qualified_dividends) -
          ira_deduction -
          student_loan_interest)
```

Mathematicians and their publishers solved this long ago by using the opposite convention. Donald Knuth states the traditional rule in *Computers and Typesetting*: “Although formulas within a paragraph always break after binary operations and relations, **displayed formulas always break before binary operations**.” Multiline code is like a displayed formula, so the operator leads the line:

```python
# Correct:
# easy to match operators with operands
income = (gross_wages
          + taxable_interest
          + (dividends - qualified_dividends)
          - ira_deduction
          - student_loan_interest)
```

All the operators line up in one column, and each sits right next to its operand.

PEP 8's actual position: **either style is permissible**, as long as the convention is consistent locally. **For new code, Knuth's style (break before) is suggested.**

---

## Blank Lines

Vertical whitespace groups code the way paragraph breaks group prose.

- Surround **top-level function and class definitions with two blank lines**.
- **Method definitions inside a class** are surrounded by a **single blank line**.
- Extra blank lines may be used *sparingly* to separate groups of related functions.
- Blank lines may be **omitted** between a bunch of related one-liners (e.g. a set of dummy implementations).
- Inside a function, use blank lines sparingly to mark logical sections.

```python
import os


def top_level_one():
    ...


class Widget:

    def method_a(self):
        ...

    def method_b(self):
        ...


def top_level_two():
    ...
```

### Form feeds

Python accepts the control-L (`^L`) form feed character as whitespace. Many tools treat it as a page separator, so you may use it to separate pages of related sections in a file. Be aware that some editors and web-based code viewers don't recognize it and will display some other glyph instead.


#### Quiz

1. **A team agrees to relax PEP 8's line length for its own codebase. According to the lesson, what is permitted?**  
   kind: `mcq` | concept: `The 79-character code limit and 72-character docstring/comment limit, and their rationale`  
   - [x] Code lines may go up to 99 characters, but comments and docstrings still wrap at 72
   - [ ] Both code and prose may go up to 99 characters, since the same limit should apply throughout
   - [ ] Code lines may go up to 120 characters as long as the team documents the choice
   - [ ] No relaxation is permitted; 79 characters is a hard requirement for all Python code
   **Expected answer:** Code lines may go up to 99 characters, but comments and docstrings still wrap at 72

2. **Which reason does the lesson give for keeping lines short?**  
   kind: `mcq` | concept: `The 79-character code limit and 72-character docstring/comment limit, and their rationale`  
   - [x] Automatic wrapping by editors and viewers destroys the visual structure of the code
   - [ ] The Python parser reads short lines faster, reducing import time
   - [ ] Long lines increase the risk of mixing tabs and spaces on the same line
   - [ ] Version control systems cannot compute diffs reliably on lines over 80 characters
   **Expected answer:** Automatic wrapping by editors and viewers destroys the visual structure of the code

3. **State Knuth's rule as quoted in the lesson, and say which of the two behaviours multiline Python expressions should imitate for new code.**  
   kind: `short` | concept: `Knuth's rule: break before binary operators in new code`  
   **Expected answer:** Formulas within a paragraph break after binary operations and relations, but displayed formulas break before binary operations. New Python code should follow the displayed-formula behaviour and break before the operator, so operators line up in a column next to their operands.

4. **How many blank lines does PEP 8 ask for around a method defined inside a class, versus around a top-level function?**  
   kind: `mcq` | concept: `Two blank lines around top-level definitions, one around methods`  
   - [x] One blank line around the method, two around the top-level function
   - [ ] Two blank lines around the method, one around the top-level function
   - [ ] One blank line in both cases, with two reserved for separating classes only
   - [ ] Two blank lines in both cases, for visual consistency
   **Expected answer:** One blank line around the method, two around the top-level function

5. **You need to split a long boolean expression across two lines. What does the lesson recommend, and when might a backslash still be justified?**  
   kind: `short` | concept: `Implied line continuation inside brackets preferred over backslashes`  
   **Expected answer:** Wrap the expression in parentheses and rely on Python's implied line continuation inside parentheses, brackets or braces; this is preferred over backslashes. Backslashes remain appropriate in cases where implicit continuation is unavailable, such as long multiple with-statements before Python 3.10, or assert statements. Either way, indent the continued line appropriately.

6. **Which statement about indentation characters matches the lesson?**  
   kind: `mcq` | concept: `Spaces as the preferred indentation, with tabs only for consistency with existing code`  
   - [x] Spaces are preferred; tabs are reserved for staying consistent with already tab-indented code, and Python forbids mixing the two
   - [ ] Tabs are preferred because editors can render them at any width, and spaces are only for alignment inside brackets
   - [ ] Either character is fine, and mixing them within a file is acceptable as long as the visual indentation looks right
   - [ ] Spaces are required by the Python interpreter, which rejects any source file containing tab characters
   **Expected answer:** Spaces are preferred; tabs are reserved for staying consistent with already tab-indented code, and Python forbids mixing the two

---

### Lesson 1.4: Encoding, Imports, and Module Dunders

**Concepts:** UTF-8 source encoding and ASCII-only identifiers, Import formatting: one per line and grouping order (stdlib, third party, local), Absolute imports versus explicit relative imports, Avoiding wildcard imports and their one defensible use case, Ordering of module-level dunder names relative to docstrings and __future__ imports

**Written from source segments:** [1, 2]

#### Lesson content

# Encoding, Imports, and Module Dunders

This lesson covers three PEP 8 topics that all concern the *top* of a Python source file: how the file is encoded, how imports are written and ordered, and where module-level dunder names go.

---

## 1. Source File Encoding

**Code in the core Python distribution should always use UTF-8, and should not carry an encoding declaration.** UTF-8 is the default source encoding in Python 3, so a line like `# -*- coding: utf-8 -*-` is redundant noise.

In the standard library, non-UTF-8 encodings should be used **only for test purposes** — for example, a test that deliberately exercises the decoder.

Guidelines for non-ASCII characters *inside* the code:

- Use them sparingly, preferably only to denote **places and human names** (e.g. a name in a comment or an author string).
- If using non-ASCII characters as data, avoid "noisy" Unicode such as zalgo-style combining-mark pileups, and avoid byte order marks.

Guidelines for **identifiers** (variable, function, class, module names):

- All identifiers in the Python standard library **MUST** use ASCII-only identifiers.
- They **SHOULD** use English words wherever feasible. (In practice abbreviations and technical terms that aren't really English are common and acceptable.)

Note the difference in strength: ASCII identifiers are a *must*; English words are a *should*. Open source projects with a global audience are encouraged to adopt a similar policy, since ASCII identifiers are typeable by everyone.

---

## 2. Imports

### One import per line

```python
# Correct:
import os
import sys

# Wrong:
import sys, os
```

The `from ... import ...` form is the exception — several names from the *same* module on one line are fine:

```python
# Correct:
from subprocess import Popen, PIPE
```

### Placement

Imports are always put at the top of the file, **just after any module comments and docstrings, and before module globals and constants**.

### Grouping and order

Imports should be grouped in this order, with a **blank line between each group**:

1. Standard library imports
2. Related third party imports
3. Local application/library specific imports

```python
"""Report generator."""

import os
import sys

import requests
from flask import Flask

from myapp.models import Report
from myapp.utils import format_date
```

### Absolute vs. explicit relative imports

**Absolute imports are recommended.** They are usually more readable and tend to be better behaved — or at least give better error messages — if the import system is misconfigured, such as when a directory *inside* a package ends up on `sys.path`.

```python
import mypkg.sibling
from mypkg import sibling
from mypkg.sibling import example
```

**Explicit relative imports are an acceptable alternative**, especially with complex package layouts where absolute imports would be unnecessarily verbose:

```python
from . import sibling
from .sibling import example
```

Note the word *explicit*: the leading dot is required. Standard library code, however, should avoid complex package layouts and always use absolute imports.

### Importing classes

When importing a class from a class-containing module, this is usually fine:

```python
from myclass import MyClass
from foo.bar.yourclass import YourClass
```

If that spelling causes **local name clashes**, import the modules instead and qualify the uses:

```python
import myclass
import foo.bar.yourclass

# then use myclass.MyClass and foo.bar.yourclass.YourClass
```

### Wildcard imports

`from <module> import *` **should be avoided**: it makes it unclear which names are present in the namespace, confusing both human readers and many automated tools (linters, IDEs, type checkers).

There is one defensible use case: **republishing an internal interface as part of a public API** — for example, overwriting a pure Python implementation with the definitions from an optional accelerator module, when exactly which definitions will be overwritten isn't known in advance. Even then, the usual guidelines about public and internal interfaces still apply.

---

## 3. Module Level Dunder Names

Module level "dunders" — names with two leading and two trailing underscores, such as `__all__`, `__author__`, `__version__` — should be placed **after the module docstring but before any import statements, except `from __future__` imports.**

The `__future__` exception is not stylistic: Python *mandates* that future-imports appear in the module before any other code except the docstring. So the required order is:

1. Module docstring
2. `from __future__ import ...`
3. Module-level dunders
4. Ordinary imports

```python
"""This is the example module.

This module does stuff.
"""

from __future__ import barry_as_FLUFL

__all__ = ['a', 'b', 'c']
__version__ = '0.1'
__author__ = 'Cardinal Biggles'

import os
import sys
```

---

## Quick checklist

- UTF-8, no encoding declaration; ASCII-only identifiers.
- One module per `import` line; `from X import a, b` is fine.
- Three groups, blank line between: stdlib, third party, local.
- Prefer absolute imports; explicit relative imports acceptable for complex layouts.
- No `import *` except when republishing an interface.
- Docstring → `__future__` → dunders → imports.


#### Quiz

1. **In the file layout PEP 8 prescribes, where do module-level dunders such as `__version__` belong?**  
   kind: `mcq` | concept: `Ordering of module-level dunder names relative to docstrings and __future__ imports`  
   - [x] After the module docstring and any `from __future__` imports, but before ordinary imports
   - [ ] At the very top of the file, above the module docstring, so tools can find them first
   - [ ] Immediately after all imports, grouped with the module's other globals and constants
   - [ ] Anywhere in the module, since Python resolves dunders independently of their position
   **Expected answer:** After the module docstring and any `from __future__` imports, but before ordinary imports

2. **Which of these import lines follows PEP 8?**  
   kind: `mcq` | concept: `Import formatting: one per line and grouping order (stdlib, third party, local)`  
   - [x] `from subprocess import Popen, PIPE`
   - [ ] `import sys, os`
   - [ ] `from os.path import *`
   - [ ] `import json, re, collections`
   **Expected answer:** `from subprocess import Popen, PIPE`

3. **List, in order, the three import groups PEP 8 asks you to use, and say what separates them.**  
   kind: `short` | concept: `Import formatting: one per line and grouping order (stdlib, third party, local)`  
   **Expected answer:** Standard library imports, then related third party imports, then local application/library specific imports, with a blank line between each group.

4. **What reason does PEP 8 give for preferring absolute imports over relative ones?**  
   kind: `mcq` | concept: `Absolute imports versus explicit relative imports`  
   - [x] They are usually more readable and behave better (or give better error messages) when the import system is misconfigured, such as when a directory inside a package lands on `sys.path`
   - [ ] They are resolved at compile time rather than at runtime, so they load measurably faster
   - [ ] Relative imports are deprecated in Python 3 and will raise a warning in future releases
   - [ ] They prevent circular imports, which relative imports cannot detect
   **Expected answer:** They are usually more readable and behave better (or give better error messages) when the import system is misconfigured, such as when a directory inside a package lands on `sys.path`

5. **Why are wildcard imports discouraged, and what is the one defensible use case mentioned?**  
   kind: `short` | concept: `Avoiding wildcard imports and their one defensible use case`  
   **Expected answer:** They make it unclear which names are present in the namespace, confusing readers and many automated tools. The one defensible use is republishing an internal interface as part of a public API — e.g. overwriting a pure Python implementation with definitions from an optional accelerator module when it isn't known in advance which definitions will be overwritten.

6. **Which statement about source encoding and identifiers matches PEP 8?**  
   kind: `mcq` | concept: `UTF-8 source encoding and ASCII-only identifiers`  
   - [x] Core Python code should use UTF-8 with no encoding declaration, and standard library identifiers must be ASCII-only
   - [ ] Core Python code should use UTF-8 and add an explicit `# -*- coding: utf-8 -*-` line for clarity
   - [ ] Non-ASCII identifiers are permitted in the standard library as long as they name places or people
   - [ ] Non-UTF-8 encodings are acceptable in standard library modules whenever the data requires them
   **Expected answer:** Core Python code should use UTF-8 with no encoding declaration, and standard library identifiers must be ASCII-only

---

## Module 2: Whitespace, Commas, and Comments

### Lesson 2.1: Whitespace Pet Peeves and Operator Spacing

**Concepts:** PEP 8 makes no single-vs-double quote recommendation, but triple-quoted strings always use double quotes, Extraneous whitespace: inside brackets, before commas/colons, before call and index parentheses, and alignment padding, The slice colon behaves as a lowest-priority binary operator with symmetric spacing, omitted when the parameter is omitted, Single spaces around binary operators, with lower-priority operators optionally spaced to show grouping, Keyword-argument and unannotated-default `=` takes no spaces, but an annotated default does

**Written from source segments:** [2]

#### Lesson content

# Whitespace Pet Peeves and Operator Spacing

Most of PEP 8's whitespace rules exist for one reason: whitespace should carry information. When a space appears where it means nothing, it slows the reader down and, worse, it makes the *meaningful* spaces harder to see. This lesson covers string quotes and then the full catalogue of whitespace habits PEP 8 asks you to drop.

## String quotes

Single-quoted and double-quoted strings are identical in Python. **PEP 8 makes no recommendation between them** — pick a rule and stick to it within a project.

There are two things it does say:

1. When a string *contains* a quote character, use the other kind of quote so you don't need backslashes. Readability wins.

   ```python
   # Correct:
   message = "don't panic"
   quote = 'she said "hello"'

   # Awkward:
   message = 'don\'t panic'
   ```

2. For **triple-quoted strings, always use double quotes** (`"""..."""`), for consistency with the docstring convention in PEP 257.

## Pet peeves: extraneous whitespace

### Immediately inside parentheses, brackets, or braces

```python
# Correct:
spam(ham[1], {eggs: 2})

# Wrong:
spam( ham[ 1 ], { eggs: 2 } )
```

### Between a trailing comma and a following close parenthesis

```python
# Correct:
foo = (0,)

# Wrong:
bar = (0, )
```

### Immediately before a comma, semicolon, or colon

```python
# Correct:
if x == 4: print(x, y); x, y = y, x

# Wrong:
if x == 4 : print(x , y) ; x , y = y , x
```

(Note that the *example* uses a compound statement only to demonstrate the semicolon — see the last section for why you shouldn't write it that way.)

### The slice exception

In a slice, the colon is not punctuation — it behaves like a **binary operator**, so it gets **equal amounts of space on both sides**, and you treat it as the operator with the *lowest* priority. In an extended slice, both colons must get the same treatment. **When a slice parameter is omitted, its space is omitted too.**

```python
# Correct:
ham[1:9], ham[1:9:3], ham[:9:3], ham[1::3], ham[1:9:]
ham[lower:upper], ham[lower:upper:], ham[lower::step]
ham[lower+offset : upper+offset]
ham[: upper_fn(x) : step_fn(x)], ham[:: step_fn(x)]

# Wrong:
ham[lower+offset:upper+offset]
ham[1: 9], ham[1 :9, 3]
ham[lower : : step]
ham[ : upper]
```

Look at `ham[lower+offset : upper+offset]`. The `+` binds tighter than the slice colon, so the colon — the lowest-priority operator in the expression — gets the spaces and `+` gets none. That's the "lowest priority operator" rule doing visible work.

### Immediately before the parenthesis of a call

```python
# Correct:
spam(1)

# Wrong:
spam (1)
```

### Immediately before the bracket of an index or slice

```python
# Correct:
dct['key'] = lst[index]

# Wrong:
dct ['key'] = lst [index]
```

### More than one space around an operator to align it with another

Column alignment feels tidy, but it makes every future rename produce a diff on unrelated lines.

```python
# Correct:
x = 1
y = 2
long_variable = 3

# Wrong:
x             = 1
y             = 2
long_variable = 3
```

### Trailing whitespace anywhere

It's invisible, so it's confusing: a backslash followed by a space and a newline is **not** a line continuation marker, and the resulting error is baffling. Many projects (CPython included) have pre-commit hooks that reject it.

## Spacing around binary operators

Always surround these with a **single space on either side**:

- assignment `=`
- augmented assignment `+=`, `-=`, etc.
- comparisons `==`, `<`, `>`, `!=`, `<=`, `>=`, `in`, `not in`, `is`, `is not`
- Booleans `and`, `or`, `not`

When operators of **different priorities** appear together, consider adding whitespace around the *lowest*-priority ones to make the grouping visible. Use your judgement, but never more than one space, and always the same amount on both sides of any given operator.

```python
# Correct:
i = i + 1
submitted += 1
x = x*2 - 1
hypot2 = x*x + y*y
c = (a+b) * (a-b)

# Wrong:
i=i+1
submitted +=1
x = x * 2 - 1
hypot2 = x * x + y * y
c = (a + b) * (a - b)
```

The "wrong" versions here aren't errors so much as missed opportunities: uniform spacing hides which operator binds tighter.

## Annotations and the keyword-argument `=`

Function annotations use the normal colon rules (no space before, one space after) and **always put spaces around the `->` arrow**:

```python
# Correct:
def munge(input: AnyStr): ...
def munge() -> PosInt: ...

# Wrong:
def munge(input:AnyStr): ...
def munge()->PosInt: ...
```

Do **not** put spaces around `=` when it marks a keyword argument, or a default value for an **unannotated** parameter:

```python
# Correct:
def complex(real, imag=0.0):
    return magic(r=real, i=imag)

# Wrong:
def complex(real, imag = 0.0):
    return magic(r = real, i = imag)
```

But when a parameter has **both an annotation and a default**, *do* use spaces around the `=`. The annotation makes the parameter long enough that the bare `=` gets lost:

```python
# Correct:
def munge(sep: AnyStr = None): ...
def munge(input: AnyStr, sep: AnyStr = None, limit=1000): ...

# Wrong:
def munge(input: AnyStr=None): ...
def munge(input: AnyStr, limit = 1000): ...
```

Notice `limit=1000` stays tight in the correct version — it has no annotation, so the plain rule applies. The two rules coexist in the same signature.

## Compound statements

Putting multiple statements on one line is generally discouraged:

```python
# Correct:
if foo == 'blah':
    do_blah_thing()
do_one()
do_two()
do_three()

# Rather not:
if foo == 'blah': do_blah_thing()
do_one(); do_two(); do_three()
```

It's occasionally tolerable to put an `if`/`for`/`while` with a very small body on one line, but **never** do it for a multi-clause statement, and never fold a long line to make it fit:

```python
# Definitely not:
if foo == 'blah': do_blah_thing()
else: do_non_blah_thing()

try: something()
finally: cleanup()

do_one(); do_two(); do_three(long, argument,
                             list, like, this)
```


#### Quiz

1. **Which line follows PEP 8's slice spacing rules?**  
   kind: `mcq` | concept: `The slice colon behaves as a lowest-priority binary operator with symmetric spacing, omitted when the parameter is omitted`  
   - [x] `ham[lower+offset : upper+offset]`
   - [ ] `ham[lower + offset:upper + offset]`
   - [ ] `ham[ lower+offset : upper+offset ]`
   - [ ] `ham[lower+offset :upper+offset]`
   **Expected answer:** `ham[lower+offset : upper+offset]`

2. **In `def munge(input: AnyStr, sep: AnyStr = None, limit=1000): ...`, why does `sep` get spaces around its `=` while `limit` does not?**  
   kind: `short` | concept: `Keyword-argument and unannotated-default `=` takes no spaces, but an annotated default does`  
   **Expected answer:** Because `sep` combines an annotation with a default value, and PEP 8 says to use spaces around `=` in that case; `limit` is an unannotated parameter with a default, so its `=` takes no surrounding spaces.

3. **What does PEP 8 say about choosing between single and double quotes for ordinary strings?**  
   kind: `mcq` | concept: `PEP 8 makes no single-vs-double quote recommendation, but triple-quoted strings always use double quotes`  
   - [x] It states no preference; choose a rule and apply it consistently, switching quote styles only to avoid backslash-escaping a quote inside the string.
   - [ ] It prefers single quotes for short literals and double quotes for anything containing whitespace or punctuation.
   - [ ] It prefers double quotes everywhere, matching the triple-quoted docstring convention required by PEP 257.
   - [ ] It leaves the choice to the author on a line-by-line basis, since the two forms are compiled identically anyway.
   **Expected answer:** It states no preference; choose a rule and apply it consistently, switching quote styles only to avoid backslash-escaping a quote inside the string.

4. **Why does PEP 8 warn specifically about trailing whitespace being hard to detect?**  
   kind: `mcq` | concept: `Extraneous whitespace: inside brackets, before commas/colons, before call and index parentheses, and alignment padding`  
   - [x] A backslash followed by a space and a newline is not treated as a line continuation, producing a confusing error.
   - [ ] A trailing space after a colon can silently change how the following indented block is parsed.
   - [ ] Trailing spaces inside a triple-quoted docstring are stripped by the interpreter, altering the stored text.
   - [ ] A trailing space at the end of an operator line makes Python treat the next line as a separate statement.
   **Expected answer:** A backslash followed by a space and a newline is not treated as a line continuation, producing a confusing error.

5. **According to the lesson, when may you legitimately use more than the uniform single space around a binary operator to show grouping, as in `hypot2 = x*x + y*y`?**  
   kind: `mcq` | concept: `Single spaces around binary operators, with lower-priority operators optionally spaced to show grouping`  
   - [x] Never — you must never exceed one space; the grouping is shown by removing spaces around the higher-priority operators instead.
   - [ ] Only when the expression exceeds the line-length limit and the extra spaces aid the wrap.
   - [ ] Whenever two operators of different priority appear, you may use two spaces around the lower-priority one.
   - [ ] Only around assignment and augmented assignment operators, which may be padded to align a block.
   **Expected answer:** Never — you must never exceed one space; the grouping is shown by removing spaces around the higher-priority operators instead.

6. **PEP 8 says a small `if` body may sometimes share a line with the `if`, but names one case where this is never acceptable. What is it?**  
   kind: `short` | concept: `Extraneous whitespace: inside brackets, before commas/colons, before call and index parentheses, and alignment padding`  
   **Expected answer:** Multi-clause statements — e.g. an `if` with an `else`, or a `try` with a `finally` — must never be written on one line (and long lines should not be folded to make such a form fit).

---

### Lesson 2.2: Trailing Commas and Writing Good Comments

**Concepts:** Trailing commas are mandatory in singleton tuples and should be parenthesized, One-item-per-line plus trailing comma keeps version-control diffs minimal, Comments must stay accurate; a stale comment is worse than none, Block comment formatting: same indentation as the code, '# ' prefix, '#' paragraph separators, Inline comments: used sparingly, two spaces before '#', explain why not what

**Written from source segments:** [3]

#### Lesson content

# Trailing Commas and Writing Good Comments

This lesson covers two small-but-visible parts of PEP 8 style: where trailing commas belong, and how to write comments that help rather than mislead.

---

## Trailing Commas

### The one place a trailing comma is mandatory

A trailing comma is usually optional. The exception is a **tuple of one element** — there, the comma is what makes it a tuple at all. PEP 8 recommends wrapping such a singleton in parentheses, even though the parentheses are technically redundant, because they make the intent obvious to a reader who might otherwise miss a lone comma at the end of a line.

```python
# Correct:
FILES = ('setup.cfg',)

# Wrong:
FILES = 'setup.cfg',
```

Both lines create the same one-element tuple. Only the first one makes that fact easy to see.

### When a redundant trailing comma is still helpful

When a list of values, arguments, or imported items is expected to grow over time, a redundant trailing comma pays off under version control. If every element sits on its own line and every element (including the last) ends in a comma, then adding a new element touches exactly one line in the diff instead of two.

The pattern is:

1. Put each value, argument, or imported name on a line by itself.
2. Always add a trailing comma, including after the last one.
3. Put the closing parenthesis/bracket/brace on the next line.

```python
# Correct:
FILES = [
    'setup.cfg',
    'tox.ini',
    ]
initialize(FILES,
           error=True,
           )
```

### When a trailing comma is just noise

It does **not** make sense to put a trailing comma on the same line as the closing delimiter — the singleton tuple is the only exception to that.

```python
# Wrong:
FILES = ['setup.cfg', 'tox.ini',]
initialize(FILES, error=True,)
```

Here the comma buys nothing: adding an item to a one-line collection changes that line regardless.

---

## Comments

### Accuracy comes first

**Comments that contradict the code are worse than no comments.** A wrong comment actively misleads the next reader; a missing one merely leaves them to read the code. So when the code changes, updating the comments is a priority, not an afterthought.

### Style of the prose

- Comments should be **complete sentences**.
- Capitalize the first word — *unless* it is an identifier that begins with a lower case letter. Never alter the case of an identifier just to satisfy a sentence rule; `foo` is not `Foo`.
- Each sentence in a block comment ends in a period.
- Use one or two spaces after a sentence-ending period in multi-sentence comments, except after the final sentence.
- Make comments clear to other speakers of the language you are writing in.
- Write comments in **English**, unless you are 120% sure the code will never be read by people who don't speak your language.

### Block comments

A block comment applies to some (or all) of the code that follows it and is **indented to the same level as that code** — not flush left, and not to the level of the surrounding block. Each line starts with a `#` and a single space, unless the line is indented text inside the comment (for example, a code sample quoted in the comment). Paragraphs inside a block comment are separated by a line containing a single `#`.

```python
def load(path):
    # Read the whole file into memory.  The files we handle are small
    # enough that streaming would add complexity for no benefit.
    #
    # If that ever changes, switch to an iterator here.
    with open(path) as f:
        return f.read()
```

### Inline comments

Use inline comments **sparingly**. An inline comment sits on the same line as a statement. It must be separated from the statement by **at least two spaces**, and it starts with a `#` and a single space.

An inline comment that states the obvious is not merely useless — it is distracting:

```python
x = x + 1                 # Increment x
```

A comment that explains *why*, which the code cannot say for itself, earns its place:

```python
x = x + 1                 # Compensate for border
```

---

## Docstrings (briefly)

The conventions for documentation strings live in PEP 257. Write docstrings for all public modules, functions, classes, and methods. Non-public methods don't need one, but they should have a comment describing what the method does, placed after the `def` line. Most importantly, the closing `"""` of a multiline docstring goes on a line by itself.


#### Quiz

1. **Which line follows PEP 8 for creating a one-element tuple?**  
   kind: `mcq` | concept: `Trailing commas are mandatory in singleton tuples and should be parenthesized`  
   - [x] FILES = ('setup.cfg',)
   - [ ] FILES = 'setup.cfg',
   - [ ] FILES = ('setup.cfg')
   - [ ] FILES = ['setup.cfg',]
   **Expected answer:** FILES = ('setup.cfg',)

2. **Why does PEP 8 recommend a trailing comma after the final item when each item is on its own line?**  
   kind: `mcq` | concept: `One-item-per-line plus trailing comma keeps version-control diffs minimal`  
   - [x] Adding a later item then changes only one line in a version-control diff
   - [ ] The interpreter otherwise treats the collection as a single concatenated value
   - [ ] It signals to readers that the collection is immutable and should not be edited
   - [ ] It lets the closing delimiter stay on the same line as the last item
   **Expected answer:** Adding a later item then changes only one line in a version-control diff

3. **Is `initialize(FILES, error=True,)` acceptable under PEP 8? Explain in one sentence.**  
   kind: `short` | concept: `One-item-per-line plus trailing comma keeps version-control diffs minimal`  
   **Expected answer:** No — a trailing comma on the same line as the closing delimiter is pointless (the singleton tuple being the only exception); the arguments should each be on their own line with the closing parenthesis on the next line if a trailing comma is wanted.

4. **A comment begins with the name of a variable called `retries`. What does PEP 8 say about capitalization here?**  
   kind: `mcq` | concept: `Comments must stay accurate; a stale comment is worse than none`  
   - [x] Leave it as `retries`, because the case of an identifier must never be altered
   - [ ] Write it as `Retries`, since every comment sentence starts with a capital letter
   - [ ] Rewrite the sentence so no identifier appears first, as identifiers may not open a comment
   - [ ] Either form is fine as long as the comment ends with a period
   **Expected answer:** Leave it as `retries`, because the case of an identifier must never be altered

5. **Which statement about block comments matches the lesson?**  
   kind: `mcq` | concept: `Block comment formatting: same indentation as the code, '# ' prefix, '#' paragraph separators`  
   - [x] Paragraphs are separated by a line containing a single `#`, and the block is indented like the code it describes
   - [ ] Paragraphs are separated by a completely blank line, and the block is aligned at the left margin
   - [ ] Each line begins with `##` and the block sits one level deeper than the code it describes
   - [ ] Paragraphs are separated by a line of `#` characters, and indentation is left to the author
   **Expected answer:** Paragraphs are separated by a line containing a single `#`, and the block is indented like the code it describes

6. **What is the minimum spacing required between a statement and an inline comment's `#`, and why is `x = x + 1  # Increment x` criticized?**  
   kind: `short` | concept: `Inline comments: used sparingly, two spaces before '#', explain why not what`  
   **Expected answer:** At least two spaces must separate the statement from the `#`. The comment is criticized because it states the obvious, making it unnecessary and distracting; a useful inline comment explains something the code cannot say, such as 'Compensate for border'.

---

### Lesson 2.3: Docstrings

**Concepts:** PEP 257 as the reference for docstring conventions, Docstrings required for all public modules, functions, classes, and methods, Comments after the def line for non-public methods, Placement of closing triple quotes in multiline vs. one-liner docstrings

**Written from source segments:** [3, 4]

#### Lesson content

# Docstrings

PEP 8 has relatively little to say about docstrings itself. Instead, it points you at a companion document, **PEP 257**, where "conventions for writing good documentation strings (a.k.a. 'docstrings') are immortalized." What PEP 8 *does* do is state which objects must have one, what to do when they don't, and remind you of the single formatting rule it considers most important.

## Who needs a docstring?

> Write docstrings for all public modules, functions, classes, and methods.

That is the rule, and it covers four kinds of object: modules, functions, classes, and methods — but only the *public* ones. Public here means the parts of your API that a user of the code is expected to touch.

For **non-public** methods, a docstring is *not* necessary. But you are not off the hook: you should still have **a comment that describes what the method does**, and PEP 8 is specific about where that comment goes — it **appears after the `def` line**, not before it.

```python
def _rebalance(self, node):
    # Rotate the subtree rooted at node so that its two children
    # differ in height by at most one.
    ...
```

Note the distinction: a docstring is a string literal that sits as the first statement of the body and is retrievable at runtime via `__doc__`; the non-public alternative is just a `#` comment. Both sit inside the body, after `def`, but only one of them is a docstring.

## The rule PEP 8 singles out: the closing quotes

PEP 8 says that of everything in PEP 257, "most importantly, the `\"\"\"` that ends a multiline docstring should be on a line by itself."

```python
def complex(real=0.0, imag=0.0):
    """Return a foobang

    Optional plotz says to frobnicate the bizbaz first.
    """
```

The opening `"""` is followed immediately by the summary line; the terminating `"""` gets a line to itself.

For **one-liner** docstrings the rule is the opposite: keep the closing `"""` on the same line.

```python
def kos_root():
    """Return an ex-parrot."""
```

So a one-liner really is one line — no line break before the closing quotes, no blank line padding.

## Docstrings versus comments

The comment conventions from the surrounding section of PEP 8 still apply to the comments you write instead of docstrings for non-public methods:

- Comments that contradict the code are worse than no comments; keep them up to date when the code changes.
- Comments should be complete sentences, with the first word capitalized — unless it is an identifier that begins with a lowercase letter, because you never alter the case of identifiers.
- Block comments are indented to the same level as the code they describe, and each line starts with `#` and a single space.

A quick summary table:

| Object | What PEP 8 asks for |
|---|---|
| Public module, function, class, method | Docstring |
| Non-public method | Comment after the `def` line |
| Multiline docstring | Closing `"""` alone on its own line |
| One-liner docstring | Closing `"""` on the same line |


#### Quiz

1. **Which PEP does PEP 8 point to for the detailed conventions on writing docstrings?**  
   kind: `mcq` | concept: `PEP 257 as the reference for docstring conventions`  
   - [x] PEP 257
   - [ ] PEP 484
   - [ ] PEP 3131
   - [ ] PEP 20
   **Expected answer:** PEP 257

2. **According to PEP 8, what should accompany a non-public method that has no docstring, and where should it go?**  
   kind: `mcq` | concept: `Comments after the def line for non-public methods`  
   - [x] A comment describing what the method does, placed after the def line
   - [ ] A block comment describing the method, placed immediately above the def line
   - [ ] A one-liner docstring is still required, just kept shorter than usual
   - [ ] An inline comment on the def line itself, separated by two spaces
   **Expected answer:** A comment describing what the method does, placed after the def line

3. **Rewrite this docstring so it follows PEP 8's rule, and say which rule applies:

```python
def parrot():
    """Return an ex-parrot.
    """
```**  
   kind: `short` | concept: `Placement of closing triple quotes in multiline vs. one-liner docstrings`  
   **Expected answer:** It is a one-liner, so the closing """ belongs on the same line: `"""Return an ex-parrot."""`. Only multiline docstrings put the terminating quotes on a line by themselves.

4. **Which statement correctly describes the placement of the terminating triple quotes?**  
   kind: `mcq` | concept: `Placement of closing triple quotes in multiline vs. one-liner docstrings`  
   - [x] Multiline docstrings end with """ alone on its own line, while one-liners keep the closing """ on the same line
   - [ ] Both multiline and one-liner docstrings should end with """ on a line by itself for consistency
   - [ ] One-liners put the closing """ on the next line, while multiline docstrings end on the last text line
   - [ ] The closing """ always goes on the same line as the last sentence, regardless of length
   **Expected answer:** Multiline docstrings end with """ alone on its own line, while one-liners keep the closing """ on the same line

5. **Name the four kinds of object for which PEP 8 says you should write docstrings when they are public.**  
   kind: `short` | concept: `Docstrings required for all public modules, functions, classes, and methods`  
   **Expected answer:** Modules, functions, classes, and methods.

6. **PEP 8 says comments should be complete sentences with the first word capitalized. What is the stated exception?**  
   kind: `mcq` | concept: `Comments after the def line for non-public methods`  
   - [x] When the first word is an identifier that begins with a lowercase letter, since identifier case is never altered
   - [ ] When the comment is an inline comment, which is written entirely in lowercase
   - [ ] When the comment sits inside a block comment paragraph rather than starting one
   - [ ] When the comment describes a non-public method, where fragments are allowed
   **Expected answer:** When the first word is an identifier that begins with a lowercase letter, since identifier case is never altered

---

## Module 3: Naming Conventions and Interface Design

### Lesson 3.1: Naming Styles and Underscore Conventions

**Concepts:** The overriding principle: public API names reflect usage, not implementation, Recognizing naming styles: lowercase, CapWords, mixedCase, and underscore variants, Leading and trailing underscore conventions, including weak internal-use markers and keyword-clash suffixes, Name mangling of double-leading-underscore class attributes and the reserved status of dunder names, Applied conventions for modules, packages, classes, and type variables

**Written from source segments:** [4]

#### Lesson content

# Naming Styles and Underscore Conventions

Python's standard library naming is, by PEP 8's own admission, "a bit of a mess." It will never be completely consistent. New modules and packages — including third-party frameworks — should follow the recommended standards, but when you're working inside an existing library that already uses a different style, **internal consistency wins**. A file that is half `mixedCase` and half `lower_case_with_underscores` is worse than a file that is consistently "wrong."

## The Overriding Principle

> Names that are visible to the user as public parts of the API should follow conventions that reflect **usage** rather than **implementation**.

In other words: name a public thing after what a caller does with it, not after how you happened to build it. If your function returns a user record, call it `get_user`, not `select_row_from_users_table`. The implementation may change; the public name should not have to.

## The Catalogue of Naming Styles

Before choosing a style, it helps to be able to *recognize* the styles, independently of what they're used for. The commonly distinguished styles are:

| Style | Example |
|---|---|
| single lowercase letter | `b` |
| single uppercase letter | `B` |
| lowercase | `lowercase` |
| lower_case_with_underscores | `lower_case_with_underscores` |
| UPPERCASE | `UPPERCASE` |
| UPPER_CASE_WITH_UNDERSCORES | `MAX_RETRIES` |
| CapitalizedWords (CapWords, CamelCase, StudlyCaps) | `CapitalizedWords` |
| mixedCase | `mixedCase` |
| Capitalized_Words_With_Underscores | `Capitalized_Words_With_Underscores` (ugly!) |

Two details worth memorizing:

- **`mixedCase` differs from `CapitalizedWords` only in the initial lowercase character.** They are not the same style, and PEP 8 treats them separately.
- **When an acronym appears in CapWords, capitalize the whole acronym.** `HTTPServerError` is better than `HttpServerError`.

### Prefix grouping

There is also the style of using a short unique prefix to group related names. Python barely uses it, but you will meet it: `os.stat()` returns an object whose items are traditionally named `st_mode`, `st_size`, `st_mtime`. The `st_` prefix emphasizes the correspondence with the fields of the POSIX `struct stat`, which helps programmers who already know that C interface.

The X11 library gives every public function a leading `X`. In Python this is generally deemed unnecessary, because attribute and method names are already prefixed by an object and function names are already prefixed by a module name — `socket.socket` needs no extra tag.

## Leading and Trailing Underscores

The following special forms are recognized, and they can generally be combined with any of the case conventions above.

### `_single_leading_underscore` — weak "internal use" indicator

This says "not part of the public API; touch at your own risk." It is a *convention* backed by one small piece of real behavior: `from M import *` does not import names beginning with an underscore.

```python
# module m.py
_cache = {}          # internal
def fetch(key): ...  # public

# elsewhere
from m import *      # brings in fetch, but not _cache
from m import _cache # ...still works if you ask for it explicitly
```

That last line is why the indicator is called *weak*: nothing is actually hidden.

A related use: when a C or C++ extension module has an accompanying Python module giving a higher-level interface, the C/C++ module takes the leading underscore — e.g. `_socket` under `socket`.

### `single_trailing_underscore_` — avoid a keyword clash

When the name you want is a Python keyword, append one underscore. Do not misspell it (`klass`) and do not abbreviate it.

```python
tkinter.Toplevel(master, class_='ClassName')
```

`class` is reserved, so the parameter is `class_`. Same trick gives `from_`, `lambda_`, `import_`.

### `__double_leading_underscore` — name mangling

When used as a **class attribute** name, two leading underscores invoke *name mangling*: inside `class FooBar`, the name `__boo` is rewritten by the interpreter to `_FooBar__boo`.

```python
class FooBar:
    def __init__(self):
        self.__boo = 1

f = FooBar()
f.__boo          # AttributeError
f._FooBar__boo   # 1
```

The mangling is textual and happens at compile time inside the class body. Its purpose is to keep a subclass from accidentally colliding with the attribute, not to provide security — the mangled name is perfectly reachable.

### `__double_leading_and_trailing_underscore__` — "magic" names

These are "magic" objects or attributes living in namespaces controlled by the language: `__init__`, `__import__`, `__file__`. Note that this form does **not** trigger name mangling — the trailing underscores switch it off. The rule is blunt: **never invent such names**; only use the ones that are documented.

## Names to Avoid

Never use `l` (lowercase el), `O` (uppercase oh), or `I` (uppercase eye) as single-character variable names. In many fonts they are indistinguishable from the numerals one and zero. When tempted to write `l`, write `L`.

Identifiers in the standard library must also be ASCII-compatible, as described in the policy section of PEP 3131.

## Where the Styles Get Used

- **Modules**: short, all-lowercase names; underscores allowed if they improve readability.
- **Packages**: short, all-lowercase names; underscores discouraged.
- **Classes**: CapWords normally. If the interface is documented and used primarily as a callable, the function naming convention may be used instead. Builtins follow a separate convention: most are single words (or two words run together), with CapWords reserved for exception names and builtin constants.
- **Type variables** (PEP 484): CapWords, preferring short names — `T`, `AnyStr`, `Num`. Add the suffix `_co` or `_contra` for covariant or contravariant behavior respectively.


#### Quiz

1. **Inside `class FooBar`, an attribute written `self.__boo` is stored under what name?**  
   kind: `mcq` | concept: `Name mangling of double-leading-underscore class attributes and the reserved status of dunder names`  
   - [x] `_FooBar__boo`, because two leading underscores in a class body invoke name mangling
   - [ ] `__boo`, unchanged, but hidden from `dir()` and from attribute access outside the class
   - [ ] `_boo`, since the interpreter collapses the doubled underscore to a single internal-use marker
   - [ ] `FooBar.__boo`, a private slot that raises `AttributeError` for any access from outside the class
   **Expected answer:** `_FooBar__boo`, because two leading underscores in a class body invoke name mangling

2. **Why does PEP 8 call `_single_leading_underscore` a *weak* internal-use indicator?**  
   kind: `mcq` | concept: `Leading and trailing underscore conventions, including weak internal-use markers and keyword-clash suffixes`  
   - [x] Because the only real behavior it triggers is exclusion from `from M import *`; an explicit import of the name still succeeds
   - [ ] Because it is honored for module-level functions but silently ignored for class attributes and methods
   - [ ] Because it hides the name from other modules unless they are in the same package directory
   - [ ] Because linters warn about it but the interpreter attaches no meaning whatsoever to the underscore
   **Expected answer:** Because the only real behavior it triggers is exclusion from `from M import *`; an explicit import of the name still succeeds

3. **You need a keyword argument whose natural name is the reserved word `class`. What does PEP 8 tell you to write, and what is the general form of the rule?**  
   kind: `short` | concept: `Leading and trailing underscore conventions, including weak internal-use markers and keyword-clash suffixes`  
   **Expected answer:** Write `class_` — a single trailing underscore is the convention for avoiding a clash with a Python keyword (as in `tkinter.Toplevel(master, class_='ClassName')`), rather than misspelling or abbreviating the word.

4. **Which statement about naming styles matches PEP 8?**  
   kind: `mcq` | concept: `Recognizing naming styles: lowercase, CapWords, mixedCase, and underscore variants`  
   - [x] `mixedCase` and `CapitalizedWords` differ only in whether the first character is lowercase
   - [ ] `CapitalizedWords` and `Capitalized_Words_With_Underscores` are treated as the same style
   - [ ] `CamelCase` and `StudlyCaps` name two distinct styles that differ in acronym handling
   - [ ] `lowercase` and `lower_case_with_underscores` are interchangeable names for one style
   **Expected answer:** `mixedCase` and `CapitalizedWords` differ only in whether the first character is lowercase

5. **State the overriding principle PEP 8 gives for names that are visible as public parts of an API.**  
   kind: `short` | concept: `The overriding principle: public API names reflect usage, not implementation`  
   **Expected answer:** They should follow conventions that reflect usage rather than implementation — the name should describe what a caller does with the thing, not how it happens to be built internally.

6. **A class in your library exposes an error type for a failing HTTP request. Which name best follows PEP 8?**  
   kind: `mcq` | concept: `Recognizing naming styles: lowercase, CapWords, mixedCase, and underscore variants`  
   - [x] `HTTPServerError`
   - [ ] `HttpServerError`
   - [ ] `httpServerError`
   - [ ] `HTTP_Server_Error`
   **Expected answer:** `HTTPServerError`

---

### Lesson 3.2: Prescriptive Naming Rules by Kind of Name

**Concepts:** Names to avoid and ASCII-compatible identifiers, CapWords conventions for classes, exceptions, and type variables, Lowercase-with-underscores for modules, functions, variables, and methods, Underscore conventions: leading, trailing, and name mangling, Argument naming: self, cls, and keyword clashes

**Written from source segments:** [4, 5]

#### Lesson content

# Prescriptive Naming Rules by Kind of Name

PEP 8's descriptive section tells you how to *recognize* naming styles (`lowercase`, `CapWords`, `UPPER_CASE_WITH_UNDERSCORES`, and so on). The prescriptive section tells you *which style goes with which kind of name*. This lesson walks through the rules, one kind of name at a time.

A reminder of the overriding principle before we start: **names visible to the user as public parts of the API should follow conventions that reflect usage rather than implementation.** And a practical caveat: Python's own standard library is inconsistent, so when you work inside an existing library that already uses a different style, internal consistency wins over these rules.

---

## Names to avoid

Never use `l` (lowercase el), `O` (uppercase oh), or `I` (uppercase eye) as **single-character** variable names. In many fonts these are indistinguishable from the digits `1` and `0`.

```python
for l in range(10):   # bad: is that an el or a one?
    ...
for L in range(10):   # if you're tempted to use 'l', use 'L'
    ...
```

Note the scope of the rule: it is about *single-character* names. `flag`, `total`, and `Order` are unaffected.

## ASCII compatibility

Identifiers used in the standard library must be ASCII compatible, as described in the policy section of PEP 3131. Python 3 permits non-ASCII identifiers in general, but stdlib code does not use them.

## Packages and modules

- Modules: short, **all-lowercase** names. Underscores are allowed if they improve readability (`json`, `csv`, `unicode_escape`).
- Packages: short, **all-lowercase** names too, but underscores are *discouraged* here.
- When a C/C++ extension module is wrapped by a higher-level Python module of the same name, the C module gets a **leading underscore**: `_socket` under `socket`, `_pickle` under `pickle`.

## Classes

Class names normally use **CapWords**: `HTTPServerError`, `QueueManager`. When an acronym appears in a CapWords name, capitalize the whole acronym — `HTTPServerError`, not `HttpServerError`.

There is one escape hatch: if the interface is documented and used primarily as a *callable*, the function naming convention (lowercase with underscores) may be used instead. This is why things like `namedtuple` don't look like classes.

Builtins follow a separate convention: most builtin names are single words or two words run together (`int`, `dict`, `staticmethod`), with CapWords reserved for exception names and builtin constants (`ValueError`, `True`).

## Type variables

Type variables introduced by PEP 484 normally use **CapWords, preferring short names**: `T`, `AnyStr`, `Num`. Add the suffix `_co` for covariant and `_contra` for contravariant type variables:

```python
from typing import TypeVar

VT_co = TypeVar('VT_co', covariant=True)
KT_contra = TypeVar('KT_contra', contravariant=True)
```

## Exceptions

Exceptions should be classes, so the class convention (CapWords) applies. Additionally, append the suffix **`Error`** if the exception really is an error: `ConnectionError`, `ConfigParseError`. An exception used for non-error control flow (`StopIteration`) does not take the suffix.

## Global variables

The conventions are about the same as those for functions: lowercase with underscores. (These are assumed to be for use inside one module only.) Modules designed for `from M import *` should use the `__all__` mechanism to prevent exporting globals, or the older convention of prefixing such globals with a single underscore to mark them module non-public.

## Functions and variables

Lowercase, with words separated by underscores as needed for readability: `send_message`, `retry_count`. Variable names follow the same rule as function names.

`mixedCase` is allowed **only** where it is already the prevailing style — for example `threading.py` — to retain backwards compatibility.

## Function and method arguments

- Always use `self` for the first argument to instance methods.
- Always use `cls` for the first argument to class methods.
- If an argument name clashes with a reserved keyword, append a **single trailing underscore** rather than abbreviating or misspelling it: `class_` is better than `clss`. Better still, find a synonym that avoids the clash.

```python
class Widget:
    def render(self, class_=None):
        ...

    @classmethod
    def from_config(cls, config):
        ...
```

## Method names and instance variables

Use the function naming rules: lowercase with underscores. Then:

- One **leading underscore** for non-public methods and instance variables (`self._cache`).
- Two **leading underscores** to invoke Python's name mangling, which avoids clashes with subclasses. If class `Foo` has an attribute `__a`, it cannot be reached as `Foo.__a`; inside the class body it becomes `_Foo__a`, and an insistent user can still write `Foo._Foo__a`.

```python
class Foo:
    def __init__(self):
        self.__a = 1     # stored as _Foo__a

Foo().__a         # AttributeError
Foo()._Foo__a     # 1 — mangling hides, it does not protect
```

Double leading underscores should generally be used **only** to avoid name conflicts in classes designed to be subclassed — not as a general "private" marker. Note also that only the *simple* class name is used in the mangled name, so a subclass with the same class name and attribute name can still collide.

Don't confuse this with `__double_leading_and_trailing_underscore__`, which marks "magic" attributes such as `__init__` or `__file__`. Never invent such names; only use the documented ones.

## Constants

Constants are usually defined at module level and written in **all capitals with underscores** separating words: `MAX_OVERFLOW`, `TOTAL`.

---

## Quick reference

| Kind of name | Convention | Example |
|---|---|---|
| Package | short, all lowercase, underscores discouraged | `email` |
| Module | short, all lowercase, underscores ok | `unicode_escape` |
| Class | CapWords | `HTTPServerError` |
| Type variable | short CapWords, `_co` / `_contra` suffixes | `VT_co` |
| Exception | CapWords + `Error` if it is an error | `ConfigParseError` |
| Function / variable / global | lowercase_with_underscores | `parse_line` |
| Instance method 1st arg | `self` | `self` |
| Class method 1st arg | `cls` | `cls` |
| Keyword-clashing argument | trailing underscore | `class_` |
| Non-public attribute | one leading underscore | `_cache` |
| Subclass-collision-proof attribute | two leading underscores | `__a` |
| Constant | UPPER_CASE_WITH_UNDERSCORES | `MAX_OVERFLOW` |


#### Quiz

1. **Which single-character variable names does PEP 8 tell you never to use, and why?**  
   kind: `short` | concept: ``  
   **Expected answer:** 'l' (lowercase el), 'O' (uppercase oh), and 'I' (uppercase eye), because in some fonts they are indistinguishable from the numerals one and zero. If tempted to use 'l', use 'L' instead.

2. **You are declaring a contravariant type variable for key types. Which name best follows PEP 8?**  
   kind: `mcq` | concept: ``  
   - [x] KT_contra = TypeVar('KT_contra', contravariant=True)
   - [ ] key_type_contravariant = TypeVar('key_type_contravariant', contravariant=True)
   - [ ] ContravariantKeyType = TypeVar('ContravariantKeyType', contravariant=True)
   - [ ] _KT = TypeVar('_KT', contravariant=True)
   **Expected answer:** KT_contra = TypeVar('KT_contra', contravariant=True)

3. **A function argument would naturally be called `class`, which is a reserved keyword. What does PEP 8 recommend?**  
   kind: `mcq` | concept: ``  
   - [x] Append a single trailing underscore, giving `class_`, or better, pick a synonym that avoids the clash
   - [ ] Prefix it with a single underscore, giving `_class`, to signal the keyword collision
   - [ ] Shorten it to `clss`, since abbreviations read better than trailing punctuation
   - [ ] Use CapWords, giving `Class`, because capitalization removes the conflict
   **Expected answer:** Append a single trailing underscore, giving `class_`, or better, pick a synonym that avoids the clash

4. **Inside `class Foo`, an attribute is named `__a`. What does Python's name mangling do, and what does that mean for access from outside?**  
   kind: `short` | concept: ``  
   **Expected answer:** The name is mangled with the class name to `_Foo__a`, so `Foo.__a` does not work; an insistent user can still reach it via `Foo._Foo__a`. Mangling avoids accidental clashes with subclass attributes, it does not make the attribute truly private.

5. **Which naming choice conforms to PEP 8's prescriptive rules?**  
   kind: `mcq` | concept: ``  
   - [x] A module-level constant written `MAX_OVERFLOW`
   - [ ] A package named `data_processing_utilities` for clarity
   - [ ] A class named `HttpServerError` so the acronym reads as a word
   - [ ] A class method whose first argument is named `self`
   **Expected answer:** A module-level constant written `MAX_OVERFLOW`

6. **An extension module written in C is wrapped by a higher-level Python module offering a more object-oriented interface. How should the C module be named?**  
   kind: `mcq` | concept: ``  
   - [x] With a leading underscore, e.g. `_socket`, while the Python wrapper keeps the plain name
   - [ ] With a trailing underscore, e.g. `socket_`, to mark it as the lower-level layer
   - [ ] In CapWords, e.g. `Socket`, since compiled modules follow the class convention
   - [ ] In all capitals, e.g. `SOCKET`, to distinguish compiled code from Python code
   **Expected answer:** With a leading underscore, e.g. `_socket`, while the Python wrapper keeps the plain name

---

### Lesson 3.3: Designing for Inheritance and Public Interfaces

**Concepts:** Classifying attributes as public, subclass API, or base-class-only, Properties as the upgrade path from plain data attributes, Name mangling with double leading underscores and its narrow justification, Marking public vs. internal interfaces with documentation, __all__, and leading underscores

**Written from source segments:** [5]

#### Lesson content

# Designing for Inheritance and Public Interfaces

When you write a class, you are also writing a promise. Everything a user of your class can reach is something they may come to depend on. PEP 8 asks you to make that promise deliberately rather than by accident.

## Three audiences, not two

Before writing a class, decide for **every method and instance variable** (collectively: *attributes*) who it is for. There are three answers:

1. **Public** — attributes you expect unrelated clients of your class to use. Using them commits you to avoiding backwards-incompatible changes.
2. **Subclass API** (what other languages call *protected*) — attributes intended for people who inherit from your class to call or override, but not for ordinary clients.
3. **Base-class-only** — internal machinery that even subclasses have no business touching.

> **If in doubt, choose non-public.** It is easy to make an attribute public later; it is painful to take a published attribute away.

PEP 8 deliberately avoids the word *private*: nothing in Python is truly private without an unreasonable amount of work. Non-public simply means "you get no guarantees; this may change or disappear."

## The naming conventions that express those decisions

| Intent | Naming |
|---|---|
| Public | no leading underscore: `size`, `render()` |
| Non-public / internal | one leading underscore: `_cache`, `_recompute()` |
| Base-class-only in a class designed for subclassing | two leading underscores: `__index` |
| Public name clashing with a keyword | one *trailing* underscore: `class_`, `lambda_` |

Note the trailing-underscore rule: `class_` is preferred over an abbreviation or a corrupted spelling like `clss` or `klass`. (Better still, find a synonym.) The one standing exception is `cls`, which is the preferred spelling for any variable known to be a class, especially the first argument of a classmethod. Instance methods always take `self` first.

## Prefer plain attributes; reach for properties later

For simple public data, **expose the attribute name itself** — no `get_x()`/`set_x()` accessor pairs. Java-style accessors buy you nothing in Python, because Python gives you an upgrade path: if the attribute later needs behavior, convert it into a `property` and callers never change.

```python
class Rectangle:
    def __init__(self, width, height):
        self.width = width       # plain public data attribute
        self.height = height

# Later, width must be validated. Callers still write rect.width.
class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        if value <= 0:
            raise ValueError("width must be positive")
        self._width = value
```

Two cautions come with properties:

- Keep the behavior **side-effect free** where you can. Caching is a generally acceptable exception.
- **Avoid properties for computationally expensive work.** Attribute syntax tells the caller "this is cheap"; hiding a database query or a full re-parse behind `obj.total` is a lie. Make that a method.

## When double leading underscores are justified

`__name` inside a class body triggers Python's *name mangling*: in class `Foo`, `__a` becomes `_Foo__a`. So `Foo.__a` from outside doesn't work, though an insistent user can still write `Foo._Foo__a`.

The justification is narrow: **avoiding accidental attribute name collisions in a class designed to be subclassed.** It is not a security feature and not a general-purpose "make it private" button. Use one underscore for ordinary non-public attributes; save two for base-class-only state in an inheritance-heavy design.

```python
class Widget:
    def __init__(self):
        self.__registry = {}     # becomes _Widget__registry

class FancyWidget(Widget):
    def __init__(self):
        super().__init__()
        self.__registry = []     # becomes _FancyWidget__registry - no clash
```

Caveats worth remembering:

- Only the *simple* class name is mangled in, so a subclass with the same class name **and** the same attribute name still collides.
- Mangling makes debugging and `__getattr__()` less convenient, though the algorithm is documented and easy to do by hand.
- Not everyone likes it. Balance the risk of accidental clashes against use by advanced callers.

## Public vs. internal interfaces at module level

Backwards-compatibility guarantees apply **only to public interfaces**, so users must be able to tell which is which.

- **Documented interfaces are public**, unless the docs explicitly mark them provisional or internal. **All undocumented interfaces should be assumed internal.**
- Modules should declare their public API explicitly with `__all__`, which also supports introspection. Setting `__all__ = []` says the module has no public API.
- `__all__` is not a substitute for underscores: internal packages, modules, classes, functions and attributes should *still* carry a single leading underscore.
- Containment propagates: if a package, module or class is internal, everything inside it is internal too.
- **Imported names are an implementation detail.** If `mymod` does `import os`, other code must not rely on `mymod.os`. The exceptions are explicitly documented re-exports, such as `os.path` or a package `__init__` that deliberately surfaces submodule functionality.

```python
"""Public API: load_config, ConfigError."""
__all__ = ['load_config', 'ConfigError']

import json          # implementation detail; not part of this module's API

_DEFAULT_PATH = '/etc/app.conf'   # module non-public

def _parse(text):     # internal helper
    ...

def load_config(path=_DEFAULT_PATH):
    ...
```

For globals in modules designed for `from M import *`, `__all__` is the modern mechanism to prevent exporting names; the older convention is prefixing such globals with an underscore.

## Exceptions and constants, briefly

Since exceptions are classes, they follow the class naming convention — and take the suffix `Error` when the exception really is an error (`ConfigError`). Module-level constants are `ALL_CAPS_WITH_UNDERSCORES`, e.g. `MAX_OVERFLOW`.


#### Quiz

1. **You are unsure whether a helper method on a new class will be useful to outside callers. What does PEP 8 advise?**  
   kind: `mcq` | concept: `Classifying attributes as public, subclass API, or base-class-only`  
   - [x] Make it non-public, since widening access later is easier than withdrawing a published attribute
   - [ ] Make it public, since users can always ignore names they don't need
   - [ ] Give it two leading underscores until at least one caller asks for it
   - [ ] Leave it undecided and document both possibilities in the docstring
   **Expected answer:** Make it non-public, since widening access later is easier than withdrawing a published attribute

2. **Which use of a property does the lesson warn against?**  
   kind: `mcq` | concept: `Properties as the upgrade path from plain data attributes`  
   - [x] Wrapping an operation that is computationally expensive, because attribute syntax implies cheap access
   - [ ] Wrapping an attribute that caches its result, because caching is a side effect
   - [ ] Wrapping a value that was previously a plain public data attribute, because callers must be updated
   - [ ] Wrapping an attribute whose setter can raise an exception, because attribute assignment should never fail
   **Expected answer:** Wrapping an operation that is computationally expensive, because attribute syntax implies cheap access

3. **In a class named `Foo`, an attribute written as `self.__a` is stored under what mangled name, and what is the one situation PEP 8 says justifies this style?**  
   kind: `short` | concept: `Name mangling with double leading underscores and its narrow justification`  
   **Expected answer:** It is stored as `_Foo__a`. Double leading underscores are justified to avoid accidental attribute name collisions in a class that is designed to be subclassed (base-class-only state that subclasses should not touch) — not as a general privacy or security mechanism.

4. **A module sets `__all__ = ['run']`. What follows for the module's other names?**  
   kind: `mcq` | concept: `Marking public vs. internal interfaces with documentation, __all__, and leading underscores`  
   - [x] Internal names should still be given a single leading underscore, since __all__ alone does not mark them
   - [ ] They automatically become internal, so leading underscores on them would be redundant
   - [ ] They become internal only if they are also undocumented; documented ones stay public
   - [ ] They can be accessed only through name mangling, since __all__ hides them from attribute lookup
   **Expected answer:** Internal names should still be given a single leading underscore, since __all__ alone does not mark them

5. **Module `report` contains the statement `import json`. May another module rely on `report.json`?**  
   kind: `mcq` | concept: `Marking public vs. internal interfaces with documentation, __all__, and leading underscores`  
   - [x] No — imported names are an implementation detail unless the module explicitly documents them as part of its API
   - [ ] Yes — any name reachable without a leading underscore carries the usual compatibility guarantee
   - [ ] Yes, but only if `report` does not define `__all__`
   - [ ] No — indirect access through another module is a syntax error in Python
   **Expected answer:** No — imported names are an implementation detail unless the module explicitly documents them as part of its API

6. **A public attribute of your class would naturally be called `class`, which is a reserved keyword. What spelling does PEP 8 recommend, and what does it advise against?**  
   kind: `short` | concept: `Classifying attributes as public, subclass API, or base-class-only`  
   **Expected answer:** Append a single trailing underscore: `class_`. Avoid abbreviations or corrupted spellings such as `clss`; better still, pick a synonym. (`cls` remains the preferred spelling for a variable known to be a class, especially a classmethod's first argument.)

---

## Module 4: Programming Recommendations and Annotations

### Lesson 4.1: Portability, Comparisons, and Exceptions

**Concepts:** Writing implementation-portable code (''.join() over repeated +=), Identity comparison to singletons like None, and is not over not ... is, Implementing all six rich comparisons, aided by functools.total_ordering, Exception design: subclass Exception, name with Error, chain with raise X from Y, Narrow try clauses and specific except clauses instead of bare except

**Written from source segments:** [5, 6]

#### Lesson content

# Portability, Comparisons, and Exceptions

PEP 8's "Programming Recommendations" section moves beyond layout and naming into questions of *behavior*: how to write code that works well across Python implementations, how to compare objects, and how to design and handle exceptions. This lesson covers those recommendations.

---

## 1. Don't disadvantage other Python implementations

CPython is not the only Python. PyPy, Jython, IronPython, Cython and others all run Python code, and they don't share CPython's internal tricks. Code should be written so it doesn't penalize them.

The classic example is in-place string concatenation:

```python
# Fragile: relies on a CPython refcounting optimization
s = ""
for chunk in chunks:
    s += chunk
```

CPython *sometimes* mutates a string in place when it can prove the old value has only one reference, making `a += b` look cheap. That optimization is fragile even in CPython (it only works for some types) and is absent entirely in implementations that don't use reference counting. Without it, each `+=` copies the whole accumulated string, giving quadratic behavior.

In performance-sensitive library code, use `''.join()` instead:

```python
# Portable: linear time everywhere
s = ''.join(chunks)
```

---

## 2. Comparisons to singletons

Comparisons to singletons like `None` should always use `is` or `is not`, never `==` or `!=`. A custom class can define `__eq__` to return anything it likes; identity comparison to a singleton cannot be fooled and is faster.

Also beware of writing `if x` when you really mean `if x is not None`. This bites hardest with arguments that default to `None`:

```python
def f(items=None):
    if not items:            # Wrong: an empty list was explicitly passed!
        items = default_items()
    ...
```

If the caller passes `[]` or `0` or `''`, the value *was* supplied, but it is false in a boolean context, so the code silently overrides it. Write `if items is None:` when you mean "the caller didn't supply one."

Prefer `is not` over `not ... is`. The two are functionally identical; the first reads better.

```python
# Correct:
if foo is not None:
    ...

# Wrong:
if not foo is None:
    ...
```

---

## 3. Rich comparisons: implement all six

When you give a class ordering behavior, implement all six rich comparison operations — `__eq__`, `__ne__`, `__lt__`, `__le__`, `__gt__`, `__ge__` — rather than relying on other code to exercise only the one you bothered to write.

To cut the work, `functools.total_ordering()` generates the missing methods from `__eq__` plus one ordering method:

```python
import functools

@functools.total_ordering
class Version:
    def __init__(self, parts):
        self.parts = tuple(parts)

    def __eq__(self, other):
        return self.parts == other.parts

    def __lt__(self, other):
        return self.parts < other.parts
```

Why not rely on Python's reflexivity? PEP 207 says the interpreter *may* swap `y > x` with `x < y`, `y >= x` with `x <= y`, and may swap the arguments of `x == y` and `x != y`. Sorting guarantees are narrow: `sort()` and `min()` are guaranteed to use `<`, and `max()` uses `>`. Those guarantees cover only a few contexts, so implementing all six avoids confusion elsewhere.

---

## 4. `def`, not a lambda assignment

```python
# Correct:
def f(x): return 2*x

# Wrong:
f = lambda x: 2*x
```

With `def`, the resulting function object's name is `'f'`, which shows up usefully in tracebacks and reprs; the lambda form leaves the generic `'<lambda>'`. Assigning a lambda to a name also throws away the only advantage a lambda has over `def` — that it can be embedded inside a larger expression.

---

## 5. Designing exceptions

**Derive from `Exception`, not `BaseException`.** Direct inheritance from `BaseException` is reserved for exceptions where catching them is almost always the wrong thing to do (like `KeyboardInterrupt` and `SystemExit`).

**Design hierarchies around what catchers need.** Base the distinctions in your exception hierarchy on the questions code catching the exceptions is likely to ask, not on the places in your source where you happen to raise them. Aim to answer "What went wrong?" programmatically rather than merely signalling "A problem occurred." PEP 3151 is the canonical example: the builtin hierarchy learned this lesson by replacing errno introspection with classes like `FileNotFoundError` and `PermissionError`.

**Naming.** Class naming conventions apply; add the suffix `Error` if the exception is an error. Non-error exceptions used for non-local flow control or other signalling need no special suffix.

**Chaining.** Use `raise X from Y` to indicate explicit replacement without losing the original traceback. When you deliberately suppress the inner exception with `raise X from None`, make sure relevant details survive — e.g. preserve the attribute name when converting a `KeyError` into an `AttributeError`, or embed the original exception's text in the new message.

```python
try:
    return self._data[name]
except KeyError:
    raise AttributeError(name) from None
```

---

## 6. Catching exceptions

Mention specific exceptions whenever possible instead of using a bare `except:`:

```python
try:
    import platform_specific_module
except ImportError:
    platform_specific_module = None
```

A bare `except:` is equivalent to `except BaseException:`. It catches `SystemExit` and `KeyboardInterrupt`, making the program hard to interrupt with Control-C, and it can disguise other problems. If you genuinely want everything that signals a program error, write `except Exception:`.

Limit bare `except:` to two cases:

1. The handler prints or logs the traceback, so at least the user knows something went wrong.
2. The code does cleanup and then re-raises with a bare `raise`. (`try...finally` is often a better fit here.)

When catching operating system errors, prefer the explicit exception hierarchy introduced in Python 3.3 over introspecting `errno` values.

**Keep the `try` clause minimal.** Everything inside `try` is a candidate for being caught, so extra code masks bugs:

```python
# Correct:
try:
    value = collection[key]
except KeyError:
    return key_not_found(key)
else:
    return handle_value(value)

# Wrong:
try:
    # Too broad!
    return handle_value(collection[key])
except KeyError:
    # Will also catch KeyError raised by handle_value()
    return key_not_found(key)
```

The `else:` clause exists precisely so the follow-up work happens outside the protected block.

---

## 7. Resources and context managers

When a resource is local to a section of code, use a `with` statement so it is cleaned up promptly and reliably; `try/finally` is also acceptable.

Invoke context managers through separate functions or methods whenever they do something other than acquire and release a resource:

```python
# Correct:
with conn.begin_transaction():
    do_stuff_in_transaction(conn)

# Wrong:
with conn:
    do_stuff_in_transaction(conn)
```

The second form gives the reader no hint that `__enter__`/`__exit__` are managing a transaction rather than just closing the connection. Be explicit.

---

## 8. Be consistent in return statements

Either every `return` in a function returns an expression, or none of them do. If any returns a value, then returns with no value should say `return None` explicitly, and there should be an explicit return at the end of the function if it's reachable.

```python
# Correct:
def foo(x):
    if x >= 0:
        return math.sqrt(x)
    else:
        return None

def bar(x):
    if x < 0:
        return None
    return math.sqrt(x)

# Wrong:
def foo(x):
    if x >= 0:
        return math.sqrt(x)
    # falls off the end, implicitly returning None
```


#### Quiz

1. **Why does PEP 8 recommend ''.join() over repeated a += b for building strings in performance-sensitive library code?**  
   kind: `mcq` | concept: `Writing implementation-portable code (''.join() over repeated +=)`  
   - [x] The in-place concatenation speedup is a fragile CPython-only optimization, absent in implementations that don't use refcounting, so += can become quadratic there
   - [ ] The += operator is deprecated for strings and will raise a warning in future Python versions
   - [ ] ''.join() releases the GIL while copying, so it parallelizes across cores on every implementation
   - [ ] String objects are mutable in CPython but immutable elsewhere, so += produces different results across implementations
   **Expected answer:** The in-place concatenation speedup is a fragile CPython-only optimization, absent in implementations that don't use refcounting, so += can become quadratic there

2. **A function has a parameter `items=None` and wants to detect whether the caller supplied a value. Why is `if not items:` the wrong test?**  
   kind: `short` | concept: `Identity comparison to singletons like None, and is not over not ... is`  
   **Expected answer:** Because a value the caller genuinely supplied — such as an empty list, 0, or '' — is false in a boolean context, so the function would wrongly treat it as 'not supplied'. The correct test is `if items is None:`.

3. **What does PEP 8 say about relying on Python's comparison reflexivity instead of implementing all six rich comparison methods?**  
   kind: `mcq` | concept: `Implementing all six rich comparisons, aided by functools.total_ordering`  
   - [x] The interpreter may swap y > x with x < y and may swap the arguments of == and !=, but the guarantees are narrow (sort()/min() use <, max() uses >), so all six should still be implemented
   - [ ] Reflexivity is fully guaranteed by PEP 207, so implementing __eq__ and __lt__ is always sufficient in every context
   - [ ] The interpreter never swaps operands, so each of the six operators must be defined or the comparison raises TypeError immediately
   - [ ] Reflexivity applies only to == and !=; ordering operators are always derived automatically from __lt__ by the interpreter
   **Expected answer:** The interpreter may swap y > x with x < y and may swap the arguments of == and !=, but the guarantees are narrow (sort()/min() use <, max() uses >), so all six should still be implemented

4. **According to the lesson, what is the concrete benefit of `def f(x): return 2*x` over `f = lambda x: 2*x`?**  
   kind: `mcq` | concept: `Writing implementation-portable code (''.join() over repeated +=)`  
   - [x] The function object's name is 'f' rather than '<lambda>', which is more useful in tracebacks and reprs
   - [ ] The def form is compiled to faster bytecode because it can be given a docstring
   - [ ] The lambda form cannot accept default arguments or keyword arguments, unlike def
   - [ ] The def form creates a closure over the enclosing scope while the lambda form does not
   **Expected answer:** The function object's name is 'f' rather than '<lambda>', which is more useful in tracebacks and reprs

5. **What is wrong with `try: return handle_value(collection[key]) except KeyError: return key_not_found(key)`, and how should it be restructured?**  
   kind: `short` | concept: `Narrow try clauses and specific except clauses instead of bare except`  
   **Expected answer:** The try clause is too broad: a KeyError raised inside handle_value() would also be caught, masking a bug. Restrict the try to `value = collection[key]`, and put `return handle_value(value)` in an `else:` clause.

6. **Which statement about exception design and handling matches PEP 8's recommendations?**  
   kind: `mcq` | concept: `Exception design: subclass Exception, name with Error, chain with raise X from Y`  
   - [x] Derive from Exception rather than BaseException, and use `except Exception:` rather than a bare except when you want to catch all program errors
   - [ ] Derive from BaseException so that your exception can never be swallowed by a bare except clause elsewhere in the program
   - [ ] Use a bare except: freely, since it is equivalent to `except Exception:` and simply reads more concisely
   - [ ] Give every exception class the suffix 'Error', including those used purely for non-local flow control signalling
   **Expected answer:** Derive from Exception rather than BaseException, and use `except Exception:` rather than a bare except when you want to catch all program errors

---

### Lesson 4.2: Idiomatic Statements and Return Values

**Concepts:** Using `with` and invoking context managers through explicitly named methods when they do more than acquire/release a resource, Consistency in return statements: explicit `return None` and a terminal return when any return yields a value, Preferring `startswith()`/`endswith()` and `isinstance()` over slicing and direct type comparison, Relying on the falsiness of empty sequences and not comparing booleans to `True`/`False`, Avoiding `return`/`break`/`continue` that jumps out of a `finally` suite because it cancels a propagating exception

**Written from source segments:** [6, 7]

#### Lesson content

# Idiomatic Statements and Return Values

This lesson collects a cluster of PEP 8 *Programming Recommendations* that are less about whitespace and more about writing statements that say what they mean. Each one has the same underlying motive: make the reader's first guess about the code the correct guess.

---

## 1. Resource cleanup: `with`, and naming what the context manager does

When a resource is local to a particular section of code, use a `with` statement so it is cleaned up promptly and reliably. A `try`/`finally` statement is also acceptable.

But there is a second, subtler rule. **Context managers should be invoked through separate functions or methods whenever they do something other than acquire and release a resource.**

```python
# Correct:
with conn.begin_transaction():
    do_stuff_in_transaction(conn)

# Wrong:
with conn:
    do_stuff_in_transaction(conn)
```

The second version is not *broken* — the connection object may well define `__enter__` and `__exit__` that begin and commit a transaction. The problem is that nothing in `with conn:` tells the reader that a transaction is being managed; the obvious reading is "close the connection afterwards." A method with a name (`begin_transaction()`) makes the behaviour explicit. Being explicit matters here precisely because `__enter__`/`__exit__` are invisible at the call site.

---

## 2. Be consistent in return statements

Either **all** return statements in a function return an expression, or **none** of them do.

If any return statement returns an expression, then:

- any return that yields no value must say so explicitly with `return None`, and
- an explicit return statement should be present at the end of the function, if that point is reachable.

```python
# Correct:
def foo(x):
    if x >= 0:
        return math.sqrt(x)
    else:
        return None

def bar(x):
    if x < 0:
        return None
    return math.sqrt(x)

# Wrong:
def foo(x):
    if x >= 0:
        return math.sqrt(x)
    # falls off the end: did the author forget a case?

def bar(x):
    if x < 0:
        return          # bare return next to a value-returning one
    return math.sqrt(x)
```

Both wrong versions behave identically to the correct ones at runtime — Python returns `None` either way. The rule exists so a reader (or reviewer) can tell the difference between *"returns nothing here deliberately"* and *"the author forgot a branch."* A function that never returns a value at all needs no `return None` anywhere; the rule only bites once one return carries an expression.

---

## 3. Prefixes and suffixes: `startswith()` / `endswith()`

```python
# Correct:
if foo.startswith('bar'):

# Wrong:
if foo[:3] == 'bar':
```

Slicing is cleaner-looking only until the literal changes length and the `3` doesn't. `startswith()` and `endswith()` are cleaner and less error prone.

---

## 4. Type checks: `isinstance()`, not type identity

```python
# Correct:
if isinstance(obj, int):

# Wrong:
if type(obj) is type(1):
```

Object type comparisons should *always* use `isinstance()`. It reads better and it respects subclasses, which direct type comparison does not.

---

## 5. Truthiness of empty sequences

For sequences — strings, lists, tuples — use the fact that empty sequences are false:

```python
# Correct:
if not seq:
if seq:

# Wrong:
if len(seq):
if not len(seq):
```

Relatedly: **don't compare boolean values to `True` or `False` using `==`.**

```python
# Correct:
if greeting:

# Wrong:
if greeting == True:

# Worse:
if greeting is True:
```

`is True` is ranked *worse* than `== True` because it demands the exact singleton `True` object, so any other truthy value — `1`, a non-empty list — silently fails the test.

One related caution from elsewhere in the same section: don't use `==` to compare something to a singleton like `None` either; use `is` / `is not`, and prefer `if foo is not None:` over `if not foo is None:`.

And a small textual rule that belongs with these: don't write string literals that rely on significant trailing whitespace. It is visually indistinguishable, and some editors (or `reindent.py`) will trim it away.

---

## 6. No flow control that escapes a `finally` suite

Using `return`, `break`, or `continue` inside a `finally` suite, where the statement would jump *outside* the finally suite, is discouraged:

```python
# Wrong:
def foo():
    try:
        1 / 0
    finally:
        return 42
```

Calling `foo()` returns `42`. The `ZeroDivisionError` that was propagating through the `finally` suite is **implicitly cancelled** by the `return` — it never reaches the caller and nothing is logged. That silent swallowing of a live exception is the reason for the rule; the danger is not the `finally` block itself but the jump out of it.

If you need cleanup that lets the exception continue, do the cleanup and let the suite end normally (or re-`raise` explicitly).

---

## Quick reference

| Instead of | Write |
|---|---|
| `with conn:` (does more than close) | `with conn.begin_transaction():` |
| bare `return` beside `return expr` | `return None` |
| `foo[:3] == 'bar'` | `foo.startswith('bar')` |
| `type(obj) is type(1)` | `isinstance(obj, int)` |
| `if len(seq):` | `if seq:` |
| `if greeting == True:` / `is True` | `if greeting:` |
| `finally: return 42` | let the suite fall through |


#### Quiz

1. **Why does PEP 8 prefer `with conn.begin_transaction():` over `with conn:` when the connection's `__enter__`/`__exit__` manage a transaction?**  
   kind: `mcq` | concept: `Using `with` and invoking context managers through explicitly named methods when they do more than acquire/release a resource`  
   - [x] A named method makes it explicit that the context manager does something beyond closing the connection, which `with conn:` hides
   - [ ] Passing the connection object directly to `with` prevents `__exit__` from ever being called on an exception
   - [ ] Only objects returned by a method call are permitted to define `__enter__` and `__exit__` in Python
   - [ ] Calling a method guarantees the resource is released promptly, while `with conn:` defers cleanup to garbage collection
   **Expected answer:** A named method makes it explicit that the context manager does something beyond closing the connection, which `with conn:` hides

2. **What does this function return, and why is the style discouraged?

```python
def foo():
    try:
        1 / 0
    finally:
        return 42
```**  
   kind: `mcq` | concept: `Avoiding `return`/`break`/`continue` that jumps out of a `finally` suite because it cancels a propagating exception`  
   - [x] It returns 42; the `return` jumping out of the `finally` suite implicitly cancels the propagating `ZeroDivisionError`
   - [ ] It raises `ZeroDivisionError`; the `return` in `finally` is ignored, so the 42 is unreachable dead code
   - [ ] It returns 42, but only after the `ZeroDivisionError` has been logged automatically by the interpreter
   - [ ] It raises `ZeroDivisionError` chained to a `RuntimeError` complaining about flow control inside `finally`
   **Expected answer:** It returns 42; the `return` jumping out of the `finally` suite implicitly cancels the propagating `ZeroDivisionError`

3. **Rewrite `def bar(x):` so it follows PEP 8's rule on consistent returns, given that it currently does a bare `return` when `x < 0` and `return math.sqrt(x)` otherwise. State the change and the reason in one or two sentences.**  
   kind: `short` | concept: `Consistency in return statements: explicit `return None` and a terminal return when any return yields a value`  
   **Expected answer:** Change the bare `return` to `return None`, so that every return statement in the function returns an expression. Since one return carries a value, the value-less return must state `None` explicitly, making it clear the author intended that branch rather than forgetting a case.

4. **Which pair of checks matches PEP 8's recommendations?**  
   kind: `mcq` | concept: `Relying on the falsiness of empty sequences and not comparing booleans to `True`/`False``  
   - [x] `if not seq:` and `if greeting:`
   - [ ] `if len(seq) == 0:` and `if greeting is True:`
   - [ ] `if not len(seq):` and `if greeting == True:`
   - [ ] `if seq == []:` and `if bool(greeting) is True:`
   **Expected answer:** `if not seq:` and `if greeting:`

5. **PEP 8 calls `if greeting is True:` *worse* than `if greeting == True:`. What is the reasoning?**  
   kind: `mcq` | concept: `Relying on the falsiness of empty sequences and not comparing booleans to `True`/`False``  
   - [x] `is True` requires the exact `True` singleton, so other truthy values such as `1` or a non-empty list fail the test
   - [ ] `is True` performs a slower identity lookup than `==`, which short-circuits on the first comparison
   - [ ] `is True` raises a `TypeError` whenever the operand is not already a `bool` instance
   - [ ] `is True` is evaluated at import time rather than at runtime, so it cannot see later reassignments
   **Expected answer:** `is True` requires the exact `True` singleton, so other truthy values such as `1` or a non-empty list fail the test

6. **A reviewer sees `if type(obj) is type(1):` and `if foo[:3] == 'bar':`. Which replacements does PEP 8 recommend, and what is the practical advantage of each?**  
   kind: `short` | concept: `Preferring `startswith()`/`endswith()` and `isinstance()` over slicing and direct type comparison`  
   **Expected answer:** Use `isinstance(obj, int)` instead of the type comparison — it reads better and also accepts subclasses, which direct type identity rejects. Use `foo.startswith('bar')` instead of the slice — it is cleaner and less error prone, since the slice length can drift out of sync with the literal being compared.

---

### Lesson 4.3: Function and Variable Annotations

**Concepts:** PEP 484 function annotation style and where experimentation is encouraged, Type checkers and stub (.pyi) files as optional, separate tooling, The `# type: ignore` file-level escape hatch, PEP 526 variable annotation spacing rules

**Written from source segments:** [7]

#### Lesson content

# Function and Variable Annotations

Python lets you attach *annotations* to function parameters, return values, and variables. The interpreter mostly just records them; the real audience is human readers and **optional, separate tools** called type checkers. PEP 8 has a short section on how to write them, and it defers the syntax itself to PEP 484 (functions) and PEP 526 (variables).

## Function annotations: use PEP 484 syntax

Early versions of PEP 8 invited people to experiment with what annotations could *mean*. That is over. Since PEP 484 was accepted:

- Function annotations should use **PEP 484 syntax** — i.e. they express types.
- The old encouragement to experiment with annotation *styles* is no longer given.
- **Outside the standard library**, experimentation *within the rules of PEP 484* is encouraged: annotating a large third-party library or application, seeing how painful it was, and observing whether readability improved is exactly the kind of experience the community wants.
- **The standard library itself should be conservative** about adopting annotations, though they are allowed in new code and in big refactorings.

```python
def greeting(name: str) -> str:
    return 'Hello ' + name
```

Spacing reminders that come from the whitespace rules: no space before the annotation colon, one space after it; spaces around the `->` arrow; and when an annotated parameter has a default, put spaces around the `=` (unlike an un-annotated parameter, where `=` gets no spaces).

```python
# Correct:
def munge(sep: str = ' ', limit: int = 1000) -> str: ...
def munge(sep=' ', limit=1000): ...

# Wrong:
def munge(sep: str=' ', limit: int=1000) -> str: ...
def munge(sep = ' ') : ...
```

## The `# type: ignore` escape hatch

Annotations are still just expressions attached to a function, and some projects use them for something other than types (dispatch tables, documentation strings, units, ...). If your code makes a different use of function annotations, PEP 8 recommends putting a comment of the form:

```python
# type: ignore
```

**near the top of the file**. This tells type checkers to ignore all annotations in that file. PEP 484 documents finer-grained ways to silence specific complaints; the file-level comment is the blunt instrument.

## Type checkers are optional tools

This is the key philosophical point:

- Like linters, type checkers are **optional, separate tools**. They are not part of running your program.
- A Python interpreter should **not** emit messages because of type checking, and should **not** change its runtime behaviour based on annotations.
- Users who don't want type checking may freely ignore it. But users of a third-party package may well want to run a checker over that package, so library authors should keep that audience in mind.

## Stub files (`.pyi`)

To make a library checkable without touching its runtime source, PEP 484 recommends **stub files**: `.pyi` files containing only signatures and annotations. A type checker reads the `.pyi` file *in preference to* the corresponding `.py` file.

```python
# shapes.pyi
class Point:
    x: float
    y: float
    def distance_to(self, other: 'Point') -> float: ...
```

Stubs can be shipped alongside the library, or distributed separately (with the author's permission) through the **typeshed** repository.

## Variable annotations (PEP 526)

PEP 526 added annotations for module-level variables, class and instance variables, and local variables. The spacing rules mirror the function-annotation ones:

1. **No space before the colon.**
2. **Exactly one space after the colon.**
3. If there is a right-hand side, the `=` gets **exactly one space on each side**.

```python
# Correct:

code: int

class Point:
    coords: Tuple[int, int]
    label: str = '<unknown>'
```

```python
# Wrong:

code:int          # No space after colon
code : int        # Space before colon

class Test:
    result: int=0  # No spaces around equality sign
```

One last note: although PEP 526 was accepted for Python 3.6, the variable-annotation syntax is the **preferred syntax for stub files on all versions of Python**, including older ones — because stubs are read by the type checker, not executed by the interpreter.

## Quick checklist

- Annotate with PEP 484 types; experiment outside the stdlib, be conservative inside it.
- Using annotations for something else? Add `# type: ignore` near the top of the file.
- Never let annotations change interpreter behaviour; checking is opt-in.
- Can't or won't annotate the source? Ship a `.pyi` stub, possibly via typeshed.
- `name: type = value` — no space before the colon, one after, one on each side of `=`.

#### Quiz

1. **Which line follows PEP 8's variable annotation spacing rules?**  
   kind: `mcq` | concept: `PEP 526 variable annotation spacing rules`  
   - [x] `label: str = '<unknown>'`
   - [ ] `label : str = '<unknown>'`
   - [ ] `label:str = '<unknown>'`
   - [ ] `label: str='<unknown>'`
   **Expected answer:** `label: str = '<unknown>'`

2. **A project uses function annotations to store units of measurement rather than types. What does PEP 8 recommend, and where?**  
   kind: `mcq` | concept: `The `# type: ignore` file-level escape hatch`  
   - [x] Add a `# type: ignore` comment near the top of the file so type checkers ignore all annotations in it
   - [ ] Add a `# type: ignore` comment on each annotated line, since file-level suppression is not supported
   - [ ] Rename the file with a `.pyi` extension so type checkers read it instead of the `.py` source
   - [ ] Wrap the annotations in string literals so the interpreter skips evaluating them
   **Expected answer:** Add a `# type: ignore` comment near the top of the file so type checkers ignore all annotations in it

3. **According to the lesson, what is the relationship between a `.pyi` stub file and the matching `.py` file when a type checker runs?**  
   kind: `short` | concept: `Type checkers and stub (.pyi) files as optional, separate tooling`  
   **Expected answer:** The type checker reads the `.pyi` stub in preference to the corresponding `.py` file; the stub holds the signatures and annotations without altering the runtime source. Stubs may ship with the library or be distributed separately through typeshed.

4. **Which statement matches PEP 8's stance on type checkers?**  
   kind: `mcq` | concept: `Type checkers and stub (.pyi) files as optional, separate tooling`  
   - [x] They are optional, separate tools; the interpreter should not emit messages or change behaviour because of annotations
   - [ ] They are part of the interpreter's normal operation, so annotated code may run differently from unannotated code
   - [ ] They must be run before code can be accepted into the standard library, though third-party code is exempt
   - [ ] They replace linters entirely, since annotation checking subsumes ordinary style checking
   **Expected answer:** They are optional, separate tools; the interpreter should not emit messages or change behaviour because of annotations

5. **How does PEP 8 treat annotation adoption differently inside the standard library versus outside it?**  
   kind: `mcq` | concept: `PEP 484 function annotation style and where experimentation is encouraged`  
   - [x] The stdlib should be conservative, allowing annotations for new code and big refactorings, while outside it experimentation within PEP 484's rules is encouraged
   - [ ] The stdlib must be fully annotated first so that third-party libraries have a model to copy
   - [ ] Both are told to experiment freely with novel annotation styles beyond PEP 484
   - [ ] Annotations are banned in the stdlib, and outside it only stub files may carry them
   **Expected answer:** The stdlib should be conservative, allowing annotations for new code and big refactorings, while outside it experimentation within PEP 484's rules is encouraged

6. **Why is the variable annotation syntax recommended for stub files even on Python versions older than 3.6?**  
   kind: `short` | concept: `PEP 526 variable annotation spacing rules`  
   **Expected answer:** Stub files are read by the type checker rather than executed by the interpreter, so the syntax does not need to be runtime-supported by the target Python version; PEP 484 makes it the preferred stub syntax on all versions.

---
