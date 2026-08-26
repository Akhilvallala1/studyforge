import logging
import os
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import generation, ingest, models
from app.concepts import normalize_concept
from app.db import get_session, init_db
from app.llm import get_provider
from app.llm.base import LLMCallError
from app.metering import CostLimitExceeded, MeteredLLM, acknowledge_alert, alert_state

logger = logging.getLogger("studyforge.api")

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
    usage_logger = logging.getLogger("studyforge.usage")
    if not usage_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        usage_logger.addHandler(handler)
        usage_logger.setLevel(logging.INFO)


def iso_utc(value: datetime | None) -> str | None:
    """Serialize a stored timestamp with an explicit UTC offset.

    SQLite drops tzinfo on write, so every datetime read back is naive. Without the
    offset, clients parse the timestamp as local time and show it shifted.
    """
    return None if value is None else value.replace(tzinfo=UTC).isoformat()


class GenerateRequest(BaseModel):
    text: str | None = None
    url: str | None = None


# User-facing copy for generation failures. The raw exception goes to the server
# log only: it leaked things like "[WinError 10061] No connection could be made
# because the target machine actively refused it" straight into the UI.
URL_FETCH_MESSAGE = "Could not fetch that URL. Check the address and that the page is reachable."
PDF_PARSE_MESSAGE = "Could not read that PDF. It may be scanned images or corrupted."
MODEL_FAILURE_MESSAGE = (
    "The model could not generate a course from this material. "
    "Try again, or try shorter material."
)
GENERIC_GENERATION_MESSAGE = "Course generation failed. Check the server logs for details."

# Parse failures (ValueError, including json.JSONDecodeError), refusals, missing
# keys in a provider response, and transport errors are all "the provider did not
# give us a usable course".
_MODEL_FAILURE_TYPES = (LLMCallError, ValueError, KeyError, httpx.HTTPError)


def _is_model_failure(exc: Exception) -> bool:
    if isinstance(exc, _MODEL_FAILURE_TYPES):
        return True
    # The Anthropic SDK's errors (connection, auth, rate limit) are provider
    # failures too; matched by module so main.py need not import the SDK.
    return type(exc).__module__.split(".")[0] == "anthropic"


def generation_failure(exc: Exception, stage: str) -> HTTPException:
    """Log the real error and return a 502 carrying copy a learner can act on.

    Call from inside an `except` block: logger.exception needs the live traceback.
    """
    logger.exception("Course generation failed during stage %s", stage)
    if stage == "url":
        message = URL_FETCH_MESSAGE
    elif stage == "pdf":
        message = PDF_PARSE_MESSAGE
    elif _is_model_failure(exc):
        message = MODEL_FAILURE_MESSAGE
    else:
        message = GENERIC_GENERATION_MESSAGE
    return HTTPException(502, message)


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


def _run_generation(session: Session, chunks: list[str]) -> dict:
    """Run the metered generation pipeline, save the course, backfill the run's
    llm_calls rows with the new course id, and return the generate-endpoint response."""
    run_id = uuid.uuid4().hex
    meter = MeteredLLM(get_provider(), run_id)
    try:
        course = generation.generate_course(meter, chunks)
    except CostLimitExceeded as exc:
        raise HTTPException(
            402,
            detail={
                "error": "cost_limit_exceeded",
                "message": "LLM spend limit reached",
                "limit_usd": exc.limit_usd,
                "spent_usd": exc.spent_usd,
            },
        ) from exc
    except Exception as exc:
        raise generation_failure(exc, "generate") from exc

    row = _save_course(session, course)
    session.query(models.LlmCall).filter(models.LlmCall.run_id == run_id).update(
        {"course_id": row.id}
    )
    session.commit()

    run_cost = (
        session.query(func.sum(models.LlmCall.estimated_cost_usd))
        .filter(models.LlmCall.run_id == run_id)
        .scalar()
        or 0.0
    )
    state = alert_state(session)
    return {
        "id": row.id,
        "title": row.title,
        "usage": {
            "run_cost_usd": run_cost,
            "total_cost_usd": state["total_usd"],
            "alert_active": state["active"],
        },
    }


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
            raise generation_failure(exc, "url") from exc
    else:
        raise HTTPException(400, "Provide 'text' or 'url'")
    if not chunks:
        raise HTTPException(400, "No usable text found in the source")
    return _run_generation(session, chunks)


