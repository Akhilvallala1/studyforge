import os
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import generation, ingest, models
from app.db import get_session, init_db
from app.llm import get_provider

app = FastAPI(title="StudyForge", version="0.1.0")

_cors_origins = os.environ.get("STUDYFORGE_CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


class GenerateRequest(BaseModel):
    text: str | None = None
    url: str | None = None


def _save_course(session: Session, course: dict) -> models.Course:
    row = models.Course(title=course["title"], description=course["description"])
    for m_pos, module in enumerate(course["modules"]):
        module_row = models.Module(title=module["title"], position=m_pos)
        for l_pos, lesson in enumerate(module["lessons"]):
            lesson_row = models.Lesson(
                title=lesson["title"],
                position=l_pos,
                content=lesson.get("content", ""),
                concepts=lesson.get("concepts", []),
            )
            for item in lesson.get("quiz", []):
                lesson_row.quiz_items.append(
                    models.QuizItem(
                        question=item.get("question", ""),
                        kind=item.get("kind", "short"),
                        options=item.get("options", []),
                        answer=item.get("answer", ""),
                        concept=item.get("concept", ""),
                    )
                )
            module_row.lessons.append(lesson_row)
        row.modules.append(module_row)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@app.post("/courses/generate")
def generate_from_text(body: GenerateRequest, session: Session = Depends(get_session)):
    """Generate a course from pasted text or a URL. Synchronous for the MVP - 
    expect it to take a minute or more for large material."""
    if body.text:
        chunks = ingest.chunk_text(body.text)
    elif body.url:
        try:
            chunks = ingest.chunk_text(ingest.extract_url(body.url))
        except Exception as exc:
            raise HTTPException(502, f"Course generation failed: {exc}") from exc
    else:
        raise HTTPException(400, "Provide 'text' or 'url'")
    if not chunks:
        raise HTTPException(400, "No usable text found in the source")
    try:
        course = generation.generate_course(get_provider(), chunks)
    except Exception as exc:
        raise HTTPException(502, f"Course generation failed: {exc}") from exc
    row = _save_course(session, course)
    return {"id": row.id, "title": row.title}


@app.post("/courses/generate/pdf")
def generate_from_pdf(file: UploadFile, session: Session = Depends(get_session)):
    chunks = ingest.chunk_text(ingest.extract_pdf(file.file.read()))
    if not chunks:
        raise HTTPException(400, "No usable text found in the PDF")
    try:
        course = generation.generate_course(get_provider(), chunks)
    except Exception as exc:
        raise HTTPException(502, f"Course generation failed: {exc}") from exc
    row = _save_course(session, course)
    return {"id": row.id, "title": row.title}


@app.get("/courses")
def list_courses(session: Session = Depends(get_session)):
    rows = session.query(models.Course).order_by(models.Course.created_at.desc()).all()
    return [{"id": r.id, "title": r.title, "description": r.description} for r in rows]


@app.get("/courses/{course_id}")
def get_course(course_id: int, session: Session = Depends(get_session)):
    row = session.get(models.Course, course_id)
    if not row:
        raise HTTPException(404, "Course not found")
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "modules": [
            {
                "id": m.id,
                "title": m.title,
                "lessons": [
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "completed": lesson.completed_at is not None,
                    }
                    for lesson in m.lessons
                ],
            }
            for m in row.modules
        ],
    }


@app.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int, session: Session = Depends(get_session)):
    lesson = session.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    return {
        "id": lesson.id,
        "title": lesson.title,
        "content": lesson.content,
        "concepts": lesson.concepts,
        "completed": lesson.completed_at is not None,
        "quiz": [
            {
                "id": q.id,
                "question": q.question,
                "kind": q.kind,
                "options": q.options,
                "concept": q.concept,
            }
            for q in lesson.quiz_items
        ],
    }


class QuizAnswer(BaseModel):
    answer: str


@app.post("/quiz/{item_id}/answer")
def answer_quiz(item_id: int, body: QuizAnswer, session: Session = Depends(get_session)):
    item = session.get(models.QuizItem, item_id)
    if not item:
        raise HTTPException(404, "Quiz item not found")
    correct = body.answer.strip().lower() == item.answer.strip().lower()
    return {"correct": correct, "expected": item.answer}


@app.post("/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: int, session: Session = Depends(get_session)):
    lesson = session.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    lesson.completed_at = datetime.now(UTC)
    session.commit()
    return {"id": lesson.id, "completed": True}
