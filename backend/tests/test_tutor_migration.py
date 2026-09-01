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

# Named rather than indexed at the point of use, so a reader does not have to count.
TUTOR_BASE = BASE_COMMITS[0]
# The pin before courses.deadline. Imported by test_planning.py, which builds a
# pre-upgrade database to test how the feature answers for a course older than itself.
DEADLINE_BASE = BASE_COMMITS[1]

MODELS_PATH = "backend/app/models.py"

NEW_TABLE = "tutor_messages"
NEW_INDEXES = {"ix_tutor_messages_concept_created", "ix_tutor_messages_created"}

# Work-it-out mode's column on that table. The only ADDED_COLUMNS entry so far that is NOT
# NULL with a constant default, and therefore the only one for which a row already in the
# base has to come back reading something rather than NULL.
ASK_COLUMN = "ask"


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


def _schema(engine) -> dict[str, dict[str, tuple]]:
    """Every table's columns KEYED BY NAME, so any change to any of them compares unequal.

    Type, nullability, default, and primary-key membership. A widened String or a column
    that quietly became nullable is as much of an ALTER that create_all cannot perform as
    a brand new column is.

    THIS IS WHAT ENFORCES app/db.py's ONE INVARIANT, that an ALTER's DDL reflects
    identically to what create_all emits for its mapped_column. It does that per column,
    for free, for every entry anyone ever appends to ADDED_COLUMNS, which is why the
    `default` field is in the tuple and why loosening any of THOSE FOUR to make a
    comparison pass would quietly retire the only check on the whole mechanism.

    KEYED BY NAME RATHER THAN AN ORDERED LIST, WHICH IS A DELIBERATE LOOSENING, AND THE
    ONLY ONE. This returned a list, so it compared physical column ORDER as well, and
    that made the whole ADDED_COLUMNS mechanism quietly placement-dependent.
    ALTER TABLE ADD COLUMN always APPENDS a column physically; create_all uses DECLARATION
    order. Declare a new column beside the fields it relates to, as anyone naturally
    would, and an upgraded database gets it last while a fresh one gets it in the middle,
    with every per-column property byte-identical:

        upgraded: [..., check_question, run_id, model, created_at, ask]
        fresh:    [..., check_question, ask, run_id, model, created_at]

    Same names, same shapes, different order. The real rule would then have been "append
    your mapped_column at the END of its class", which was written down nowhere, and the
    failure message pointed at the DDL string, which was correct. Nothing in this codebase
    reads a column by position (ORM everywhere; the seeding above uses Core inserts with
    named values), so ordinal position is cosmetic and is not compared.

    DO NOT "RESTORE" STRICTNESS HERE without reintroducing that hidden rule and documenting
    it as a fourth rule in app/db.py. The SET of column names is still compared, so a
    missing or extra column fails exactly as loudly as before; only the order is free.
    """
    inspector = inspect(engine)
    return {
        table: {
            column["name"]: (
                str(column["type"]),
                bool(column["nullable"]),
                str(column.get("default")),
                bool(column.get("primary_key")),
            )
            for column in inspector.get_columns(table)
        }
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
    # Names first, so a missing or extra column is reported as that column rather than
    # as a diff of two large dictionaries. THE TWO DIRECTIONS GET DIFFERENT REMEDIES,
    # because they are different mistakes: a column MISSING from an upgraded install is
    # one that needs an ADDED_COLUMNS entry, and a column EXTRA on one is a column that
    # was taken out of models.py while its entry stayed, which no entry can fix. Telling
    # someone in the second case to add an entry sends them to write the line that is
    # already there.
    for table in sorted(set(databases.upgraded) | set(databases.fresh)):
        upgraded_columns = set(databases.upgraded.get(table, {}))
        fresh_columns = set(databases.fresh.get(table, {}))
        assert not fresh_columns - upgraded_columns, (
            f"measured from {databases.ref[:12]}: {table} is MISSING "
            f"{sorted(fresh_columns - upgraded_columns)} on an upgraded install, which a "
            f"fresh one has. create_all cannot ALTER an existing table, so a column added "
            f"to one needs an entry in ADDED_COLUMNS in app/db.py."
        )
        assert not upgraded_columns - fresh_columns, (
            f"measured from {databases.ref[:12]}: {table} has EXTRA "
            f"{sorted(upgraded_columns - fresh_columns)} on an upgraded install that a "
            f"fresh one does not, so a column was removed from models.py while its "
            f"ADDED_COLUMNS entry in app/db.py stayed. Adding an entry cannot fix this "
            f"and removing that one would only strand the installs that never got the "
            f"column: neither create_all nor _add_missing_columns can DROP a column, so "
            f"either restore the mapped_column or this needs a real migration tool."
        )

    assert databases.upgraded == databases.fresh, (
        f"measured from {databases.ref[:12]}: an upgraded database and a fresh one agree "
        f"on which columns exist but not on their shape, so an entry in ADDED_COLUMNS in "
        f"app/db.py does not reflect what create_all emits for its mapped_column. Compare "
        f"type, nullability, default and primary-key membership; physical column ORDER is "
        f"deliberately not compared and cannot be the cause."
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
        upgraded_columns = set(databases.upgraded[table])
        fresh_columns = set(databases.fresh[table])
        # Split by direction for the reason given in the test above: an added column and
        # a removed one need opposite fixes, and only one of them is an ADDED_COLUMNS
        # entry.
        assert not fresh_columns - upgraded_columns, (
            f"{table} is MISSING {sorted(fresh_columns - upgraded_columns)} on an upgraded "
            f"install (from {databases.ref[:12]}) that a fresh one has. create_all cannot "
            f"ALTER, so a column added to this table needs an entry in ADDED_COLUMNS in "
            f"app/db.py."
        )
        assert not upgraded_columns - fresh_columns, (
            f"{table} has EXTRA {sorted(upgraded_columns - fresh_columns)} on an upgraded "
            f"install (from {databases.ref[:12]}) that a fresh one does not, so a column "
            f"was removed from models.py while its ADDED_COLUMNS entry in app/db.py "
            f"stayed. Nothing here can DROP a column: restore the mapped_column, or reach "
            f"for a real migration tool. Do not delete the entry, which would only strand "
            f"the installs that never got the column."
        )
        assert databases.upgraded[table] == databases.fresh[table], (
            f"{table} has the same columns on an upgraded install (from "
            f"{databases.ref[:12]}) as on a fresh one but not the same shapes, so an "
            f"ADDED_COLUMNS entry in app/db.py does not reflect what create_all builds. "
            f"Physical column ORDER is deliberately not compared and cannot be the cause."
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


def test_beyond_check_question_and_ask_are_separate_columns(databases):
    """The one decision here that cannot be fixed later.

    beyond is what the tutor said that its material did not support, check_question is the
    question it asked back, and ask is the move a guided reply deliberately stopped short
    of. Flattened into content as markdown, every row written afterwards loses the
    boundary permanently: the information is not in the text, so no migration can recover
    it. Flattening ask into check_question is the same loss one step smaller, and it takes
    tutor.guided_run with it, since a run is counted by asking each row which of the two
    it carries.

    check_question rather than `check` because CHECK is reserved SQL. SQLAlchemy quotes it
    correctly; a raw-SQL session or a future Postgres path would not. `ask` needs no such
    dodge and gets none, so the column name is the JSON key.
    """
    names = databases.upgraded[NEW_TABLE]

    assert "beyond" in names
    assert "check_question" in names
    assert "check" not in names
    assert ASK_COLUMN in names
    assert "content" in names


def test_the_ask_column_reaches_an_upgraded_database(databases):
    """Work-it-out mode's own entry, and the DELIBERATE OPPOSITE of the deadline one.

    The two columns took opposite decisions on both nullability and the default clause,
    and each is right for its own case, which is why app/db.py refuses to have a rule
    either way. An absent deadline means something, so it is NULL with no default. An
    absent `ask` means the reply withheld nothing, which is a fact about the reply rather
    than a gap in it, so it is '' and never NULL, and on an upgrade that is only reachable
    if the ALTER carries the default with it.

    WRITTEN BECAUSE THE GENERIC COMPARISONS DEMONSTRABLY DO NOT SEE THIS, and the
    measurement is in test_the_deadline_columns_reach_an_upgraded_database's docstring:
    with the base unseeded and a column mutated to NOT NULL with no default in models.py
    and ADDED_COLUMNS together, upgraded == fresh passes, the per-table loop passes, the
    mapped-column loop passes, and upgrading twice passes. Only the seeding guard and that
    test caught it, and that test catches it by naming study planning's OWN two columns.
    `ask` had no equivalent, so this is it. It is still a NARROW NET and still not a
    substitute for the seeded base, which is the only thing that makes the bad ALTER fail
    at all.
    """
    columns = databases.upgraded[NEW_TABLE]
    column_type, nullable, default, primary_key = columns[ASK_COLUMN]

    assert column_type == "TEXT"
    assert nullable is False
    assert default == "''", "the server_default is what keeps upgraded equal to fresh"
    assert primary_key is False


def test_an_existing_conversation_backfills_to_empty_string(databases):
    """The value a row that predates the column reads afterwards, which is '' and not NULL.

    Two things are on trial and the fixture proves the first by reaching the assertions at
    all: the ALTER has to RUN against a table with a row in it, which NOT NULL with no
    default would not. What is asserted here is the second, and it is the reason the
    default is a constant rather than NULL: a conversation written before guided mode
    existed reads back as an unbroken run of answer-mode turns, so tutor.guided_run counts
    it correctly with no special case for legacy rows. A NULL there would make every
    pre-existing row a three-valued question for a column whose entire job is to be
    checked for emptiness.

    Skipped where the base predates tutor_messages, on the CONDITION rather than on a pin,
    so appending a pin never has to touch this test.
    """
    from app import models

    if NEW_TABLE not in databases.base:
        pytest.skip(f"{databases.ref[:12]} predates {NEW_TABLE}, so it seeds no conversation")

    with Session(databases.upgraded_engine) as session:
        rows = session.query(models.TutorMessage).all()
        assert rows, "the seeder for tutor_messages put no rows in the base"
        for row in rows:
            assert row.ask is not None, "an upgraded row must never read NULL"
            assert row.ask == ""
        # The rest of the row is untouched, so this is a backfill and not a rewrite.
        assert rows[0].content == "Why downhill?"
        assert rows[0].role == "learner"


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
    columns = databases.upgraded["courses"]

    for name, expected_type in (("deadline", "VARCHAR(10)"), ("deadline_label", "VARCHAR(200)")):
        column_type, nullable, default, primary_key = columns[name]
        assert column_type == expected_type
        assert nullable is True
        assert default == "None"
        assert primary_key is False