@app.post("/courses/generate/pdf")
def generate_from_pdf(file: UploadFile, session: Session = Depends(get_session)):
    try:
        chunks = ingest.chunk_text(ingest.extract_pdf(file.file.read()))
    except Exception as exc:
        raise generation_failure(exc, "pdf") from exc
    if not chunks:
        raise HTTPException(400, "No usable text found in the PDF")
    return _run_generation(session, chunks)


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


LESSON_QUIZ_SOURCE = "lesson_quiz"
# Grading policy identifier, stored on every attempt. Bump it if the comparison
# below changes, so old rows stay interpretable under the rules they were graded by.
GRADER = "exact_ci"
MAX_ELAPSED_MS = 86_400_000
# A second click on the submit button is one answer, not two.
DOUBLE_SUBMIT_WINDOW = timedelta(seconds=2)


def _normalized_answer(text: str) -> str:
    return text.strip().lower()


def _grade(submitted: str, expected: str) -> bool:
    return _normalized_answer(submitted) == _normalized_answer(expected)


def _attempt_state(attempts: list[models.Attempt]) -> dict:
    """Summarize one quiz item's history, from its attempts ordered by attempt_no.

    attempts/first_attempt_correct/latest_quiz_attempt describe the lesson quiz only,
    so a later review session cannot rewrite how the item went the first time.
    ever_correct counts every source: recalling it in review is still evidence of
    knowing it.

    latest_quiz_attempt is named for its scope on purpose. Once review attempts exist
    it is no longer "most recent activity" on the item, and a caller treating it as
    "last practiced" would be wrong in a way nothing would flag.
    """
    quiz_attempts = [a for a in attempts if a.source == LESSON_QUIZ_SOURCE]
    latest = quiz_attempts[-1] if quiz_attempts else None
    return {
        "attempts": len(quiz_attempts),
        "first_attempt_correct": quiz_attempts[0].correct if quiz_attempts else None,
        "ever_correct": any(a.correct for a in attempts),
        "latest_quiz_attempt": None
        if latest is None
        else {
            # expected rides inside this object, which exists only once the learner
            # has answered. That is what keeps unattempted questions from leaking the key.
            "answer": latest.submitted_answer,
            "correct": latest.correct,
            "expected": latest.expected_answer,
            "created_at": iso_utc(latest.created_at),
        },
    }


def _attempts_for_item(session: Session, quiz_item_id: int) -> list[models.Attempt]:
    return (
        session.query(models.Attempt)
        .filter(models.Attempt.quiz_item_id == quiz_item_id)
        .order_by(models.Attempt.attempt_no)
        .all()
    )


def _attempts_by_item(session: Session, lesson_id: int) -> dict[int, list[models.Attempt]]:
    """Every attempt in the lesson in one query, grouped in Python (no per-item N+1)."""
    rows = (
        session.query(models.Attempt)
        .filter(models.Attempt.lesson_id == lesson_id)
        .order_by(models.Attempt.quiz_item_id, models.Attempt.attempt_no)
        .all()
    )
    grouped: dict[int, list[models.Attempt]] = defaultdict(list)
    for row in rows:
        grouped[row.quiz_item_id].append(row)
    return grouped


def _sanitize_elapsed_ms(value: int | None) -> int | None:
    """Drop an implausible client-reported duration instead of rejecting the answer.

    elapsed_ms is a soft signal for future scheduling; a bad clock or a tab left
    open overnight must never cost the learner a real answer.
    """
    if value is None or not 0 <= value <= MAX_ELAPSED_MS:
        return None
    return value


def _recent_duplicate(
    session: Session, quiz_item_id: int, submitted: str, source: str = LESSON_QUIZ_SOURCE
) -> models.Attempt | None:
    """Best-effort double-click guard: catches a resubmit that arrives after the first
    one committed. Truly simultaneous submits both read no prior row and both insert.

    Scoped to one source so a review attempt can never swallow a lesson-quiz submission
    and hand the caller back a row of the wrong kind.
    """
    newest = (
        session.query(models.Attempt)
        .filter(models.Attempt.quiz_item_id == quiz_item_id)
        .filter(models.Attempt.source == source)
        .order_by(models.Attempt.attempt_no.desc())
        .first()
    )
    if newest is None:
        return None
    if _normalized_answer(newest.submitted_answer) != _normalized_answer(submitted):
        return None
    age = datetime.now(UTC) - newest.created_at.replace(tzinfo=UTC)
    return newest if abs(age) <= DOUBLE_SUBMIT_WINDOW else None


