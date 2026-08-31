"""What this branch does to a database that already exists.

The rest of the suite cannot answer this. conftest points STUDYFORGE_DB at a fresh
temp file, so every other test proves only the fresh-install path, and a fresh install
is exactly the case that cannot fail: init_db() is create_all(checkfirst=True), which
creates whatever is missing and never alters anything.

The failure this file exists to catch is the asymmetric one. create_all CANNOT ALTER a
table, so a new column added to attempts, llm_calls, review_cards or any other existing
table produces a fresh install that works perfectly and an upgraded install that raises
"no such column" on the first query touching it. That is worse than a database that
refuses to open, because it starts fine and fails later, in front of the learner.

So three schemas are built and compared: the BASE one from the metadata models.py
declared at BASE_COMMIT, the UPGRADED one that is the base with this branch's init_db()
run over it, and the FRESH one this branch creates from nothing.

Note carefully which comparison carries the weight. Comparing upgraded against base is
nearly worthless on its own: create_all skips a table it already found, so an existing
table is byte-identical afterwards NO MATTER WHAT the models say, and a column added to
attempts sails straight through. The claim with teeth is UPGRADED == FRESH, because
that is the one an added column breaks, and test_every_mapped_column_exists_in_an_upgraded_database
states the same thing as the symptom the learner would actually see.
"""

import subprocess
import sys
import types
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session

# The revision this feature forked from, PINNED BY SHA rather than named by branch.
#
# This read ("origin/main", "main"), and that was correct for exactly as long as the
# tutor branch was unmerged. The moment it landed, origin/main became a commit that
# already has tutor_messages, so the base stopped meaning "the schema before this
# feature" and started meaning "the schema including it", and
# test_upgrade_adds_the_tutor_table_and_nothing_else went red and stayed red. Nothing in
# the tree caused that and no change to the models could fix it: the same commit passed
# this file an hour before it was merged and failed it afterwards, untouched.
#
# A branch name cannot express what this file needs. Its subject is ONE migration, what
# the tutor feature did to a database predating it, and that is a claim about a fixed
# pair of revisions rather than about whatever main happens to be today. 797e50f is
# aa760df^, the parent of the commit that first put TutorMessage in models.py, so it is
# exactly what origin/main denoted while this work was in flight. Pinning does not
# narrow the file, it freezes the reading that was already intended.
#
# Pinning also makes the three comparisons below STRONGER as the project moves rather
# than ageing out of use. `fresh` is always the CURRENT models, so a future feature that
# adds a column to an existing table still fails test_no_existing_table_gains_or_loses_a
# _column and test_an_upgraded_database_ends_up_identical_to_a_fresh_one, and now fails
# them measured from further back. That is the direction that matters here: init_db() is
# create_all(checkfirst=True) with no migration system under it, so what an upgrade has
# to survive is the OLDEST schema still in the wild, not last week's.
#
# DO NOT "FIX" A FUTURE FAILURE BY MOVING THIS FORWARD. Advancing it past a schema
# change makes every comparison below trivially true and the file silently stops
# testing anything, which is worse in both directions than the red it replaced. The
# first assertion in test_upgrade_adds_the_tutor_table_and_nothing_else is the guard
# against that and it names this constant when it fires.
BASE_COMMIT = "797e50fe684e4a0c5062672aab8ae730ae20477c"

MODELS_PATH = "backend/app/models.py"

NEW_TABLE = "tutor_messages"
NEW_INDEXES = {"ix_tutor_messages_concept_created", "ix_tutor_messages_created"}


def _git(*args: str) -> subprocess.CompletedProcess:
    here = Path(__file__).resolve().parent
    return subprocess.run(
        ["git", "-C", str(here), *args], capture_output=True, text=True, check=False
    )


