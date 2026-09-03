"""Runs one course generation while recording everything the metrics need.

The recorder sits between `generation.generate_course` and `MeteredLLM`, so the
pipeline under test is the real one: same prompts, same parser, same metering,
same cost cap. Nothing here is imported by app code.
"""

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field

from app import generation, ingest, models
from app.db import SessionLocal
from app.generation import parse_json_response
from app.llm import get_provider
from app.metering import MeteredLLM
from evals.metrics import evaluate

# Keys the pipeline needs from each stage's JSON. A response that parses but is
# missing these is a reliability failure too, just a quieter one.
REQUIRED_KEYS = {"outline": ("title", "modules"), "lesson": ("content", "concepts", "quiz")}


@dataclass
class CallRecord:
    """One provider call: how it was parsed, how long it took, what it cost."""

    index: int
    stage: str
    latency_s: float
    prompt_chars: int
    response_chars: int
    # Parse reliability, from strictest to loosest.
    strict_json: bool = False  # json.loads on the raw response, untouched
    tolerant_json: bool = False  # what app/generation.py actually does
    used_code_fence: bool = False  # response was wrapped in ```json ... ```
    used_prose_trim: bool = False  # prose before/after the JSON object
    schema_ok: bool = False  # parsed object had the keys the stage needs
    error: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float = 0.0


@dataclass
class RunOutcome:
    """Result of one generation attempt, successful or not."""

    name: str
    ok: bool
    error: str | None = None
    course: dict | None = None
    chunks: list = field(default_factory=list)
    calls: list = field(default_factory=list)
    wall_clock_s: float = 0.0


def prompt_fingerprint() -> dict:
    """Identifies the prompt version a result was produced under.

    Without this, comparing two result files tells you the scores changed but not
    that the prompts did, which is the whole point of a before/after run.
    """

    def digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]

    return {
        "outline_system": digest(generation.OUTLINE_SYSTEM),
        "lesson_system": digest(generation.LESSON_SYSTEM),
        "outline_system_chars": len(generation.OUTLINE_SYSTEM),
        "lesson_system_chars": len(generation.LESSON_SYSTEM),
    }


