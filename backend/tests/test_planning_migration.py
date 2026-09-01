"""What the deadline columns do to a database that already has courses in it.

This is the sibling of test_tutor_migration.py and it exists because of one structural
gap in that file: ITS BASE DATABASE IS EMPTY. It builds the base schema, runs init_db()
over it and compares, and every claim it makes is about shape. That is exactly right for
the failure it was written for, a new TABLE, and it is blind to the failure this feature
can have.

SQLite ACCEPTS `ALTER TABLE ... ADD COLUMN ... NOT NULL` against an EMPTY table and
REJECTS it against a table holding even one row. So a migration written with NOT NULL
passes test_tutor_migration.py completely, passes on a developer's scratch database, and
raises on every install that has ever been used. An empty fixture cannot see that class
of bug at all. THE BASE DATABASE HERE HAS ROWS IN IT, and that is the whole reason the
file is separate rather than three more tests over there.

This is also the first change in the project's history to need a migration at all.
create_all is checkfirst=True and cannot ALTER, so before app/db.py grew _ADDED_COLUMNS,
adding courses.deadline would have produced an install that BOOTS PERFECTLY and then
answers GET /courses with "no such column: courses.deadline", because every read through
the Course mapper emits every mapped column. The course list breaks, not the deadline
feature. test_the_course_list_still_works_on_an_upgraded_database names that symptom
directly rather than as a schema diff.

Five things are asserted here that test_tutor_migration.py does not assert:

  1. Pre-existing rows SURVIVE the upgrade and read back with deadline NULL.
  2. The course list query specifically works against the upgraded database.
  3. Upgrading TWICE is a no-op. Without this, an unconditional ALTER passes everything
     on the first run and raises "duplicate column name" on the second boot, which the
     developer who wrote it never sees.
  4. upgraded == fresh, which is what catches a DEFAULT '' on the ALTER: sqlite records
     dflt_value "''" where create_all records None, and the two schemas stop comparing
     equal for a reason nobody would guess from the failure message.
  5. A course written BEFORE the upgrade produces a working plan rather than an
     exception.
"""

import subprocess
import sys
import types
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session

# The revision this feature forked from, PINNED BY SHA, exactly as test_tutor_migration
# pins its own. d453f50 is the parent of the commit that first put `deadline` in
# models.py, so it denotes "the schema before study planning" permanently, rather than
# "whatever main happens to be", which stops meaning that the moment this branch lands.
#
# DO NOT "FIX" A FUTURE FAILURE BY MOVING THIS FORWARD. Advancing it past a schema change
# makes every comparison below trivially true and the file silently stops testing
# anything. test_the_base_revision_predates_the_deadline_columns is the guard against
# that and it names this constant when it fires.
BASE_COMMIT = "d453f50505a2e3fbd3171bde8f4deed1a6b194dc"

MODELS_PATH = "backend/app/models.py"

NEW_COLUMNS = {"deadline", "deadline_label"}


def _git(*args: str) -> subprocess.CompletedProcess:
    here = Path(__file__).resolve().parent
    return subprocess.run(
        ["git", "-C", str(here), *args], capture_output=True, text=True, check=False
    )


def _base_models_source() -> tuple[str, str]:
    """(ref, source) for models.py as it stood before this feature.

    SKIPS rather than passes when the commit is unreachable, which is what a shallow or
    partial clone gives. A skip says the comparison did not happen; falling back to the
    working tree would compare this branch against ITSELF and report that as a pass,
    which is the shape of failure this file exists to make impossible.
    """
    if _git("rev-parse", "--git-dir").returncode != 0:
        pytest.skip("not a git checkout, so there is no base revision to compare against")
    found = _git("show", f"{BASE_COMMIT}:{MODELS_PATH}")
    if found.returncode != 0:
        pytest.skip(
            f"base commit {BASE_COMMIT[:12]} is not in this clone (shallow or partial "
            f"checkout), so there is no base revision to compare against"
        )
    return BASE_COMMIT, found.stdout


