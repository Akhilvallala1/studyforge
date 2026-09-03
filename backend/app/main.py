import logging
import os
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import (
    days,
    deletion,
    fsrs,
    generation,
    ics,
    ingest,
    models,
    planning,
    remediation,
    review,
    tutor,
)
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


# --------------------------------------------------------------------------
# Request validation
# --------------------------------------------------------------------------
#
# ONE ERROR SHAPE FOR THE WHOLE API, and this handler is what makes that true rather than
# aspirational. Every refusal anywhere in this file is
# {"detail": {"error": ..., "message": ...}}: a code the client switches on, and a sentence
# a person reads. FastAPI's own 422 is not that shape. It is a list of validation objects,
# so until this existed the honest answer to "how many error shapes does this API have"
# was TWO, and which one a client got depended on whether its bug was a wrong TYPE or a
# wrong VALUE. A wrong value reached a hand-rolled check and came back in the good shape; a
# wrong type was rejected by pydantic first and came back as the array.
#
# THAT SPLIT IS NOT A TYPING PROBLEM AND WIDENING ANNOTATIONS IS THE WRONG INSTRUMENT.
# tutor_messages.mode was fixed that way first, one field, and it worked; but a client has
# to write both parsing paths as long as EITHER shape is reachable anywhere, so fixing
# fields one at a time never retires the second path. It also costs something measurable
# every time: an annotation widened to Any loses its `type` in the generated OpenAPI, which
# has to be handed back by declaring json_schema_extra. Six fields would have paid that
# price six times and still left the array reachable through any field nobody thought of,
# and through a MISSING required field, which no annotation can widen at all.
#
# WHAT THIS DOES NOT TOUCH, which is the risk it carries. Every hand-rolled refusal already
# raises HTTPException, and HTTPException does not pass through here, so no existing
# refusal changes by a byte. test_error_shape.py asserts that directly rather than trusting
# the reasoning.
#
# THE MESSAGE IS BUILT FROM `loc` AND `msg` ONLY, never from `input`. Pydantic's error
# objects carry the offending value, and echoing a caller's own input back into a response
# body is how a reflection vector gets built by accident; it is also unbounded, since the
# rejected value can be a megabyte of JSON. `msg` is pydantic's own short sentence and
# names no value.
INVALID_REQUEST_ERROR = "invalid_request"
INVALID_REQUEST_MESSAGE = "The request is not valid."
# Enough to fix a broken client, few enough that the sentence stays a sentence.
MAX_REPORTED_PROBLEMS = 3


