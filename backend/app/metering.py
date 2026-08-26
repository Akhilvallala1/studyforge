"""Per-call LLM usage metering: cost estimation, persistence, hard cap, and alerts.

MeteredLLM wraps a raw provider so every generate() call is recorded to the
llm_calls table (even on a failed call that still consumed tokens) and checked
against an optional hard spend cap before it runs.
"""

import logging
import math
import os

from sqlalchemy import func

from app import models
from app.costs import estimate_cost
from app.db import SessionLocal
from app.llm.base import LLMCallError, LLMProvider

logger = logging.getLogger("studyforge.usage")

DEFAULT_ALERT_THRESHOLD_USD = 10.0


class CostLimitExceeded(Exception):
    """Raised when a paid provider call would push cumulative spend past the configured cap."""

    def __init__(self, limit_usd: float, spent_usd: float):
        super().__init__(f"LLM spend limit ${limit_usd:.2f} reached (spent ${spent_usd:.2f})")
        self.limit_usd = limit_usd
        self.spent_usd = spent_usd


def total_spend(session) -> float:
    """Cumulative estimated_cost_usd across every recorded llm_calls row."""
    total = session.query(func.sum(models.LlmCall.estimated_cost_usd)).scalar()
    return float(total or 0.0)


def _acked_spend(session) -> float | None:
    row = session.get(models.AppSetting, "cost_alert_acked_usd")
    return float(row.value) if row is not None else None


def alert_state(session) -> dict:
    """Recurring alert: fires again every time cumulative spend crosses another
    multiple of the threshold, until acknowledged at (or past) that multiple."""
    threshold = float(os.environ.get("STUDYFORGE_COST_ALERT_USD", str(DEFAULT_ALERT_THRESHOLD_USD)))
    total = total_spend(session)
    acked = _acked_spend(session)
    if threshold <= 0:
        active = total > 0 and (acked is None or acked < total)
    else:
        active = total >= threshold and (
            acked is None or math.floor(total / threshold) > math.floor(acked / threshold)
        )
    return {
        "active": active,
        "threshold_usd": threshold,
        "total_usd": total,
        "acknowledged": acked,
    }


def acknowledge_alert(session) -> dict:
    """Record the current total as acknowledged, clearing the active alert."""
    total = total_spend(session)
    row = session.get(models.AppSetting, "cost_alert_acked_usd")
    if row is None:
        session.add(models.AppSetting(key="cost_alert_acked_usd", value=str(total)))
    else:
        row.value = str(total)
    session.commit()
    return alert_state(session)


def _format_threshold(threshold: float) -> str:
    return f"{threshold:g}"


class MeteredLLM:
    """Wraps an LLMProvider so every call is cost-estimated, persisted, and cap-checked."""

    def __init__(self, provider: LLMProvider, run_id: str):
        self.provider = provider
        self.run_id = run_id

    def generate(self, stage: str, system: str, prompt: str, max_tokens: int = 64000) -> str:
        self._check_cap()
        try:
            result = self.provider.generate(system, prompt, max_tokens)
        except LLMCallError as exc:
            self._record(stage, exc.input_tokens, exc.output_tokens)
            raise
        self._record(stage, result.input_tokens, result.output_tokens)
        return result.text

    def _check_cap(self) -> None:
        if not self.provider.is_paid:
            return
        limit_env = os.environ.get("STUDYFORGE_COST_LIMIT_USD")
        if limit_env is None:
            return
        limit = float(limit_env)
        session = SessionLocal()
        try:
            spent = total_spend(session)
        finally:
            session.close()
        if spent >= limit:
            raise CostLimitExceeded(limit, spent)

    def _record(self, stage: str, input_tokens: int | None, output_tokens: int | None) -> None:
        if self.provider.is_paid:
            cost, approximate = estimate_cost(self.provider.model, input_tokens, output_tokens)
        else:
            cost, approximate = 0.0, input_tokens is None or output_tokens is None

        session = SessionLocal()
        try:
            old_state = alert_state(session)
            row = models.LlmCall(
                run_id=self.run_id,
                course_id=None,
                provider=self.provider.name,
                model=self.provider.model,
                stage=stage,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=cost,
                approximate=approximate,
            )
            session.add(row)
            session.commit()
            new_state = alert_state(session)
        finally:
            session.close()

        logger.info(
            # No course id here: it is backfilled onto the run's rows only after the
            # course is saved, so logging one at call time would always say "pending".
            "LLM call: provider=%s model=%s stage=%s in=%s out=%s cost=$%.4f total=$%.2f run=%s",
            self.provider.name,
            self.provider.model,
            stage,
            input_tokens,
            output_tokens,
            cost,
            new_state["total_usd"],
            self.run_id,
        )
        if new_state["active"] and not old_state["active"]:
            logger.warning(
                "COST ALERT: cumulative LLM spend $%.2f has crossed $%s",
                new_state["total_usd"],
                _format_threshold(new_state["threshold_usd"]),
            )