def _base_models_source() -> tuple[str, str]:
    """(ref, source) for models.py as it stood at BASE_COMMIT, before this feature.

    Skips rather than passes when the commit is unreachable, which is what a shallow or
    partial clone gives. A skip says the comparison did not happen; falling back to the
    working tree would compare this branch against ITSELF and report that as a pass,
    which is the shape of failure this whole file exists to make impossible.
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
        # exec, deliberately: the source is this repository's own models.py at a commit
        # git already has, and importing it normally would bind it to the live
        # app.db.Base and compare this branch against itself.
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
    """Every table's columns, in a form where any change to any of them compares unequal.

    Name, type, nullability, default, and primary-key membership. A widened String or a
    column that quietly became nullable is as much of an ALTER that create_all cannot
    perform as a brand new column is.
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
    """The three schemas, and the live engines behind the upgraded one."""

    def __init__(self, base, upgraded, fresh, upgraded_engine):
        self.base = base
        self.upgraded = upgraded
        self.fresh = fresh
        self.upgraded_engine = upgraded_engine


@pytest.fixture
def databases(tmp_path, monkeypatch):
    """A base-revision database upgraded by this branch, plus a fresh one for comparison."""
    from app import db as db_module

    existing = tmp_path / "existing.sqlite3"
    base_engine = create_engine(f"sqlite:///{existing}")
    _base_metadata().create_all(base_engine)
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


def test_upgrade_adds_the_tutor_table_and_nothing_else(databases):
    assert NEW_TABLE not in databases.base, (
        f"BASE_COMMIT ({BASE_COMMIT[:12]}) already has {NEW_TABLE}, so it does not "
        f"predate this feature and every comparison in this file is now trivially "
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
    """
    assert databases.upgraded == databases.fresh, (
        "an upgraded database and a fresh one disagree. create_all cannot ALTER an "
        "existing table, so whatever is missing above will never appear on an upgraded "
        "install, and the first query touching it raises 'no such column'."
    )


def test_no_existing_table_gains_or_loses_a_column(databases):
    """The same constraint stated per table, so a failure names the table."""
    for table, columns in databases.base.items():
        assert databases.fresh[table] == columns, (
            f"{table} changed shape on this branch. create_all cannot ALTER, so an "
            f"upgraded database would never gain this."
        )
        assert databases.upgraded[table] == columns


def test_every_mapped_column_exists_in_an_upgraded_database(databases):
    """The constraint as the symptom, rather than as a schema diff.

    Every mapped class is queried against the upgraded database. This is the exact
    thing that breaks in front of the learner: the app boots, then the first read of
    the table raises OperationalError: no such column.
    """
    from app.db import Base

    with Session(databases.upgraded_engine) as session:
        for mapper in Base.registry.mappers:
            session.query(mapper.class_).limit(1).all()


def test_both_tutor_indexes_are_created_with_the_table(databases):
    """Created with the table, because create_all never adds an index to a table it
    already found. An index this feature ships without is an index no existing
    database ever gets."""
    names = {index["name"] for index in inspect(databases.upgraded_engine).get_indexes(NEW_TABLE)}
    assert NEW_INDEXES <= names


def test_upgrading_twice_is_a_no_op(databases, monkeypatch):
    """checkfirst=True, so a second boot must find everything already there."""
    from app import db as db_module

    monkeypatch.setattr(db_module, "engine", databases.upgraded_engine)
    db_module.init_db()
    assert _schema(databases.upgraded_engine) == databases.upgraded


def test_beyond_and_check_question_are_separate_columns(databases):
    """The one decision here that cannot be fixed later.

    beyond is what the tutor said that its material did not support, and
    check_question is the question it asked back. Flattened into content as markdown,
    every row written afterwards loses the grounded/ungrounded boundary permanently:
    the information is not in the text, so no migration can recover it.

    check_question rather than `check` because CHECK is reserved SQL. SQLAlchemy quotes
    it correctly; a raw-SQL session or a future Postgres path would not.
    """
    names = [name for name, *_ in databases.upgraded[NEW_TABLE]]

    assert "beyond" in names
    assert "check_question" in names
    assert "check" not in names
    assert "content" in names
