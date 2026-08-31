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

from app import days, fsrs, generation, ingest, models, remediation, review
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
from app.costs import is_priced
from app.db import SessionLocal, get_session, init_db
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

    # One-time repair of re-teaching calls recorded before they were attributed to a
    # course. On the first boot after upgrading; a no-op on every boot after that.
    session = SessionLocal()
    try:
        attributed = remediation.backfill_course_ids(session)
        session.commit()
    finally:
        session.close()
    if attributed:
        logger.info(
            "Attributed %s re-teaching call(s) recorded before attribution existed", attributed
        )


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
REMEDIATION_FAILURE_MESSAGE = (
    "Could not write an explanation for this concept just now. Try again in a moment."
)
NO_MATERIAL_MESSAGE = (
    "There is no lesson text for this concept to explain from. It may have come from a "
    "course that has since been deleted."
)

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
    """Log the real error and return copy a learner can act on.

    Call from inside an `except` block: logger.exception needs the live traceback.

    The status says whose problem it is. A refused URL or an unreadable upload is
    the request's fault and gets a 4xx; a provider or pipeline failure is ours and
    gets a 502. Returning 502 for a corrupt PDF told the caller to retry something
    that will never succeed.
    """
    logger.exception("Course generation failed during stage %s", stage)
    # This branch must stay above _is_model_failure. UnsafeURLError subclasses
    # ValueError, which counts as a model failure, so moving it down would turn every
    # refused URL into "the model could not generate a course from this material".
    if isinstance(exc, ingest.UnsafeURLError):
        return HTTPException(400, str(exc))
    if stage == "url":
        return HTTPException(502, URL_FETCH_MESSAGE)
    if stage == "pdf":
        return HTTPException(400, PDF_PARSE_MESSAGE)
    if _is_model_failure(exc):
        return HTTPException(502, MODEL_FAILURE_MESSAGE)
    return HTTPException(502, GENERIC_GENERATION_MESSAGE)


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
    due_now = counts["due_now"]
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


def _remediation_conflict(
    code: str, message: str, note: models.RemediationNote | None
) -> HTTPException:
    """409 that carries the note the caller cannot replace.

    The note travels with the refusal rather than being fetched in a second round
    trip, because the only sensible thing for the UI to do about "you already have
    one of these" is show the one it already has.
    """
    return HTTPException(
        409,
        detail={
            "error": code,
            "message": message,
            "note": remediation.note_payload(note),
        },
    )


def _blocking_conflict(
    existing: models.RemediationNote | None, now: datetime
) -> HTTPException | None:
    """The 409 an existing note earns, or None if it does not stand in the way."""
    if existing is None:
        return None
    if existing.status == remediation.ACTIVE:
        return _remediation_conflict(
            "note_active", "This concept already has an explanation.", existing
        )
    # Checked against the latest row whatever its status, so clearing a note does not
    # reopen the budget. The cooldown is what keeps a thrashing card from buying a
    # fresh explanation on every lapse.
    if remediation.in_cooldown(existing, now):
        return _remediation_conflict(
            "cooldown_active",
            "This concept was explained recently. Here is that explanation.",
            existing,
        )
    return None


