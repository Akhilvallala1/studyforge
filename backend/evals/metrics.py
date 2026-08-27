"""Objectively checkable quality metrics for a generated course.

Every function here takes a plain course dict (the shape `generation.generate_course`
returns) plus the source chunks it was generated from, and returns plain data. No
model calls, no judgement calls: each number can be recomputed by hand from the
same inputs, which is what makes a before/after prompt comparison meaningful.

The four thresholds below are the only tuning knobs. They are stated once, exported,
and recorded into every result file so a comparison across prompt versions can tell
whether the thresholds moved as well as the scores.
"""

import re
from dataclasses import dataclass, field

from evals.textmatch import (
    best_window_recall,
    contains_phrase,
    content_tokens,
    excerpt,
    global_recall,
    is_trivial_answer,
    normalize,
    novel_tokens,
    sentences,
    stem_vocab,
    tokenize,
    window_size_for,
)

# Support tiers, by best window recall of the answer's content tokens.
STRONG_SUPPORT = 0.80
PARTIAL_SUPPORT = 0.50
# Answers shorter than this carry too little signal for overlap to mean much;
# counted and reported separately instead of padding the pass rate.
LOW_SIGNAL_TOKENS = 2

# Structural expectations, taken verbatim from the prompts in app/generation.py.
# If a prompt changes, change these with it: a drift between the two is exactly
# the kind of silent regression this harness exists to catch.
EXPECTED_MODULES = (2, 5)
EXPECTED_LESSONS_PER_MODULE = (2, 4)
EXPECTED_CONCEPTS_PER_LESSON = (2, 5)
EXPECTED_QUIZ_ITEMS_PER_LESSON = (3, 6)
EXPECTED_MCQ_OPTIONS = 4

TIER_EXACT = "exact"
TIER_STRONG = "strong"
TIER_PARTIAL = "partial"
TIER_UNSUPPORTED = "unsupported"
TIERS = (TIER_EXACT, TIER_STRONG, TIER_PARTIAL, TIER_UNSUPPORTED)

# --- scoring classes -------------------------------------------------------
#
# Token overlap answers one question: "does this wording appear in the source?"
# For two common and perfectly legitimate item forms that question has the wrong
# answer built in, and counting them as ungrounded measures phrasing rather than
# hallucination. Both are separated out before the headline number is computed.
#
#   odd_one_out  an MCQ asking which option is NOT in the material. Its correct
#                answer is a deliberately false statement, so it SHOULD be absent
#                from the source. Its distractors are the true statements, so they
#                are what gets scored instead.
#   restatement  a short-answer item that asks the learner to explain or restate.
#                A paraphrase is the requested output, so low verbatim overlap is
#                the item working as intended.
#   extractive   everything else. These are expected to be findable in the source,
#                and they are the honest hallucination denominator.
CLASS_EXTRACTIVE = "extractive"
CLASS_ODD_ONE_OUT = "odd_one_out"
CLASS_RESTATEMENT = "restatement"
CLASS_TRIVIAL = "trivial"
SCORING_CLASSES = (CLASS_EXTRACTIVE, CLASS_ODD_ONE_OUT, CLASS_RESTATEMENT, CLASS_TRIVIAL)

# Deliberately narrow. A bare "except" or "least" also appears inside quotations
# from the source ("cares nothing for appearances, except in so far as..."), and
# misreading one of those as an odd-one-out would excuse a real ungrounded answer.
# Each alternative below needs the surrounding enumerating construction as well.
_ODD_ONE_OUT = re.compile(
    r"\b(?:following|these|those|listed|options?)\b[^?]{0,80}\bexcept\b"
    r"|\bnot\s+(?:one\s+of|among|include[ds]?|listed|mentioned|part\s+of)"
    r"|\bwhich[^?]*\b(?:is|are|does|do|did|was|were|can)\s+not\b"
    r"|\bwhich[^?]*\bleast\b"
    r"|\bnone\s+of\s+(?:these|the\s+following)\b",
    re.IGNORECASE,
)
# "Why" earns its place here: a why-question asks for a reason in the learner's
# own words, and the source states the reason without ever phrasing it as one.
_RESTATEMENT = re.compile(
    r"\bin your own words\b"
    r"|\bexplain\b|\bdescribe\b|\bsummari[sz]e\b|\bbriefly\b"
    r"|\bwhy\b|\bwhat is the (?:purpose|point|significance)\b",
    re.IGNORECASE,
)

