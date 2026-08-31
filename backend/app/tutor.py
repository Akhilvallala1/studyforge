"""The AI tutor: what it is allowed to know, and how much of it there can be.

This module is the reading half of the tutor. It answers two questions and writes
nothing: what context may be put in front of the model for one concept, and how many
turns the learner has left today. The prompt text and the endpoints live elsewhere and
are built on top of these; keeping them apart is what makes the exclusion rules below
testable without a model call.

THE RULE THE WHOLE MODULE ENFORCES: the tutor may know only what the learner can
already see on screen. That is why TutorContext carries a mastery bucket and a
missed-of count, which the Today screen already prints, and carries no stability, no
difficulty, no retrievability, no due date, and no lapse count. Those are latent
scheduler values, and a tutor that mentions one is telling the learner something about
themselves that the interface never told them, sourced from a number they cannot check.
The exclusion is structural rather than a convention: the fields are not on the struct,
so a renderer cannot reach them by accident.

THE SECOND RULE: an answer the learner might still be asked for is never shown to the
tutor. See open_answer_item_ids. This is a per-item decision, not a filter over items,
because dropping the whole item would take its question away too and leave the tutor
teaching a concept it cannot see the shape of.

The tutor writes only tutor_messages. Nothing here touches review_cards, review_logs,
or attempts, and nothing here is a rating: a conversation is not a retrieval test, and
folding one into the schedule would let a learner talk their way to a longer interval.
"""

from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy.orm import Session

from app import days, models, remediation, review
from app.attempts import LESSON_QUIZ_SOURCE
from app.concepts import normalize_concept

# The stage string these calls are recorded under in llm_calls, so tutor spend shows up
# in /usage beside outline, lesson, and remediation, and counts against the cap.
# models.LlmCall.stage is String(20), which this fits with room to spare.
TUTOR_STAGE = "tutor"

# A tutor reply is a couple of paragraphs and a question, not a lesson. The pipeline's
# default 64k budget would let one runaway answer cost more than the course it explains.
MAX_TOKENS = 1000

# The longest question the learner can send. Past this it is not a question, it is a
# document, and a document belongs in course generation where it is chunked and paid
# for deliberately.
MAX_MESSAGE_CHARS = 2000

# How many previous messages travel with a new question, and this number is load
# bearing rather than a taste. 12,000 characters of material plus six history messages
# plus a 2,000-character question fits Ollama's 8192-token window ONLY because history
# is capped here. Raise it and _reject_if_window_filled starts refusing tutor calls on
# local models, which is the configuration this project defaults to.
HISTORY_MESSAGES = 6

# Two daily bounds, both counted in learner turns, because a learner turn is what buys
# a model call. The per-concept cap stops one confusing idea from consuming the day;
# the day-wide cap is the actual spend bound, since without it a learner could sit at
# the per-concept limit on twenty concepts at once.
CONCEPT_TURNS_PER_DAY = 12
DAY_TURNS = 40

# The bounds on the ungrounded half of a reply. "Beyond" is what the tutor says that
# its material does not support, and it is allowed to exist because a learner's
# question often reaches past the course. It is kept short so it reads as an aside
# rather than as a second lesson the material never justified.
BEYOND_MAX_SENTENCES = 3
BEYOND_MAX_CHARS = 400

# How many recent wrong answers the tutor is shown. Three is enough to see a pattern
# and few enough that the tutor cannot recite the learner's whole failure history back
# at them, which is the version of "personalized" nobody wants.
RECENT_INCORRECT = 3

LEARNER_ROLE = "learner"
TUTOR_ROLE = "tutor"


def _moment(now: datetime | None) -> datetime:
    """Every stored timestamp is naive UTC. See the timezone note in review.py."""
    if now is None:
        return review.now_utc()
    return now if now.tzinfo is None else now.astimezone(UTC).replace(tzinfo=None)


# --------------------------------------------------------------------------
# The daily budget
# --------------------------------------------------------------------------


class TurnCounts(NamedTuple):
    """Both daily caps and when they lift, derived from the message rows themselves.

    No counter column and no counter table. The rows are the count, so a restart, a
    second tab, and a rebuilt card all agree, and there is no state that can drift out
    of step with the conversation it describes.

    One function, read by both the POST that spends a turn and the GET that displays
    what is left. Remedial practice nearly shipped a bug because its two endpoints each
    derived the session separately; practice_facts was the fix, and this is that shape.
    """

    concept_used: int
    day_used: int
    day_end: datetime


