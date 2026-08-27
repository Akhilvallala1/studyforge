"""The four Phase 2 scheduling tables, and the guarantee that adding them does not
disturb a database that predates them.

There is no migration tool in this project: init_db() is create_all(), which creates
what is missing and leaves what exists alone. That is fine for adding tables and
catastrophic for changing one, so the second test here is the guard rail. It builds a
database with only the pre-Phase-2 tables, fills it, runs init_db(), and asserts the
attempts table came out the other side byte-identical with its rows intact.
"""

import os
import tempfile

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app import models
from app.db import Base, init_db

PRE_PHASE2_TABLES = (
    "courses",
    "modules",
    "lessons",
    "quiz_items",
    "attempts",
    "llm_calls",
    "app_settings",
)
PHASE2_TABLES = ("review_cards", "review_logs", "unavailable_days", "remediation_notes")


def _table_info(engine, table):
    with engine.connect() as conn:
        return conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()


def _seed_pre_phase2_rows(engine):
    """One course/module/lesson/quiz item/attempt chain, plus a settings row."""
    session = sessionmaker(bind=engine)()
    try:
        course = models.Course(title="Optimization", description="")
        module = models.Module(title="Module 1", position=0)
        lesson = models.Lesson(title="Lesson A", position=0, content="# A", concepts=["gd"])
        lesson.quiz_items.append(
            models.QuizItem(
                question="Which way?", kind="short", options=[], answer="downhill", concept="gd"
            )
        )
        module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.add(models.AppSetting(key="cost_alert_acked_usd", value="1.5"))
        session.commit()

        session.add(
            models.Attempt(
                quiz_item_id=lesson.quiz_items[0].id,
                lesson_id=lesson.id,
                concept_key="gd",
                concept_label="gd",
                submitted_answer="downhill",
                expected_answer="downhill",
                correct=True,
                attempt_no=1,
            )
        )
        session.commit()
    finally:
        session.close()


@pytest.fixture
def legacy_engine(monkeypatch):
    """A database containing only the tables that existed before Phase 2."""
    path = os.path.join(tempfile.mkdtemp(), "legacy.sqlite3")
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(
        engine, tables=[Base.metadata.tables[name] for name in PRE_PHASE2_TABLES]
    )
    # init_db() creates against the module-level engine, so point that at this one
    # rather than reimplementing what init_db does and testing the reimplementation.
    monkeypatch.setattr("app.db.engine", engine)
    yield engine
    engine.dispose()


def test_fresh_init_creates_every_phase2_table():
    init_db()
    from app.db import engine

    existing = set(inspect(engine).get_table_names())
    for table in PHASE2_TABLES:
        assert table in existing


def test_phase2_columns_are_present():
    from app.db import engine

    init_db()
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("review_cards")}
    assert {
        "concept_key",
        "concept_label",
        "state",
        "stability",
        "difficulty",
        "due",
        "last_review",
        "reps",
        "lapses",
        "step",
        "fsrs_v",
        "weights_hash",
        "created_at",
    } <= columns

    log_columns = {c["name"] for c in inspector.get_columns("review_logs")}
    assert {
        "card_id",
        "reviewed_at",
        "rating",
        "suggested_rating",
        "rating_source",
        "rating_v",
        "state_before",
        "stability_before",
        "difficulty_before",
        "elapsed_days",
        "state_after",
        "stability_after",
        "difficulty_after",
        "scheduled_days",
        "due_after",
        "attempt_ids",
        "items_correct",
        "items_total",
        "duration_ms",
        "fsrs_v",
        "weights_hash",
    } <= log_columns


def test_indexes_exist():
    from app.db import engine

    init_db()
    inspector = inspect(engine)
    card_indexes = {i["name"] for i in inspector.get_indexes("review_cards")}
    assert {"ix_review_cards_due", "ix_review_cards_state"} <= card_indexes
    log_indexes = {i["name"] for i in inspector.get_indexes("review_logs")}
    assert {"ix_review_logs_card_time", "ix_review_logs_time"} <= log_indexes
    note_indexes = {i["name"] for i in inspector.get_indexes("remediation_notes")}
    assert "ix_remediation_notes_card_created" in note_indexes