# A hallucination candidate has to fail both ways: too little of it sits together
# anywhere in the source, AND too much of its vocabulary is absent from the source
# entirely. Either alone is satisfied by ordinary paraphrase.
NOVEL_RATE_LIMIT = 0.60


def scoring_class(kind: str, question: str, answer: str) -> str:
    if is_trivial_answer(answer):
        return CLASS_TRIVIAL
    if kind == "mcq" and _ODD_ONE_OUT.search(question):
        return CLASS_ODD_ONE_OUT
    if kind == "short" and _RESTATEMENT.search(question):
        return CLASS_RESTATEMENT
    return CLASS_EXTRACTIVE


@dataclass
class Support:
    """How well one piece of text is backed by one body of reference text."""

    tier: str
    exact: bool
    window_recall: float
    global_recall: float
    best_chunk: int
    evidence: str
    token_count: int
    low_signal: bool

    def as_dict(self) -> dict:
        return {
            "tier": self.tier,
            "exact": self.exact,
            "window_recall": round(self.window_recall, 4),
            "global_recall": round(self.global_recall, 4),
            "best_chunk": self.best_chunk,
            "evidence": self.evidence,
            "token_count": self.token_count,
            "low_signal": self.low_signal,
        }


class ReferenceText:
    """Tokenized reference material that answers get matched against.

    Used both for the source document (grounding) and for a single lesson's own
    content (answerability), so the two metrics are computed by identical rules and
    their numbers are directly comparable.
    """

    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.chunk_norm = [normalize(c) for c in chunks]
        self.chunk_tokens = [tokenize(c) for c in chunks]
        self.vocab: set[str] = set()
        for toks in self.chunk_tokens:
            self.vocab.update(toks)
        # Inflection-tolerant form, used only by the novelty signal.
        self.folded_vocab: set[str] = stem_vocab(self.vocab)
        self.total_tokens = sum(len(t) for t in self.chunk_tokens)

    def novelty(self, text: str) -> tuple[list[str], float]:
        """Words of `text` absent from the reference, and their share of its content."""
        novel = novel_tokens(text, self.folded_vocab)
        distinct = len(set(content_tokens(text)))
        return novel, (len(novel) / distinct if distinct else 0.0)

    def support(self, text: str) -> Support:
        needle = content_tokens(text)
        exact_chunk = next(
            (i for i, norm in enumerate(self.chunk_norm) if contains_phrase(norm, text)), -1
        )
        best_recall = 0.0
        best_chunk = -1
        best_start = 0
        for i, toks in enumerate(self.chunk_tokens):
            recall, start = best_window_recall(needle, toks)
            if recall > best_recall:
                best_recall, best_chunk, best_start = recall, i, start
        if exact_chunk >= 0:
            tier = TIER_EXACT
        elif best_recall >= STRONG_SUPPORT:
            tier = TIER_STRONG
        elif best_recall >= PARTIAL_SUPPORT:
            tier = TIER_PARTIAL
        else:
            tier = TIER_UNSUPPORTED
        evidence_chunk = exact_chunk if exact_chunk >= 0 else best_chunk
        if evidence_chunk >= 0:
            start = 0 if exact_chunk >= 0 else best_start
            if exact_chunk >= 0:
                toks = self.chunk_tokens[exact_chunk]
                first = normalize(text).split(" ")[0] if normalize(text) else ""
                start = max(0, toks.index(first) - 15) if first in toks else 0
            evidence = excerpt(
                self.chunk_tokens[evidence_chunk], start, window_size_for(len(set(needle)))
            )
        else:
            evidence = ""
        return Support(
            tier=tier,
            exact=exact_chunk >= 0,
            window_recall=best_recall,
            global_recall=global_recall(needle, self.vocab),
            best_chunk=evidence_chunk,
            evidence=evidence,
            token_count=len(set(needle)),
            low_signal=len(set(needle)) < LOW_SIGNAL_TOKENS,
        )


