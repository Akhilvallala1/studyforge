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

    source discriminates lesson quizzes from later review sessions, and grader
    versions the grading policy, so a future change from exact-match to something
    smarter does not make old rows unreadable. There is deliberately no rating
    column: FSRS ratings are derived from (correct, attempt_no, elapsed_ms) when
    scheduling lands, so storing one now would freeze a policy we have not chosen.
    """

    __tablename__ = "attempts"
    __table_args__ = (
        # A concurrent double-submit collides here instead of writing two rows
        # that both claim the same position in the item's history.
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
