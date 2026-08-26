"""API-level tests for cost tracking: metered generation, GET /usage, the recurring
cost alert, and the hard spend cap. Uses TestClient with env/provider monkeypatching -
no real LLM API is ever called."""

import json
from datetime import datetime, timedelta

from app import models
from app.db import SessionLocal
from app.llm.base import LLMCallError, LLMResult
from app.llm.fake_provider import FakeProvider


class SucceedsOnceThenRaises:
    """First call returns a valid one-module/one-lesson outline; the second call
    (the lesson stage) raises LLMCallError carrying partial usage, simulating a
    mid-run failure that still consumed tokens (e.g. a refusal)."""

    name = "anthropic"
    model = "claude-opus-5"
    is_paid = True

    def __init__(self):
        self.calls = 0

    def generate(self, system: str, prompt: str, max_tokens: int = 64000):
        self.calls += 1
        if self.calls == 1:
            text = json.dumps(
                {
                    "title": "Doomed Course",
                    "description": "Fails on the lesson stage",
                    "modules": [
                        {"title": "Module 1", "lessons": [{"title": "Lesson A", "summary": "s"}]}
                    ],
                }
            )
            return LLMResult(text=text, input_tokens=100, output_tokens=50)
        raise LLMCallError("simulated mid-run failure", input_tokens=20, output_tokens=0)


def _llm_call_count() -> int:
    session = SessionLocal()
    try:
        return session.query(models.LlmCall).count()
    finally:
        session.close()


def test_fake_provider_generation_creates_committed_rows_with_course_id_backfilled(
    client, monkeypatch
):
    monkeypatch.setenv("STUDYFORGE_LLM_PROVIDER", "fake")

    resp = client.post(
        "/courses/generate",
        json={"text": "Whales are mammals that live in the ocean and breathe air."},
    )
    assert resp.status_code == 200
    body = resp.json()
    course_id = body["id"]
    assert body["usage"]["run_cost_usd"] == 0.0
    assert body["usage"]["total_cost_usd"] >= 0.0
    assert isinstance(body["usage"]["alert_active"], bool)

    session = SessionLocal()
    try:
        rows = session.query(models.LlmCall).filter(models.LlmCall.course_id == course_id).all()
    finally:
        session.close()

    # FakeProvider always builds 2 modules x 2 lessons: 1 outline call + 4 lesson calls.
    assert len(rows) == 5
    for row in rows:
        assert row.estimated_cost_usd == 0.0
        assert row.input_tokens > 0
        assert row.output_tokens > 0
        assert row.provider == "fake"
        assert row.model == "fake"
        assert row.approximate is False