def _validation_message(errors: list) -> str:
    """A readable sentence naming what was wrong and where, and never what was sent."""
    problems = [
        "{}: {}".format(
            ".".join(str(piece) for piece in error.get("loc") or ()) or "body",
            error.get("msg") or "is not valid",
        )
        for error in errors[:MAX_REPORTED_PROBLEMS]
    ]
    if not problems:
        return INVALID_REQUEST_MESSAGE
    hidden = len(errors) - len(problems)
    listed = "; ".join(problems)
    if hidden > 0:
        listed = f"{listed}; and {hidden} more"
    return f"{INVALID_REQUEST_MESSAGE} {listed}"


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI's 422, in the shape every other refusal on this API already uses.

    Covers a wrong type, a missing required field, a malformed JSON body, and a path or
    query parameter that will not parse, on every route, because all of them arrive here
    as the same exception. That breadth is the point: the previous fix had to be repeated
    per field and could not reach the missing-field case at all.
    """
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "error": INVALID_REQUEST_ERROR,
                "message": _validation_message(exc.errors()),
            }
        },
    )


def _unprocessable(code: str, message: str) -> HTTPException:
    """422 in the shared refusal shape: the request parsed, and this API will not act on it.

    ONE definition, because there were three identical ones and a fourth was about to be
    written. _tutor_invalid and _planning_invalid now delegate here rather than each
    spelling the dict out; they keep their names because a refusal reads better at the call
    site when it says which feature is refusing.
    """
    return HTTPException(422, detail={"error": code, "message": message})


def _bad_request(code: str, message: str) -> HTTPException:
    """400 in the shared refusal shape: a code to branch on, a sentence to read.

    The same shape as _tutor_invalid and its siblings, and it exists for the reason the
    handler above exists. A refusal whose `detail` is a bare string gives a client nothing
    to switch on, so it has to match on prose, and prose is the part most likely to be
    edited. Every refusal that carries a code is one a client can handle without guessing.

    NOT a sweep of every bare string in this file. There are 41 of them and most are
    deliberate; see the audit in the commit message. This factory exists so that the two
    that were fixed, and any refusal added later, have somewhere obvious to go.
    """
    return HTTPException(400, detail={"error": code, "message": message})


# NULL IS NOT ABSENCE, and this is the rule for every optional field on every body in this
# file. It is written here because this is where request bodies are validated and where
# somebody adding an optional field will be looking.
#
# OMISSION IS THE ABSENCE OF AN OPINION, and a default exists precisely to serve a client
# that has none: one written before the field existed, or one that does not care. Serving
# it the default is right.
#
# NULL IS AN OPINION THAT FAILED TO BE FORMED. Almost nothing sends a literal null on
# purpose; it is an unset variable serialised straight through, which means the client has
# a bug it does not know about. Coercing it to the default makes that request SUCCEED, so
# the bug produces working requests with the wrong behaviour and stays invisible for
# exactly as long as it takes to ship. Refusing it costs a client that meant nothing by it
# one clear error, and saves a client that meant something a silent wrong answer.
#
# So an optional field takes its default from OMISSION only, and an explicit null is
# refused like any other value the field does not accept. TutorQuestion.mode is the worked
# example: omit it for "answer", send null and get invalid_mode.


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


class SourceInput(BaseModel):
    """One source in a generate request: what kind it is and where its content comes from.

    `value` is the text itself for a text source and the address for a URL. `ref` is the
    label a refusal names it by, and it defaults to the value for a URL, because a URL is
    already its own name, and to a positional label for text, because a wall of pasted
    prose is not.

    PDFs are not a kind here. They arrive as an upload on the other endpoint, and mixing a
    PDF alongside a URL in one request needs both endpoints collapsed into one multipart
    route, which is deliberately out of scope.

    `kind` IS A Literal AND NOT A PLAIN str, which is the opposite of what TutorQuestion.mode
    does and is right for the opposite reason. Widening `mode` to Any bought a specific
    message that names the legal values and says the field may be omitted, and that was
    worth a hand-rolled check because a learner's own button puts `mode` in flight. Nothing
    a learner does produces `kind`: it is set by client code once, so what that client needs
    is the legal values in the OpenAPI schema and a refusal it can already parse, both of
    which a Literal gives for free.

    IT WAS A str AND THAT WAS A 500. An unknown kind reached a bare ValueError inside
    ingestion, which load_sources does not catch, so it escaped as the one refusal on this
    API with no `detail` at all. "URL" and "Text" are the cases that mattered: a
    capitalisation slip by the first client integrating against this field, on the field
    every client is being told to migrate to. The Literal moves that to `invalid_request`
    from the shared handler, before any fetching, naming the field.
    """

    kind: Literal["text", "url"]
    value: str
    ref: str | None = None


class GenerateRequest(BaseModel):
    """Material for one course, as one or more sources.

    `sources` IS THE ONLY FIELD ANYTHING DOWNSTREAM SEES. `text` and `url` are the original
    single-source spellings, kept working and normalized into a one-element `sources` by
    the validator below, so no code past this class knows they exist.

    THAT IS WHY THEY ARE KEPT RATHER THAN REMOVED. The rot in a compatibility alias is two
    CODE PATHS, not two spellings: a second path is a second thing to change, and the one
    nobody uses is the one that quietly stops working. A spelling that collapses into the
    canonical shape at the edge costs one validator and leaves exactly one path forever.
    test_the_alias_and_the_canonical_form_produce_the_same_course is what proves it, and if
    that test ever fails there are two paths again whatever this docstring says.

    DEPRECATED, and with a date rather than an aspiration: `text` and `url` are removed in
    0.4.0. Until then they are supported, not merely tolerated.
    """

    sources: list[SourceInput] | None = None
    text: str | None = None
    url: str | None = None

    @model_validator(mode="after")
    def _normalize_aliases(self) -> "GenerateRequest":
        """Fold the deprecated single-source fields into `sources`.

        `sources` wins when both are sent. A request carrying both is confused, and the
        canonical field is the one to believe; refusing instead would be a new error shape
        for a case no client produces.

        `text` before `url`, which is the precedence the old endpoint had when both were
        set, kept so that a client relying on it is not quietly re-pointed at the other one.
        """
        if self.sources is not None:
            return self
        if self.text:
            self.sources = [SourceInput(kind="text", value=self.text)]
        elif self.url:
            self.sources = [SourceInput(kind="url", value=self.url)]
        return self

    def used_canonical_field(self) -> bool:
        """Whether the caller spelled it `sources` rather than using a deprecated alias.

        Read by the refusal translation, and by nothing else. See _generation_refusal for
        why the shape of a failure depends on this and the shape of a SUCCESS does not.
        """
        return self.text is None and self.url is None


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
TUTOR_FAILURE_MESSAGE = (
    "The tutor could not answer that just now. Nothing was saved, so try asking again."
)
# INVALID_RATING_MESSAGE is derived from fsrs.RATINGS rather than spelling the numbers out,
# for the reason the tutor's mode enum is derived from TUTOR_MODES: two spellings of one
# list is a divergence nothing would catch, and the message would go on naming a rating the
# scheduler had stopped accepting.
#
# NO_SOURCE_MESSAGE is the one refusal message this feature CHANGED rather than reshaped.
# Its code and status are untouched and its test passes verbatim, because that test compares
# against this constant. The wording moved because the old one named only the deprecated
# fields, and a refusal that tells you to use `text` or `url` while `sources` is the field
# to use is a message that will be wrong before it is old.
# Names `sources` first because that is the field to use, and still names the aliases
# because they work until 0.4.0 and a message that hid them would be telling half the
# truth to anyone reading it from an older client.
NO_SOURCE_MESSAGE = "Provide 'sources', or the deprecated 'text' or 'url'"
SOURCE_FAILED_MESSAGE = (
    "Some of your sources could not be read. Nothing was generated and nothing was "
    "charged, so fix the ones listed and send them again."
)
# The per-source copy, passed into app.ingest so that these sentences have one definition
# and that module holds none of them. Keyed by the failure codes ingest reports.
SOURCE_FAILURE_COPY = {
    ingest.FETCH_FAILED: URL_FETCH_MESSAGE,
    ingest.PDF_UNREADABLE: PDF_PARSE_MESSAGE,
    ingest.NO_USABLE_TEXT: "No usable text found in the source",
}


def too_many_sources_message(sent: int) -> str:
    """Names the cap AND the count sent, because a cap alone leaves the caller counting."""
    return (
        f"That request has {sent} sources and the limit is {ingest.MAX_SOURCES}. "
        f"Generation runs while you wait, so the limit is what keeps that wait finite."
    )


def source_too_large_message(total: int) -> str:
    return (
        f"Those sources come to {total:,} characters and the limit is "
        f"{ingest.MAX_TOTAL_CHARS:,}. Nothing was generated and nothing was charged. "
        f"Try fewer or shorter documents."
    )
INVALID_RATING_MESSAGE = f"rating must be one of {list(fsrs.RATINGS)}"

MESSAGE_EMPTY_MESSAGE = "Type a question before sending it."
CONCEPT_KEY_EMPTY_MESSAGE = (
    "Name the concept. An empty concept_key does not identify one, so there is nothing "
    "to answer about."
)
MESSAGE_TOO_LONG_MESSAGE = (
    f"That message is longer than {tutor.MAX_MESSAGE_CHARS} characters. The tutor answers "
    "questions about one concept; material that long belongs in a course of its own."
)
# Addressed to whoever wrote the client rather than to the learner, because no learner can
# produce this: the request body carries a mode the UI chose, and a wrong one is a bug in
# the sender. Naming the two accepted values is what makes the message actionable.
INVALID_MODE_MESSAGE = (
    "That is not a mode the tutor answers in. Send "
    f"{tutor.MODE_ANSWER!r} or {tutor.MODE_GUIDED!r}, or leave it out for "
    f"{tutor.MODE_ANSWER!r}."
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


def _cost_limit_exceeded(exc: CostLimitExceeded) -> HTTPException:
    """The 402 every metered surface answers a reached spend cap with.

    One function rather than the same dict written out at each call site. The client
    branches on `error` and reads `limit_usd` and `spent_usd`, and each extra copy of
    that shape is another chance for one surface to spell it differently from the rest.
    """
    return HTTPException(
        402,
        detail={
            "error": "cost_limit_exceeded",
            "message": "LLM spend limit reached",
            "limit_usd": exc.limit_usd,
            "spent_usd": exc.spent_usd,
        },
    )


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
        raise _cost_limit_exceeded(exc) from exc
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


def _source_failed(failures: list[ingest.SourceFailure]) -> HTTPException:
    """422 naming every source that failed, individually.

    INDIVIDUALLY IS THE WHOLE POINT. "One of your five URLs failed" is useless: the caller
    cannot tell which to fix, and the frontend cannot keep the good rows and mark the bad
    ones. The list carries the same {kind, ref, error, message} for each, so a client
    renders one row per source with the sentence that belongs to it.
    """
    return HTTPException(
        422,
        detail={
            "error": "source_failed",
            "message": SOURCE_FAILED_MESSAGE,
            "sources": [failure.payload() for failure in failures],
        },
    )


def _legacy_refusal(failure: ingest.SourceFailure, stage: str) -> HTTPException:
    """The refusal the single-source endpoints have always returned, unchanged.

    A COMPATIBILITY SEAM, and it has TWO HALVES WITH DIFFERENT LIFETIMES. Saying it is
    "keyed on the spelling, not the count" is true of the JSON body only, and the
    distinction matters enough to write down rather than leave implied.

    THE JSON HALF is keyed purely on spelling: a request using `text` or `url` keeps the
    bare-string body it always had, and anything using `sources` gets the one shape however
    many sources it carries. That half DIES WITH THE ALIASES IN 0.4.0, because removing the
    fields removes the only way to reach it.

    THE PDF HALF IS KEYED ON COUNT, `len(specs) <= 1`, and HAS NO END DATE. There is no
    spelling signal available: the upload field is deliberately still `file` so that every
    existing caller keeps working, so a one-file request is indistinguishable from a
    pre-feature one. That is the same count-keying rejected on the JSON side, accepted here
    only because the alternative is renaming the field and breaking every caller to buy a
    cleaner seam.

    SO DO NOT DELETE THIS FUNCTION WITH THE ALIASES. Removing `text` and `url` implies
    nothing about single-file uploads, and deleting this would silently change that
    contract too. Retiring the PDF half needs its own decision: either a second field name
    that means "I understand the new shape", or a major version that accepts the break.

    The mapping is exactly what the old code did. An unsafe URL keeps the guard's own
    message and its 400; a fetch failure keeps its 502; a bad PDF and an empty source keep
    their 400s. generation_failure is not reused here because it takes a live exception and
    wants a traceback, and by this point the failure is a value that was already logged.
    """
    if failure.error == ingest.UNSAFE_URL:
        return HTTPException(400, failure.message)
    if failure.error == ingest.FETCH_FAILED:
        return HTTPException(502, URL_FETCH_MESSAGE)
    if failure.error == ingest.PDF_UNREADABLE:
        return HTTPException(400, PDF_PARSE_MESSAGE)
    if stage == "pdf":
        return HTTPException(400, "No usable text found in the PDF")
    return HTTPException(400, "No usable text found in the source")


def _ingest_or_refuse(
    specs: list[ingest.SourceSpec], *, legacy: bool, stage: str
) -> list[str]:
    """Read every source, refuse the whole request if any failed, and return the chunks.

    FAIL CLOSED, AND IT COSTS NOTHING TO DO SO. Everything here happens before the first
    token is bought: the fetching and the parsing are done, the caps are applied, and only
    then does _run_generation call a provider. So refusing costs the caller a corrected
    resubmit, while best-effort would cost them a course built from three of five documents,
    paid for in full, and discovered afterwards when the missing material is not in it.

    The order is deliberate. Count first, because it is the only check that can be made
    before any fetching and an over-limit request should cost zero requests to other
    people's servers. Failures next, because a caller with a broken source has to fix it
    whatever the total size turns out to be. Size last, on what actually arrived.
    """
    if not specs:
        raise _bad_request("no_source", NO_SOURCE_MESSAGE)

    try:
        sources, failures = ingest.load_sources(specs, SOURCE_FAILURE_COPY)
    except ingest.TooManySources as exc:
        raise _unprocessable("too_many_sources", too_many_sources_message(len(specs))) from exc

    if failures:
        for failure in failures:
            logger.warning(
                "source refused (%s %s): %s", failure.kind, failure.ref, failure.error
            )
        raise _legacy_refusal(failures[0], stage) if legacy else _source_failed(failures)

    total = ingest.total_chars(sources)
    if total > ingest.MAX_TOTAL_CHARS:
        raise _unprocessable("source_too_large", source_too_large_message(total))
    return ingest.chunk_sources(sources)


@app.post("/courses/generate")
def generate_from_text(body: GenerateRequest, session: Session = Depends(get_session)):
    """Generate a course from one or more sources. Synchronous for the MVP -
    expect it to take a minute or more for large material.

    One outline call whatever the source count: the sources are chunked into one segment
    list and the pipeline below is the same one a single paste has always used.
    """
    specs = [
        ingest.SourceSpec(
            kind=source.kind,
            ref=source.ref or (source.value if source.kind == "url" else f"source {index + 1}"),
            value=source.value,
        )
        for index, source in enumerate(body.sources or [])
    ]
    chunks = _ingest_or_refuse(
        specs, legacy=not body.used_canonical_field(), stage="url"
    )
    return _run_generation(session, chunks)


@app.post("/courses/generate/pdf")
def generate_from_pdf(file: list[UploadFile], session: Session = Depends(get_session)):
    """One or more PDFs, uploaded under the field name `file`.

    STILL `file` AND NOT `files`, which is not a naming slip. FastAPI collects every part
    with that name into the list, so a client sending one part is unchanged and a client
    sending five needs no new field. Renaming it would have broken every existing caller to
    buy nothing.
    """
    specs = [
        ingest.SourceSpec(
            kind="pdf", ref=upload.filename or f"upload {index + 1}", value=upload.file.read()
        )
        for index, upload in enumerate(file)
    ]
    chunks = _ingest_or_refuse(specs, legacy=len(specs) <= 1, stage="pdf")
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


@app.get("/courses/{course_id}/deletion-preview")
def preview_course_deletion(course_id: int, session: Session = Depends(get_session)):
    """What deleting this course would destroy, so the learner can see it first.

    Writes nothing, and is safe to call repeatedly from a confirmation dialog the learner
    may well abandon. Same payload shape as the delete itself: they consent to this and are
    then told what happened, and two shapes would let those drift apart.

    There is no refusal here and no coded error. A course is always deletable, so a 409 or
    a 422 would be a code no client could ever branch on.
    """
    course = session.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    return deletion.deletion_preview(session, course)


@app.delete("/courses/{course_id}")
def delete_course(course_id: int, session: Session = Depends(get_session)):
    """Delete a course, everything under it, and the scheduling state it was the last to
    justify. Returns what was removed.

    200 WITH A BODY, not 204: api.ts's request() ends in `return res.json()`
    unconditionally, so a 204 throws in the client on the success path.

    NOT IDEMPOTENT. A second call is a 404, deliberately unlike DELETE
    /plan/days-off/{day}, which succeeds on an unmarked day. A day off is set membership
    and removing an absent one leaves the learner where they asked to be; a course is an
    entity, and answering 200 for one that does not exist would tell a client its delete
    worked when there was nothing to delete.
    """
    course = session.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    return deletion.delete_course(session, course)


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
    idempotent for the same reason the timestamp is: review.grade_lesson skips every
    attempt some rating already counted, so a repeat POST rates nothing.
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
        raise _bad_request("invalid_rating", INVALID_RATING_MESSAGE)

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
        raise _unprocessable("no_material", NO_MATERIAL_MESSAGE) from exc
    except CostLimitExceeded as exc:
        raise _cost_limit_exceeded(exc) from exc
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


# What each unavailable reason is told to the learner. Keyed by the reason itself, so
# a refusal quotes the state's own vocabulary instead of a parallel copy of it.
PRACTICE_UNAVAILABLE_MESSAGES = {
    remediation.NO_NOTE: "This concept has no explanation open to practice against.",
    remediation.NO_ITEMS: "This concept has no quiz questions to practice with.",
}


def _practice_conflict(code: str, message: str, state: dict) -> HTTPException:
    """409 that carries the practice session the answer could not join.

    Shaped like _remediation_conflict, with the session where that one carries the
    note, because the only sensible thing a UI can do about "not that answer" is
    redraw the session it should have been looking at. The next question to ask, when
    there is one, rides in detail.state.item rather than in a second copy of it that
    could disagree.

    INVARIANT. When `code` is drawn from the reason vocabulary, it MUST equal
    detail.state.reason. Both preconditions can fail on the same card, so a code
    decided independently of the state can name the second reason while the state
    names the first, and the response then gives two answers for one refusal.
    SESSION_COMPLETE and ITEM_ALREADY_ANSWERED are deliberately outside that
    vocabulary: they describe the request rather than the session, and there is no
    reason for them to collide with.
    """
    return HTTPException(409, detail={"error": code, "message": message, "state": state})


@app.get("/review/cards/{card_id}/remediation/practice")
def get_remedial_practice(card_id: int, session: Session = Depends(get_session)):
    """Today's remedial practice session for this card. It describes; it never refuses.

    Any real card gets a 200. "This concept has no explanation open" and "this concept
    has no quiz questions" are facts about the session, reported as status and reason,
    not errors: the Today screen fans this out per concept, and a 4xx per concept would
    make a page full of ordinary answers look broken.

    Unlike the note endpoints this deliberately does not call remediation.clear_resolved.
    Retiring a note is a write, and this is the read the practice panel polls; a GET
    that can end the session it is describing would let one tab close another tab's
    session between the question and the answer.
    """
    card = session.get(models.ReviewCard, card_id)
    if not card:
        raise HTTPException(404, "Review card not found")
    return remediation.practice_state(session, card, review.now_utc())


@app.post("/review/cards/{card_id}/remediation/practice")
def answer_remedial_practice(
    card_id: int, body: ReviewAnswer, session: Session = Depends(get_session)
):
    """Record one remedial practice answer and hand back the session that follows it.

    The top-level fields are answer_review's, so the feedback UI binds to the same
    names. `state` is the GET's payload recomputed after the insert, never a mutated
    copy of what was read, so the two endpoints cannot drift into two answers about
    the same session. Its `item` is the NEXT question, or null when this answer ended
    the session.

    Nothing here is an assessment. No model is called, no review log is written, no
    column of the card is touched, and the note keeps its status and its cooldown. The
    only row this produces is one attempt, under its own source, which is what makes
    the session reconstructible after a restart.

    "No quiz questions for this concept" is decided before the item is looked at, and
    the missing-note case after it. That is not an accident: with no items there is no
    item that could pass the concept check, so 404 or 400 would answer a question about
    the request instead of about the session, while a note that has gone still has to
    let through an answer the learner was already holding. A card can be missing both at
    once, so that first refusal still reports the reason the state reports, and does not
    decide a second one of its own.

    The session is derived from attempts alone, so a card deleted and recreated for the
    same concept picks that day's practice back up. That is deliberate: the memory being
    practiced belongs to the concept, not to the row that schedules it.

    Every refusal is a 409 carrying an `error` code and the same `state` the GET would
    return, except the two that describe a malformed request: an unknown item is a 404
    and an item from another concept or an empty answer is a 400, matching the review
    endpoint the client already talks to.
    """
    card = session.get(models.ReviewCard, card_id)
    if not card:
        raise HTTPException(404, "Review card not found")

    now = review.now_utc()
    facts = remediation.practice_facts(session, card, now)
    state = remediation.practice_state(session, card, now, facts=facts)
    if not facts.items:
        # The code is read off the state rather than decided again here, which is what
        # makes them agree by construction. Both preconditions can fail at once, and a
        # refusal that says no_items beside a state that says no_note is one response
        # giving two reasons for the same refusal. state["reason"] is never null on this
        # path: with no items the status is always unavailable.
        raise _practice_conflict(
            state["reason"], PRACTICE_UNAVAILABLE_MESSAGES[state["reason"]], state
        )

    item = session.get(models.QuizItem, body.item_id)
    if not item:
        raise HTTPException(404, "Quiz item not found")
    if normalize_concept(item.concept) != card.concept_key:
        raise HTTPException(400, "That quiz item does not test this concept")
    if not body.answer.strip():
        raise HTTPException(400, "Answer cannot be empty")

    # Read before anything is written, because the duplicate guard cannot stand in for
    # it: that guard matches on the answer text, so a DIFFERENT answer to an item this
    # session already used would sail past it and write a second row for the same
    # question, which is exactly the repetition this rule exists to prevent.
    servable = facts.stop_reason is None and item.id not in facts.used_item_ids
    if facts.note is None:
        # The note can be retired underneath a session: the Today screen fans out per
        # concept, so another tab can clear it between this question and this answer.
        # Terminating means no NEW question is served. It does not mean an answer
        # already in the learner's hands is thrown away, so this one is still graded
        # and kept, and the terminal state arrives on the response that carries it.
        #
        # A retired note and no note at all are different situations, and only the
        # first one can have handed the learner a question. latest_note sees cleared
        # rows, which is what tells them apart: a card that has never been re-taught
        # refuses every answer, here and in the state the GET reports.
        #
        # Be clear about what this does NOT establish. Nothing records that an item was
        # served, so "already in the learner's hands" is not a fact this endpoint can
        # check, and what is actually allowed is wider: any answer to a servable item on
        # a card whose note was cleared at any point, weeks ago included, with no GET in
        # between. Narrowing it would mean recording each item as it is served, which is
        # the durable state this feature is built to do without. The cost is bounded and
        # known: at most the day's answers, on concepts that were genuinely remediated,
        # and it cannot reach scheduling, because grade_lesson rates from
        # _lesson_quiz_attempts. What moves is display state. See the test named for it.
        if not servable or remediation.latest_note(session, card.id) is None:
            raise _practice_conflict(
                remediation.NO_NOTE,
                PRACTICE_UNAVAILABLE_MESSAGES[remediation.NO_NOTE],
                state,
            )
    elif facts.stop_reason is not None:
        raise _practice_conflict(
            remediation.SESSION_COMPLETE,
            "You have finished practicing this concept for today.",
            state,
        )
    elif item.id in facts.used_item_ids:
        # state.item is the next question, and it is never null here: a session with
        # nothing left to serve is a finished session, which the branch above answered.
        raise _practice_conflict(
            remediation.ITEM_ALREADY_ANSWERED,
            "You have already answered that question in today's practice.",
            state,
        )

    attempt = _record_attempt(
        session,
        item,
        body.answer,
        _grade(body.answer, item.answer),
        _sanitize_elapsed_ms(body.elapsed_ms),
        source=remediation.REMEDIAL_PRACTICE_SOURCE,
    )
    return {
        "correct": attempt.correct,
        "expected": item.answer,
        "submitted": attempt.submitted_answer,
        "attempt_id": attempt.id,
        "state": remediation.practice_state(session, card, now),
    }


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
# The tutor
# --------------------------------------------------------------------------

# What each refusal says. The two cap messages differ in one load-bearing way: the day
# message names the whole day so the learner does not go looking for another concept to
# ask on, and the concept message says the opposite, because there really are others.
DAILY_TURN_LIMIT_MESSAGE = (
    f"You have asked the tutor {tutor.DAY_TURNS} questions today, which is the limit "
    "across every concept. They come back at the start of your next study day."
)
CONCEPT_TURN_LIMIT_MESSAGE = (
    f"You have asked the tutor {tutor.CONCEPT_TURNS_PER_DAY} questions about this "
    "concept today. Other concepts still have questions left, and this one opens again "
    "at the start of your next study day."
)


# THIS DOCSTRING IS PUBLISHED. FastAPI renders it as the request schema's `description`
# at /docs, so it is read by people writing clients rather than by people reading this
# file. Everything below the class line has to earn its place on that page: what the
# fields accept, what a default does, what gets refused. The reasoning about how we got
# here is up HERE instead, where it is just as findable to anyone in this file and
# invisible to anyone in the docs.
#
# WHY `mode` IS TYPED Any AND VALIDATED BY HAND, which looks like giving up on the schema
# and is the opposite. A Literal would reject an unknown value with pydantic's own 422,
# whose detail is a list of validation objects, and every other tutor refusal is
# {"error": ..., "message": ...}; a client parsing this route's errors would meet two
# unrelated shapes from one route. So the check was hand rolled from the start.
#
# A plain `str` only got that half right, and QA found the other half. Pydantic rejects a
# mode of the wrong TYPE before this endpoint's code runs at all, so {"mode": 7} and
# {"mode": null} escaped the hand-rolled check and came back as exactly the raw array it
# exists to avoid, with "Input should be a valid string" as the sentence a learner would
# have been shown. A wrong type and a wrong value are THE SAME MISTAKE from the caller's
# side, and they now produce the same refusal, because widening the annotation is what
# lets both reach one code path and one message.
#
# json_schema_extra IS WHAT KEEPS THE DOCS HONEST, and it leaves them better than the
# `str` annotation did rather than merely as good. Measured on the generated OpenAPI:
#   str          {"title": "Mode", "default": "answer", "type": "string"}
#   Any alone    {"title": "Mode", "default": "answer"}
#   Any + this   {"title": "Mode", "default": "answer", "type": "string",
#                 "enum": ["answer", "guided"]}
# So widening the annotation had quietly dropped `type` from the published schema, and
# declaring it back also publishes the legal VALUES, which no version of this field ever
# advertised. It documents; it does not validate. Pydantic still hands `mode` through
# untouched, which is the whole point, and the hand-rolled check below is still the only
# thing that refuses anything.
#
# THE ENUM IS DERIVED FROM TUTOR_MODES, never written out. Two spellings of the same list
# is a divergence nothing would catch: the docs would advertise a value the server refuses,
# or omit one it accepts, and both read as correct until a client trusts them.
#
# WHY `mode` KEEPS ITS OWN CHECK NOW THAT THE HANDLER EXISTS. The RequestValidationError
# handler above would already put a wrong-type mode in the right SHAPE, so this could have
# been reverted to a plain `str` when that landed. It was not, and the reason is the
# MESSAGE rather than the shape. invalid_mode says which values are legal and that omitting
# the field is allowed; the generic handler can only say that a string was expected. This
# is the one field on this body a learner's own action puts in flight, through a button in
# the tutor panel, so it is the one worth a sentence written for it. Every other field here
# is set by the client once and never varies, and the generic message is the right size for
# those.
class TutorQuestion(BaseModel):
    """One question about one concept.

    concept_key travels in the BODY rather than in the path, and that is not a taste.
    normalize_concept preserves slashes, spaces and parentheses, so "o(n log n)" and
    "big-o / complexity" are ordinary keys, and Starlette will not match a path segment
    containing "/": the concept most in need of explaining would be the one URL the
    learner could not reach.

    `mode` chooses the form of the reply and accepts "answer" or "guided". OMIT IT for
    "answer": that is the compatibility promise, so a client written before guided mode
    existed sends no mode at all and gets exactly the behaviour it already had. Sending
    null is NOT the same as omitting it. Null, any other string, and any non-string are
    all refused with 422 invalid_mode, in the same {"error", "message"} shape as every
    other refusal on this route.

    Guided mode is opt in per request. It is never inferred from the learner's message,
    their mastery bucket, or how many times they have missed the concept.
    """

    concept_key: str
    message: str
    mode: Any = Field(
        tutor.MODE_ANSWER,
        json_schema_extra={"type": "string", "enum": list(tutor.TUTOR_MODES)},
    )


def _require_concept_key(raw: str) -> str:
    """The normalized concept key, or a refusal. Used by BOTH tutor endpoints.

    AN EMPTY KEY IS NOT AN UNKNOWN CONCEPT, and that is the whole of the argument.
    normalize_concept can never return "" from a real label, so "" is unreachable as a
    legitimate key and can only mean the caller failed to send one. That is the
    null-versus-omitted rule stated at the top of this file, applied to a second field:
    omitting the parameter is already a 422 from the validation handler, and sending it
    empty is the same mistake spelled differently. Whitespace normalises to nothing real
    either, so it takes the same path.

    THE EVIDENCE THIS WAS WRONG was that the two endpoints disagreed. The POST refused an
    empty key as `no_material`, which is a true sentence about the wrong thing, while the
    GET answered 200 with an empty transcript and a blank concept_label. One request, two
    answers, and a client would have had to learn both. They now give the same code.

    Not a hazard for any caller that exists: ConceptTutor is passed entry.concept_key from
    a server-provided needs_attention row, which is never empty. This refuses a shape only
    a buggy client can produce, which is exactly when refusing is cheap and silence is not.
    """
    key = normalize_concept(raw)
    if not key:
        raise _tutor_invalid("concept_key_empty", CONCEPT_KEY_EMPTY_MESSAGE)
    return key


def _tutor_invalid(code: str, message: str) -> HTTPException:
    """422 for a request the tutor cannot act on, whatever the conversation looks like."""
    return _unprocessable(code, message)


def _tutor_conflict(code: str, message: str, counts: tutor.TurnCounts) -> HTTPException:
    """409 that carries the daily limits, and nothing else.

    Deliberately unlike _remediation_conflict, which carries the note, and
    _practice_conflict, which carries the session. Those refusals hand back what the UI
    has to redraw. Here the conversation is already on screen and this refusal did not
    change it, so sending it back would be a second copy of something the client already
    holds, and two copies can disagree. What the refusal is actually about is the limits.
    """
    return HTTPException(
        409,
        detail={"error": code, "message": message, "limits": tutor.limits_payload(counts)},
    )


def _conversation_label(
    session: Session, concept_key: str, rows: list[models.TutorMessage]
) -> str:
    """The name to show above a conversation, taken from what is already stored.

    The conversation's own rows first. TutorMessage.concept_label exists precisely so a
    transcript can still name its concept after the card, the lesson, and the course that
    named it are gone, and reading it here is what makes that promise true.

    Then the review card, which is the name the Today screen prints, then the key itself.
    Deliberately NOT tutor.context(), which would name the concept from the courseware:
    that reads every lesson in the database, and this is the request a panel makes on
    open. The read would buy a better name in exactly one case, a concept with no
    messages and no card, and the POST stamps the courseware name onto the first row it
    writes, so that case ends as soon as anyone asks anything.
    """
    for row in reversed(rows):
        if row.concept_label:
            return row.concept_label
    card = review.get_card(session, concept_key)
    if card is not None and card.concept_label:
        return card.concept_label
    return concept_key


@app.post("/tutor/messages")
def post_tutor_message(body: TutorQuestion, session: Session = Depends(get_session)):
    """Ask the tutor one question about one concept: one metered call, two rows, one commit.

    Hands back the learner's message and the reply, not the whole conversation. The
    client already drew what it had and appends these two. `limits` AND `guided` are both
    recomputed AFTER the insert, the way answer_remedial_practice recomputes its state, so
    what the learner is shown is what the next request will be measured against.

    PRECEDENCE IS FIXED HERE AND NOWHERE ELSE, in this order:
      1. an empty message                  422 message_empty
      2. a message over the character cap   422 message_too_long, decided before any
         material is read and before any model call, because past that length it is a
         document, and a document belongs in course generation where it is chunked and
         paid for deliberately
      3. a mode nobody answers in          422 invalid_mode, checked here with the other
         things that are wrong with the REQUEST itself, and before any read, because a
         request naming a mode this server does not have is malformed whatever the
         concept turns out to hold
      4. no material for the concept        422 no_material
      5. the day's turns are gone           409 daily_turn_limit
      6. this concept's turns are gone      409 concept_turn_limit
      7. the spend cap is reached           402 cost_limit_exceeded
    The day cap is checked BEFORE the concept cap because it is the wider fact. Telling
    someone they are out of turns on this concept while they are out for the whole day
    sends them to another concept to be refused there as well.

    A GUIDED REQUEST AT THE END OF ITS RUN IS NOT IN THAT LIST, and that is the design
    rather than an omission. It is served, with a complete answer, as a 200 reporting mode
    "answer". The learner asked for help; handing them the help is not a refusal, and the
    `mode` in the response is how the client knows what it got. tutor.effective_mode is the
    only place that decision is taken, and the single value it returns is threaded into
    every consumer below: the system prompt, the parser, the row, and the response.

    THERE IS NO 404. This looks up no ReviewCard and needs none: mastery_bucket(None)
    answers not_started, and the material comes from the lessons rather than from a card.
    A concept with no card is one the learner met on the concept map and was never
    quizzed on, and refusing to explain it would be a 404 for something that exists.

    THERE IS NO GENERATION SLOT, unlike create_remediation. That lock is there because a
    double-clicked button bought two model calls against a WEEKLY budget, where the
    second one costs a week of re-teaching. Here a lost race costs one turn out of twelve
    that come back tomorrow, and the send button is disabled while a question is in
    flight, so the guard would buy an ordering nobody can observe.

    A REPLY THAT WILL NOT PARSE WRITES NOTHING, the learner's own message included. Both
    rows are built after the reply parses, added together, and committed once, so there
    is no window in which the transcript holds a question with nothing under it. The
    llm_calls row is still written by the meter WHEN THE PROVIDER ANSWERED, because those
    tokens were spent, exactly as in remediation.generate_note. A provider that raised
    before answering records nothing at all, since metering only writes a row on a clean
    return or on LLMCallError, so "the tokens were spent" is a claim about the reply that
    would not parse, not about every failure below.

    Nothing here rates, schedules, or grades. The only rows this can produce are two
    tutor_messages: a conversation is not a retrieval test, and folding one into the
    schedule would let a learner talk their way to a longer interval.
    """
    concept_key = _require_concept_key(body.concept_key)
    message = body.message.strip()
    if not message:
        raise _tutor_invalid("message_empty", MESSAGE_EMPTY_MESSAGE)
    # Measured on the stripped message, which is what gets stored and what gets sent. A
    # question at the cap followed by trailing newlines is not a longer question.
    if len(message) > tutor.MAX_MESSAGE_CHARS:
        raise _tutor_invalid("message_too_long", MESSAGE_TOO_LONG_MESSAGE)
    if body.mode not in tutor.TUTOR_MODES:
        raise _tutor_invalid("invalid_mode", INVALID_MODE_MESSAGE)

    now = review.now_utc()
    context = tutor.context(session, concept_key, now=now)
    if not context.lessons and not context.items:
        raise _tutor_invalid("no_material", NO_MATERIAL_MESSAGE)

    counts = tutor.turn_counts(session, concept_key, now)
    if counts.day_used >= tutor.DAY_TURNS:
        raise _tutor_conflict("daily_turn_limit", DAILY_TURN_LIMIT_MESSAGE, counts)
    if counts.concept_used >= tutor.CONCEPT_TURNS_PER_DAY:
        raise _tutor_conflict("concept_turn_limit", CONCEPT_TURN_LIMIT_MESSAGE, counts)

    provider = get_provider()
    run_id = uuid.uuid4().hex
    # Which course this call is charged to, decided here at call time and from the
    # UNTRIMMED matches: sole_course_id is answering which courses teach the concept, and
    # an answer that changed with how many lessons happened to fit in a prompt would not
    # be an answer about courses at all. Read after the caps, so a turn refused by either
    # cap pays for one read of the courseware rather than two; a turn refused by the SPEND
    # cap still pays for both, because that cap fires inside meter.generate, below. That
    # is the rarest refusal and the read is one the request was about to make anyway, so
    # it is left alone rather than reaching inside the meter to check the cap early.
    # Never backfilled afterwards either, because unlike a generation run there is no
    # course saved later to backfill from.
    matches = remediation.teaching_lessons(session, concept_key)
    meter = MeteredLLM(provider, run_id, course_id=remediation.sole_course_id(session, matches))
    prompt = tutor.build_prompt(context, tutor.history(session, concept_key), message)

    # THE MODE, DECIDED ONCE, and every use below reads this name rather than asking
    # again. The three consumers are the system prompt, the parser, and the response, and
    # a second computation in any of them is the bug this shape removes: the model
    # prompted to withhold while the parser is told to expect a complete answer drops
    # `ask` from a reply that was written around it, silently, with a well formed row to
    # show for it.
    mode = tutor.effective_mode(session, concept_key, body.mode, now)
    system = tutor.system_prompt(session, concept_key, mode, now)

    # Nothing has been added to the session at this point, and nothing is until the reply
    # has parsed, which is what makes every failure below leave zero rows behind.
    try:
        reply = tutor.parse_reply(
            meter.generate(tutor.TUTOR_STAGE, system, prompt, tutor.MAX_TOKENS), mode
        )
    except CostLimitExceeded as exc:
        raise _cost_limit_exceeded(exc) from exc
    except ValueError as exc:
        # The provider answered and the answer did not match the schema. Logged apart
        # from a transport failure for the reason create_remediation gives: the two need
        # opposite fixes, and reporting a schema mismatch as "the model could not be
        # reached" is what hid the fake provider having no remediation branch at all.
        logger.error(
            "Tutor reply for concept %r: the model replied but the reply did not match "
            "the schema (%s)",
            concept_key,
            exc,
        )
        raise HTTPException(502, TUTOR_FAILURE_MESSAGE) from exc
    except (TypeError, AttributeError, NameError):
        # A BUG IN THIS FILE, re-raised rather than reported as a network failure.
        #
        # The handler below is broad on purpose, because a provider adapter can fail in
        # ways no import here can enumerate. The cost of that breadth is that it also
        # catches the exceptions that mean the CODE is wrong, and answers them 502 with
        # "the provider call failed" in the log, which sends whoever reads it to the
        # network for a problem three lines above.
        #
        # This is not hypothetical and it is why these three are named. parse_reply takes
        # `mode` with no default precisely so that a call site forgetting it fails loudly;
        # the TypeError that produces is raised INSIDE this try, so before this clause
        # existed the whole mechanism degraded to a 502 blaming the provider. The tests of
        # any caller still went red, which is what kept the design working, but a
        # production install would have shown a network error for a programming one.
        #
        # Re-raised bare, so it reaches the framework as an unhandled error with its
        # traceback intact, exactly as the same bug anywhere outside a try block would.
        # No rows have been added yet, so the "a failed turn writes nothing" promise is
        # unaffected by which of these two paths a failure takes.
        raise
    except Exception as exc:
        logger.exception("Tutor call failed for concept %r: the provider call failed", concept_key)
        raise HTTPException(502, TUTOR_FAILURE_MESSAGE) from exc

    # Both rows carry the moment the turn was ACCEPTED rather than the moment the reply
    # came back, so a turn is counted in the same study day whose cap let it through: a
    # question asked at 03:59 and answered at 04:00 spent yesterday's turn, which is the
    # day it was checked against.
    learner_row = models.TutorMessage(
        concept_key=concept_key,
        concept_label=context.concept_label,
        role=tutor.LEARNER_ROLE,
        content=message,
        beyond="",
        check_question="",
        ask="",
        run_id="",
        model="",
        created_at=now,
    )
    reply_row = models.TutorMessage(
        concept_key=concept_key,
        concept_label=context.concept_label,
        role=tutor.TUTOR_ROLE,
        content=reply.answer,
        beyond=reply.beyond,
        check_question=reply.check,
        # Whichever of the two the mode allowed; parse_reply has already blanked the
        # other, so this row can never carry two questions.
        ask=reply.ask,
        run_id=run_id,
        model=getattr(provider, "model", ""),
        created_at=now,
    )
    # One commit for the pair. Saving the question first and the reply after the call is
    # the natural implementation and it is precisely the one this must not be: a reply
    # that will not parse would leave the learner's message standing in the transcript
    # with nothing under it. The two share created_at, and conversation() breaks that tie
    # on id, which add_all assigns in the order given.
    session.add_all([learner_row, reply_row])
    session.commit()
    logger.info(
        "tutor turn %s answered for concept=%r run=%s mode=%s",
        reply_row.id,
        concept_key,
        run_id,
        mode,
    )

    return {
        "concept_key": concept_key,
        "concept_label": context.concept_label,
        # What was SERVED, not what was asked for. The two come apart at the end of a run,
        # and this is the only thing that tells the client which of the two it got.
        "mode": mode,
        "learner": tutor.message_payload(learner_row),
        "reply": tutor.message_payload(reply_row),
        "limits": tutor.limits_payload(tutor.turn_counts(session, concept_key, now)),
        # Recomputed after the commit for the same reason `limits` is: the turn that was
        # just written is part of the run now, so what the client is shown is what its
        # next request will actually be measured against. Reading it before the insert
        # would be off by one for exactly the request the learner is about to make.
        "guided": tutor.guided_payload(tutor.guided_run(session, concept_key, now)),
    }


@app.get("/tutor/conversation")
def get_tutor_conversation(concept_key: str, session: Session = Depends(get_session)):
    """One concept's whole conversation, oldest first. It describes; it barely refuses.

    Any concept_key THAT NAMES SOMETHING gets a 200, like get_remedial_practice. A concept
    nobody has asked about is an empty conversation, which is a fact about it rather than
    an error, and there is no card lookup here for the same reason the POST has none. That
    is worth defending: the Today screen fans this out per concept, and a 4xx per concept
    would make a page of ordinary answers look broken.

    The one refusal is an EMPTY key, which is not an unknown concept but an absent one.
    See _require_concept_key; the short version is that "" cannot be a real key, so it can
    only mean the caller sent nothing, and answering it with a blank-titled empty panel
    described a concept that does not exist.

    Every message goes through tutor.message_payload, the same function the POST hands
    its two rows back through, so the rows a client appends and the rows it reloads are
    the same shape. Both roles use that one shape, discriminated on `role`, with `beyond`
    and `check` always null on a learner row: a reader that only ever met one shape could
    render a tutor message without its register split, which is the one mistake in this
    feature that nothing downstream can detect.

    `last_message_at` is the newest row's timestamp, null on an empty conversation, so a
    panel can tell "we have never spoken about this" from "we spoke last week" without
    reading the array.

    `guided` is here for the reason `limits` is. A panel opening on an existing
    conversation has to know whether the work-it-out button will actually work before the
    learner presses it, and the alternative is the client counting `ask` fields in the
    array it happens to hold, which is a second definition of the run living somewhere it
    cannot be kept correct. Same function as the POST's, off the same rows.

    Writes nothing, deliberately, like get_remedial_practice: this is the read the panel
    makes on open, and a GET that could change what it describes would let one tab move
    another tab's conversation between drawing it and answering in it.
    """
    key = _require_concept_key(concept_key)
    rows = tutor.conversation(session, key)
    now = review.now_utc()
    return {
        "concept_key": key,
        "concept_label": _conversation_label(session, key, rows),
        "messages": [tutor.message_payload(row) for row in rows],
        "last_message_at": iso_utc(rows[-1].created_at) if rows else None,
        "limits": tutor.limits_payload(tutor.turn_counts(session, key, now)),
        "guided": tutor.guided_payload(tutor.guided_run(session, key, now)),
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
GROUP_TUTOR = "tutor"
GROUP_FAILED_RUN = "failed_run"

GROUP_LABELS = {
    GROUP_REMEDIATION: "Re-teaching (no single course)",
    GROUP_TUTOR: "Tutor chat (no single course)",
    GROUP_FAILED_RUN: "Unattributed",
}

GROUP_NOTES = {
    # Examples, not a closed list, and the two words carrying that are "at the time they
    # were charged" and "commonly". No list can close, because the course id is decided
    # once and never revisited while a sentence in the present tense is a claim about
    # today's courseware: whatever the row was charged under, editing the courses
    # afterwards can falsify it. A re-teach charged while two courses taught the concept
    # reads as none of "several", "gone", or "failed" once one of those courses is
    # deleted. Scoping the claim to when the charge happened is what the row actually
    # records, and it survives every later edit. Says nothing about whether these calls
    # succeeded, either: a re-teaching call that failed still records the tokens it
    # spent, and lands in this group like any other.
    GROUP_REMEDIATION: (
        "Re-teaching a concept is charged to the course that teaches it, when exactly one "
        "does. These calls could not be tied to a single course at the time they were "
        "charged, commonly because several courses teach the concept, because the lessons "
        "that taught it are gone, or because the call failed before anything recorded which "
        "concept it was for."
    ),
    # Written on the same principle as the re-teaching sentence above, and NOT by copying
    # it: three of its clauses are false here. A tutor call knows its course before it is
    # made, so a call that failed is still attributed, which rules out "the call failed
    # before anything recorded which concept it was for". And the tutor refuses outright
    # when a concept has no material, so "the lessons that taught it are gone" cannot
    # describe a tutor row either; what is left is lessons that exist and belong to no
    # course. The two properties that DO carry over are the ones that took four review
    # rounds to arrive at: the claim is scoped to when the row was charged, because the
    # course id is decided once and later edits to the courseware would falsify any
    # present-tense version of it, and the reasons are offered as examples rather than as
    # a closed set. The last sentence exists so the group is never read as a list of
    # failures, which is the mistake the whole /usage grouping was rebuilt to stop.
    GROUP_TUTOR: (
        "A tutor question is charged to the course that teaches the concept it was asked "
        "about, when exactly one does. These calls could not be tied to a single course "
        "at the time they were charged, commonly because several courses teach that "
        "concept, or because the lessons teaching it belong to no course. Whether the "
        "call succeeded is a separate question this group does not answer: a tutor call "
        "that failed still records the tokens it spent, when the provider reported them, "
        "and is grouped by the same rule as one that worked."
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

    One gap, left open knowingly. The proof rests on cost, so it fails wherever the
    surviving count prices to nothing (costs.estimate_cost reads a missing count as
    zero). A zero INPUT count essentially never happens, but a missing input count
    beside zero OUTPUT tokens is the ordinary shape of a call that failed before it
    produced anything, and estimate_cost on an unpriced model answers (0.0, True) for
    it. Such a row reports the token cause alone: still true, merely less complete.
    Closing it properly would mean recording whether the provider was paid, which is a
    column this change is not entitled to add.
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

    Every stage that is neither re-teaching nor the tutor belongs to the generation
    pipeline (generation.STAGES), and those rows have their course id backfilled the
    moment the course is saved, so one still missing means the run never got that far.

    A NEW STAGE MUST BE ADDED HERE, and the cost of forgetting is not a missing row: it
    is the row landing in the failed-run group wearing a sentence about a generation run
    that failed before its course could be saved. That is exactly the defect this
    grouping was rebuilt to remove, and the tutor would have shipped with it on day one.
    test_every_stage_actually_recorded_is_one_the_page_can_explain is what catches the
    next one.
    """
    if stage == remediation.REMEDIATION_STAGE:
        return GROUP_REMEDIATION
    if stage == tutor.TUTOR_STAGE:
        return GROUP_TUTOR
    return GROUP_FAILED_RUN