def _record_attempt(
    session: Session,
    item: models.QuizItem,
    submitted: str,
    correct: bool,
    elapsed_ms: int | None,
    source: str = LESSON_QUIZ_SOURCE,
) -> models.Attempt:
    """Append one attempt row. Attempts are never updated: the history is the data.

    Everything but the submitted answer and the elapsed time comes off the quiz item
    server-side, so a client cannot claim a different lesson, concept, or answer key.
    """
    duplicate = _recent_duplicate(session, item.id, submitted)
    if duplicate is not None:
        return duplicate

    # count+1 is safe only while attempts are never removed. If pruning or archival
    # is ever added, a gap makes every recount collide on the same taken ordinal and
    # this wedges permanently at 409; switch to max(attempt_no)+1 at that point.
    for _ in range(2):
        prior = (
            session.query(func.count(models.Attempt.id))
            .filter(models.Attempt.quiz_item_id == item.id)
            .scalar()
            or 0
        )
        row = models.Attempt(
            quiz_item_id=item.id,
            lesson_id=item.lesson_id,
            concept_key=normalize_concept(item.concept),
            concept_label=item.concept or "",
            submitted_answer=submitted,
            expected_answer=item.answer,
            correct=correct,
            attempt_no=prior + 1,
            source=source,
            grader=GRADER,
            elapsed_ms=elapsed_ms,
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            # Another request took this attempt_no between the count and the insert.
            # Re-count and try once more before giving up.
            session.rollback()
            continue
        session.refresh(row)
        return row

    raise HTTPException(409, "That answer collided with another submission. Try again.")


@app.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int, session: Session = Depends(get_session)):
    lesson = session.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    by_item = _attempts_by_item(session, lesson.id)
    quiz = []
    answered = correct = first_try_correct = 0
    for q in lesson.quiz_items:
        state = _attempt_state(by_item.get(q.id, []))
        if state["attempts"]:
            answered += 1
        if state["ever_correct"]:
            correct += 1
        if state["first_attempt_correct"]:
            first_try_correct += 1
        quiz.append(
            {
                "id": q.id,
                "question": q.question,
                "kind": q.kind,
                "options": q.options,
                "concept": q.concept,
                "attempt_state": state,
            }
        )

    return {
        "id": lesson.id,
        "title": lesson.title,
        "content": lesson.content,
        "concepts": lesson.concepts,
        "completed": lesson.completed_at is not None,
        "completed_at": iso_utc(lesson.completed_at),
        "quiz": quiz,
        "quiz_progress": {
            "items": len(quiz),
            "answered": answered,
            "correct": correct,
            "first_try_correct": first_try_correct,
        },
    }


@app.get("/lessons/{lesson_id}/attempts")
def get_lesson_attempts(lesson_id: int, session: Session = Depends(get_session)):
    """Full attempt history for the lesson, oldest first."""
    lesson = session.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    rows = (
        session.query(models.Attempt)
        .filter(models.Attempt.lesson_id == lesson_id)
        .order_by(models.Attempt.created_at, models.Attempt.id)
        .all()
    )
    return {
        "lesson_id": lesson.id,
        "attempts": [
            {
                "id": r.id,
                "quiz_item_id": r.quiz_item_id,
                "lesson_id": r.lesson_id,
                "concept_key": r.concept_key,
                "concept_label": r.concept_label,
                "submitted_answer": r.submitted_answer,
                "expected_answer": r.expected_answer,
                "correct": r.correct,
                "attempt_no": r.attempt_no,
                "source": r.source,
                "grader": r.grader,
                "elapsed_ms": r.elapsed_ms,
                "created_at": iso_utc(r.created_at),
            }
            for r in rows
        ],
    }


class QuizAnswer(BaseModel):
    answer: str
    elapsed_ms: int | None = None