def test_usage_endpoint_contract(client, monkeypatch):
    # A successful fake-provider run -> a course_id-keyed bucket.
    monkeypatch.setattr("app.main.get_provider", lambda: FakeProvider())
    ok_resp = client.post("/courses/generate", json={"text": "Photosynthesis and plant biology."})
    assert ok_resp.status_code == 200
    course_id = ok_resp.json()["id"]

    # A run that fails partway through -> orphan rows (course_id never backfilled).
    monkeypatch.setattr("app.main.get_provider", lambda: SucceedsOnceThenRaises())
    fail_resp = client.post("/courses/generate", json={"text": "Some other unrelated source."})
    assert fail_resp.status_code == 502

    usage = client.get("/usage?limit=10").json()
    assert set(usage.keys()) == {"totals", "per_course", "recent_calls", "alert", "limit"}

    totals = usage["totals"]
    assert set(totals.keys()) == {
        "calls",
        "input_tokens",
        "output_tokens",
        "estimated_cost_usd",
        "approximate",
    }
    assert totals["calls"] >= 7  # 5 from the fake run + 2 from the failing run

    per_course_ids = {bucket["course_id"] for bucket in usage["per_course"]}
    assert course_id in per_course_ids
    assert None in per_course_ids  # unattributed bucket for the never-backfilled run

    null_bucket = next(b for b in usage["per_course"] if b["course_id"] is None)
    assert null_bucket["title"] is None
    assert null_bucket["calls"] >= 2

    course_bucket = next(b for b in usage["per_course"] if b["course_id"] == course_id)
    assert course_bucket["calls"] == 5
    assert course_bucket["title"]

    assert len(usage["recent_calls"]) <= 10
    for call in usage["recent_calls"]:
        assert set(call.keys()) == {
            "id",
            "created_at",
            "provider",
            "model",
            "stage",
            "course_id",
            "input_tokens",
            "output_tokens",
            "estimated_cost_usd",
            "approximate",
        }
    ids = [c["id"] for c in usage["recent_calls"]]
    assert ids == sorted(ids, reverse=True)  # newest first

    # Timestamps must carry an explicit UTC offset. Without one, JavaScript parses
    # them as local time and the UI shows every call shifted by the viewer's offset.
    for call in usage["recent_calls"]:
        parsed = datetime.fromisoformat(call["created_at"])
        assert parsed.tzinfo is not None, "created_at must be timezone-aware"
        assert parsed.utcoffset() == timedelta(0)

    assert set(usage["alert"].keys()) == {"active", "threshold_usd", "total_usd", "acknowledged"}
    assert set(usage["limit"].keys()) == {"configured", "limit_usd", "reached"}


def test_rows_persist_when_a_later_call_in_the_run_raises(client, monkeypatch):
    provider = SucceedsOnceThenRaises()
    monkeypatch.setattr("app.main.get_provider", lambda: provider)

    count_before = _llm_call_count()
    resp = client.post("/courses/generate", json={"text": "Text that will fail partway."})
    assert resp.status_code == 502
    assert provider.calls == 2

    count_after = _llm_call_count()
    assert count_after == count_before + 2

    session = SessionLocal()
    try:
        rows = session.query(models.LlmCall).order_by(models.LlmCall.id.desc()).limit(2).all()
    finally:
        session.close()
    newest, previous = rows[0], rows[1]
    assert newest.stage == "lesson"
    assert newest.input_tokens == 20
    assert newest.output_tokens == 0
    assert newest.course_id is None  # generation failed before _save_course ran
    assert previous.stage == "outline"
    assert previous.input_tokens == 100
    assert previous.course_id is None


def test_recurring_cost_alert_activates_acks_and_reactivates(client, stub_paid_provider,
                                                               monkeypatch):
    monkeypatch.setenv("STUDYFORGE_COST_ALERT_USD", "0.01")

    # Start from a clean (acknowledged) baseline regardless of spend from earlier tests.
    baseline = client.post("/usage/alert/ack").json()
    assert baseline["active"] is False
    assert baseline["threshold_usd"] == 0.01

    resp1 = client.post("/courses/generate", json={"text": "Alert test source material one."})
    assert resp1.status_code == 200
    assert resp1.json()["usage"]["alert_active"] is True

    usage1 = client.get("/usage").json()
    assert usage1["alert"]["active"] is True

    acked = client.post("/usage/alert/ack").json()
    assert acked["active"] is False
    assert acked["acknowledged"] == usage1["alert"]["total_usd"]

    resp2 = client.post("/courses/generate", json={"text": "Alert test source material two."})
    assert resp2.status_code == 200
    assert resp2.json()["usage"]["alert_active"] is True

    usage2 = client.get("/usage").json()
    assert usage2["alert"]["active"] is True
    assert usage2["alert"]["total_usd"] > usage1["alert"]["total_usd"]