@dataclass
class QuizItemRef:
    """One quiz item with enough context to report where it came from."""

    module_index: int
    lesson_index: int
    item_index: int
    module_title: str
    lesson_title: str
    lesson_content: str
    question: str
    kind: str
    options: list = field(default_factory=list)
    answer: str = ""
    concept: str = ""

    @property
    def location(self) -> str:
        return (
            f"module {self.module_index + 1} / lesson {self.lesson_index + 1} "
            f"/ item {self.item_index + 1}"
        )


def iter_lessons(course: dict):
    for m_index, module in enumerate(course.get("modules", []) or []):
        for l_index, lesson in enumerate(module.get("lessons", []) or []):
            yield m_index, l_index, module, lesson


def iter_quiz_items(course: dict):
    for m_index, l_index, module, lesson in iter_lessons(course):
        for q_index, item in enumerate(lesson.get("quiz", []) or []):
            # generation.py normalizes these now, but the harness also rescoring saved
            # result files from before that fix, and a metric that dies on odd input
            # is a metric that cannot measure the runs worth measuring.
            if not isinstance(item, dict):
                continue
            yield QuizItemRef(
                module_index=m_index,
                lesson_index=l_index,
                item_index=q_index,
                module_title=module.get("title", ""),
                lesson_title=lesson.get("title", ""),
                lesson_content=lesson.get("content", "") or "",
                question=item.get("question", "") or "",
                kind=item.get("kind", "") or "",
                options=list(item.get("options", []) or []),
                answer=item.get("answer", "") or "",
                concept=item.get("concept", "") or "",
            )


def _tier_counts(supports: list[Support]) -> dict:
    return {tier: sum(1 for s in supports if s.tier == tier) for tier in TIERS}


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def grounding(course: dict, chunks: list[str]) -> dict:
    """Can each quiz item's expected answer be found in, or fairly inferred from, the source?

    Two numbers come out of this, and they are not interchangeable.

    `supported_rate` is every non-trivial answer scored by raw token overlap. It is
    kept because earlier result files report it and a comparison has to be
    like-for-like, but it understates quality: an odd-one-out MCQ is *supposed* to
    have an answer the source never says, and a "in your own words" item is
    *supposed* to be a paraphrase. Overlap cannot tell either from invention.

    `extractive_supported_rate` is the honest hallucination number. It scores only
    the items that genuinely claim to restate the source, and reports the other two
    forms in their own buckets: odd-one-out items scored on their distractors (the
    true statements), restatement items scored on novelty rather than on wording.
    """
    reference = ReferenceText(chunks)
    per_item = []
    supports = []
    by_class: dict[str, list[dict]] = {name: [] for name in SCORING_CLASSES}
    trivial = 0
    for ref in iter_quiz_items(course):
        trivial_answer = is_trivial_answer(ref.answer)
        item_class = scoring_class(ref.kind, ref.question, ref.answer)
        support = reference.support(ref.answer)
        novel, novel_rate = reference.novelty(ref.answer)
        if trivial_answer:
            trivial += 1
        else:
            supports.append(support)
        # An odd-one-out item's evidence is its distractors: those are the claims
        # the source is supposed to contain, and if they check out the item is
        # grounded no matter how absent the deliberately false answer is.
        distractor_rate = None
        if item_class == CLASS_ODD_ONE_OUT:
            others = [o for o in ref.options if normalize(o) != normalize(ref.answer)]
            checked = [reference.support(o) for o in others]
            distractor_rate = (
                sum(1 for s in checked if s.tier in (TIER_EXACT, TIER_STRONG, TIER_PARTIAL))
                / len(checked)
                if checked
                else 0.0
            )
        item = {
            "location": ref.location,
            "lesson_title": ref.lesson_title,
            "question": ref.question,
            "kind": ref.kind,
            "answer": ref.answer,
            "concept": ref.concept,
            "trivial_answer": trivial_answer,
            "scoring_class": item_class,
            "novel_tokens": novel,
            "novel_rate": round(novel_rate, 4),
            "distractor_supported_rate": distractor_rate,
            "hallucination_candidate": (
                support.window_recall < PARTIAL_SUPPORT and novel_rate > NOVEL_RATE_LIMIT
            ),
            **support.as_dict(),
        }
        per_item.append(item)
        by_class[item_class].append(item)

    counts = _tier_counts(supports)
    scored = len(supports)
    supported = counts[TIER_EXACT] + counts[TIER_STRONG]

    extractive = by_class[CLASS_EXTRACTIVE]
    ex_supported = [i for i in extractive if i["tier"] in (TIER_EXACT, TIER_STRONG)]
    odd = by_class[CLASS_ODD_ONE_OUT]
    restated = by_class[CLASS_RESTATEMENT]
    return {
        "total_items": len(per_item),
        "trivial_answers_excluded": trivial,
        "scored_items": scored,
        "tier_counts": counts,
        "supported_items": supported,
        "supported_rate": (supported / scored) if scored else 0.0,
        "unsupported_items": counts[TIER_UNSUPPORTED],
        "low_signal_items": sum(1 for s in supports if s.low_signal),
        "mean_window_recall": (sum(s.window_recall for s in supports) / scored) if scored else 0.0,
        # Corrected view.
        "class_counts": {name: len(items) for name, items in by_class.items()},
        "extractive_items": len(extractive),
        "extractive_supported_items": len(ex_supported),
        "extractive_supported_rate": (
            len(ex_supported) / len(extractive) if extractive else 0.0
        ),
        "extractive_unsupported_items": sum(
            1 for i in extractive if i["tier"] == TIER_UNSUPPORTED
        ),
        "extractive_mean_window_recall": _mean([i["window_recall"] for i in extractive]),
        "odd_one_out_mean_distractor_rate": _mean(
            [i["distractor_supported_rate"] or 0.0 for i in odd]
        ),
        "restatement_mean_novel_rate": _mean([i["novel_rate"] for i in restated]),
        "mean_novel_rate": _mean([i["novel_rate"] for i in per_item if not i["trivial_answer"]]),
        "hallucination_candidates": sum(1 for i in per_item if i["hallucination_candidate"]),
        "flagged": [i for i in per_item if i["hallucination_candidate"]],
        "failures": [
            item
            for item in extractive
            if item["tier"] == TIER_UNSUPPORTED and not item["trivial_answer"]
        ],
        "items": per_item,
    }


