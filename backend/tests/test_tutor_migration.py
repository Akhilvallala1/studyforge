"""What this branch does to a database that already exists.

The rest of the suite cannot answer this. conftest points STUDYFORGE_DB at a fresh temp
file, so every other test proves only the fresh-install path, and a fresh install is
exactly the case that cannot fail: init_db() creates whatever is missing.

The failure this file exists to catch is the asymmetric one. create_all CANNOT ALTER a
table, so a new column added to courses, attempts, review_cards or any other existing
table produces a fresh install that works perfectly and an upgraded install that raises
"no such column" on the first query touching it. That is worse than a database that
refuses to open, because it starts fine and fails later, in front of the learner.

So three schemas are built and compared: the BASE one from the metadata models.py
declared at a pinned commit, the UPGRADED one that is the base with this branch's
init_db() run over it, and the FRESH one this branch creates from nothing.

Note carefully which comparison carries the weight. Comparing upgraded against base is
nearly worthless on its own: create_all skips a table it already found, so an existing
table is byte-identical afterwards NO MATTER WHAT the models say, and a column added to
attempts sails straight through. The claim with teeth is UPGRADED == FRESH, because that
is the one an added column breaks, and test_every_mapped_column_exists_in_an_upgraded
_database states the same thing as the symptom the learner would actually see.

WHAT THIS FILE ASSERTS NOW, restated after study planning added courses.deadline.
It used to assert that no existing table ever changes shape, which was the correct
reading while init_db() was create_all() alone and an ALTER was simply unavailable.
init_db() now runs a migration step after create_all (ADDED_COLUMNS in app/db.py), so an
existing table CAN change shape, and the invariant is one step weaker and considerably
more useful: AN ALTER MUST BE ACCOMPANIED BY A MIGRATION STEP, AND THIS FILE PROVES THE
STEP RAN. See test_no_existing_table_gains_or_loses_a_column for what was given up.

THREE RULES FOR WHOEVER CHANGES THE SCHEMA NEXT. Each one is self-maintaining, which is
the only kind of rule that survives in a test file nobody opens for six months.

  1. APPEND A PIN AT YOUR FORK POINT. NEVER MOVE ONE. BASE_COMMITS is a tuple and every
     comparison below runs once per entry. A pin denotes "the schema before one specific
     feature", which is a claim about a fixed revision, not about whatever main happens
     to be today. Advancing one past a schema change makes every comparison trivially
     true and the file silently stops testing anything, which is worse in both
     directions than the red it replaced.

     You do not always need a new pin. 797e50f covers every table older than the tutor,
     d453f50 covers tutor_messages, and only a column on a table introduced AFTER the
     newest pin needs its own. Study planning's columns are on `courses`, which exists
     at both pins, so it added no pin: it is covered twice over.

     Which pin covers your change is not a detail. A column on a table that POSTDATES
     every pin is INVISIBLE here: _base_metadata never declares that table, create_all
     builds it whole in the upgraded database, and it compares equal to fresh no matter
     what the models say. That is precisely the case a new pin exists to close.

  2. SEED THE TABLE YOU ALTER. test_every_altered_table_is_seeded enforces it and will
     name your table if you forget. The reason is in that test's docstring and it is the
     single most valuable property in this file.

  3. DO NOT LOOSEN _schema() TO MAKE A COMPARISON PASS. It is what enforces, for free
     and per column, that an ALTER's DDL reflects identically to what create_all emits.
"""

import subprocess
import sys
import types
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session

from app.db import ADDED_COLUMNS

# The revisions this file measures from, PINNED BY SHA rather than named by branch.
#
# This was a single BASE_COMMIT reading ("origin/main", "main"), and that was correct for
# exactly as long as the tutor branch was unmerged. The moment it landed, origin/main
# became a commit that already had tutor_messages, so the base stopped meaning "the
# schema before this feature" and started meaning "the schema including it". Nothing in
# the tree caused that and no change to the models could fix it: the same commit passed
# an hour before the merge and failed afterwards, untouched. A branch name cannot express
# what this file needs.
#
#   797e50f is aa760df^, the parent of the commit that first put TutorMessage in
#           models.py. It covers every table older than the tutor.
#   d453f50 is c296ecd^, the parent of the commit that first put `deadline` on Course.
#           It is the only pin at which tutor_messages exists in the base, so it is the
#           only one that can see a column added to that table.
#
# APPEND ONE AT YOUR FORK POINT; NEVER MOVE ONE. See rule 1 in the module docstring.
BASE_COMMITS = (
    "797e50fe684e4a0c5062672aab8ae730ae20477c",
    "d453f50505a2e3fbd3171bde8f4deed1a6b194dc",
)