@app.post("/review/cards/{card_id}/remediation")
def create_remediation(card_id: int, session: Session = Depends(get_session)):
    """Re-teach a concept the learner keeps missing: one metered model call.

    Every refusal is a 409 carrying an `error` code, so the client has one branch to
    write rather than four. `note_active` and `cooldown_active` hand back the
    existing note in `detail.note`. The other two carry `detail.note = null`:
    `generation_in_progress` because the request holding the slot has not written
    anything yet, and `not_flagged` because review.needs_attention does not
    currently report this concept, which is the same trigger the Today screen's
    button is drawn from, so it only fires on a stale or hand-made request.

    The whole check-and-call sits inside remediation.generation_slot, because
    checking whether a note exists and then writing one is a check-then-act guard
    that two simultaneous requests both pass; a double-clicked button produces
    exactly that pair, and both would pay for a model call. The second request is
    refused at once with `generation_in_progress` rather than made to wait, since
    waiting behind a 600s provider timeout looks to the browser like a hang.

    The card is not touched. It keeps its stability, its lapses, and its due date,
    and it stays in the review queue: re-teaching is offered alongside the schedule,
    not instead of it.
    """
    card = session.get(models.ReviewCard, card_id)
    if not card:
        raise HTTPException(404, "Review card not found")

    now = review.now_utc()
    try:
        with remediation.generation_slot(card.id):
            if remediation.clear_resolved(session, now):
                session.commit()

            conflict = _blocking_conflict(remediation.latest_note(session, card.id), now)
            if conflict is not None:
                raise conflict
            if card.concept_key not in remediation.flagged_keys(session, now):
                raise _remediation_conflict(
                    "not_flagged", "This concept is not currently one you are missing.", None
                )
            note = remediation.generate_note(session, card, get_provider(), now=now)
    except remediation.AlreadyGenerating as exc:
        # No note to hand back: the request holding the slot has not written one yet.
        logger.info("remediation for card %s refused, already generating", card_id)
        raise _remediation_conflict(
            "generation_in_progress",
            "An explanation for this concept is already being written.",
            None,
        ) from exc
    except HTTPException:
        # The 409s raised inside the slot above. Re-raised before the catch-all, which
        # would otherwise turn every one of them into a 502.
        raise
    except remediation.NoMaterial as exc:
        session.rollback()
        logger.warning("remediation refused for card %s: %s", card_id, exc)
        raise HTTPException(422, NO_MATERIAL_MESSAGE) from exc
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
    except ValueError as exc:
        # The provider answered and the answer did not match the schema. Logged
        # apart from a transport failure because the two need opposite fixes, and
        # because reporting a schema mismatch as "the model could not be reached"
        # is what hid the fake provider having no remediation branch at all: every
        # offline re-teach failed, and the log said the network was to blame.
        session.rollback()
        logger.error(
            "Remediation for card %s: the model replied but the reply did not match the "
            "schema (%s)",
            card_id,
            exc,
        )
        raise HTTPException(502, REMEDIATION_FAILURE_MESSAGE) from exc
    except Exception as exc:
        # A failed generation writes no row and the slot is released on the way out,
        # so the learner can click again rather than waiting out a week's cooldown
        # for a note that was never written.
        session.rollback()
        logger.exception("Remediation failed for card %s: the provider call failed", card_id)
        raise HTTPException(502, REMEDIATION_FAILURE_MESSAGE) from exc

    return remediation.note_payload(note)


@app.get("/review/cards/{card_id}/remediation")
def get_remediation(card_id: int, session: Session = Depends(get_session)):
    """The card's active remedial note, or null once the concept stops being flagged."""
    card = session.get(models.ReviewCard, card_id)
    if not card:
        raise HTTPException(404, "Review card not found")
    if remediation.clear_resolved(session, review.now_utc()):
        session.commit()
    return remediation.note_payload(remediation.active_note(session, card.id))


@app.get("/courses/{course_id}/concepts")
def get_course_concepts(course_id: int, session: Session = Depends(get_session)):
    """The concept map's data: every concept in the course with its mastery bucket.

    `locked` is deliberately absent from the buckets. Concept prerequisites are not in
    the data model yet, so nothing here can honestly say a concept is gated.

    `edges_available` says the same thing to the client in a field it can branch on,
    and it is False because no code path anywhere extracts a dependency between two
    concepts. It exists so the map never has to guess: while it is False a client must
    draw no arrows, and it must not infer them from `lesson_index`, which is course
    order and not a dependency. Should a real prerequisite graph ever land, this flips
    and an `edges` payload joins it; until then a client receiving `locked` from a
    future server should degrade to not-started rather than invent a gate.

    `lessons` is the map's column list, in the order the course teaches them, and is
    sent whole rather than derived from `concepts` so that a lesson which teaches
    nothing still gets a column instead of silently vanishing from the map.
    """
    course = session.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    now = review.now_utc()
    lessons = review.course_lessons(session, course)
    concepts = review.course_concepts(session, course, now, lessons=lessons)
    counts: dict[str, int] = defaultdict(int)
    for concept in concepts:
        counts[concept["bucket"]] += 1
    weakest = review.weakest_concept(concepts)
    return {
        "course_id": course.id,
        "title": course.title,
        "edges_available": False,
        "counts": dict(counts),
        "lessons": [
            {"id": lesson.id, "title": lesson.title, "index": index}
            for index, lesson in enumerate(lessons)
        ],
        "concepts": [entry | {"due": iso_utc(entry["due"])} for entry in concepts],
        "weakest": None if weakest is None else weakest | {"due": iso_utc(weakest["due"])},
    }