def answerability(course: dict) -> dict:
    """Is each item answerable from its OWN lesson's content, as the prompt claims?

    Same matcher as grounding, but the reference text is the single lesson the item
    belongs to. An item that is well grounded in the source yet unsupported here was
    written from material the learner was never actually taught.
    """
    per_item = []
    supports = []
    trivial = 0
    for ref in iter_quiz_items(course):
        reference = ReferenceText([ref.lesson_content])
        support = reference.support(ref.answer)
        trivial_answer = is_trivial_answer(ref.answer)
        if trivial_answer:
            trivial += 1
        else:
            supports.append(support)
        # An MCQ whose correct option is quoted from the lesson while none of the
        # distractors are is answerable by string-matching alone, without
        # understanding anything. Objectively checkable, so worth counting.
        lesson_norm = normalize(ref.lesson_content)
        answer_in_lesson = contains_phrase(lesson_norm, ref.answer)
        distractors_in_lesson = sum(
            1
            for opt in ref.options
            if normalize(opt) != normalize(ref.answer) and contains_phrase(lesson_norm, opt)
        )
        per_item.append(
            {
                "location": ref.location,
                "lesson_title": ref.lesson_title,
                "question": ref.question,
                "kind": ref.kind,
                "answer": ref.answer,
                "trivial_answer": trivial_answer,
                "answer_verbatim_in_lesson": answer_in_lesson,
                "distractors_verbatim_in_lesson": distractors_in_lesson,
                "giveaway_mcq": (
                    ref.kind == "mcq"
                    and answer_in_lesson
                    and distractors_in_lesson == 0
                    and len(ref.options) > 1
                ),
                **support.as_dict(),
            }
        )
    counts = _tier_counts(supports)
    scored = len(supports)
    answerable = counts[TIER_EXACT] + counts[TIER_STRONG]
    return {
        "total_items": len(per_item),
        "trivial_answers_excluded": trivial,
        "scored_items": scored,
        "tier_counts": counts,
        "answerable_items": answerable,
        "answerable_rate": (answerable / scored) if scored else 0.0,
        "unanswerable_items": counts[TIER_UNSUPPORTED],
        "giveaway_mcqs": sum(1 for i in per_item if i["giveaway_mcq"]),
        "failures": [
            item
            for item in per_item
            if item["tier"] == TIER_UNSUPPORTED and not item["trivial_answer"]
        ],
        "items": per_item,
    }