@app.post("/quiz/{item_id}/answer")
def answer_quiz(item_id: int, body: QuizAnswer, session: Session = Depends(get_session)):
    item = session.get(models.QuizItem, item_id)
    if not item:
        raise HTTPException(404, "Quiz item not found")
    if not body.answer.strip():
        raise HTTPException(400, "Answer cannot be empty")

    attempt = _record_attempt(
        session,
        item,
        body.answer,
        _grade(body.answer, item.answer),
        _sanitize_elapsed_ms(body.elapsed_ms),
    )
    return {
        "correct": attempt.correct,
        "expected": item.answer,
        "attempt_id": attempt.id,
        "attempt_no": attempt.attempt_no,
        "attempt_state": _attempt_state(_attempts_for_item(session, item.id)),
    }


def _completion_state(lesson: models.Lesson) -> dict:
    return {
        "id": lesson.id,
        "completed": lesson.completed_at is not None,
        "completed_at": iso_utc(lesson.completed_at),
    }


@app.post("/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: int, session: Session = Depends(get_session)):
    """Idempotent: completed_at records when the lesson was first finished, so a
    repeat POST must not push that timestamp forward."""
    lesson = session.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    if lesson.completed_at is None:
        lesson.completed_at = datetime.now(UTC)
        session.commit()
    return _completion_state(lesson)


@app.delete("/lessons/{lesson_id}/complete")
def uncomplete_lesson(lesson_id: int, session: Session = Depends(get_session)):
    """Reopen a lesson. Attempts are untouched: un-completing means "I want another
    pass at this", not "erase what I did"."""
    lesson = session.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    if lesson.completed_at is not None:
        lesson.completed_at = None
        session.commit()
    return _completion_state(lesson)


@app.get("/usage")
def get_usage(limit: int = 50, session: Session = Depends(get_session)):
    limit = max(1, min(limit, 500))

    calls = session.query(func.count(models.LlmCall.id)).scalar() or 0
    input_tokens = session.query(func.sum(models.LlmCall.input_tokens)).scalar() or 0
    output_tokens = session.query(func.sum(models.LlmCall.output_tokens)).scalar() or 0
    estimated_cost_usd = session.query(func.sum(models.LlmCall.estimated_cost_usd)).scalar() or 0.0
    any_approximate = (
        session.query(models.LlmCall.id).filter(models.LlmCall.approximate.is_(True)).first()
        is not None
    )

    per_course_rows = (
        session.query(
            models.LlmCall.course_id,
            func.count(models.LlmCall.id),
            func.sum(models.LlmCall.input_tokens),
            func.sum(models.LlmCall.output_tokens),
            func.sum(models.LlmCall.estimated_cost_usd),
        )
        .group_by(models.LlmCall.course_id)
        .all()
    )
    per_course = []
    for course_id, course_calls, course_in, course_out, course_cost in per_course_rows:
        title = None
        if course_id is not None:
            course_row = session.get(models.Course, course_id)
            title = course_row.title if course_row else None
        per_course.append(
            {
                "course_id": course_id,
                "title": title,
                "calls": course_calls,
                "input_tokens": course_in or 0,
                "output_tokens": course_out or 0,
                "estimated_cost_usd": course_cost or 0.0,
            }
        )

    recent_rows = (
        session.query(models.LlmCall).order_by(models.LlmCall.id.desc()).limit(limit).all()
    )
    recent_calls = [
        {
            "id": r.id,
            "created_at": iso_utc(r.created_at),
            "provider": r.provider,
            "model": r.model,
            "stage": r.stage,
            "course_id": r.course_id,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "estimated_cost_usd": r.estimated_cost_usd,
            "approximate": r.approximate,
        }
        for r in recent_rows
    ]

    limit_env = os.environ.get("STUDYFORGE_COST_LIMIT_USD")
    limit_usd = float(limit_env) if limit_env is not None else None
    total_spent = estimated_cost_usd
    limit_info = {
        "configured": limit_env is not None,
        "limit_usd": limit_usd,
        "reached": limit_env is not None and total_spent >= limit_usd,
    }

    return {
        "totals": {
            "calls": calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "approximate": any_approximate,
        },
        "per_course": per_course,
        "recent_calls": recent_calls,
        "alert": alert_state(session),
        "limit": limit_info,
    }


@app.post("/usage/alert/ack")
def ack_usage_alert(session: Session = Depends(get_session)):
    return acknowledge_alert(session)