def _base_metadata():
    """The MetaData models.py declared before this branch, on its own Base.

    Executed against a stand-in app.db module rather than imported, because models.py
    binds to the real app.db.Base, and registering a second copy of every table on that
    shared MetaData would raise "Table 'courses' is already defined" and, worse, would
    end up comparing this branch's metadata against itself.
    """
    ref, source = _base_models_source()

    class BaseRevisionBase(DeclarativeBase):
        pass

    shim = types.ModuleType("app.db")
    shim.Base = BaseRevisionBase
    saved = sys.modules.get("app.db")
    sys.modules["app.db"] = shim
    try:
        exec(  # noqa: S102
            compile(source, f"<{ref}:{MODELS_PATH}>", "exec"), {"__name__": "base_models"}
        )
    finally:
        if saved is None:
            del sys.modules["app.db"]
        else:
            sys.modules["app.db"] = saved
    return BaseRevisionBase.metadata


def _schema(engine) -> dict[str, list[tuple]]:
    """Every table's columns, in the same 5-tuple test_tutor_migration.py compares.

    Name, type, nullability, DEFAULT, and primary-key membership. The default is in here
    for a specific reason on this branch: an ALTER written with DEFAULT '' produces a
    column that is otherwise identical and still wrong, and dropping the field from this
    tuple would make the trap invisible.
    """
    inspector = inspect(engine)
    return {
        table: [
            (
                column["name"],
                str(column["type"]),
                bool(column["nullable"]),
                str(column.get("default")),
                bool(column.get("primary_key")),
            )
            for column in inspector.get_columns(table)
        ]
        for table in inspector.get_table_names()
    }


def _seed_base_rows(engine, metadata) -> None:
    """One course/module/lesson/quiz item/attempt chain, plus a settings row.

    Written with Core inserts against the BASE metadata, not through the current ORM
    models. That is forced rather than stylistic: the current mapper emits `deadline` on
    every insert, so seeding through it would fail against a database that does not have
    the column yet, which is the very state this fixture has to produce.

    Mirrors test_review_models._seed_pre_phase2_rows, whose shape is the closest thing
    this project has to a realistic legacy database.
    """
    tables = metadata.tables
    with engine.begin() as connection:
        course_id = connection.execute(
            tables["courses"].insert().values(title="Optimization", description="")
        ).inserted_primary_key[0]
        module_id = connection.execute(
            tables["modules"]
            .insert()
            .values(course_id=course_id, title="Module 1", position=0)
        ).inserted_primary_key[0]
        lesson_id = connection.execute(
            tables["lessons"]
            .insert()
            .values(
                module_id=module_id,
                title="Lesson A",
                position=0,
                content="# A",
                concepts=["gd"],
                completed_at=None,
            )
        ).inserted_primary_key[0]
        item_id = connection.execute(
            tables["quiz_items"]
            .insert()
            .values(
                lesson_id=lesson_id,
                question="Which way?",
                kind="short",
                options=[],
                answer="downhill",
                concept="gd",
            )
        ).inserted_primary_key[0]
        connection.execute(
            tables["attempts"]
            .insert()
            .values(
                quiz_item_id=item_id,
                lesson_id=lesson_id,
                concept_key="gd",
                concept_label="gd",
                submitted_answer="downhill",
                expected_answer="downhill",
                correct=True,
                attempt_no=1,
                source="lesson_quiz",
                grader="exact_ci",
            )
        )
        connection.execute(
            tables["app_settings"].insert().values(key="cost_alert_acked_usd", value="1.5")
        )


class Databases:
    """The three schemas, and the live engine behind the upgraded one."""

    def __init__(self, base, upgraded, fresh, upgraded_engine):
        self.base = base
        self.upgraded = upgraded
        self.fresh = fresh
        self.upgraded_engine = upgraded_engine