TUTOR_BASE = BASE_COMMITS[0]

MODELS_PATH = "backend/app/models.py"

NEW_TABLE = "tutor_messages"
NEW_INDEXES = {"ix_tutor_messages_concept_created", "ix_tutor_messages_created"}


def _git(*args: str) -> subprocess.CompletedProcess:
    here = Path(__file__).resolve().parent
    return subprocess.run(
        ["git", "-C", str(here), *args], capture_output=True, text=True, check=False
    )


def _base_models_source(ref: str) -> str:
    """models.py as it stood at `ref`.

    Skips rather than passes when the commit is unreachable, which is what a shallow or
    partial clone gives. A skip says the comparison did not happen; falling back to the
    working tree would compare this branch against ITSELF and report that as a pass,
    which is the shape of failure this whole file exists to make impossible.
    """
    if _git("rev-parse", "--git-dir").returncode != 0:
        pytest.skip("not a git checkout, so there is no base revision to compare against")
    found = _git("show", f"{ref}:{MODELS_PATH}")
    if found.returncode != 0:
        pytest.skip(
            f"base commit {ref[:12]} is not in this clone (shallow or partial "
            f"checkout), so there is no base revision to compare against"
        )
    return found.stdout


def base_metadata(ref: str):
    """The MetaData models.py declared at `ref`, on its own Base.

    Executed against a stand-in app.db module rather than imported, because models.py
    binds to the real app.db.Base, and registering a second copy of every table on that
    shared MetaData would raise "Table 'courses' is already defined" and, worse, would
    end up comparing this branch's metadata against itself.

    Public, unlike its neighbours, because backend/tests/test_planning.py builds a
    pre-upgrade database with it to test the BEHAVIOUR of a course row that predates the
    deadline columns. One definition of "the schema at a pin" for both files.
    """

    class BaseRevisionBase(DeclarativeBase):
        pass

    shim = types.ModuleType("app.db")
    shim.Base = BaseRevisionBase
    saved = sys.modules.get("app.db")
    sys.modules["app.db"] = shim
    try:
        # exec, deliberately: the source is this repository's own models.py at a commit
        # git already has, and importing it normally would bind it to the live
        # app.db.Base and compare this branch against itself.
        exec(  # noqa: S102
            compile(_base_models_source(ref), f"<{ref}:{MODELS_PATH}>", "exec"),
            {"__name__": "base_models"},
        )
    finally:
        if saved is None:
            del sys.modules["app.db"]
        else:
            sys.modules["app.db"] = saved
    return BaseRevisionBase.metadata


# --------------------------------------------------------------------------
# Seeding the base
# --------------------------------------------------------------------------
#
# WHY THESE ARE CORE INSERTS AND NOT ORM CALLS, which is the thing that looks like an
# awkward long way round and is not. base_metadata() DISCARDS the base revision's mapped
# classes on purpose: they are exec'd into a throwaway namespace so they cannot collide
# with the live app.db.Base, so there is simply nothing to import here. Core inserts
# against the base MetaData are also the only form that survives an OLD schema, because
# they name the columns that revision actually had rather than the attributes today's
# models happen to declare. Rewriting these as models.Course(...) would work until the
# first pin whose schema no longer matches the current class, and then it would break IN
# THE DIRECTION THAT MAKES THIS FILE PASS, which is the failure mode the whole file
# exists to prevent. Leave them as Core inserts.


def _seed_course_chain(connection, tables) -> None:
    """One course/module/lesson/quiz item/attempt chain, plus a settings row.

    Mirrors test_review_models.py::_seed_pre_phase2_rows, whose shape is the closest
    thing this project has to a realistic legacy database.
    """
    course_id = connection.execute(
        tables["courses"].insert().values(title="Optimization", description="")
    ).inserted_primary_key[0]
    module_id = connection.execute(
        tables["modules"].insert().values(course_id=course_id, title="Module 1", position=0)
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
        )
    )
    connection.execute(
        tables["app_settings"].insert().values(key="cost_alert_acked_usd", value="1.5")
    )


