"""Named prompt variants, so an A/B run is a flag rather than an edit to app code.

Two rules keep the comparisons meaningful:

Only the wording under test changes. Every variant keeps the output-format paragraph
verbatim, because that paragraph is the fix for a real crash (a lesson containing a
code fence used to destroy the JSON around it) and a variant that quietly reintroduced
it would look like a quality result while actually being a bug.

Variants are declared here, never inlined at a call site, so the fingerprint recorded
in each result file names the exact wording that produced it.
"""

from dataclasses import dataclass

from app import generation

# The format contract. Not under test, shared by every variant.
_FORMAT = """You are a teacher writing one lesson of a course. Given the lesson title, \
its summary, and the relevant source material, respond with ONLY a JSON object matching:
{
  "content": str,            # the lesson itself, in markdown: explanations, examples
  "concepts": [str],         # 2-5 key concepts this lesson teaches
  "quiz": [
    {"question": str, "kind": "mcq" | "short", "options": [str], "answer": str, "concept": str}
  ]
}
Output format: the JSON object is the entire reply. Do not put a ``` fence around it and do not \
write anything before or after it. Code examples belong inside the "content" string as ordinary \
markdown, fences and all, escaped the way JSON requires; a code example is never a reason to \
stop emitting JSON.

Quiz rules:
- Write 3-6 items. For "mcq" give exactly 4 options and set "answer" to the correct option's \
text. For "short" leave "options" empty."""

# A: what shipped before any of this work. The prompt that scored best on grounding
# and answerability, and worst on giveaway MCQs.
_A_ORIGINAL = """
- Questions should test understanding of the lesson, not recall of trivia."""

# B: what is on main now. Fixed giveaway MCQs in both runs, and measured worse on
# grounding and answerability in both.
_B_CURRENT = """
- Every question must be answerable from the lesson content alone. Before asking about \
something, teach it in "content" first, in enough detail that a reader who has only this lesson \
can answer.
- Write all four MCQ options in the same voice, at similar length and specificity. Never lift \
the correct option word for word from a sentence in the content while inventing the other three: \
that makes the item solvable by spotting the familiar phrase. Each wrong option should be a \
claim a reader who half-understood the lesson could genuinely believe."""

# C: B's distractor rule without B's teach-first rule. Isolates which half of B caused
# the grounding drop, since B changed two things at once.
_C_DISTRACTORS_ONLY = """
- Write all four MCQ options in the same voice, at similar length and specificity. Never lift \
the correct option word for word from a sentence in the content while inventing the other three: \
that makes the item solvable by spotting the familiar phrase. Each wrong option should be a \
claim a reader who half-understood the lesson could genuinely believe."""

# D: aims at the metric the maintainer chose to optimize. Asks for the answer to be
# traceable to the source rather than merely to the lesson, which is what "grounded"
# measures, and keeps the distractor rule that demonstrably works.
_D_SOURCE_ANCHORED = """
- Every answer must be traceable to the source material: a reader should be able to point at \
the passage it comes from. Do not ask about anything the source does not actually say, and do \
not require knowledge the source assumes but never states.
- Teach a thing in "content" before asking about it, so the lesson alone is enough to answer.
- Write all four MCQ options in the same voice, at similar length and specificity. Never lift \
the correct option word for word from a sentence in the content while inventing the other three: \
that makes the item solvable by spotting the familiar phrase. Each wrong option should be a \
claim a reader who half-understood the lesson could genuinely believe."""


@dataclass(frozen=True)
class Variant:
    key: str
    note: str
    lesson_system: str


# D won and is now what app code ships. A and B are kept so the comparison can be
# re-run: a future prompt change should have to beat the wording it replaces on the
# same trial, rather than on someone's intuition.
VARIANTS: dict[str, Variant] = {
    "A-original": Variant("A-original", "pre-change wording", _FORMAT + _A_ORIGINAL),
    "B-current": Variant("B-current", "what is on main", _FORMAT + _B_CURRENT),
    "C-distractors": Variant("C-distractors", "B without teach-first", _FORMAT + _C_DISTRACTORS_ONLY),
    "D-source": Variant("D-source", "anchors answers to the source", _FORMAT + _D_SOURCE_ANCHORED),
}


def apply(key: str) -> Variant:
    """Point the generator at one variant for the rest of the process.

    Assigning to the module attribute rather than threading a parameter through the
    pipeline keeps the experiment entirely inside the eval: app code has no idea a
    trial is running, so nothing under test is shaped by the harness.
    """
    variant = VARIANTS[key]
    generation.LESSON_SYSTEM = variant.lesson_system
    return variant