@pytest.fixture
def databases(tmp_path, monkeypatch):
    """A POPULATED base-revision database upgraded by this branch, plus a fresh one.

    The seeding is what distinguishes this fixture from test_tutor_migration.py's, and
    it is load-bearing rather than decorative: a NOT NULL variant of the ALTER in
    app/db.py raises HERE, during setup, and would pass over there forever.
    """
    from app import db as db_module

    existing = tmp_path / "existing.sqlite3"
    metadata = _base_metadata()
    base_engine = create_engine(f"sqlite:///{existing}")
    metadata.create_all(base_engine)
    _seed_base_rows(base_engine, metadata)
    base = _schema(base_engine)
    base_engine.dispose()

    upgraded_engine = create_engine(f"sqlite:///{existing}")
    monkeypatch.setattr(db_module, "engine", upgraded_engine)
    db_module.init_db()
    upgraded = _schema(upgraded_engine)

    fresh_engine = create_engine(f"sqlite:///{tmp_path / 'fresh.sqlite3'}")
    monkeypatch.setattr(db_module, "engine", fresh_engine)
    db_module.init_db()
    fresh = _schema(fresh_engine)
    fresh_engine.dispose()

    try:
        yield Databases(base, upgraded, fresh, upgraded_engine)
    finally:
        upgraded_engine.dispose()


def test_the_base_revision_predates_the_deadline_columns(databases):
    """The guard that stops this file from quietly becoming a no-op."""
    base_columns = {name for name, *_ in databases.base["courses"]}

    assert NEW_COLUMNS.isdisjoint(base_columns), (
        f"BASE_COMMIT ({BASE_COMMIT[:12]}) already has {sorted(NEW_COLUMNS & base_columns)} "
        f"on courses, so it does not predate this feature and every comparison in this "
        f"file is now trivially true. Point it back at the revision the feature forked "
        f"from rather than forward past the change it is supposed to measure."
    )


def test_the_base_database_actually_has_rows_in_courses(databases):
    """The premise of this whole file, asserted rather than assumed.

    If this fixture ever stops seeding, every test below silently weakens to what
    test_tutor_migration.py already covers, and the NOT NULL class of bug becomes
    invisible again with nothing going red to say so.
    """
    from app import models

    with Session(databases.upgraded_engine) as session:
        assert session.query(models.Course).count() == 1
        assert session.query(models.Module).count() == 1
        assert session.query(models.Lesson).count() == 1
        assert session.query(models.QuizItem).count() == 1
        assert session.query(models.Attempt).count() == 1


def test_the_upgrade_adds_the_deadline_columns_and_no_others(databases):
    upgraded_columns = {name for name, *_ in databases.upgraded["courses"]}
    base_columns = {name for name, *_ in databases.base["courses"]}

    assert NEW_COLUMNS <= upgraded_columns
    assert upgraded_columns - base_columns == NEW_COLUMNS
    assert not base_columns - upgraded_columns, "an ALTER must never drop a column"


def test_existing_rows_survive_the_upgrade_and_read_back_with_a_null_deadline(databases):
    """The failure an empty base database cannot see.

    A NOT NULL variant of the ALTER raises against a populated table, so this test could
    not even reach its assertions; that is the point. What it asserts once it gets there
    is that the rows are untouched and the new column reads NULL, which is the state a
    course that predates the feature must be in: no deadline, behaving exactly as it did.
    """
    from app import models

    with Session(databases.upgraded_engine) as session:
        course = session.query(models.Course).one()
        assert course.title == "Optimization"
        assert course.deadline is None
        assert course.deadline_label is None

        attempt = session.query(models.Attempt).one()
        assert attempt.submitted_answer == "downhill"
        assert attempt.correct is True
        assert attempt.attempt_no == 1

        setting = session.query(models.AppSetting).one()
        assert setting.value == "1.5"


