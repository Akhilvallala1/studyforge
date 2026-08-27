import logging
import os
import uuid
from collections import defaultdict
from datetime import UTC, datetime

import httpx
from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import days, fsrs, generation, ingest, models, review
from app.attempts import (
    _attempt_state,
    _attempts_by_item,
    _attempts_for_item,
    _grade,
    _record_attempt,
    _sanitize_elapsed_ms,
    iso_utc,
)
from app.concepts import normalize_concept
from app.db import get_session, init_db
from app.llm import get_provider
from app.llm.base import LLMCallError
from app.metering import CostLimitExceeded, MeteredLLM, acknowledge_alert, alert_state
from app.rating import rating_v1

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
    repeat POST must not push that timestamp forward.

    Completion is also where a lesson's concepts enter the review schedule. Grading
    here rather than on each answer means the learner chose the boundary, and it is
    idempotent for the same reason the timestamp is: review.grade_lesson only reads
    attempts newer than the card's last review, so a repeat POST rates nothing.
    """
    lesson = session.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    scheduled = review.grade_lesson(session, lesson)
    if lesson.completed_at is None:
        lesson.completed_at = datetime.now(UTC)
    session.commit()
    return _completion_state(lesson) | {"scheduled_concepts": len(scheduled)}


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


def _card_payload(
    row: models.ReviewCard, item: models.QuizItem | None, now: datetime
) -> dict:
    """One queue entry: the card, the question to ask, and the four button intervals."""
    return {
        "card_id": row.id,
        "concept_key": row.concept_key,
        "concept_label": row.concept_label,
        "state": row.state,
        "due": iso_utc(row.due),
        "lapses": row.lapses,
        "retrievability": review.card_retrievability(row, now),
        "preview": review.preview(row, now),
        # No answer key: the learner has not answered yet, and the whole point of a
        # review is that they retrieve it rather than recognize it.
        "item": None
        if item is None
        else {
            "id": item.id,
            "question": item.question,
            "kind": item.kind,
            "options": item.options,
        },
    }


@app.get("/review/today")
def get_review_today(session: Session = Depends(get_session)):
    """The Today screen: what is due, how the learner is doing, and what is slipping."""
    now = review.now_utc()
    counts = review.due_counts(session, now)
    struggling = review.needs_attention(session, now)
    due_now = counts["due_today"]
    return {
        "date": days.today_key(now),
        **counts,
        **review.retention(session, now),
        "day_streak": review.day_streak(session, now),
        "estimated_minutes": review.estimated_minutes(session, due_now),
        # "4 of these you have struggled with before", on the review session card.
        "struggling_due": sum(1 for entry in struggling if entry["is_due"]),
        "needs_attention": [entry | {"due": iso_utc(entry["due"])} for entry in struggling],
    }


@app.get("/review/queue")
def get_review_queue(
    limit: int = review.DEFAULT_QUEUE_LIMIT, session: Session = Depends(get_session)
):
    """Cards due right now, hardest-to-recall first.

    `limit` caps how many are handed to the client, but nothing is rescheduled to fit
    it: `due_total` reports the real backlog. Trimming the schedule to fit a session
    would be the scheduler lying to make a number look better.
    """
    limit = max(1, min(limit, 200))
    now = review.now_utc()
    rows = review.due_cards(session, now)
    served = rows[:limit]
    items = review.pick_items(session, [row.concept_key for row in served])
    return {
        "due_total": len(rows),
        "estimated_minutes": review.estimated_minutes(session, len(rows)),
        "cards": [_card_payload(row, items.get(row.concept_key), now) for row in served],
    }


class ReviewAnswer(BaseModel):
    item_id: int
    answer: str
    elapsed_ms: int | None = None


@app.post("/review/cards/{card_id}/answer")
def answer_review(card_id: int, body: ReviewAnswer, session: Session = Depends(get_session)):
    """Record an answer given during a review session and suggest a rating for it.

    Nothing is scheduled here. The learner sees their own answer against the expected
    one and then rates their recall, which is what the review screen shows and what
    the separate rate endpoint applies. The suggestion exists so the UI can preselect
    a button, and whether the learner overrides it is recorded when they rate.
    """
    card = session.get(models.ReviewCard, card_id)
    if not card:
        raise HTTPException(404, "Review card not found")
    item = session.get(models.QuizItem, body.item_id)
    if not item:
        raise HTTPException(404, "Quiz item not found")
    if normalize_concept(item.concept) != card.concept_key:
        raise HTTPException(400, "That quiz item does not test this concept")
    if not body.answer.strip():
        raise HTTPException(400, "Answer cannot be empty")

    # One try per item per exposure, enforced here because this response hands back
    # the answer key. Without the guard a learner can answer wrong, read `expected`,
    # resubmit it, and be graded as a clean recall, which defeats the retrieval test
    # the card exists to run. The exposure starts at the card's last review, so the
    # next time this concept comes due the item is answerable again.
    if review.already_answered_this_exposure(session, card, item):
        raise HTTPException(409, "You have already answered this question in this review")

    attempt = _record_attempt(
        session,
        item,
        body.answer,
        _grade(body.answer, item.answer),
        _sanitize_elapsed_ms(body.elapsed_ms),
        source=review.REVIEW_SESSION_SOURCE,
    )
    suggested = rating_v1([attempt], {item.id: item})
    return {
        "correct": attempt.correct,
        "expected": item.answer,
        "submitted": attempt.submitted_answer,
        "attempt_id": attempt.id,
        "suggested_rating": suggested.rating,
        "rating_v": suggested.rating_v,
        "preview": review.preview(card, review.now_utc()),
    }


class ReviewRating(BaseModel):
    rating: int
    suggested_rating: int | None = None
    attempt_ids: list[int] | None = None


@app.post("/review/cards/{card_id}/rate")
def rate_review(card_id: int, body: ReviewRating, session: Session = Depends(get_session)):
    """Apply the learner's rating to a card and reschedule it."""
    card = session.get(models.ReviewCard, card_id)
    if not card:
        raise HTTPException(404, "Review card not found")
    if body.rating not in fsrs.RATINGS:
        raise HTTPException(400, f"rating must be one of {list(fsrs.RATINGS)}")

    suggested = body.suggested_rating
    log = review.record_review(
        session,
        card.concept_key,
        card.concept_label,
        body.rating,
        suggested_rating=suggested,
        # "learner" only when they actually disagreed with the suggestion. Recording
        # every rating as an override would drown the signal that the derivation is
        # miscalibrated, which is the reason the column exists.
        rating_source=review.LEARNER
        if suggested is not None and suggested != body.rating
        else review.DERIVED,
        attempt_ids=body.attempt_ids,
    )
    session.commit()
    return {
        "card_id": card.id,
        "concept_key": card.concept_key,
        "state": card.state,
        "stability": card.stability,
        "difficulty": card.difficulty,
        "due": iso_utc(card.due),
        "reps": card.reps,
        "lapses": card.lapses,
        "scheduled_days": log.scheduled_days,
        "interval_label": review.format_interval(card.due - log.reviewed_at),
    }


@app.get("/courses/{course_id}/concepts")
def get_course_concepts(course_id: int, session: Session = Depends(get_session)):
    """The concept map's data: every concept in the course with its mastery bucket.

    `locked` is deliberately absent from the buckets. Concept prerequisites are not in
    the data model yet, so nothing here can honestly say a concept is gated.
    """
    course = session.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    now = review.now_utc()
    concepts = review.course_concepts(session, course, now)
    counts: dict[str, int] = defaultdict(int)
    for concept in concepts:
        counts[concept["bucket"]] += 1
    return {
        "course_id": course.id,
        "title": course.title,
        "counts": dict(counts),
        "concepts": [entry | {"due": iso_utc(entry["due"])} for entry in concepts],
    }


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