def test_init_db_on_a_pre_phase2_database_adds_tables_without_touching_attempts(legacy_engine):
    _seed_pre_phase2_rows(legacy_engine)

    before_schema = _table_info(legacy_engine, "attempts")
    session = sessionmaker(bind=legacy_engine)()
    try:
        before_rows = [
            (a.id, a.quiz_item_id, a.attempt_no, a.submitted_answer, a.correct)
            for a in session.query(models.Attempt).order_by(models.Attempt.id).all()
        ]
    finally:
        session.close()
    assert before_rows, "the fixture must actually have written an attempt"
    assert set(PHASE2_TABLES).isdisjoint(inspect(legacy_engine).get_table_names())

    init_db()

    existing = set(inspect(legacy_engine).get_table_names())
    for table in PHASE2_TABLES:
        assert table in existing

    assert _table_info(legacy_engine, "attempts") == before_schema

    session = sessionmaker(bind=legacy_engine)()
    try:
        after_rows = [
            (a.id, a.quiz_item_id, a.attempt_no, a.submitted_answer, a.correct)
            for a in session.query(models.Attempt).order_by(models.Attempt.id).all()
        ]
    finally:
        session.close()
    assert after_rows == before_rows


def test_init_db_is_idempotent_on_a_pre_phase2_database(legacy_engine):
    """A second start must be a no-op, not an error and not a rewrite."""
    _seed_pre_phase2_rows(legacy_engine)
    init_db()
    snapshot = {t: _table_info(legacy_engine, t) for t in PRE_PHASE2_TABLES + PHASE2_TABLES}
    init_db()
    assert {t: _table_info(legacy_engine, t) for t in snapshot} == snapshot


def test_concept_key_is_unique(legacy_engine):
    """Two courses teaching the same concept share one card on purpose: the learner
    has one memory of it, and a second card would review it twice as often while
    reporting mastery separately for each."""
    from sqlalchemy.exc import IntegrityError

    init_db()
    session = sessionmaker(bind=legacy_engine)()
    try:
        session.add(models.ReviewCard(concept_key="gradient descent", concept_label="Gradient"))
        session.commit()
        session.add(
            models.ReviewCard(concept_key="gradient descent", concept_label="Gradient Descent")
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.close()


def test_unavailable_day_is_unique(legacy_engine):
    from sqlalchemy.exc import IntegrityError

    init_db()
    session = sessionmaker(bind=legacy_engine)()
    try:
        session.add(models.UnavailableDay(day="2026-09-14", note="travel"))
        session.commit()
        session.add(models.UnavailableDay(day="2026-09-14"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.close()


def test_a_new_card_stores_null_stability_and_difficulty(legacy_engine):
    """Both NULL exactly while state is "new". One set and the other not is a
    corrupted row that the scheduler cannot schedule from."""
    init_db()
    session = sessionmaker(bind=legacy_engine)()
    try:
        session.add(models.ReviewCard(concept_key="recursion", concept_label="Recursion"))
        session.commit()
        card = session.query(models.ReviewCard).filter_by(concept_key="recursion").one()
        assert card.state == "new"
        assert card.stability is None
        assert card.difficulty is None
        assert card.reps == 0
        assert card.lapses == 0
        assert card.step == 0
        assert card.fsrs_v == "fsrs6"
        assert card.created_at is not None
    finally:
        session.close()


def test_review_log_round_trips_a_full_row(legacy_engine):
    init_db()
    session = sessionmaker(bind=legacy_engine)()
    try:
        card = models.ReviewCard(concept_key="backprop", concept_label="Backpropagation")
        session.add(card)
        session.commit()
        session.add(
            models.ReviewLog(
                card_id=card.id,
                rating=3,
                suggested_rating=4,
                rating_source="learner",
                rating_v="v1",
                state_before="review",
                stability_before=2.3065,
                difficulty_before=2.1181,
                elapsed_days=2.0,
                state_after="review",
                stability_after=10.9643,
                difficulty_after=2.1112,
                scheduled_days=11,
                attempt_ids=[7, 8],
                items_correct=2,
                items_total=2,
                duration_ms=4200,
                weights_hash="abc123",
            )
        )
        session.commit()

        row = session.query(models.ReviewLog).one()
        assert row.attempt_ids == [7, 8]
        assert row.suggested_rating == 4 and row.rating == 3
        assert row.rating_source == "learner"
        assert row.stability_before == 2.3065
        assert row.created_at is not None
    finally:
        session.close()


def test_remediation_note_defaults(legacy_engine):
    init_db()
    session = sessionmaker(bind=legacy_engine)()
    try:
        card = models.ReviewCard(concept_key="big-o", concept_label="Big O")
        session.add(card)
        session.commit()
        session.add(
            models.RemediationNote(
                card_id=card.id,
                concept_key="big-o",
                concept_label="Big O",
                content="Think of it as growth rate, not runtime.",
                model="claude-opus-5",
                run_id="deadbeef",
                triggered_by=[1, 2, 3],
            )
        )
        session.commit()
        note = session.query(models.RemediationNote).one()
        assert note.status == "active"
        assert note.source == "llm"
        assert note.cleared_at is None
        assert note.cooldown_until is None
        assert note.triggered_by == [1, 2, 3]
    finally:
        session.close()
