"""Unit tests for app/costs.py pricing/estimation and the metering layer's
zero-cost-for-unpaid-providers behavior."""

import os

from app.costs import estimate_cost
from app.db import SessionLocal
from app.metering import MeteredLLM


def test_estimate_cost_exact_match():
    cost, approximate = estimate_cost("claude-sonnet-5", 1_000_000, 1_000_000)
    assert cost == 2.00 + 10.00
    assert approximate is False


def test_estimate_cost_prefix_match_with_date_suffix():
    # Not a literal PRICING key, but the "claude-opus-5" pricing should still apply.
    cost, approximate = estimate_cost("claude-opus-5-20260115", 1_000_000, 1_000_000)
    assert cost == 5.00 + 25.00
    assert approximate is False


def test_estimate_cost_unknown_model_falls_back_and_is_approximate(monkeypatch):
    monkeypatch.delenv("STUDYFORGE_PRICE_DEFAULT_IN_USD", raising=False)
    monkeypatch.delenv("STUDYFORGE_PRICE_DEFAULT_OUT_USD", raising=False)
    cost, approximate = estimate_cost("some-totally-unknown-model", 1_000_000, 1_000_000)
    assert approximate is True
    assert cost == 5.00 + 25.00  # default fallback prices


def test_estimate_cost_unknown_model_respects_env_fallback(monkeypatch):
    monkeypatch.setenv("STUDYFORGE_PRICE_DEFAULT_IN_USD", "1.00")
    monkeypatch.setenv("STUDYFORGE_PRICE_DEFAULT_OUT_USD", "2.00")
    cost, approximate = estimate_cost("some-totally-unknown-model", 1_000_000, 1_000_000)
    assert approximate is True
    assert cost == 1.00 + 2.00


def test_estimate_cost_none_token_counts_are_approximate():
    cost, approximate = estimate_cost("claude-sonnet-5", None, None)
    assert cost == 0.0
    assert approximate is True


class _NonPaidStub:
    name = "stub-nonpaid"
    model = "claude-sonnet-5"
    is_paid = False

    def generate(self, system: str, prompt: str, max_tokens: int = 64000):
        from app.llm.base import LLMResult

        return LLMResult(text="ok", input_tokens=1000, output_tokens=1000)


def test_metering_records_zero_cost_for_is_paid_false(client):
    """Even though the model would normally price out non-zero, a non-paid provider
    (e.g. ollama/fake) is always recorded at $0.00 cost - only tokens are tracked.

    Takes the client fixture so init_db() has run; without it this file fails when
    run on its own because llm_calls does not exist yet.
    """
    from app import models

    provider = _NonPaidStub()
    meter = MeteredLLM(provider, run_id="cost-test-run")
    meter.generate("outline", "system prompt", "user prompt")

    session = SessionLocal()
    try:
        row = (
            session.query(models.LlmCall)
            .filter(models.LlmCall.run_id == "cost-test-run")
            .one()
        )
        assert row.estimated_cost_usd == 0.0
        assert row.input_tokens == 1000
        assert row.output_tokens == 1000
    finally:
        session.close()


def test_estimate_cost_pricing_table_matches_current_rates():
    # Guards against silent drift in the PRICING table (backend/app/costs.py).
    from app.costs import PRICING

    assert PRICING["claude-opus-5"] == (5.00, 25.00)
    assert PRICING["claude-sonnet-5"] == (2.00, 10.00)
    assert PRICING["claude-haiku-4-5"] == (1.00, 5.00)
    assert PRICING["claude-fable-5"] == (10.00, 50.00)


def test_env_fallback_defaults_when_unset(monkeypatch):
    """With no env overrides, an unknown model prices at the built-in 5.00/25.00
    defaults. Uses non-zero token counts so the rates are actually exercised."""
    monkeypatch.delenv("STUDYFORGE_PRICE_DEFAULT_IN_USD", raising=False)
    monkeypatch.delenv("STUDYFORGE_PRICE_DEFAULT_OUT_USD", raising=False)
    assert os.environ.get("STUDYFORGE_PRICE_DEFAULT_IN_USD") is None
    cost, approximate = estimate_cost("unknown-x", 200_000, 40_000)
    assert approximate is True
    assert cost == (200_000 / 1_000_000 * 5.00) + (40_000 / 1_000_000 * 25.00)
