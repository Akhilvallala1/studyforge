"""Quiz attempt persistence: the append-only attempt history, the attempt_state
summary both quiz endpoints return, lesson completion round-tripping, and the
friendly copy that replaced raw exception text on generation failures."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app import models
from app.concepts import normalize_concept
from app.db import SessionLocal


def _make_lesson(concepts=("Gradient Descent", "Backpropagation")):
    """Insert a one-module course whose lesson has two short-answer quiz items.

    Returns (lesson_id, [item_id, ...]). Built directly rather than through the
    generation pipeline so the expected answers and concept labels are exact.
    """
    session = SessionLocal()
    try:
        course = models.Course(title="Optimization", description="")
        module = models.Module(title="Module 1", position=0)
        lesson = models.Lesson(
            title="Lesson A", position=0, content="# Lesson A", concepts=list(concepts)
        )
        lesson.quiz_items.append(
            models.QuizItem(
                question="Which direction does gradient descent step in?",
                kind="short",
                options=[],
                answer="downhill",
                concept=concepts[0],
            )
        )
        lesson.quiz_items.append(
            models.QuizItem(
                question="What rule does backprop apply?",
                kind="short",
                options=[],
                answer="chain rule",
                concept=concepts[1],
            )
        )
        module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.commit()
        return lesson.id, [q.id for q in lesson.quiz_items]
    finally:
        session.close()


def _rows_for_item(item_id):
    session = SessionLocal()
    try:
        return (
            session.query(models.Attempt)
            .filter(models.Attempt.quiz_item_id == item_id)
            .order_by(models.Attempt.attempt_no)
            .all()
        )
    finally:
        session.close()


def _backdate(attempt_id, seconds):
    """Move one attempt's created_at into the past, to step outside a time window."""
    session = SessionLocal()
    try:
        row = session.get(models.Attempt, attempt_id)
        row.created_at = datetime.now(UTC) - timedelta(seconds=seconds)
        session.commit()
    finally:
        session.close()


@pytest.fixture
def lesson(client):
    """Takes the client fixture so init_db() has run: without it this file fails
    on its own because the attempts table does not exist yet."""
    return _make_lesson()


def test_normalize_concept_folds_case_spacing_and_edge_punctuation():
    key = normalize_concept("Gradient Descent")
    assert key == "gradient descent"
    assert normalize_concept(" gradient  descent ") == key
    assert normalize_concept("gradient descent.") == key
    assert normalize_concept("(Gradient Descent)") == key
    assert normalize_concept("") == ""
    assert normalize_concept(None) == ""