def concept_coverage(course: dict, chunks: list[str]) -> dict:
    """Do the extracted concepts span the document, or cluster in the opening chunks?

    Each concept is anchored to the source chunk whose text best matches it, giving
    a positional histogram. A course that only anchors into chunk 0 has read the
    first page and guessed the rest.
    """
    reference = ReferenceText(chunks)
    histogram = [0] * max(1, len(chunks))
    lesson_histogram = [0] * max(1, len(chunks))
    per_concept = []
    unanchored = 0
    for m_index, l_index, _module, lesson in iter_lessons(course):
        lesson_support = reference.support(
            f"{lesson.get('title', '')} {' '.join(lesson.get('concepts', []) or [])}"
        )
        if lesson_support.best_chunk >= 0 and lesson_support.tier != TIER_UNSUPPORTED:
            lesson_histogram[lesson_support.best_chunk] += 1
        for concept in lesson.get("concepts", []) or []:
            support = reference.support(concept)
            anchored = support.best_chunk >= 0 and support.tier != TIER_UNSUPPORTED
            if anchored:
                histogram[support.best_chunk] += 1
            else:
                unanchored += 1
            per_concept.append(
                {
                    "concept": concept,
                    "lesson": lesson.get("title", ""),
                    "module_index": m_index,
                    "lesson_index": l_index,
                    "anchored": anchored,
                    **support.as_dict(),
                }
            )
    covered = sum(1 for count in histogram if count > 0)
    total_anchored = sum(histogram)
    # Raw shares are not comparable across chunks of different sizes. A chunk
    # holding 74% of the document's words should hold about 74% of its concepts,
    # so the honest reading is actual share over expected share: 1.0 is balanced,
    # and only a ratio well above 1.0 means the course crowded into one place.
    total_chunk_tokens = sum(len(t) for t in reference.chunk_tokens) or 1
    expected = [len(t) / total_chunk_tokens for t in reference.chunk_tokens]
    actual = [(c / total_anchored) if total_anchored else 0.0 for c in histogram]
    ratios = [round(a / e, 4) if e else 0.0 for a, e in zip(actual, expected)]
    return {
        "total_concepts": len(per_concept),
        "anchored_concepts": total_anchored,
        "unanchored_concepts": unanchored,
        "source_chunks": len(chunks),
        "chunks_with_a_concept": covered,
        "chunk_coverage_rate": covered / len(chunks) if chunks else 0.0,
        "concepts_per_chunk": histogram,
        "lessons_per_chunk": lesson_histogram,
        "uncovered_chunk_indexes": [i for i, count in enumerate(histogram) if count == 0],
        "max_chunk_share": (max(histogram) / total_anchored) if total_anchored else 0.0,
        "expected_share_per_chunk": [round(e, 4) for e in expected],
        "actual_share_per_chunk": [round(a, 4) for a in actual],
        "share_vs_expected": ratios,
        "max_concentration_ratio": max(ratios) if ratios else 0.0,
        "concepts": per_concept,
    }


# A source sentence shorter than this is a heading or a fragment: mostly stopwords,
# and it would read as covered by any text at all.
MIN_SOURCE_SENTENCE_CHARS = 60
# Share of a source sentence's content words that must appear together somewhere in
# the course for that sentence to count as taught.
SENTENCE_COVERED = 0.60