# --------------------------------------------------------------------------
# Usage reporting
# --------------------------------------------------------------------------

# How /usage groups spend, and the sentence the page prints under each group that is
# not a course. The copy lives beside the grouping rather than in the page because
# whether a sentence is TRUE is a fact about how these rows were grouped, and the two
# drifted apart once already: re-teaching calls were filed under "Unattributed", whose
# note told the learner that seven successful re-teaches were failed generation runs.
GROUP_COURSE = "course"
GROUP_REMEDIATION = "remediation"
GROUP_FAILED_RUN = "failed_run"

GROUP_LABELS = {
    GROUP_REMEDIATION: "Re-teaching (no single course)",
    GROUP_FAILED_RUN: "Unattributed",
}

GROUP_NOTES = {
    # Three causes, because there are three, and a shorter list asserts something false
    # about the rows it leaves out. A concept taught by NO course is not the same story
    # as one taught by several: remediation._sole answers None to both, and by the time
    # this renders nothing can tell them apart, so both are named. Says nothing about
    # whether these calls succeeded, either: a re-teaching call that failed still records
    # the tokens it spent, and lands in this group like any other.
    GROUP_REMEDIATION: (
        "Re-teaching a concept is charged to the course that teaches it. These calls could "
        "not be charged to one course: the concept is taught by several courses, or by none "
        "of them any more, or the call failed before anything recorded which concept it "
        "was for."
    ),
    # "or from one still running" is not padding. Generation is synchronous and can take
    # minutes, and its rows carry no course until it finishes, so a learner who opens
    # this page mid-run is reading about a run that has not failed at all.
    GROUP_FAILED_RUN: (
        '"Unattributed" calls have no course to attach to: they come from a generation run '
        "that failed before its course could be saved, or from one still running now."
    ),
}

# Keyed on (a token count was estimated, a price was estimated). The row's single
# approximate flag is set by either, and the page used to name only the first.
APPROXIMATE_NOTES = {
    (True, False): (
        "Some of these figures are approximate: at least one recorded call is missing an "
        "exact token count, so its cost was worked out from an estimated count."
    ),
    (False, True): (
        "Some of these figures are approximate: at least one recorded call used a model with "
        "no entry in the pricing table, so its cost was worked out from the configured "
        "fallback price. The token counts are exact."
    ),
    (True, True): (
        "Some of these figures are approximate: at least one recorded call used a model with "
        "no entry in the pricing table, and at least one is missing an exact token count."
    ),
}


def _approximation_causes(session: Session) -> tuple[bool, bool]:
    """(a token count was estimated, a price was estimated), across all recorded calls.

    llm_calls stores one boolean for two different causes, and the page named only the
    first of them. A model whose id is not in costs.PRICING reports exact token counts
    and gets an estimated PRICE, and was told its token counts were the estimate.

    The two stay separable from what is already recorded, with no new column. A row
    with both counts present is flagged only when the model had no price, so it is the
    price case outright. A row missing a count is the token case, and is ALSO the price
    case when an unpriced model still charged for the count that was present: cost above
    zero is what proves a price was applied at all, since an unpaid provider always
    records zero and a paid one with no counts at all prices zero tokens at any rate.

    One gap, left open knowingly. If the count that survived is itself 0, the cost is 0
    too (costs.estimate_cost treats a missing count as zero), so nothing proves a rate
    was applied and the row reports the token cause alone. The sentence stays true and
    is merely less complete, and a call that really consumed zero input tokens does not
    happen; closing it properly would mean recording whether the provider was paid,
    which is a column this change is not entitled to add.
    """
    rows = (
        session.query(
            models.LlmCall.model,
            models.LlmCall.input_tokens,
            models.LlmCall.output_tokens,
            models.LlmCall.estimated_cost_usd,
        )
        .filter(models.LlmCall.approximate.is_(True))
        .all()
    )
    estimated_tokens = False
    estimated_price = False
    for model, input_tokens, output_tokens, cost in rows:
        if input_tokens is None or output_tokens is None:
            estimated_tokens = True
            if cost and cost > 0 and not is_priced(model):
                estimated_price = True
        else:
            estimated_price = True
        if estimated_tokens and estimated_price:
            break
    return estimated_tokens, estimated_price