def test_the_course_list_still_works_on_an_upgraded_database(databases):
    """THE SYMPTOM, named rather than described as a schema diff.

    The generic mapper loop below covers this case too, but not by name, and the name is
    the useful part. Without the migration step the app boots fine and then GET /courses
    raises "no such column: courses.deadline", because session.query(Course) emits every
    mapped column. What breaks is the COURSE LIST, not the deadline feature, and someone
    reading a future failure needs to see that connection immediately.
    """
    from app import models

    with Session(databases.upgraded_engine) as session:
        rows = (
            session.query(models.Course).order_by(models.Course.created_at.desc()).limit(1).all()
        )
        assert len(rows) == 1


def test_every_mapped_column_exists_in_an_upgraded_database(databases):
    """The same claim across every table, so a future column on any of them fails here."""
    from app.db import Base

    with Session(databases.upgraded_engine) as session:
        for mapper in Base.registry.mappers:
            session.query(mapper.class_).limit(1).all()


def test_an_upgraded_database_ends_up_identical_to_a_fresh_one(databases):
    """The comparison that catches the DEFAULT trap.

    ADD COLUMN with no default produces a schema byte-identical to what create_all
    builds. ADD COLUMN ... DEFAULT '' does not: sqlite records dflt_value "''" and
    create_all records None, so the two disagree on a field nobody would think to look
    at. Everything a query does still works, which is what makes it worth a test rather
    than a comment.
    """
    assert databases.upgraded == databases.fresh, (
        "an upgraded database and a fresh one disagree. Either a column was added to an "
        "existing table with no entry in _ADDED_COLUMNS in app/db.py, or an entry there "
        "does not reproduce what create_all builds (a DEFAULT clause is the usual cause)."
    )


def test_upgrading_twice_is_a_no_op(databases, monkeypatch):
    """The second boot, which is the one the developer who wrote the ALTER never sees.

    An unconditional ALTER passes every other test in this file on the first run and
    raises "duplicate column name: deadline" the next time the app starts. The inspector
    guard in _add_missing_columns is what makes this pass; remove it and this goes red
    while nothing else does.
    """
    from app import db as db_module

    monkeypatch.setattr(db_module, "engine", databases.upgraded_engine)
    db_module.init_db()
    db_module.init_db()

    assert _schema(databases.upgraded_engine) == databases.upgraded


def test_a_course_written_before_the_upgrade_gets_a_working_plan(databases):
    """The feature itself, exercised against a database that predates it.

    A pre-existing course has to reach the no-deadline shape rather than raising, and
    this is the path that actually proves it: planning.course_plan reads the course row,
    its lessons and their completed_at, all through mappers that now name two columns the
    original database was created without.

    The module function rather than the HTTP route, because the route's session comes
    from the process-wide SessionLocal and this database is a temporary file. The route
    adds a 404 lookup and nothing else; everything that could raise on an unmigrated
    database is inside this call.
    """
    from app import models, planning

    with Session(databases.upgraded_engine) as session:
        course = session.query(models.Course).one()
        plan = planning.course_plan(session, course)

    assert plan["status"] == "none"
    assert plan["deadline"] is None
    assert plan["deadline_label"] is None
    assert plan["required_per_week"] is None
    assert plan["reason"] == "no_deadline"
    assert plan["lessons_total"] == 1
    assert plan["lessons_remaining"] == 1


def test_the_deadline_columns_are_nullable_strings_with_no_server_default(databases):
    """The three properties the ALTER depends on, pinned so a later edit cannot drop one.

    Nullable, because SQLite rejects ADD COLUMN ... NOT NULL against a populated table.
    No default, because a DEFAULT clause breaks upgraded == fresh. VARCHAR, because a day
    the learner named is not an instant; see models.UnavailableDay.day, which the deadline
    columns were modelled on.
    """
    columns = {name: rest for name, *rest in databases.upgraded["courses"]}

    for name, expected_type in (("deadline", "VARCHAR(10)"), ("deadline_label", "VARCHAR(200)")):
        column_type, nullable, default, primary_key = columns[name]
        assert column_type == expected_type
        assert nullable is True
        assert default == "None"
        assert primary_key is False