def course_text(course: dict) -> str:
    """Everything the course says, as one string: lesson prose, concepts, and quizzes."""
    parts: list[str] = [course.get("title", ""), course.get("description", "")]
    for _m, _l, _module, lesson in iter_lessons(course):
        parts.append(lesson.get("title", ""))
        parts.append(lesson.get("content", "") or "")
        parts.extend(lesson.get("concepts", []) or [])
        for item in lesson.get("quiz", []) or []:
            parts.append(item.get("question", "") or "")
            parts.append(item.get("answer", "") or "")
            parts.extend(item.get("options", []) or [])
    return "\n".join(p for p in parts if p)


def source_coverage(course: dict, chunks: list[str]) -> dict:
    """How much of each part of the document actually made it into the course.

    Measured from the source side, which is the direction the question is really
    asked in: walk every substantial sentence of every chunk and check whether the
    course says it anywhere. Chunk length cancels out, because each chunk is scored
    against its own sentences.

    This is the headline coverage number, in place of `concept_coverage`'s
    histogram. That histogram anchors each concept to its best-matching chunk, and a
    chunk three times longer than its neighbour offers three times as many candidate
    windows, so it wins the argmax for any concept built from ordinary words no
    matter what the course covered. On the first real run the bias alone read as 92%
    of concepts concentrated in chunk 0, for a course whose sentences in fact covered
    chunk 1 slightly better than chunk 0.
    """
    haystack = tokenize(course_text(course))
    per_chunk = []
    for index, chunk in enumerate(chunks):
        spans = sentences(chunk, MIN_SOURCE_SENTENCE_CHARS)
        recalls = [best_window_recall(content_tokens(s), haystack)[0] for s in spans]
        covered = sum(1 for r in recalls if r >= SENTENCE_COVERED)
        per_chunk.append(
            {
                "chunk": index,
                "chars": len(chunk),
                "sentences": len(spans),
                "covered_sentences": covered,
                "recall": round(covered / len(spans), 4) if spans else 0.0,
                "mean_sentence_recall": round(_mean(recalls), 4),
            }
        )
    rates = [c["recall"] for c in per_chunk if c["sentences"]]
    # Lessons carry the segments the outline routed them to, so on a document big
    # enough for routing this is a direct reading of the plan rather than an
    # inference from wording.
    per_segment = [0] * max(1, len(chunks))
    routed = 0
    for _m, _l, _module, lesson in iter_lessons(course):
        for index in lesson.get("segments", []) or []:
            if 0 <= index < len(per_segment):
                per_segment[index] += 1
                routed += 1
    return {
        "source_chunks": len(chunks),
        "per_chunk": per_chunk,
        "mean_chunk_recall": round(_mean(rates), 4),
        "min_chunk_recall": round(min(rates), 4) if rates else 0.0,
        "worst_chunk": min(per_chunk, key=lambda c: c["recall"])["chunk"] if per_chunk else -1,
        "chunks_below_half": sum(1 for r in rates if r < 0.5),
        "lessons_per_segment": per_segment,
        "segments_with_no_lesson": (
            [i for i, n in enumerate(per_segment) if n == 0] if routed else None
        ),
    }


def _in_range(value: int, bounds: tuple[int, int]) -> bool:
    return bounds[0] <= value <= bounds[1]