class TestRecording:
    def test_first_attempt_snapshots_the_item(self, client, lesson):
        lesson_id, (item_id, _) = lesson
        resp = client.post(f"/quiz/{item_id}/answer", json={"answer": "downhill"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["correct"] is True
        assert body["expected"] == "downhill"
        assert body["attempt_no"] == 1

        rows = _rows_for_item(item_id)
        assert len(rows) == 1
        row = rows[0]
        assert row.id == body["attempt_id"]
        assert row.attempt_no == 1
        assert row.lesson_id == lesson_id
        assert row.concept_key == "gradient descent"
        assert row.concept_label == "Gradient Descent"
        assert row.expected_answer == "downhill"
        assert row.submitted_answer == "downhill"
        assert row.correct is True
        assert row.source == "lesson_quiz"
        assert row.grader == "exact_ci"
        assert row.elapsed_ms is None

    def test_concept_key_is_normalized_from_a_messy_label(self, client):
        _, (item_id, _) = _make_lesson(concepts=("  Gradient   DESCENT. ", "x"))
        client.post(f"/quiz/{item_id}/answer", json={"answer": "downhill"})
        assert _rows_for_item(item_id)[0].concept_key == "gradient descent"

    def test_wrong_then_right_keeps_both_rows(self, client, lesson):
        _, (item_id, _) = lesson
        first = client.post(f"/quiz/{item_id}/answer", json={"answer": "uphill"}).json()
        assert first["correct"] is False
        assert first["attempt_no"] == 1

        second = client.post(f"/quiz/{item_id}/answer", json={"answer": "downhill"}).json()
        assert second["correct"] is True
        assert second["attempt_no"] == 2

        state = second["attempt_state"]
        assert state["attempts"] == 2
        # The mastery signal: right on the second try is not the same as right away.
        assert state["first_attempt_correct"] is False
        assert state["ever_correct"] is True
        assert state["latest"]["answer"] == "downhill"
        assert state["latest"]["correct"] is True

        rows = _rows_for_item(item_id)
        assert [r.attempt_no for r in rows] == [1, 2]
        assert [r.submitted_answer for r in rows] == ["uphill", "downhill"]

    def test_right_first_try(self, client, lesson):
        _, (item_id, _) = lesson
        state = client.post(
            f"/quiz/{item_id}/answer", json={"answer": "DOWNHILL"}
        ).json()["attempt_state"]
        assert state["attempts"] == 1
        assert state["first_attempt_correct"] is True
        assert state["ever_correct"] is True

    def test_attempts_are_never_rewritten(self, client, lesson):
        _, (item_id, _) = lesson
        client.post(f"/quiz/{item_id}/answer", json={"answer": "uphill"})
        first_id = _rows_for_item(item_id)[0].id
        client.post(f"/quiz/{item_id}/answer", json={"answer": "downhill"})
        rows = _rows_for_item(item_id)
        assert rows[0].id == first_id
        assert rows[0].submitted_answer == "uphill"  # history, not last-write-wins

    def test_unknown_item_is_404_and_writes_nothing(self, client, lesson):
        assert client.post("/quiz/999999/answer", json={"answer": "x"}).status_code == 404

    @pytest.mark.parametrize("answer", ["", "   ", "\n\t "])
    def test_empty_answer_is_rejected_without_recording(self, client, lesson, answer):
        _, (item_id, _) = lesson
        resp = client.post(f"/quiz/{item_id}/answer", json={"answer": answer})
        assert resp.status_code == 400
        assert _rows_for_item(item_id) == []


class TestDoubleSubmit:
    def test_identical_answers_within_the_window_record_once(self, client, lesson):
        _, (item_id, _) = lesson
        first = client.post(f"/quiz/{item_id}/answer", json={"answer": "downhill"}).json()
        second = client.post(f"/quiz/{item_id}/answer", json={"answer": "downhill"}).json()

        assert second["attempt_id"] == first["attempt_id"]
        assert second["attempt_no"] == 1
        assert second["attempt_state"]["attempts"] == 1
        assert len(_rows_for_item(item_id)) == 1

    def test_a_different_answer_within_the_window_still_records(self, client, lesson):
        _, (item_id, _) = lesson
        client.post(f"/quiz/{item_id}/answer", json={"answer": "uphill"})
        second = client.post(f"/quiz/{item_id}/answer", json={"answer": "downhill"}).json()
        assert second["attempt_no"] == 2
        assert len(_rows_for_item(item_id)) == 2

    def test_the_same_answer_later_is_a_real_second_attempt(self, client, lesson):
        _, (item_id, _) = lesson
        first = client.post(f"/quiz/{item_id}/answer", json={"answer": "uphill"}).json()
        _backdate(first["attempt_id"], seconds=10)
        second = client.post(f"/quiz/{item_id}/answer", json={"answer": "uphill"}).json()
        assert second["attempt_id"] != first["attempt_id"]
        assert second["attempt_no"] == 2


    def test_an_unresolvable_collision_returns_409(self, client, lesson):
        """The unique constraint must fail loudly rather than silently overwrite.

        attempt_no is count(*) + 1, so a history with a gap (rows 1 and 3) makes
        every retry compute 3 and collide. A concurrent double-submit hits the same
        constraint; this reproduces it without threads.
        """
        _, (item_id, _) = lesson
        session = SessionLocal()
        try:
            for attempt_no in (1, 3):
                session.add(
                    models.Attempt(
                        quiz_item_id=item_id,
                        lesson_id=session.get(models.QuizItem, item_id).lesson_id,
                        submitted_answer=f"prior {attempt_no}",
                        expected_answer="downhill",
                        correct=False,
                        attempt_no=attempt_no,
                    )
                )
            session.commit()
        finally:
            session.close()

        resp = client.post(f"/quiz/{item_id}/answer", json={"answer": "downhill"})
        assert resp.status_code == 409
        assert len(_rows_for_item(item_id)) == 2  # nothing half-written


class TestElapsedMs:
    @pytest.mark.parametrize(
        ("answer", "sent", "stored"),
        [
            ("uphill", None, None),
            ("sideways", 1500, 1500),
            ("downhill", -5, None),
            ("nowhere", 999_999_999, None),
        ],
    )
    def test_bad_timings_are_dropped_not_rejected(self, client, lesson, answer, sent, stored):
        _, (item_id, _) = lesson
        resp = client.post(f"/quiz/{item_id}/answer", json={"answer": answer, "elapsed_ms": sent})
        assert resp.status_code == 200
        assert _rows_for_item(item_id)[-1].elapsed_ms == stored


class TestLessonView:
    def test_restores_answers_and_leaves_untouched_items_null(self, client, lesson):
        lesson_id, (answered_id, untouched_id) = lesson
        client.post(f"/quiz/{answered_id}/answer", json={"answer": "uphill"})

        body = client.get(f"/lessons/{lesson_id}").json()
        by_id = {q["id"]: q for q in body["quiz"]}

        answered = by_id[answered_id]["attempt_state"]
        assert answered["attempts"] == 1
        assert answered["latest"]["answer"] == "uphill"
        assert answered["latest"]["correct"] is False
        assert answered["first_attempt_correct"] is False
        assert answered["ever_correct"] is False

        untouched = by_id[untouched_id]["attempt_state"]
        assert untouched == {
            "attempts": 0,
            "first_attempt_correct": None,
            "ever_correct": False,
            "latest": None,
        }

    def test_answer_key_is_hidden_until_the_learner_has_answered(self, client, lesson):
        lesson_id, (item_id, untouched_id) = lesson
        before = client.get(f"/lessons/{lesson_id}").json()
        assert "downhill" not in str(before["quiz"])
        for question in before["quiz"]:
            assert "answer" not in question
            assert question["attempt_state"]["latest"] is None

        client.post(f"/quiz/{item_id}/answer", json={"answer": "uphill"})
        after = client.get(f"/lessons/{lesson_id}").json()
        by_id = {q["id"]: q for q in after["quiz"]}
        # Revealed only inside latest, and only for the item that was attempted.
        assert by_id[item_id]["attempt_state"]["latest"]["expected"] == "downhill"
        assert by_id[untouched_id]["attempt_state"]["latest"] is None
        assert "answer" not in by_id[item_id]

    def test_quiz_progress_counts(self, client, lesson):
        lesson_id, (first_id, second_id) = lesson
        progress = client.get(f"/lessons/{lesson_id}").json()["quiz_progress"]
        assert progress == {"items": 2, "answered": 0, "correct": 0, "first_try_correct": 0}

        client.post(f"/quiz/{first_id}/answer", json={"answer": "uphill"})
        client.post(f"/quiz/{first_id}/answer", json={"answer": "downhill"})
        client.post(f"/quiz/{second_id}/answer", json={"answer": "chain rule"})

        progress = client.get(f"/lessons/{lesson_id}").json()["quiz_progress"]
        assert progress == {"items": 2, "answered": 2, "correct": 2, "first_try_correct": 1}

    def test_created_at_carries_a_utc_offset(self, client, lesson):
        lesson_id, (item_id, _) = lesson
        client.post(f"/quiz/{item_id}/answer", json={"answer": "downhill"})
        stamps = [
            client.get(f"/lessons/{lesson_id}")
            .json()["quiz"][0]["attempt_state"]["latest"]["created_at"],
            client.get(f"/lessons/{lesson_id}/attempts").json()["attempts"][0]["created_at"],
            client.post(f"/lessons/{lesson_id}/complete").json()["completed_at"],
        ]
        for stamp in stamps:
            parsed = datetime.fromisoformat(stamp)
            assert parsed.tzinfo is not None, "timestamps must be timezone-aware"
            assert parsed.utcoffset() == timedelta(0)


class TestAttemptHistoryEndpoint:
    def test_returns_the_lesson_history_oldest_first(self, client, lesson):
        lesson_id, (first_id, second_id) = lesson
        client.post(f"/quiz/{first_id}/answer", json={"answer": "uphill"})
        client.post(f"/quiz/{first_id}/answer", json={"answer": "downhill"})
        client.post(f"/quiz/{second_id}/answer", json={"answer": "chain rule"})

        body = client.get(f"/lessons/{lesson_id}/attempts").json()
        assert body["lesson_id"] == lesson_id
        rows = body["attempts"]
        assert len(rows) == 3
        assert [r["submitted_answer"] for r in rows] == ["uphill", "downhill", "chain rule"]
        assert [datetime.fromisoformat(r["created_at"]) for r in rows] == sorted(
            datetime.fromisoformat(r["created_at"]) for r in rows
        )
        assert rows[0]["concept_key"] == "gradient descent"
        assert rows[0]["grader"] == "exact_ci"

    def test_unknown_lesson_is_404(self, client):
        assert client.get("/lessons/999999/attempts").status_code == 404


class TestCompletion:
    def test_complete_uncomplete_round_trip_leaves_attempts_alone(self, client, lesson):
        lesson_id, (item_id, _) = lesson
        client.post(f"/quiz/{item_id}/answer", json={"answer": "downhill"})

        done = client.post(f"/lessons/{lesson_id}/complete").json()
        assert done["completed"] is True
        assert done["completed_at"] is not None

        reopened = client.delete(f"/lessons/{lesson_id}/complete").json()
        assert reopened == {"id": lesson_id, "completed": False, "completed_at": None}

        body = client.get(f"/lessons/{lesson_id}").json()
        assert body["completed"] is False
        assert body["quiz"][0]["attempt_state"]["attempts"] == 1
        assert len(_rows_for_item(item_id)) == 1

    def test_repeat_complete_does_not_move_the_timestamp(self, client, lesson):
        lesson_id, _ = lesson
        first = client.post(f"/lessons/{lesson_id}/complete").json()
        second = client.post(f"/lessons/{lesson_id}/complete").json()
        assert second == first

    def test_uncomplete_is_idempotent(self, client, lesson):
        lesson_id, _ = lesson
        first = client.delete(f"/lessons/{lesson_id}/complete")
        second = client.delete(f"/lessons/{lesson_id}/complete")
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()

    def test_unknown_lesson_is_404(self, client):
        assert client.post("/lessons/999999/complete").status_code == 404
        assert client.delete("/lessons/999999/complete").status_code == 404


class TestFriendlyGenerationErrors:
    def test_unreachable_url_does_not_leak_the_exception(self, client, monkeypatch):
        def refuse(url):
            raise httpx.ConnectError(
                "[WinError 10061] No connection could be made because the target "
                "machine actively refused it"
            )

        monkeypatch.setattr("app.ingest.extract_url", refuse)
        resp = client.post("/courses/generate", json={"url": "http://localhost:1/nope"})
        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert detail == (
            "Could not fetch that URL. Check the address and that the page is reachable."
        )
        assert "WinError" not in detail
        assert "refused" not in detail

    def test_unreadable_pdf_gets_pdf_copy(self, client):
        resp = client.post(
            "/courses/generate/pdf",
            files={"file": ("broken.pdf", b"not a pdf at all", "application/pdf")},
        )
        assert resp.status_code == 502
        assert resp.json()["detail"] == (
            "Could not read that PDF. It may be scanned images or corrupted."
        )

    def test_provider_connection_failure_gets_model_copy(self, client, monkeypatch):
        class Unreachable:
            name = "ollama"
            model = "llama3.1"
            is_paid = False

            def generate(self, system, prompt, max_tokens=64000):
                raise httpx.ConnectError("[WinError 10061] target machine actively refused it")

        monkeypatch.setattr("app.main.get_provider", lambda: Unreachable())
        resp = client.post("/courses/generate", json={"text": "Some source material here."})
        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert detail == (
            "The model could not generate a course from this material. "
            "Try again, or try shorter material."
        )
        assert "WinError" not in detail

    def test_unparseable_model_output_gets_model_copy(self, client, monkeypatch):
        class Babbling:
            name = "fake"
            model = "fake"
            is_paid = False

            def generate(self, system, prompt, max_tokens=64000):
                from app.llm.base import LLMResult

                return LLMResult(text="I am not JSON", input_tokens=1, output_tokens=1)

        monkeypatch.setattr("app.main.get_provider", lambda: Babbling())
        resp = client.post("/courses/generate", json={"text": "Some source material here."})
        assert resp.status_code == 502
        assert resp.json()["detail"].startswith("The model could not generate a course")

    def test_unclassified_failure_gets_generic_copy(self, client, failing_provider):
        resp = client.post("/courses/generate", json={"text": "Some source material here."})
        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert detail == "Course generation failed. Check the server logs for details."
        assert "provider exploded" not in detail