def turn_counts(session: Session, concept_key: str, now: datetime | None = None) -> TurnCounts:
    """Turns spent today on this concept and across all concepts, and when that resets.

    Counted on learner rows only. A turn is a question the learner asked, which is what
    buys a model call; counting tutor rows as well would halve both caps the moment a
    reply is written, and a failed exchange that wrote no reply would then charge
    differently from a successful one.

    The day is the 04:00 local study day from days.day_bounds, not midnight, so a
    learner working at 01:00 is still inside the day they started, exactly as the
    streak and the practice session already treat it.

    Two queries, both served by the indexes on tutor_messages.
    """
    moment = _moment(now)
    day_start, day_end = days.day_bounds(now=moment)
    today = (
        session.query(models.TutorMessage.id)
        .filter(models.TutorMessage.role == LEARNER_ROLE)
        .filter(models.TutorMessage.created_at >= day_start)
        .filter(models.TutorMessage.created_at < day_end)
    )
    day_used = today.count()
    concept_used = today.filter(models.TutorMessage.concept_key == concept_key).count()
    return TurnCounts(concept_used=concept_used, day_used=day_used, day_end=day_end)


# --------------------------------------------------------------------------
# What the tutor may see
# --------------------------------------------------------------------------


def open_answer_item_ids(
    session: Session,
    concept_key: str,
    items: list[models.QuizItem],
    card: models.ReviewCard | None,
) -> set[int]:
    """The items whose expected answers must be WITHHELD from the tutor.

    An item is open when the learner could still be asked it and have their recall
    counted. Showing the tutor that answer key would let a learner ask about the
    concept, read the answer in the reply, and submit it as a remembered one: a failed
    retrieval recorded as a clean success, which corrupts that concept's schedule and
    leaves no trace saying why.

    The union of two conditions, covering the two places a question can come from:

      (a) items with no lesson-quiz attempt at all. The learner has never been shown
          this answer, so it is still a live question.
      (b) when a card exists, items not already answered in the current review
          exposure. review.already_answered_this_exposure is the predicate the review
          endpoint refuses a second submission with, so anything it still calls
          answerable is an answer the tutor must not spoil.

    Over-inclusive in the safe direction, deliberately. For a concept that has never
    been quizzed, EVERY item is open, the tutor gets no answer keys at all, and it
    teaches from the lesson text alone. That is the common case rather than the
    exception, and it is the right trade: the under-inclusive version of this function
    leaks an answer key, and the damage it does is silent.

    Two queries, not one per item. The obvious loop calling
    review.already_answered_this_exposure per item is N queries on a page render, and
    that function is left alone rather than widened: it answers only the review half
    (REVIEW_SESSION_SOURCE, created_at > card.last_review), and nothing in the tree
    computes the lesson-quiz half, which is why it is written out below.
    """
    item_ids = [item.id for item in items]
    if not item_ids:
        return set()

    quizzed = {
        item_id
        for (item_id,) in session.query(models.Attempt.quiz_item_id)
        .filter(models.Attempt.quiz_item_id.in_(item_ids))
        .filter(models.Attempt.source == LESSON_QUIZ_SOURCE)
        .distinct()
    }
    open_ids = {item_id for item_id in item_ids if item_id not in quizzed}

    if card is None:
        return open_ids

    exposed = (
        session.query(models.Attempt.quiz_item_id)
        .filter(models.Attempt.quiz_item_id.in_(item_ids))
        .filter(models.Attempt.source == review.REVIEW_SESSION_SOURCE)
    )
    if card.last_review is not None:
        exposed = exposed.filter(models.Attempt.created_at > card.last_review)
    answered_this_exposure = {item_id for (item_id,) in exposed.distinct()}
    return open_ids | {item_id for item_id in item_ids if item_id not in answered_this_exposure}


class MaterialItem(NamedTuple):
    """One quiz question, with its expected answer only if the learner may see it.

    A pair rather than a filtered list of QuizItem, and the shape is the point.
    remediation.build_prompt reads item.answer straight off the ORM object, so an
    implementer reusing that shape here has two moves and both are wrong: filter the
    items out, which throws away grounding the tutor needs, or keep the item and
    quietly keep its answer with it. Neither mistake is available against this type.
    An answer of None means question-only, and a renderer must be able to say so.
    """

    question: str
    answer: str | None


class MissedAttempt(NamedTuple):
    """One recent wrong answer: what was asked, and what the learner said.

    Carries no expected answer, on purpose. Attempt rows snapshot the expected answer,
    and passing the ORM row through would put an answer key into the prompt by a side
    door, defeating open_answer_item_ids for exactly the items the learner keeps
    getting wrong, which is the set where it matters most.
    """

    question: str
    submitted: str
    created_at: datetime


class TutorContext(NamedTuple):
    """Everything the tutor is allowed to know about one concept, and nothing else.

    Read the module docstring before adding a field. Stability, difficulty,
    retrievability, due date, and raw lapse count are absent by design, not by
    oversight; `bucket` and `missed`/`of` are here because the learner has already been
    shown both, in those words, on the Today screen and the concept map.
    """

    concept_label: str
    lessons: list[models.Lesson]
    items: list[MaterialItem]
    flagged: bool
    missed: int
    of: int
    bucket: str
    recent_incorrect: list[MissedAttempt]


