"""Mechanical text-overlap primitives shared by the grounding, answerability, and
coverage metrics.

Everything here is deliberately dumb and deterministic: no embeddings, no model
call, no stemming. The point of the eval is to produce a number a human can
re-derive by hand from the same two strings. A smarter matcher would be more
generous to the generator and less trustworthy as evidence.
"""

import re
import unicodedata

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:['’\-][a-z0-9]+)*")

# Function words carry no evidence that an answer came from the source: a long
# answer made entirely of these would score a perfect overlap against any English
# document. Kept small and explicit rather than pulled from a corpus list, so the
# metric stays reproducible across machines.
STOPWORDS = frozenset(
    """
    a an the and or but if then than that this these those of in on at to for from by with
    without into onto about as is are was were be been being am do does did doing done
    have has had having it its it's they them their there here he she his her you your we our
    us i me my not no nor so such can could should would may might must will shall
    which who whom whose what when where why how all any both each few more most other some
    only own same too very just also up down out over under again further once
    """.split()  # noqa: SIM905  (a wrapped word list stays readable; a list literal would not)
)

# Answers that a substring test would "ground" against almost any document. They
# are counted, reported, and excluded from the honest grounding denominator
# rather than silently inflating it.
TRIVIAL_ANSWERS = frozenset(
    {
        "true",
        "false",
        "yes",
        "no",
        "none",
        "all of the above",
        "none of the above",
        "both a and b",
        "all of these",
        "none of these",
    }
)


def normalize(text: str) -> str:
    """Casefold, strip accents-preserving compatibility forms, and reduce every run
    of non-alphanumeric characters to a single space."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(normalize(text))


def content_tokens(text: str) -> list[str]:
    """Tokens with function words removed.

    Falls back to the raw token list when stopword removal would empty it, so a
    short answer like "it is" still gets compared against something instead of
    scoring a vacuous 0 or 1.
    """
    toks = tokenize(text)
    kept = [t for t in toks if t not in STOPWORDS]
    return kept or toks


# Suffix folding, used ONLY by `novel_tokens` below. The recall numbers stay
# unstemmed on purpose so old result files remain directly comparable; this list
# exists because the novelty signal asks a different question ("is this word in
# the document at all?") where "survival" vs "surviving" and "generation" vs
# "generations" are the same word and counting them as new is simply wrong.
# Ordered longest first; only one suffix is ever removed.
_SUFFIXES = (
    "ational",
    "ations",
    "ances",
    "ences",
    "ement",
    "ation",
    "ance",
    "ence",
    "ings",
    "ness",
    "ing",
    "ers",
    "ies",
    "ive",
    "ity",
    "ed",
    "es",
    "er",
    "ly",
    "al",
    "s",
)
# Below this length a stem stops being a word, so the fold is skipped.
MIN_STEM_CHARS = 4

# Words a lesson writer needs in any answer regardless of the source's vocabulary.
# Left out of the novelty count so ordinary connective prose is not mistaken for
# invented material.
PEDAGOGICAL_WORDS = frozenset(
    """
    answer question lesson example examples explain explains explanation means meaning
    because therefore shows show showing point purpose reason reasons idea concept
    learner reader course module quiz topic section term terms word words phrase
    """.split()  # noqa: SIM905  (a wrapped word list stays readable)
)


def stem(token: str) -> str:
    """Fold one inflected suffix off a token, if what remains is still word-sized."""
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= MIN_STEM_CHARS:
            return token[: -len(suffix)]
    return token


def stem_vocab(tokens) -> set[str]:
    """Every token plus its stem, so a lookup matches either form."""
    folded = set()
    for token in tokens:
        folded.add(token)
        folded.add(stem(token))
    return folded


def novel_tokens(text: str, reference_vocab: set[str]) -> list[str]:
    """Content words in `text` that appear nowhere in the reference, in any inflection.

    This is the hallucination signal that window recall cannot give. A paraphrase
    restates the document in the document's own words rearranged, so it scores low
    on window recall but low on novelty too. Invented material brings in words the
    document never used, which is what this counts.
    """
    novel = []
    for token in dict.fromkeys(content_tokens(text)):
        if token in PEDAGOGICAL_WORDS or stem(token) in PEDAGOGICAL_WORDS:
            continue
        if token in reference_vocab or stem(token) in reference_vocab:
            continue
        novel.append(token)
    return novel


def sentences(text: str, min_chars: int) -> list[str]:
    """Sentence-ish spans long enough to match on. Headings and list fragments are
    dropped: they are mostly stopwords and would score as covered by anything."""
    parts = re.split(r"(?<=[.!?;:])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) >= min_chars]


def is_trivial_answer(answer: str) -> bool:
    return normalize(answer) in TRIVIAL_ANSWERS


def contains_phrase(haystack_norm: str, needle: str) -> bool:
    """Whole-token substring test against an already-normalized haystack."""
    needle_norm = normalize(needle)
    if not needle_norm:
        return False
    return f" {needle_norm} " in f" {haystack_norm} "


def window_size_for(needle_len: int) -> int:
    """Span of source tokens allowed to jointly support one answer.

    Support should be local: if the words of an answer only co-occur across
    thousands of tokens of unrelated text, that is not evidence, it is
    coincidence. Scales with the answer but never shrinks below a sentence or two.
    """
    return max(40, min(400, 4 * needle_len))


def best_window_recall(
    needle_tokens: list[str], haystack_tokens: list[str], window: int | None = None
) -> tuple[float, int]:
    """Largest fraction of the answer's distinct tokens found inside any single
    window of the source, plus that window's start index.

    This is the core grounding number. Global vocabulary overlap is far too
    generous on a long document (every common technical word appears somewhere),
    so support is only counted when the words appear close together.
    """
    need = set(needle_tokens)
    if not need or not haystack_tokens:
        return 0.0, 0
    window = window or window_size_for(len(need))
    counts = dict.fromkeys(need, 0)
    present = 0
    best = 0.0
    best_start = 0
    for i, token in enumerate(haystack_tokens):
        if token in counts:
            if counts[token] == 0:
                present += 1
            counts[token] += 1
        if i >= window:
            leaving = haystack_tokens[i - window]
            if leaving in counts:
                counts[leaving] -= 1
                if counts[leaving] == 0:
                    present -= 1
        recall = present / len(need)
        if recall > best:
            best = recall
            best_start = max(0, i - window + 1)
            if best == 1.0:
                break
    return best, best_start


def global_recall(needle_tokens: list[str], haystack_vocab: set[str]) -> float:
    """Fraction of the answer's distinct tokens appearing anywhere in the source.

    Reported alongside the window recall to show how much of an item's apparent
    support is only an artifact of document length.
    """
    need = set(needle_tokens)
    if not need:
        return 0.0
    return sum(1 for t in need if t in haystack_vocab) / len(need)


def excerpt(haystack_tokens: list[str], start: int, length: int, max_tokens: int = 60) -> str:
    """Readable slice of the source around a matched window, for quoting in reports."""
    end = min(len(haystack_tokens), start + min(length, max_tokens))
    return " ".join(haystack_tokens[start:end])
