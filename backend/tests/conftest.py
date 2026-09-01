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
        elif "GIVE EVERYTHING BUT THE LAST MOVE" in system:
            # Guided mode reaches here through the SAME phrase the answer-mode branch
            # below matches, because both modes are built off one shared prompt body, so
            # this has to be tested first. Without it a guided cost test would meter a
            # reply in answer-mode shape: it parses, `ask` is empty because the model
            # never sent one, and the test passes while exercising the degraded path.
            # That is the failure this class's docstring describes, one level subtler,
            # because here there is not even a parse error to notice.
            text = json.dumps(
                {
                    "answer": "Stub guided answer, carried up to the last move.",
                    "beyond": "Stub aside your course does not cover.",
                    "ask": "What is the last move?",
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


def clear_todays_tutor_turns() -> None:
    """Delete this study day's tutor messages. Call before a turn that must not be refused.

    THE RULE THIS EXISTS FOR: any POST to /tutor/messages that expects not to be refused
    needs today's window clear first. The tutor's day-wide cap counts every learner turn
    written today across EVERY concept, the whole suite shares one SQLite file, and
    test_tutor_endpoints.py deliberately seeds runs of turns to drive the caps. Without
    this, a tutor test starts failing once enough other tutor tests exist, which is the
    most expensive kind of failure to diagnose: it points at the wrong file, and at a
    change that did not cause it.

    Here in conftest rather than in either test module because two files need it and a
    third will. It was written out twice, byte for byte, with two docstrings that could
    drift apart; whoever writes the third file finds this instead of neither copy.

    Callers couple it to whatever actually needs it. test_tutor_endpoints.py runs it from
    an autouse fixture, because every test in that file is about the tutor.
    test_usage_attribution.py calls it from its _ask_tutor helper instead, because six of
    its forty tests touch the tutor and an autouse delete would misdescribe the other
    thirty-four as caring about tutor_messages.

    SCOPED TO TODAY'S WINDOW, never the whole table. test_tutor_context.py seeds rows at
    fixed past dates precisely to prove where the 04:00 day boundary falls, and a blanket
    delete would take exactly those rows and quietly hollow out that proof.
    """
    from app import days, models
    from app.db import SessionLocal, init_db

    init_db()
    day_start, day_end = days.day_bounds()
    session = SessionLocal()
    try:
        session.query(models.TutorMessage).filter(
            models.TutorMessage.created_at >= day_start
        ).filter(models.TutorMessage.created_at < day_end).delete()
        session.commit()
    finally:
        session.close()


def clear_days_off() -> None:
    """Delete every marked day off. Call before anything that reads a study-day count.

    THE RULE THIS EXISTS FOR: any test whose assertion depends on available_days,
    required_per_week, or days_off_in_window needs this first. unavailable_days is a
    GLOBAL table with a unique constraint on `day` and no course id, and the whole suite
    shares one SQLite file, so a test that marks 2026-10-01 off leaves it marked for
    every test that runs afterwards. The damage is silent and order-dependent: a plan
    test asserting "12 available days" gets 11, and only when the other test happens to
    run first. It would not fail today. It would fail when the fifth test is added, and
    it would point at that test rather than at the one that left the row.

    Here in conftest rather than in the planning tests for the reason
    clear_todays_tutor_turns is here: the .ics tests need it too, a third file will, and
    two byte-identical copies with two docstrings are how those drift apart.

    A BLANKET DELETE HERE, unlike clear_todays_tutor_turns, which is carefully scoped to
    today's window. That difference is deliberate and not an inconsistency. Tutor
    messages carry a timestamp that test_tutor_context.py seeds at fixed past dates
    precisely to prove where the 04:00 boundary falls, so a blanket delete there would
    take exactly the rows that are the proof. A day off has no such fixture anywhere: it
    is a bare calendar key with no window semantics, nothing seeds one to demonstrate a
    boundary, and a window-scoped delete would be worse than useless, since the row that
    poisons a denominator is the one another test left OUTSIDE the window under test.

    Callers couple it to what actually needs it. test_planning.py runs it from an autouse
    fixture, because every test in that file reads a study-day count. Anything else
    should call it directly rather than adding a second autouse delete, which would
    misdescribe tests that do not care about days off as tests that do.
    """
    from app import models
    from app.db import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        session.query(models.UnavailableDay).delete()
        session.commit()
    finally:
        session.close()


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