def _spend_groups(session: Session) -> list[dict]:
    """Spend for the /usage table: one row per course, then one row per reason a call
    has no course. Courses first in id order, then re-teaching, then the tutor, then
    the failed runs."""
    rows = (
        session.query(
            models.LlmCall.course_id,
            models.LlmCall.course_title_at_deletion,
            models.LlmCall.stage,
            func.count(models.LlmCall.id),
            func.sum(models.LlmCall.input_tokens),
            func.sum(models.LlmCall.output_tokens),
            func.sum(models.LlmCall.estimated_cost_usd),
        )
        .group_by(
            models.LlmCall.course_id,
            models.LlmCall.course_title_at_deletion,
            models.LlmCall.stage,
        )
        .all()
    )
    # THE STAMP IS PART OF THE KEY, not just of the label. A deleted course's id can be
    # reissued to a new course, and without this the old rows and the new ones would share
    # a bucket and be reported as one course's spend. Grouping on the stamp keeps them
    # apart even when the id is identical.
    buckets: dict[tuple[str, int | None, str | None], dict] = {}
    for course_id, stamped, stage, stage_calls, stage_in, stage_out, stage_cost in rows:
        group = GROUP_COURSE if course_id is not None else _unattributed_group(stage)
        bucket = buckets.setdefault(
            (group, course_id, stamped),
            {"calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0},
        )
        bucket["calls"] += stage_calls
        bucket["input_tokens"] += stage_in or 0
        bucket["output_tokens"] += stage_out or 0
        bucket["estimated_cost_usd"] += stage_cost or 0.0

    rank = {GROUP_COURSE: 0, GROUP_REMEDIATION: 1, GROUP_TUTOR: 2, GROUP_FAILED_RUN: 3}
    groups = []
    for (group, course_id, stamped), bucket in sorted(
        buckets.items(),
        key=lambda item: (rank[item[0][0]], item[0][1] or 0, item[0][2] or ""),
    ):
        # A STAMPED ROW IS NEVER LOOKED UP. The stamp means the course was deleted and its
        # title recorded, so the id is free to have been reissued to somebody else, and
        # resolving it is exactly how this row's money would be handed to the wrong course.
        # Not looked up and then ignored: not looked up at all, so there is no live title
        # here for a later edit to accidentally start preferring.
        #
        # A CONSEQUENCE THAT LOOKS LIKE A HOLE AND IS NOT: reordering the label below to
        # `title or stamped` survives the whole suite. That is because this guard makes
        # `title` provably None whenever `stamped` is set, so the ordering is unreachable
        # belt-and-braces rather than the thing doing the work. Its inertness is evidence
        # the guard holds; if the lookup ran and were merely ignored, that same mutation
        # would be both catchable and dangerous.
        course_row = (
            session.get(models.Course, course_id)
            if group == GROUP_COURSE and stamped is None
            else None
        )
        title = course_row.title if course_row else None
        groups.append(
            {
                "group": group,
                "course_id": course_id,
                # The LIVE course's title, and None once it is deleted. A client can still
                # read this as "does this course still exist"; the stamp is not put here,
                # because a title that survives deletion would make that question
                # unanswerable.
                "title": title,
                # The leftmost column, in precedence order. The stamp comes before the
                # resolved title and cannot be overtaken by it: a deleted course shows the
                # name it actually had, and only a row with no stamp falls back to the id.
                "label": GROUP_LABELS.get(group) or stamped or title or f"Course #{course_id}",
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


# --------------------------------------------------------------------------
# Study planning: deadlines, pace, and days off
# --------------------------------------------------------------------------

DEADLINE_MALFORMED_MESSAGE = "A deadline must be a calendar date written as YYYY-MM-DD."
DEADLINE_IN_PAST_MESSAGE = (
    "That date has already passed. Pick today or a day in the future."
)
DEADLINE_LABEL_TOO_LONG_MESSAGE = (
    f"That name is longer than {models.Course.deadline_label.type.length} characters. "
    "A short one like 'Midterm' is what shows up in your calendar."
)
DAY_MALFORMED_MESSAGE = "A day off must be a calendar date written as YYYY-MM-DD."
NO_DEADLINE_MESSAGE = (
    "This course has no deadline, so there is nothing to put in a calendar. Set one first."
)


class DeadlineRequest(BaseModel):
    """The date the material has to be known by, and what the learner calls it.

    `deadline` is a plain YYYY-MM-DD string rather than a date, so that a malformed
    value produces this feature's own 422 with a sentence the learner can act on,
    instead of pydantic's generic date-parsing error.
    """

    deadline: str
    label: str | None = None


class DayOffRequest(BaseModel):
    day: str
    note: str | None = None


def _planning_invalid(code: str, message: str) -> HTTPException:
    """422 for a date this feature cannot use, in the shape the other 422s here take."""
    return _unprocessable(code, message)


def _parse_day(value: str | None) -> date | None:
    """A strict YYYY-MM-DD, or None.

    Strict on purpose. date.fromisoformat has accepted "20260901" and other ISO 8601
    spellings since 3.11, and the column is a 10-character string that days.today_key
    compares against by equality. A value that parses but does not round-trip to the
    same 10 characters would be a day off that never matches the day it names.
    """
    text = (value or "").strip()
    if len(text) != 10:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _day_off_payload(row: models.UnavailableDay) -> dict:
    return {"day": row.day, "note": row.note, "created_at": iso_utc(row.created_at)}


@app.put("/courses/{course_id}/deadline")
def set_course_deadline(
    course_id: int, body: DeadlineRequest, session: Session = Depends(get_session)
):
    """Set or move a course's deadline. Returns the recomputed plan.

    TODAY IS ACCEPTED, the past is not. A deadline of today is a real thing a learner
    sets ("the exam is this afternoon"), and refusing it would be refusing the truth.
    It does mean available_days is zero, which the read path below reports as a defined
    state rather than dividing by it.

    The past is rejected because setting one is always a typo, and because a deadline
    the learner can see is in the past carries no information they do not already have.
    Note that this rejection does NOT protect the read path: a deadline that was valid
    when it was written becomes today, and then yesterday, with no request in between.
    """
    course = session.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")

    deadline = _parse_day(body.deadline)
    if deadline is None:
        raise _planning_invalid("deadline_malformed", DEADLINE_MALFORMED_MESSAGE)
    if deadline < planning.today():
        raise _planning_invalid("deadline_in_past", DEADLINE_IN_PAST_MESSAGE)

    label = (body.label or "").strip()
    if len(label) > models.Course.deadline_label.type.length:
        raise _planning_invalid("deadline_label_too_long", DEADLINE_LABEL_TOO_LONG_MESSAGE)

    course.deadline = deadline.isoformat()
    # Empty label stored as NULL rather than "", so "has a label" is one question with
    # one answer instead of two spellings of no.
    course.deadline_label = label or None
    session.commit()
    return planning.course_plan(session, course)


@app.delete("/courses/{course_id}/deadline")
def clear_course_deadline(course_id: int, session: Session = Depends(get_session)):
    """Remove a deadline. Idempotent: a course that has none is already in this state.

    Nothing else is touched. No review card moves, no lesson is un-completed, and the
    course goes back to behaving exactly as a course with no deadline always has.
    """
    course = session.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    course.deadline = None
    course.deadline_label = None
    session.commit()
    return planning.course_plan(session, course)


@app.get("/courses/{course_id}/plan")
def get_course_plan(course_id: int, session: Session = Depends(get_session)):
    """How fast new material has to go in, and how fast it actually is.

    200 WITH A NULL-DEADLINE SHAPE, NOT 404, when the course has no deadline. The
    observed pace is real and worth showing either way, and a 404 would force the
    frontend to branch on an error response to draw a perfectly ordinary screen.
    "No deadline" is a state of this resource, not the absence of it.

    WHERE THE CONCEPT COUNTS WENT, since the spec listed concepts_total,
    concepts_not_started and concepts_due_now here and they are deliberately absent.

    The decisive reason is the ordinary one: BOTH NUMBERS ALREADY HAVE AN OWNER.
    GET /courses/{course_id}/concepts returns `counts` keyed by mastery bucket, including
    not_started, over exactly this course, and GET /review/today returns due_now.
    Reporting them here as well would give one number two owners that can disagree, which
    is a plain API defect and needs no theory behind it. A client that wants all three on
    one screen calls the endpoint that owns each.

    The second reason is cost. review.course_concepts is a Python join that eagerly loads
    every lesson's quiz items and chunks card lookups across the whole course. Everything
    else on this endpoint is the lesson rows plus one small table, so composing it in
    would make the cheapest read in the feature the most expensive read in the backend,
    for three numbers that are already served elsewhere.

    There is a third argument and it is deliberately listed last, because it proves too
    much to carry the decision. Putting "3 concepts due now" beside "your exam is in 4
    days" invites reading those three as at risk FOR THE EXAM, which app/planning.py's
    header shows is never true. That inference comes from JUXTAPOSITION on a screen, and
    this backend cannot prevent it: a frontend wanting both numbers fetches them from
    their owners and juxtaposes them anyway. By that argument /review/today should not
    report due_now either, which nobody believes. The retrievability proof forbids
    deadline-aware SCHEDULING, which is a real and enforced constraint on this backend;
    it does not forbid a count, and it should not be stretched into doing so.
    """
    course = session.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    return planning.course_plan(session, course)


@app.get("/courses/{course_id}/plan.ics")
def get_course_plan_ics(course_id: int, session: Session = Depends(get_session)):
    """The deadline as a calendar file. The only non-JSON response in this API.

    404 rather than an empty VCALENDAR when there is no deadline. A calendar with no
    events imports silently and leaves the learner believing it worked.

    The filename is hardcoded from the course id and never derived from the title. See
    ics.download_filename: a title is LLM output, and a title in a Content-Disposition
    header is header injection rather than a broken calendar.
    """
    course = session.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    plan = planning.course_plan(session, course)
    # THE PARSED VALUE, not the raw column. planning.parse_deadline deliberately degrades
    # an unreadable stored date to "this course has no usable deadline", and its docstring
    # promises that must never take an endpoint down. A truthiness check on the raw string
    # breaks that promise silently, because garbage is truthy: the guard would let it past
    # and ics.deadline_calendar would raise ValueError on date.fromisoformat, turning a
    # bad row into a 500. Only reachable through a row not written by PUT, which is why it
    # is low severity and not why it is worth fixing: this is the module that is a
    # security surface, and it should honour its own module's contract.
    if planning.parse_deadline(plan["deadline"]) is None:
        raise HTTPException(404, NO_DEADLINE_MESSAGE)
    return Response(
        content=ics.deadline_calendar(plan),
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{ics.download_filename(course.id)}"'
        },
    )


@app.get("/plan/days-off")
def list_days_off(session: Session = Depends(get_session)):
    """Every day the learner has marked off, oldest first.

    Global, not per course. The table has no course_id because a learner who is away is
    away from all of it; see models.UnavailableDay.
    """
    rows = (
        session.query(models.UnavailableDay).order_by(models.UnavailableDay.day).all()
    )
    return {"days_off": [_day_off_payload(row) for row in rows]}


@app.post("/plan/days-off")
def add_day_off(body: DayOffRequest, session: Session = Depends(get_session)):
    """Mark a day off. IDEMPOTENT: marking an already-marked day is a success.

    Never a 409 off the unique constraint. Pressing the button twice, or pressing it on
    a day that was already off, is not an error the learner can learn anything from, and
    an endpoint that refuses here while DELETE happily accepts an unmarked day would be
    an asymmetry they can see and cannot explain.

    An existing row is returned UNCHANGED rather than having its note overwritten, so
    this is a genuine no-op and not a silent edit. Changing a note means deleting the
    day and adding it again.

    The IntegrityError branch is the same idempotence under a race: two simultaneous
    posts both find no row and both insert, and the loser must still come back with the
    winner's row rather than a 500.
    """
    day = _parse_day(body.day)
    if day is None:
        raise _planning_invalid("day_malformed", DAY_MALFORMED_MESSAGE)

    key = day.isoformat()
    existing = (
        session.query(models.UnavailableDay)
        .filter(models.UnavailableDay.day == key)
        .one_or_none()
    )
    if existing is not None:
        return _day_off_payload(existing)

    row = models.UnavailableDay(day=key, note=(body.note or "").strip())
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        row = (
            session.query(models.UnavailableDay)
            .filter(models.UnavailableDay.day == key)
            .one()
        )
    return _day_off_payload(row)


@app.delete("/plan/days-off/{day}")
def remove_day_off(day: str, session: Session = Depends(get_session)):
    """Unmark a day. Succeeds whether or not it was marked.

    THE DATE IS IN THE PATH, and this deliberately does not copy the tutor's
    concept_key, which travels in the query string. That was forced: a normalized
    concept key can contain a slash, and Starlette will not match a path segment
    containing one, so the concept most in need of explaining would be the one URL the
    learner could not reach. A YYYY-MM-DD has no slashes and never will, so the reason
    does not apply and the plainer URL wins.

    Idempotent, matching POST above. Deleting a day that was not marked leaves the
    learner in exactly the state they asked for.
    """
    parsed = _parse_day(day)
    if parsed is None:
        raise _planning_invalid("day_malformed", DAY_MALFORMED_MESSAGE)
    removed = (
        session.query(models.UnavailableDay)
        .filter(models.UnavailableDay.day == parsed.isoformat())
        .delete()
    )
    session.commit()
    return {"day": parsed.isoformat(), "removed": bool(removed)}