class _MultiLessonPaidProvider:
    """Paid provider whose outline has several lessons, so a run makes many calls.

    Lets a test trip the spend cap partway through a run rather than before it starts.
    """

    name = "anthropic"
    model = "claude-opus-5"
    is_paid = True

    def __init__(self, lessons: int = 4):
        self.lessons = lessons
        self.calls = 0

    def generate(self, system: str, prompt: str, max_tokens: int = 64000):
        import json

        from app.llm.base import LLMResult

        self.calls += 1
        if "curriculum designer" in system:
            text = json.dumps(
                {
                    "title": "Multi Lesson Course",
                    "description": "Several lessons so the cap can trip mid-run",
                    "modules": [
                        {
                            "title": "Module 1",
                            "lessons": [
                                {"title": f"Lesson {i}", "summary": "s"}
                                for i in range(self.lessons)
                            ],
                        }
                    ],
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
        return LLMResult(text=text, input_tokens=1000, output_tokens=500)


def test_hard_cap_stops_a_run_partway_not_only_at_the_start(client, monkeypatch):
    """Regression guard: the cap must be checked before EVERY call.

    If the check were hoisted into MeteredLLM.__init__ (once per run), this run would
    complete in full instead of aborting after the calls that fit under the cap.
    """
    from app import main, models
    from app.db import SessionLocal

    provider = _MultiLessonPaidProvider(lessons=4)
    monkeypatch.setattr(main, "get_provider", lambda: provider)

    baseline = client.get("/usage").json()["totals"]["estimated_cost_usd"]
    # One call costs 1000/1e6*5.00 + 500/1e6*25.00 = 0.0175 on claude-opus-5, so a
    # 0.02 headroom admits the outline plus one lesson, then blocks the rest.
    monkeypatch.setenv("STUDYFORGE_COST_LIMIT_USD", str(baseline + 0.02))

    session = SessionLocal()
    try:
        rows_before = session.query(models.LlmCall).count()
    finally:
        session.close()

    resp = client.post("/courses/generate", json={"text": "Partway cap test material."})
    assert resp.status_code == 402
    assert resp.json()["detail"]["error"] == "cost_limit_exceeded"

    # The run started (so the cap was not checked only up front) but did not finish
    # (so it was still checked on later calls). A full run would be 1 outline + 4 lessons.
    assert 0 < provider.calls < 5

    session = SessionLocal()
    try:
        rows_after = session.query(models.LlmCall).count()
    finally:
        session.close()
    # Calls made before the cap tripped are still recorded, so partial spend is not lost.
    assert rows_after == rows_before + provider.calls


def test_hard_cap_blocks_paid_provider_but_not_fake(client, stub_paid_provider, monkeypatch):
    baseline_total = client.get("/usage").json()["totals"]["estimated_cost_usd"]

    resp = client.post("/courses/generate", json={"text": "Cap test source material."})
    assert resp.status_code == 200
    after_one_run = client.get("/usage").json()["totals"]["estimated_cost_usd"]
    assert after_one_run > baseline_total

    limit = after_one_run - 0.0001
    monkeypatch.setenv("STUDYFORGE_COST_LIMIT_USD", str(limit))

    calls_before = stub_paid_provider.calls
    resp2 = client.post("/courses/generate", json={"text": "Cap test source material two."})
    assert resp2.status_code == 402
    detail = resp2.json()["detail"]
    assert detail["error"] == "cost_limit_exceeded"
    assert detail["message"] == "LLM spend limit reached"
    assert detail["limit_usd"] == limit
    assert detail["spent_usd"] == after_one_run
    # Blocked before the provider was ever called again.
    assert stub_paid_provider.calls == calls_before

    usage_check = client.get("/usage").json()
    assert usage_check["limit"]["configured"] is True
    assert usage_check["limit"]["limit_usd"] == limit
    assert usage_check["limit"]["reached"] is True

    # is_paid=False providers are never blocked, even with the cap still configured.
    monkeypatch.setattr("app.main.get_provider", lambda: FakeProvider())
    resp3 = client.post("/courses/generate", json={"text": "Fake provider still works fine."})
    assert resp3.status_code == 200
