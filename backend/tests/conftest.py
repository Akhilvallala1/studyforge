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

    def generate(self, system: str, prompt: str, max_tokens: int = 64000) -> str:
        raise RuntimeError("provider exploded")


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