def _display_label(
    concept_key: str,
    card: models.ReviewCard | None,
    lessons: list[models.Lesson],
    items: list[models.QuizItem],
) -> str:
    """The name to show for this concept, preferring what the learner has been shown.

    The card's label first, because that is what the Today screen and the concept map
    already print. A concept with no card has never been reviewed and still needs a
    display name, so the raw label falls back to the courseware that named it, and only
    then to the normalized key, which is lowercased text the learner never wrote.
    """
    if card is not None and card.concept_label:
        return card.concept_label
    for item in items:
        if item.concept:
            return item.concept
    for lesson in lessons:
        for raw in lesson.concepts or []:
            if isinstance(raw, str) and raw and normalize_concept(raw) == concept_key:
                return raw
    return concept_key


def _attention(session: Session, concept_key: str, now: datetime) -> tuple[bool, int, int]:
    """(flagged, missed, of) for this concept, from review.needs_attention.

    Read off the shared definition rather than recomputed. There is exactly one
    definition of "a concept the learner keeps missing" in this codebase, and a second
    one here would drift from the sentence the Today screen prints.
    """
    for entry in review.needs_attention(session, now):
        if entry["concept_key"] == concept_key:
            return True, entry["missed"], entry["of"]
    return False, 0, 0


def _recent_incorrect(
    session: Session, concept_key: str, limit: int = RECENT_INCORRECT
) -> list[MissedAttempt]:
    """The learner's last few wrong answers on this concept, any source, newest first.

    Any source on purpose: a concept missed in a lesson quiz, again in a review, and
    again in remedial practice was missed three times, and a tutor asking "which part
    of this is not landing" wants all three.
    """
    rows = (
        session.query(
            models.QuizItem.question,
            models.Attempt.submitted_answer,
            models.Attempt.created_at,
        )
        .join(models.QuizItem, models.Attempt.quiz_item_id == models.QuizItem.id)
        .filter(models.Attempt.concept_key == concept_key)
        .filter(models.Attempt.correct.is_(False))
        .order_by(models.Attempt.created_at.desc(), models.Attempt.id.desc())
        .limit(limit)
        .all()
    )
    return [
        MissedAttempt(question=question, submitted=submitted, created_at=created_at)
        for question, submitted, created_at in rows
    ]


def context(session: Session, concept_key: str, now: datetime | None = None) -> TutorContext:
    """Everything the tutor may be shown about one concept. Writes nothing.

    The material is remediation.concept_material, reused rather than redefined: there
    is one answer to "what is this concept's material", and a second definition here
    would drift from the one re-teaching grounds in.

    The expected answers are then withheld per item by open_answer_item_ids, which is
    the only difference between what re-teaching sees and what the tutor sees. Both are
    grounded in the same lessons and the same questions.
    """
    moment = _moment(now)
    lessons, quiz_items = remediation.concept_material(session, concept_key)
    card = review.get_card(session, concept_key)
    withheld = open_answer_item_ids(session, concept_key, quiz_items, card)
    flagged, missed, of = _attention(session, concept_key, moment)
    return TutorContext(
        concept_label=_display_label(concept_key, card, lessons, quiz_items),
        lessons=lessons,
        items=[
            MaterialItem(
                question=item.question,
                answer=None if item.id in withheld else item.answer,
            )
            for item in quiz_items
        ],
        flagged=flagged,
        missed=missed,
        of=of,
        bucket=review.mastery_bucket(card, moment),
        recent_incorrect=_recent_incorrect(session, concept_key),
    )


# --------------------------------------------------------------------------
# The conversation
# --------------------------------------------------------------------------


def conversation(session: Session, concept_key: str) -> list[models.TutorMessage]:
    """Every message for this concept, oldest first. The whole conversation.

    Ordered by (created_at, id) rather than created_at alone: a learner question and
    the reply to it can land inside the same clock tick on SQLite, and an order that
    put the answer first would render a conversation that never happened.
    """
    return (
        session.query(models.TutorMessage)
        .filter(models.TutorMessage.concept_key == concept_key)
        .order_by(models.TutorMessage.created_at, models.TutorMessage.id)
        .all()
    )


def history(
    session: Session, concept_key: str, limit: int = HISTORY_MESSAGES
) -> list[models.TutorMessage]:
    """The last `limit` messages for this concept, oldest first, for the prompt.

    The tail rather than the head: a follow-up question is about what was just said.
    Read as the newest rows and then reversed, so a long conversation costs one bounded
    query instead of loading every message to slice the end off it.

    See HISTORY_MESSAGES for why the default is not larger than it is.
    """
    if limit <= 0:
        return []
    rows = (
        session.query(models.TutorMessage)
        .filter(models.TutorMessage.concept_key == concept_key)
        .order_by(models.TutorMessage.created_at.desc(), models.TutorMessage.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))