def _seed_tutor_message(connection, tables) -> None:
    """One learner turn, so a base that has tutor_messages has a ROW in it.

    Nothing in ADDED_COLUMNS alters this table yet. It is seeded anyway so that the entry
    work-it-out mode is going to append stays the ONE LINE app/db.py promises: a column
    on an unseeded table would otherwise fail test_every_altered_table_is_seeded and turn
    a one-line change into two.
    """
    connection.execute(
        tables["tutor_messages"]
        .insert()
        .values(concept_key="gd", concept_label="gd", role="learner", content="Why downhill?")
    )


# Tables this file knows how to put a row in. Every seeder whose table exists in a given
# base is run, so the base is as realistic as that revision allows.
SEEDERS = {
    "courses": _seed_course_chain,
    NEW_TABLE: _seed_tutor_message,
}

# Tables _seed_course_chain fills, which is more than the one it is keyed by.
_CHAIN_TABLES = frozenset(
    {"courses", "modules", "lessons", "quiz_items", "attempts", "app_settings"}
)


def seed_base_rows(engine, metadata) -> None:
    """Fill a base database with a row in every table this file has a seeder for.

    Public for the same reason base_metadata is: test_planning.py builds a pre-upgrade
    database and needs it populated for the read-back to mean anything.
    """
    with engine.begin() as connection:
        for table, seeder in SEEDERS.items():
            if table in metadata.tables:
                seeder(connection, metadata.tables)


def _row_counts(engine, tables) -> dict[str, int]:
    with engine.connect() as connection:
        return {
            table: connection.exec_driver_sql(f"SELECT COUNT(*) FROM {table}").scalar()
            for table in tables
        }