class RecordingMeter:
    """Passes calls through to MeteredLLM, recording parse outcome and latency.

    The response is handed back verbatim: the pipeline still does its own parsing,
    so a parse failure here is the same failure the app would hit in production.
    """

    def __init__(self, inner, keep_raw: bool = False):
        self.inner = inner
        self.records: list[CallRecord] = []
        self.raw_responses: list[str] = []
        self.keep_raw = keep_raw

    def generate(self, stage: str, system: str, prompt: str, max_tokens: int = 64000) -> str:
        index = len(self.records)
        started = time.monotonic()
        try:
            text = self.inner.generate(stage, system, prompt, max_tokens)
        except Exception as exc:
            self.records.append(
                CallRecord(
                    index=index,
                    stage=stage,
                    latency_s=time.monotonic() - started,
                    prompt_chars=len(prompt) + len(system),
                    response_chars=0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            raise
        latency = time.monotonic() - started
        record = CallRecord(
            index=index,
            stage=stage,
            latency_s=latency,
            prompt_chars=len(prompt) + len(system),
            response_chars=len(text),
        )
        self._classify(record, text, stage)
        self.records.append(record)
        if self.keep_raw:
            self.raw_responses.append(text)
        return text

    @staticmethod
    def _classify(record: CallRecord, text: str, stage: str) -> None:
        stripped = text.strip()
        try:
            parsed = json.loads(stripped)
            record.strict_json = isinstance(parsed, dict)
        except ValueError:
            record.strict_json = False
        record.used_code_fence = "```" in stripped
        record.used_prose_trim = not record.strict_json and not (
            stripped.startswith("{") and stripped.endswith("}")
        )
        try:
            parsed = parse_json_response(text)
            record.tolerant_json = True
            record.schema_ok = all(key in parsed for key in REQUIRED_KEYS.get(stage, ()))
        except ValueError as exc:
            record.tolerant_json = False
            record.error = f"parse: {exc}"


def _cost_rows(run_id: str) -> list[dict]:
    """Metered token/cost rows for one run, in call order."""
    session = SessionLocal()
    try:
        rows = (
            session.query(models.LlmCall)
            .filter(models.LlmCall.run_id == run_id)
            .order_by(models.LlmCall.id)
            .all()
        )
        return [
            {
                "stage": r.stage,
                "model": r.model,
                "provider": r.provider,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_usd": r.estimated_cost_usd,
                "approximate": r.approximate,
            }
            for r in rows
        ]
    finally:
        session.close()


def parse_reliability(records: list[CallRecord]) -> dict:
    """Per-stage counts of how the model's JSON actually arrived.

    `hard_parse_failures` counts individual calls that would not parse, which is no
    longer the same as a lost course: `app/generation.py` retries the call once with
    a corrective instruction, and drops only that lesson if the retry fails too. A
    non-zero count here with `ok: true` on the run means the recovery path fired.
    """
    stages = sorted({r.stage for r in records})
    per_stage = {}
    for stage in stages:
        subset = [r for r in records if r.stage == stage]
        per_stage[stage] = {
            "calls": len(subset),
            "strict_json_first_try": sum(1 for r in subset if r.strict_json),
            "tolerant_parse_ok": sum(1 for r in subset if r.tolerant_json),
            "needed_code_fence_strip": sum(1 for r in subset if r.used_code_fence),
            "needed_prose_trim": sum(1 for r in subset if r.used_prose_trim),
            "schema_ok": sum(1 for r in subset if r.schema_ok),
            "hard_parse_failures": sum(1 for r in subset if not r.tolerant_json),
            "call_errors": sum(1 for r in subset if r.error and not r.tolerant_json),
        }
    total = len(records)
    return {
        "total_calls": total,
        "strict_json_first_try": sum(1 for r in records if r.strict_json),
        "tolerant_parse_ok": sum(1 for r in records if r.tolerant_json),
        "hard_parse_failures": sum(1 for r in records if not r.tolerant_json),
        "retry_path_exists": True,
        "per_stage": per_stage,
    }


def latency_and_cost(records: list[CallRecord], cost_rows: list[dict]) -> dict:
    for record, row in zip(records, cost_rows):
        record.input_tokens = row["input_tokens"]
        record.output_tokens = row["output_tokens"]
        record.cost_usd = row["cost_usd"]
    stages = sorted({r.stage for r in records})
    per_stage = {}
    for stage in stages:
        subset = [r for r in records if r.stage == stage]
        per_stage[stage] = {
            "calls": len(subset),
            "total_latency_s": round(sum(r.latency_s for r in subset), 2),
            "mean_latency_s": round(sum(r.latency_s for r in subset) / len(subset), 2),
            "max_latency_s": round(max(r.latency_s for r in subset), 2),
            "input_tokens": sum(r.input_tokens or 0 for r in subset),
            "output_tokens": sum(r.output_tokens or 0 for r in subset),
            "cost_usd": round(sum(r.cost_usd for r in subset), 6),
        }
    return {
        "calls": len(records),
        "model": cost_rows[0]["model"] if cost_rows else None,
        "provider": cost_rows[0]["provider"] if cost_rows else None,
        "total_llm_latency_s": round(sum(r.latency_s for r in records), 2),
        "input_tokens": sum(r.input_tokens or 0 for r in records),
        "output_tokens": sum(r.output_tokens or 0 for r in records),
        "cost_usd": round(sum(r.cost_usd for r in records), 6),
        "any_approximate": any(row["approximate"] for row in cost_rows),
        "per_stage": per_stage,
    }


def run_course_eval(
    name: str,
    text: str,
    source_meta: dict,
    provider=None,
    documents: list[tuple[str, str]] | None = None,
    tag_sources: bool = True,
) -> dict:
    """Generate one course from `text` and measure it. Returns a JSON-safe result dict.

    A failed generation still returns a result: the call records up to the failure
    are the most interesting data a failure produces, and losing them to an
    exception would waste money already spent.

    `documents` makes this a MULTI-SOURCE run: (label, text) pairs chunked separately so
    every chunk knows which document it came from. `text` is still passed and is still
    what the metrics score against, because grounding asks whether an answer is in the
    corpus and the corpus is all of it.

    `tag_sources` is the A/B switch, and it is a switch rather than a prompt variant on
    purpose. Passing owners=None reproduces the pre-feature code path EXACTLY rather than
    approximately: label_segments and outline_system both branch on whether owners names
    more than one document, so the untagged arm is byte for byte the prompt that shipped
    before multi-source existed. A variants.py entry would have been a second copy of
    that wording, which is the thing that drifts.
    """
    if documents is not None:
        chunks, owners = generation.chunk_sources(documents)
    else:
        chunks, owners = ingest.chunk_text(text), None
    if not tag_sources:
        owners = None
    run_id = uuid.uuid4().hex
    # Raw responses are kept so a hard parse failure can be diagnosed from the result
    # file instead of from a truncated exception message. Only the failing response is
    # persisted, and only on failure, so a successful run stays small.
    meter = RecordingMeter(MeteredLLM(provider or get_provider(), run_id), keep_raw=True)
    started = time.monotonic()
    outcome = RunOutcome(name=name, ok=False, chunks=chunks)
    try:
        outcome.course = generation.generate_course(meter, chunks, owners)
        outcome.ok = True
    except Exception as exc:  # noqa: BLE001  (deliberate: see docstring)
        outcome.error = f"{type(exc).__name__}: {exc}"
    outcome.wall_clock_s = time.monotonic() - started
    outcome.calls = meter.records

    cost_rows = _cost_rows(run_id)
    result = {
        "name": name,
        "ok": outcome.ok,
        "error": outcome.error,
        "run_id": run_id,
        "prompts": prompt_fingerprint(),
        "source": {
            **source_meta,
            "chars": len(text),
            "chunks": len(chunks),
            "chunk_chars": [len(c) for c in chunks],
            # Recorded on every run, single-source included, so a bundle says which arm
            # produced it without anyone having to remember the flags.
            "documents": [label for label, _ in documents] if documents else None,
            "source_tags": bool(documents) and tag_sources,
        },
        "wall_clock_s": round(outcome.wall_clock_s, 2),
        "parse_reliability": parse_reliability(meter.records),
        "cost_latency": latency_and_cost(meter.records, cost_rows),
        "calls": [asdict(r) for r in meter.records],
    }
    if outcome.course is not None:
        result["metrics"] = evaluate(outcome.course, chunks)
        result["course"] = outcome.course
    if not outcome.ok and meter.raw_responses:
        result["failing_raw_response"] = meter.raw_responses[-1]
    return result