def structure(course: dict) -> dict:
    """Shape checks against what the prompts promise, plus outright malformations.

    `mcq_answer_not_in_options` is the one that matters most: grading is exact string
    comparison against `answer`, so if the answer text is not one of the rendered
    options the learner cannot possibly get the item right.
    """
    problems: list[dict] = []
    modules = course.get("modules", []) or []
    lesson_count = 0
    quiz_counts: list[int] = []
    concept_counts: list[int] = []
    content_lengths: list[int] = []
    kinds: dict[str, int] = {}
    seen_questions: dict[str, str] = {}

    def flag(kind: str, location: str, detail: str) -> None:
        problems.append({"problem": kind, "location": location, "detail": detail})

    if not _in_range(len(modules), EXPECTED_MODULES):
        flag("module_count_out_of_range", "course", f"{len(modules)} modules")
    if not (course.get("title") or "").strip():
        flag("empty_course_title", "course", "")
    if not (course.get("description") or "").strip():
        flag("empty_course_description", "course", "")

    for m_index, module in enumerate(modules):
        lessons = module.get("lessons", []) or []
        location = f"module {m_index + 1}"
        if not _in_range(len(lessons), EXPECTED_LESSONS_PER_MODULE):
            flag("lesson_count_out_of_range", location, f"{len(lessons)} lessons")
        if not (module.get("title") or "").strip():
            flag("empty_module_title", location, "")

    for ref_m, ref_l, _module, lesson in iter_lessons(course):
        lesson_count += 1
        location = f"module {ref_m + 1} / lesson {ref_l + 1}"
        content = lesson.get("content", "") or ""
        concepts = lesson.get("concepts", []) or []
        quiz = lesson.get("quiz", []) or []
        content_lengths.append(len(content))
        concept_counts.append(len(concepts))
        quiz_counts.append(len(quiz))
        if not content.strip():
            flag("empty_lesson_content", location, lesson.get("title", ""))
        if not (lesson.get("title") or "").strip():
            flag("empty_lesson_title", location, "")
        if not _in_range(len(concepts), EXPECTED_CONCEPTS_PER_LESSON):
            flag("concept_count_out_of_range", location, f"{len(concepts)} concepts")
        if len({normalize(c) for c in concepts}) != len(concepts):
            flag("duplicate_concepts", location, str(concepts))
        if not _in_range(len(quiz), EXPECTED_QUIZ_ITEMS_PER_LESSON):
            flag("quiz_count_out_of_range", location, f"{len(quiz)} items")

    for ref in iter_quiz_items(course):
        kinds[ref.kind] = kinds.get(ref.kind, 0) + 1
        location = ref.location
        if ref.kind not in ("mcq", "short"):
            flag("unknown_quiz_kind", location, ref.kind)
        if not ref.question.strip():
            flag("empty_question", location, "")
        if not ref.answer.strip():
            flag("empty_answer", location, ref.question)
        if not ref.concept.strip():
            flag("empty_concept", location, ref.question)
        key = normalize(ref.question)
        if key and key in seen_questions:
            flag("duplicate_question", location, f"also at {seen_questions[key]}")
        elif key:
            seen_questions[key] = location
        if ref.kind == "mcq":
            if len(ref.options) != EXPECTED_MCQ_OPTIONS:
                flag("mcq_option_count", location, f"{len(ref.options)} options")
            normalized_options = [normalize(o) for o in ref.options]
            if len(set(normalized_options)) != len(normalized_options):
                flag("duplicate_mcq_options", location, str(ref.options))
            if any(not o.strip() for o in ref.options):
                flag("empty_mcq_option", location, str(ref.options))
            if normalize(ref.answer) not in normalized_options:
                flag("mcq_answer_not_in_options", location, f"answer={ref.answer!r}")
        elif ref.kind == "short" and ref.options:
            flag("short_item_has_options", location, str(ref.options))

    total_items = sum(quiz_counts)
    by_problem: dict[str, int] = {}
    for problem in problems:
        by_problem[problem["problem"]] = by_problem.get(problem["problem"], 0) + 1
    return {
        "modules": len(modules),
        "lessons": lesson_count,
        "quiz_items": total_items,
        "quiz_items_per_lesson": quiz_counts,
        "concepts_per_lesson": concept_counts,
        "lesson_content_chars": content_lengths,
        "mean_lesson_content_chars": (
            sum(content_lengths) / len(content_lengths) if content_lengths else 0
        ),
        "min_lesson_content_chars": min(content_lengths) if content_lengths else 0,
        "kinds": kinds,
        "problem_counts": by_problem,
        "problems": problems,
        "clean": not problems,
    }


def evaluate(course: dict, chunks: list[str]) -> dict:
    """Every content metric for one generated course.

    `coverage` is kept under its original key so old result bundles stay comparable;
    `source_coverage` is the corrected reading of the same question.
    """
    return {
        "structure": structure(course),
        "grounding": grounding(course, chunks),
        "answerability": answerability(course),
        "coverage": concept_coverage(course, chunks),
        "source_coverage": source_coverage(course, chunks),
    }