def _schema(engine) -> dict[str, list[tuple]]:
    """Every table's columns, in a form where any change to any of them compares unequal.

    Name, type, nullability, default, and primary-key membership. A widened String or a
    column that quietly became nullable is as much of an ALTER that create_all cannot
    perform as a brand new column is.

    THIS IS ALSO WHAT ENFORCES app/db.py's ONE INVARIANT, that an ALTER's DDL reflects
    identically to what create_all emits for its mapped_column. It does that per column,
    for free, for every entry anyone ever appends to ADDED_COLUMNS, which is why the
    `default` field is in this tuple and why loosening any of it to make a comparison
    pass would quietly retire the only check on the whole mechanism.
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


class Databases:
    """The three schemas, the live engine behind the upgraded one, and which pin it is."""

    def __init__(self, ref, base, upgraded, fresh, upgraded_engine, base_rows):
        self.ref = ref
        self.base = base
        self.upgraded = upgraded
        self.fresh = fresh
        self.upgraded_engine = upgraded_engine
        self.base_rows = base_rows


@pytest.fixture(params=BASE_COMMITS, ids=lambda ref: ref[:12])
def databases(request, tmp_path, monkeypatch):
    """A POPULATED base-revision database upgraded by this branch, plus a fresh one.

    Parametrized over every pin, so each comparison below runs once per base and a
    failure names the revision it was measured from.

    THE SEEDING IS LOAD-BEARING, not hygiene. Measured, with a deliberately bad
    migration (VARCHAR(10) NOT NULL and no default) against this exact fixture:

        base seeded=False   courses rows=0   ALTER ACCEPTED   <- the bug ships
        base seeded=True    courses rows=1   ALTER REJECTED   <- caught, right here

    An empty base cannot see the one DDL mistake that passes CI and bricks every
    populated install. See test_every_altered_table_is_seeded.
    """
    from app import db as db_module

    ref = request.param
    metadata = base_metadata(ref)

    existing = tmp_path / "existing.sqlite3"
    base_engine = create_engine(f"sqlite:///{existing}")
    metadata.create_all(base_engine)
    seed_base_rows(base_engine, metadata)
    base = _schema(base_engine)
    base_rows = _row_counts(base_engine, sorted(set(base) & set(metadata.tables)))
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
        yield Databases(ref, base, upgraded, fresh, upgraded_engine, base_rows)
    finally:
        upgraded_engine.dispose()


def test_every_altered_table_is_seeded(databases):
    """THE GUARD THAT KEEPS THE REST OF THIS FILE HONEST.

    Every rule about safe DDL is advisory unless a test can see it broken, and what makes
    the dangerous shape visible is a base database with ROWS IN IT. SQLite accepts
    `ADD COLUMN x TEXT NOT NULL` against an empty table and rejects it against a table
    holding even one row, so an unseeded base never executes the statement that fails on
    a real install: the migration is accepted, every schema comparison passes, and the
    bug ships.

    Asserted mechanically over ADDED_COLUMNS rather than by naming `courses`, so whoever
    appends the next entry is TOLD to seed its table instead of silently reopening the
    hole. Naming the table would fix today and leave the next person to rediscover it.

    Tables ABSENT from a given base are skipped rather than failed. tutor_messages does
    not exist at the 797e50f pin and does exist at d453f50, and that asymmetry is the
    entire reason BASE_COMMITS is a tuple; an unconditional assertion here would make
    the older pin unusable.
    """
    for table in sorted({table for table, _, _ in ADDED_COLUMNS}):
        if table not in databases.base:
            continue
        assert databases.base_rows.get(table, 0) >= 1, (
            f"ADDED_COLUMNS alters {table!r}, but the base at {databases.ref[:12]} has no "
            f"rows in it, so this file cannot see a NOT NULL column added without a "
            f"default: SQLite accepts that against an empty table and rejects it against "
            f"a populated one. Add a seeder for {table!r} to SEEDERS in this file."
        )


def test_upgrade_adds_the_tutor_table_and_nothing_else(databases):
    """Scoped to the pin that PREDATES the tutor, rather than weakened to pass at both.

    At d453f50 the base already has tutor_messages, so the first assertion below would be
    false there and telling it to tolerate that would destroy it: that assertion is the
    guard against someone advancing a pin past the change it measures, and a version that
    accepts a base which already contains the feature cannot guard anything.
    """
    if databases.ref != TUTOR_BASE:
        pytest.skip(f"this claim is about the pin before the tutor, not {databases.ref[:12]}")

    assert NEW_TABLE not in databases.base, (
        f"BASE_COMMITS[0] ({TUTOR_BASE[:12]}) already has {NEW_TABLE}, so it does not "
        f"predate this feature and every comparison measured from it is now trivially "
        f"true. Point it back at the revision the feature forked from rather than "
        f"forward past the change it is supposed to measure."
    )
    assert NEW_TABLE in databases.upgraded
    assert set(databases.upgraded) - set(databases.base) == {NEW_TABLE}
    assert not set(databases.base) - set(databases.upgraded), "create_all cannot drop a table"


def test_an_upgraded_database_ends_up_identical_to_a_fresh_one(databases):
    """THE hard constraint, and the comparison that actually has teeth.

    create_all skips a table it already found, so asking whether the upgraded database
    changed answers nothing: it cannot have. The real question is whether it now matches
    what this branch's models describe, because that is what every query is written
    against. A column added to an existing table breaks exactly here.

    This is also what enforces app/db.py's invariant per column, so a DDL string that
    does not reflect what create_all emits (a stray DEFAULT '', a NOT NULL that the
    mapped_column does not carry, a mismatched width) fails here and nowhere else.
    """
    assert databases.upgraded == databases.fresh, (
        f"measured from {databases.ref[:12]}: an upgraded database and a fresh one "
        f"disagree. Either a column was added to an existing table with no entry in "
        f"ADDED_COLUMNS in app/db.py, or an entry there does not reflect what create_all "
        f"emits for its mapped_column."
    )


def test_no_existing_table_gains_or_loses_a_column(databases):
    """The same constraint stated per table, so a failure names the table.

    NARROWED when study planning added courses.deadline, and it is worth being precise
    about what was given up, because narrowing a test is usually how a test dies.

    This compared each base table against FRESH, which asserted that no existing table
    ever changes shape at all. That was the right claim for exactly as long as there was
    no way to change one: init_db() was create_all() alone, create_all cannot ALTER, so
    an added column was unimplementable and forbidding it cost nothing. app/db.py now
    carries a migration step, and the claim stopped being true the moment it landed:
    courses legitimately gains two columns, and a test asserting otherwise is asserting
    that the mechanism must never be used.

    The comparison is now UPGRADED against FRESH, per table. Every tooth is still here. A
    column added with no ADDED_COLUMNS entry still fails, by table name, because the
    upgraded database will not have it and the fresh one will. A column REMOVED still
    fails, because fresh lacks it and upgraded keeps it. A widened type still fails. What
    is gone is only the part that had stopped being a bug: the same column WITH a working
    migration entry now passes, which is the right answer.
    """
    for table in databases.base:
        assert databases.upgraded[table] == databases.fresh[table], (
            f"{table} has a different shape on an upgraded install (from "
            f"{databases.ref[:12]}) than on a fresh one. create_all cannot ALTER, so "
            f"either this branch changed the table without adding an entry to "
            f"ADDED_COLUMNS in app/db.py, or the entry it added does not reflect what "
            f"create_all builds."
        )


def test_every_mapped_column_exists_in_an_upgraded_database(databases):
    """The constraint as the symptom, rather than as a schema diff.

    Every mapped class is queried against the upgraded database. This is the exact thing
    that breaks in front of the learner: the app boots, then the first read of the table
    raises OperationalError: no such column. For study planning's columns that read is
    GET /courses, not anything to do with deadlines, because every query through the
    Course mapper emits every mapped column.
    """
    from app.db import Base

    with Session(databases.upgraded_engine) as session:
        for mapper in Base.registry.mappers:
            session.query(mapper.class_).limit(1).all()


def test_seeded_rows_survive_the_upgrade(databases):
    """An ALTER must not cost anyone their data.

    The counts are compared against what the base was seeded with rather than against a
    constant, so this keeps working when a seeder is added for a newly altered table.
    """
    with databases.upgraded_engine.connect() as connection:
        after = {
            table: connection.exec_driver_sql(f"SELECT COUNT(*) FROM {table}").scalar()
            for table in databases.base_rows
        }
    assert after == databases.base_rows


def test_both_tutor_indexes_are_created_with_the_table(databases):
    """Created with the table, because create_all never adds an index to a table it
    already found. An index this feature ships without is an index no existing database
    ever gets, and app/db.py's helper deliberately cannot add one."""
    names = {index["name"] for index in inspect(databases.upgraded_engine).get_indexes(NEW_TABLE)}
    assert NEW_INDEXES <= names


