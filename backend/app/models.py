from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    modules: Mapped[list["Module"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Module.position"
    )


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    title: Mapped[str] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(Integer)

    course: Mapped[Course] = relationship(back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="Lesson.position"
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"))
    title: Mapped[str] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text, default="")  # markdown
    concepts: Mapped[list] = mapped_column(JSON, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    module: Mapped[Module] = relationship(back_populates="lessons")
    quiz_items: Mapped[list["QuizItem"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )


class QuizItem(Base):
    __tablename__ = "quiz_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    question: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20))  # "mcq" | "short"
    options: Mapped[list] = mapped_column(JSON, default=list)  # MCQ choices, empty for short
    answer: Mapped[str] = mapped_column(Text)
    concept: Mapped[str] = mapped_column(String(200), default="")

    lesson: Mapped[Lesson] = relationship(back_populates="quiz_items")
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="quiz_item", cascade="all, delete-orphan"
    )


class Attempt(Base):
    """One recorded answer to one quiz item. Append-only: rows are never updated.

    attempt_no is what makes this table worth keeping. "Correct" alone cannot tell
    a first-try recall from a fourth-try guess, and that difference is the mastery
    signal the scheduler will read later.

    expected_answer is snapshotted rather than joined at read time because courses
    are regenerable: if the material is regenerated the quiz item's answer can
    change, and a history that silently re-points at the new answer would misreport
    what the learner was actually graded against.

    attempt_no counts every attempt on the item regardless of source, so once review
    sessions exist it means "nth touch of this item overall", not "nth quiz attempt".
    Per-source ordinals stay derivable from (source, attempt_no, created_at); the
    scheduler will need to compute them rather than reading attempt_no directly.

    source discriminates lesson quizzes from later review sessions, and grader
    versions the grading policy, so a future change from exact-match to something
    smarter does not make old rows unreadable. There is deliberately no rating
    column: FSRS ratings are derived from (correct, attempt_no, elapsed_ms) when
    scheduling lands, so storing one now would freeze a policy we have not chosen.
    """

    __tablename__ = "attempts"
    __table_args__ = (
        # Guarantees sequence integrity: no two rows can claim the same position in
        # an item's history. It does NOT deduplicate answers. The double-click guard
        # in main.py is an unlocked read-then-write, so genuinely simultaneous
        # submits all see no prior row and all insert; only the ordinal is protected.
        UniqueConstraint("quiz_item_id", "attempt_no", name="uq_attempts_item_seq"),
        Index("ix_attempts_item_created", "quiz_item_id", "created_at"),
        Index("ix_attempts_lesson_created", "lesson_id", "created_at"),
        Index("ix_attempts_concept_created", "concept_key", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_item_id: Mapped[int] = mapped_column(ForeignKey("quiz_items.id"))
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    concept_key: Mapped[str] = mapped_column(String(200), default="")
    concept_label: Mapped[str] = mapped_column(String(200), default="")
    submitted_answer: Mapped[str] = mapped_column(Text)
    expected_answer: Mapped[str] = mapped_column(Text)
    correct: Mapped[bool] = mapped_column(Boolean)
    attempt_no: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), default="lesson_quiz")
    grader: Mapped[str] = mapped_column(String(16), default="exact_ci")
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    quiz_item: Mapped[QuizItem] = relationship(back_populates="attempts")


class LlmCall(Base):
    """One record per provider.generate() call, for cost tracking and usage history.

    course_id is a plain nullable integer (no foreign key) so usage history
    survives course deletion.
    """

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(100))
    stage: Mapped[str] = mapped_column(String(20))
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    approximate: Mapped[bool] = mapped_column(Boolean, default=False)


class AppSetting(Base):
    """Small persisted key/value store, e.g. the acknowledged cost-alert threshold."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class ReviewCard(Base):
    """One concept's scheduling state: the answer to "when should this come back?".

    Keyed on concept_key globally, with no course id, and the uniqueness constraint
    makes that deliberate rather than accidental. A learner who meets gradient descent
    in two courses has one memory of it, not two, and two cards would review the same
    concept twice as often while reporting mastery for each separately.

    concept_label is stored alongside the key because the key is normalized and lossy.
    Recomputing a display name from "gradient descent" would show the learner
    lowercase text they never wrote.

    state exists as its own column rather than being inferred from due and reps: the
    learning and relearning steps are minutes apart, and a card ten minutes into
    relearning is not the same thing as a card due today.

    stability and difficulty are NULL exactly while state is "new". One set and the
    other not is a corrupted row, not a state the scheduler can schedule from.

    fsrs_v and weights_hash stamp which algorithm and which parameters produced this
    row. Retraining the weights later must not silently reinterpret intervals that
    were computed under the old ones.
    """

    __tablename__ = "review_cards"
    __table_args__ = (
        # The queue query is "what is due now", so due carries the index. state is
        # indexed separately for the counts the dashboard shows per state.
        Index("ix_review_cards_due", "due"),
        Index("ix_review_cards_state", "state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_key: Mapped[str] = mapped_column(String(200), unique=True)
    concept_label: Mapped[str] = mapped_column(String(200), default="")
    # "new" | "learning" | "review" | "relearning"
    state: Mapped[str] = mapped_column(String(12), default="new")
    stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    due: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_review: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    step: Mapped[int] = mapped_column(Integer, default=0)
    fsrs_v: Mapped[str] = mapped_column(String(16), default="fsrs6")
    weights_hash: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    logs: Mapped[list["ReviewLog"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )


class ReviewLog(Base):
    """One rating applied to one card. Append-only: rows are never updated.

    review_cards holds only the current state, which is one row per concept and tells
    you nothing about how it got there. This table is what makes the schedule
    auditable and, more importantly, replayable: retraining the FSRS weights on this
    learner's own history needs the full sequence of (elapsed_days, rating), and a
    schedule you cannot recompute is a schedule you cannot improve.

    Both stability_before and stability_after are stored rather than just the result,
    so a row is readable on its own without replaying every row before it.

    suggested_rating and rating_source record what the derivation proposed and whether
    the learner overrode it. If overrides turn out to be common in one direction, that
    is the signal that the derivation policy is wrong, and it is invisible if only the
    final rating is kept.

    attempt_ids links back to the evidence: the exact attempt rows this rating was
    derived from, so a surprising interval can be traced to the answers behind it.
    """

    __tablename__ = "review_logs"
    __table_args__ = (
        # (card_id, reviewed_at) serves one card's history in order, which is what a
        # weight retrain and the per-concept timeline both read.
        Index("ix_review_logs_card_time", "card_id", "reviewed_at"),
        Index("ix_review_logs_time", "reviewed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("review_cards.id"))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    rating: Mapped[int] = mapped_column(Integer)  # 1 Again | 2 Hard | 3 Good | 4 Easy
    suggested_rating: Mapped[int] = mapped_column(Integer)
    # "derived" | "learner"
    rating_source: Mapped[str] = mapped_column(String(10), default="derived")
    rating_v: Mapped[str] = mapped_column(String(16), default="v1")
    state_before: Mapped[str] = mapped_column(String(12))
    stability_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    elapsed_days: Mapped[float] = mapped_column(Float, default=0.0)
    state_after: Mapped[str] = mapped_column(String(12))
    stability_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    scheduled_days: Mapped[int] = mapped_column(Integer, default=0)
    due_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempt_ids: Mapped[list] = mapped_column(JSON, default=list)
    items_correct: Mapped[int] = mapped_column(Integer, default=0)
    items_total: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fsrs_v: Mapped[str] = mapped_column(String(16), default="fsrs6")
    weights_hash: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    card: Mapped[ReviewCard] = relationship(back_populates="logs")


class UnavailableDay(Base):
    """A day the learner has declared off, so the planner does not schedule into it.

    day is a string, not a datetime, and that is the whole point of the column. A day
    off is a calendar day the learner named, not an instant: storing 2026-09-14T00:00
    would make it depend on which timezone read it back, and a day marked off in one
    place would silently become a different day in another.
    """

    __tablename__ = "unavailable_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[str] = mapped_column(String(10), unique=True)  # local YYYY-MM-DD
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RemediationNote(Base):
    """Generated help for a concept the learner keeps losing.

    Written when a card lapses in a way that repeated practice alone is not fixing.
    The rows persist rather than being generated on demand because they cost a model
    call: regenerating the same explanation on every page load would bill the learner
    for the same paragraph over and over.

    cooldown_until is what stops a struggling concept from generating a new note after
    every single lapse. A learner who is failing something repeatedly needs one good
    explanation and time to use it, not five near-identical ones stacking up.

    status goes to "cleared" rather than the row being deleted, so the history of what
    was hard, and when it stopped being hard, survives.

    model and run_id record which model wrote it and which generation run it belongs
    to, matching llm_calls, so a note can be tied back to its cost and to the prompt
    version that produced it.
    """

    __tablename__ = "remediation_notes"
    __table_args__ = (Index("ix_remediation_notes_card_created", "card_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("review_cards.id"))
    concept_key: Mapped[str] = mapped_column(String(200), default="")
    concept_label: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(10), default="llm")  # "llm" | "manual"
    model: Mapped[str] = mapped_column(String(100), default="")
    run_id: Mapped[str] = mapped_column(String(32), default="")
    triggered_by: Mapped[list] = mapped_column(JSON, default=list)  # review_logs ids
    # "active" | "cleared"
    status: Mapped[str] = mapped_column(String(12), default="active")
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
