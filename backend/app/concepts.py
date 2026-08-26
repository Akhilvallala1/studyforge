"""Concept key normalization.

Attempts are grouped by concept so that later phases (spaced repetition scheduling)
can ask "how is this learner doing on gradient descent?" across lessons and courses.
That grouping only works if every writer and every reader derives the key the same
way, so this is deliberately the single shared function: no stemming, no synonym
table, no model call. Anything smarter would have to be versioned, and a silent
drift in normalization would split one concept's history into two.
"""

import re
import unicodedata

# Punctuation that commonly trails or leads an LLM-written concept label
# ("Gradient Descent." / "(recursion)") and carries no meaning for grouping.
# Brackets are handled separately: stripping them blindly turns "O(n)" into "o(n",
# which technical material produces constantly.
_EDGE_CHARS = " .,:;!?-_\"'"
_BRACKET_PAIRS = (("(", ")"), ("[", "]"))

_WHITESPACE = re.compile(r"\s+")


def normalize_concept(raw: str | None) -> str:
    """Fold a concept label into a stable grouping key.

    Returns "" for missing or empty input, which callers treat as "unclassified"
    rather than as a concept in its own right.
    """
    if not raw:
        return ""
    text = unicodedata.normalize("NFKC", raw).casefold()
    text = _WHITESPACE.sub(" ", text).strip()
    text = text.strip(_EDGE_CHARS)
    # Peel wrapping brackets only when both sides are present, so "(recursion)" folds
    # to "recursion" while "O(n log n)" keeps its closing paren.
    changed = True
    while changed and text:
        changed = False
        for opener, closer in _BRACKET_PAIRS:
            if text.startswith(opener) and text.endswith(closer) and len(text) > 1:
                text = text[1:-1].strip(_EDGE_CHARS)
                changed = True
    return text