def test_upgrading_twice_is_a_no_op(databases, monkeypatch):
    """The second boot, which is the one the developer who wrote the ALTER never sees.

    create_all is checkfirst=True, so it finds everything already there. The migration
    step has no such guarantee for free: an unconditional ALTER passes every other test
    in this file on the first run and raises "duplicate column name" the next time the
    app starts. The inspector check in _add_missing_columns is what makes this pass.
    """
    from app import db as db_module

    monkeypatch.setattr(db_module, "engine", databases.upgraded_engine)
    db_module.init_db()
    db_module.init_db()

    assert _schema(databases.upgraded_engine) == databases.upgraded


def test_beyond_and_check_question_are_separate_columns(databases):
    """The one decision here that cannot be fixed later.

    beyond is what the tutor said that its material did not support, and check_question
    is the question it asked back. Flattened into content as markdown, every row written
    afterwards loses the grounded/ungrounded boundary permanently: the information is not
    in the text, so no migration can recover it.

    check_question rather than `check` because CHECK is reserved SQL. SQLAlchemy quotes it
    correctly; a raw-SQL session or a future Postgres path would not.
    """
    names = [name for name, *_ in databases.upgraded[NEW_TABLE]]

    assert "beyond" in names
    assert "check_question" in names
    assert "check" not in names
    assert "content" in names


def test_the_deadline_columns_reach_an_upgraded_database(databases):
    """Study planning's own entries, asserted at every pin.

    `courses` exists at both, so these columns are covered twice over and needed no new
    pin of their own. The nullability and absent default are not style: nullable is what
    lets the ALTER run against a populated table with no default clause, and no default
    is what keeps upgraded equal to fresh, since the mapped_column carries no
    server_default either.

    THIS IS A NARROW NET AND NOT A SUBSTITUTE FOR SEEDING, which is worth stating because
    it looks like broader cover than it is. Measured: with the base left unseeded and
    `deadline` mutated to NOT NULL with no default in both models.py and ADDED_COLUMNS,
    every GENERIC comparison in this file passes. upgraded == fresh passes, the per-table
    loop passes, the mapped-column loop passes, upgrading twice passes. Only this test and
    test_every_altered_table_is_seeded fail, and this one only because it names
    study planning's own two columns. A column belonging to any other feature has no
    equivalent here, so for that column the seeded base is the ONLY thing standing between
    a green suite and an install that will not boot. Do not read this test as making the
    seeding optional.
    """
    columns = {name: rest for name, *rest in databases.upgraded["courses"]}

    for name, expected_type in (("deadline", "VARCHAR(10)"), ("deadline_label", "VARCHAR(200)")):
        column_type, nullable, default, primary_key = columns[name]
        assert column_type == expected_type
        assert nullable is True
        assert default == "None"
        assert primary_key is False
