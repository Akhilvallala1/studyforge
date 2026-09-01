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
    text,
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

    # The exam, the interview, the day the material stops being optional. A string in
    # local YYYY-MM-DD, not a DateTime, for exactly the reason UnavailableDay.day gives
    # below: a day the learner named is not an instant. "My exam is on the 14th" stays
    # the 14th wherever it is read back from, and storing 2026-09-14T00:00 would make it
    # the 13th for anyone east of the machine that wrote it.
    #
    # Both columns are NULLABLE and carry NO server default, and neither is a style
    # choice. A course without a deadline is the normal case and behaves exactly as it
    # did before this feature, so NULL has to mean something. And the ALTER TABLE that
    # adds these to an existing database (see app/db.py) is only legal without a default
    # while the column is nullable: SQLite accepts ADD COLUMN ... NOT NULL against an
    # empty table and rejects it against a table with even one row, so a NOT NULL variant
    # would pass every test on a fresh install and brick every real one.
    deadline: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # What the deadline IS, in the learner's words: "Midterm", "CS230 final". Free text
    # they typed, so anything rendering it (including the .ics export) treats it as
    # untrusted the way it treats an LLM-written course title.
    deadline_label: Mapped[str | None] = mapped_column(String(200), nullable=True)

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

    WHAT A DAY OFF ACTUALLY DOES, now that study planning reads this table (it has
    existed since Phase 2 and had no consumer until then). It removes a day from the
    INTAKE DENOMINATOR: available_days shrinks, so the lessons-per-week the learner
    needs to hit their deadline goes up. That is the whole effect.

    It does NOT move a review card, and nothing may make it. Reviews are scheduled by
    memory decay and lessons by the calendar, and the two do not negotiate: a card due
    on a day off stays due on that day, because the learner's memory does not take the
    day off with them. Pushing it would corrupt the elapsed_days that FSRS fits against.
    The planner does not schedule LESSONS into a day off either; it schedules nothing
    into any particular day, it only counts the days that remain.

    Days off are GLOBAL, not per course, which is what the missing course_id says. A
    learner who is travelling is travelling for every course they are taking. Adding a
    course_id later would have to answer what an existing global row means for a course
    that did not exist when it was written, and there is no good answer.
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
    was hard, and when it stopped being hard, survives. A row is only ever written
    for a generation that succeeded, so a failed call leaves nothing here and the
    learner can try again; see remediation.generate_note.

    model and run_id record which model wrote it and which generation run it belongs
    to, matching llm_calls, so a note can be tied back to its cost and to the prompt
    version that produced it.
    """

    # SCHEMA DIVERGENCE, deliberate, and the reason is worth knowing before adding
    # a second active note per card. A partial unique index on card_id over the
    # open statuses briefly existed on this table and was removed when the
    # concurrency guard moved in-process (see remediation.generation_slot).
    # create_all never drops anything, so a database created while it existed
    # still carries uq_remediation_notes_open_card and a fresh one does not. No
    # current path can trip it, since exactly one note per card is ever active,
    # and adding the startup DDL to drop it would reintroduce the machinery that
    # removal was the point of. But a change that allows two active notes for one
    # card would pass on a fresh install and fail only on an old one, which is a
    # bad afternoon to hand someone without this note.
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


class TutorMessage(Base):
    """One turn of the tutor conversation about one concept. Append-only.

    There is no conversation table, for the same reason remedial practice has no
    practice table: a conversation is not a thing that gets updated, it is the rows
    for one concept_key read in (created_at, id) order. Adding a parent row would
    create a second place to ask "which conversation is this", which could then
    disagree with the messages themselves.

    concept_label is stored alongside the key for the reason RemediationNote stores
    one: the key is normalized and lossy, and a conversation has to render a display
    name long after the card, the lesson, and the course that named it are gone.

    beyond and check_question are SEPARATE COLUMNS and must stay that way. beyond is
    what the tutor said that its material did not support, and check_question is the
    question it asked back; flattening either into content as markdown would destroy
    the grounded/ungrounded boundary on every row written afterwards, and no migration
    can restore it because the information is simply not in the text. The JSON key the
    model replies with is still "check": this column is check_question because CHECK is
    reserved SQL, and while SQLAlchemy quotes it correctly, a raw-SQL debugging session
    or a future Postgres path would trip on it.

    `ask` is a THIRD column for the same reason, and NOT a reuse of check_question. A
    check question is optional decoration on a complete answer, and `ask` is the move the
    reply deliberately stopped short of, so a row carrying one is a reply that is not
    finished on purpose. Sharing the column would make "the tutor asked something back"
    and "the tutor withheld the last step" indistinguishable on every row ever written,
    and the run that decides when guided mode falls back to a plain answer is counted off
    exactly that distinction. Flattening it into content is the same loss one level worse:
    the withheld move would be replayed to the next turn as part of the grounded answer.
    Exactly one of the two is ever non-empty on a row, and tutor.parse_reply is what
    guarantees it.

    run_id and model match llm_calls, so a reply can be tied back to what it cost and
    to the model that wrote it. Both are blank on a learner row, which pays for nothing.
    """

    __tablename__ = "tutor_messages"
    __table_args__ = (
        # One conversation, read in order, and the per-concept daily cap counted off
        # the same rows.
        Index("ix_tutor_messages_concept_created", "concept_key", "created_at"),
        # The day-wide cap is not concept-scoped, so the index above cannot serve it
        # and it would otherwise scan every message ever written.
        Index("ix_tutor_messages_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_key: Mapped[str] = mapped_column(String(200))
    concept_label: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(10))  # "learner" | "tutor"
    # The learner's question, or the tutor's grounded answer.
    content: Mapped[str] = mapped_column(Text, default="")
    beyond: Mapped[str] = mapped_column(Text, default="")
    check_question: Mapped[str] = mapped_column(Text, default="")
    # The one move a guided reply withheld, handed back as a question. Empty on a learner
    # row and on every answer-mode reply, and beside check_question because that is the
    # field it is a sibling of: exactly one of the two is ever non-empty on a row.
    #
    # THE server_default IS NOT POLISH. This column is added to a table that has already
    # shipped, so app/db.py has to ALTER it into existing databases, and the entry there
    # and this line are a MATCHED PAIR: half of it is worse than neither half, because
    # neither half can be caught by reading either file alone. Measured, all three
    # spellings, reading (nullable, default) off the inspector:
    #   mapped_column(Text, default="") with ALTER ... TEXT NOT NULL DEFAULT ''
    #     -> fresh (False, None), upgraded (False, "''"), so they never agree;
    #   server_default here with ALTER ... TEXT DEFAULT '' and no NOT NULL
    #     -> upgraded is nullable where fresh is not;
    #   server_default here with ALTER ... TEXT NOT NULL DEFAULT ''
    #     -> identical, and every pre-existing row backfills to '' rather than to NULL.
    # `text` is imported at the top of this file for exactly this.
    ask: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    run_id: Mapped[str] = mapped_column(String(32), default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
