from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
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