def _unattributed_group(stage: str) -> str:
    """Why a call carrying no course id has none, read from the stage that wrote it.

    Every stage that is not re-teaching belongs to the generation pipeline
    (generation.STAGES), and those rows have their course id backfilled the moment
    the course is saved, so one still missing means the run never got that far.
    """
    if stage == remediation.REMEDIATION_STAGE:
        return GROUP_REMEDIATION
    return GROUP_FAILED_RUN


def _spend_groups(session: Session) -> list[dict]:
    """Spend for the /usage table: one row per course, then one row per reason a call
    has no course. Courses first in id order, then re-teaching, then the failed runs."""
    rows = (
        session.query(
            models.LlmCall.course_id,
            models.LlmCall.stage,
            func.count(models.LlmCall.id),
            func.sum(models.LlmCall.input_tokens),
            func.sum(models.LlmCall.output_tokens),
            func.sum(models.LlmCall.estimated_cost_usd),
        )
        .group_by(models.LlmCall.course_id, models.LlmCall.stage)
        .all()
    )
    buckets: dict[tuple[str, int | None], dict] = {}
    for course_id, stage, stage_calls, stage_in, stage_out, stage_cost in rows:
        group = GROUP_COURSE if course_id is not None else _unattributed_group(stage)
        bucket = buckets.setdefault(
            (group, course_id),
            {"calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0},
        )
        bucket["calls"] += stage_calls
        bucket["input_tokens"] += stage_in or 0
        bucket["output_tokens"] += stage_out or 0
        bucket["estimated_cost_usd"] += stage_cost or 0.0

    rank = {GROUP_COURSE: 0, GROUP_REMEDIATION: 1, GROUP_FAILED_RUN: 2}
    groups = []
    for (group, course_id), bucket in sorted(
        buckets.items(), key=lambda item: (rank[item[0][0]], item[0][1] or 0)
    ):
        course_row = session.get(models.Course, course_id) if group == GROUP_COURSE else None
        title = course_row.title if course_row else None
        groups.append(
            {
                "group": group,
                "course_id": course_id,
                "title": title,
                # The leftmost column. Usage history outlives the courses it came
                # from (see models.LlmCall), so a deleted course keeps its spend and
                # loses its name, and falls back to the id the row still carries.
                "label": GROUP_LABELS.get(group) or title or f"Course #{course_id}",
                "note": GROUP_NOTES.get(group),
            }
            | bucket
        )
    return groups


@app.get("/usage")
def get_usage(limit: int = 50, session: Session = Depends(get_session)):
    limit = max(1, min(limit, 500))

    calls = session.query(func.count(models.LlmCall.id)).scalar() or 0
    input_tokens = session.query(func.sum(models.LlmCall.input_tokens)).scalar() or 0
    output_tokens = session.query(func.sum(models.LlmCall.output_tokens)).scalar() or 0
    estimated_cost_usd = session.query(func.sum(models.LlmCall.estimated_cost_usd)).scalar() or 0.0
    approximate_tokens, approximate_pricing = _approximation_causes(session)

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
            "approximate": approximate_tokens or approximate_pricing,
            "approximate_note": APPROXIMATE_NOTES.get((approximate_tokens, approximate_pricing)),
        },
        "per_course": _spend_groups(session),
        "recent_calls": recent_calls,
        "alert": alert_state(session),
        "limit": limit_info,
    }


@app.post("/usage/alert/ack")
def ack_usage_alert(session: Session = Depends(get_session)):
    return acknowledge_alert(session)
