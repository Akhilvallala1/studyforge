import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# app.db creates its engine at import time, so the test database path (and a
# deterministic CORS config) must be set before anything imports the app.
os.environ["STUDYFORGE_DB"] = os.path.join(tempfile.mkdtemp(), "test.sqlite3")
# Pin (not just pop) the CORS config: app/__init__ loads backend/.env, and env
# vars set here take precedence over it, keeping tests independent of dev .env files.
os.environ["STUDYFORGE_CORS_ORIGINS"] = "http://localhost:3000"

import pytest


class FailingProvider:
    """Provider whose generate() always raises, for exercising error handling."""

    name = "failing"
    model = "failing-model"
    is_paid = False

    def generate(self, system: str, prompt: str, max_tokens: int = 64000):
        raise RuntimeError("provider exploded")


class StubPaidProvider:
    """Deterministic is_paid=True provider with fabricated token counts, for cost tests.

    Produces a minimal but valid outline/lesson JSON pair (one module, one lesson)
    so it can drive the full generate_course pipeline like the fake provider, while
    reporting fixed, non-zero token counts so cost accrues predictably.

    It dispatches by system-prompt phrase and falls through to the lesson shape, the
    same way FakeProvider does, and it carries the same hazard: a stage with no
    branch here answers with lesson JSON, the caller fails to parse it, and a cost
    test for that stage exercises the FAILURE path while still passing, because a
    failed call is metered too. The remediation and tutor branches below exist for
    that reason. Remediation had no branch here for as long as the stage has
    existed; nothing was passing for the wrong reason yet only because no
    remediation cost test had been written, which is not a property to rely on.
    """

    name = "anthropic"
    is_paid = True

    def __init__(
        self, model: str = "claude-opus-5", input_tokens: int = 1000, output_tokens: int = 500
    ):
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls = 0

    def generate(self, system: str, prompt: str, max_tokens: int = 64000):
        import json

        from app.llm.base import LLMResult

        self.calls += 1
        if "curriculum designer" in system:
            text = json.dumps(
                {
                    "title": "Stub Course",
                    "description": "A stub-provider course",
                    "modules": [
                        {"title": "Module 1", "lessons": [{"title": "Lesson A", "summary": "s"}]}
                    ],
                }
            )
        elif "re-teaching one concept" in system:
            text = json.dumps(
                {
                    "restatement": "Stub restatement in plainer words.",
                    "worked_example": "Stub worked example, one step at a time.",
                }
            )
        elif "answering a learner's question" in system:
            text = json.dumps(
                {
                    "answer": "Stub tutor answer, grounded in your course.",
                    "beyond": "Stub aside your course does not cover.",
                    "check": "What does it take in?",
                }
            )
        else:
            text = json.dumps(
                {
                    "content": "# Lesson\nStub content",
                    "concepts": ["concept-1"],
                    "quiz": [
                        {
                            "question": "Q?",
                            "kind": "short",
                            "options": [],
                            "answer": "a",
                            "concept": "concept-1",
                        }
                    ],
                }
            )
        return LLMResult(text=text, input_tokens=self.input_tokens, output_tokens=self.output_tokens)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def failing_provider(monkeypatch):
    from app import main

    provider = FailingProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    return provider


@pytest.fixture
def stub_paid_provider(monkeypatch):
    from app import main

    provider = StubPaidProvider()
    monkeypatch.setattr(main, "get_provider", lambda: provider)
    return provider
