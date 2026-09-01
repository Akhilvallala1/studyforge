import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def get_engine():
    db_path = os.environ.get("STUDYFORGE_DB", "studyforge.sqlite3")
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False)


# --------------------------------------------------------------------------
# Added columns
# --------------------------------------------------------------------------
#
# WHY THIS EXISTS. Base.metadata.create_all is checkfirst=True: it creates a table it
# cannot find and leaves a table it finds ALONE, forever. It cannot ALTER. Adding a
# TABLE is therefore free, and every schema change in this project's history until now
# has been one. A COLUMN on a table that already shipped is not free, and it fails
# asymmetrically in the worst direction: a fresh install is perfect, and an existing
# install BOOTS FINE and then raises on the first query through that mapper. Adding
# `deadline` to courses without a step here breaks GET /courses, not the deadline
# feature, because every read through the Course mapper emits every mapped column.
#
# HOW TO ADD A COLUMN: declare the mapped_column in models.py wherever it belongs, then
# append one line to ADDED_COLUMNS below. Seed its table in
# backend/tests/test_tutor_migration.py if nothing seeds it yet; a guard test there will
# tell you if so, and every table currently named here is already seeded. It is a table
# rather than a function body precisely so that the next person copies a LINE and not a
# TECHNIQUE.
#
# WHEREVER IT BELONGS is meant literally: put the column next to the fields it relates
# to, not at the end of the class. Physical column order is not compared; see the note on
# ordinal position below. Two smaller things the one-line promise does not cover, so that
# nobody discovers them mid-change: a server_default needs `text` imported from sqlalchemy
# in models.py, and a NOT NULL column needs that server_default to keep upgraded == fresh.
#
# THE ONE INVARIANT EVERY ENTRY MUST SATISFY:
#
#     THE ALTER'S DDL MUST REFLECT IDENTICALLY TO WHAT create_all EMITS FOR THAT
#     mapped_column: same type, same nullability, same default, same primary-key
#     membership.
#
# Nobody has to enforce that by hand. test_tutor_migration.py's upgraded == fresh
# comparison already does it per column, automatically, for every entry anyone ever
# appends. That is also why _schema() over there compares type, nullability, DEFAULT and
# primary-key membership rather than something looser: DO NOT LOOSEN IT TO MAKE A
# COMPARISON PASS. The comparison failing is the mechanism working.
#
# ORDINAL POSITION IS THE ONE THING DELIBERATELY EXCLUDED, and it has to be, or this
# whole table would carry a hidden rule. ALTER TABLE ADD COLUMN always APPENDS the
# column physically, while create_all lays columns out in DECLARATION order. So a column
# declared in the middle of its class (which is where it usually belongs, next to the
# fields it relates to) lands last on an upgraded database and mid-table on a fresh one,
# with every per-column property identical. If the comparison were order-sensitive, the
# real rule would be "append your mapped_column at the END of its class", which appears
# nowhere, is invisible until the entry is uncommented, and would fail in the PR of
# whoever added the column rather than in the commit that introduced the rule.
# `deadline` and `deadline_label` satisfy it only by the accident of sitting after
# created_at. Nothing in this codebase reads a column by position: it is ORM everywhere,
# and the test seeding uses Core inserts with named values. See _schema in
# test_tutor_migration.py.
#
# There is deliberately NO rule here about whether to use a server default, because the
# right answer depends on the column and a rule either way would be wrong half the time.
# "Columns must be nullable" and "never write a DEFAULT clause" are both true of the only
# spelling this table happened to contain first, and both false in general: they would
# forbid the perfectly safe NOT NULL DEFAULT shape outright. Two shapes, both correct:
#
#   nullable      mapped_column(String(10), nullable=True)        -> "VARCHAR(10)"
#   not nullable  mapped_column(Text, server_default=text("''"))  -> "TEXT NOT NULL
#                                                                     DEFAULT ''"
#
# A SERVER DEFAULT IS A MATCHED PAIR: server_default on the mapped_column AND the same
# default written into the entry's definition, BOTH OR NEITHER. Half the pair is worse
# than neither half, because neither half is caught by reading either file alone:
#
#   server_default on the model, no DEFAULT in the entry -> fresh records dflt_value
#       "''" and upgraded records None
#   DEFAULT in the entry, no server_default on the model -> upgraded records "''" and
#       fresh records None
#
# Both directions fail upgraded == fresh on the `default` field, which is a comparison
# nobody looks at until it fires, so the pairing is worth knowing before you write the
# entry rather than after.

# (table, column, definition), where `definition` is EVERYTHING that follows the column
# name in ALTER TABLE <table> ADD COLUMN <column> <definition>. A COLUMN DEFINITION, not
# a type name, and it is called that everywhere here because thinking of it as a type is
# what leads to writing "TEXT" and losing the constraint and default a NOT NULL column
# carries in the same string.
#
# APPEND, NEVER EDIT OR REMOVE A ROW. A database in the wild can be at any point in this
# list, and deleting an entry means the install that never got that column never will.
ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    # Study planning: the learner's exam date and what they call it. Nullable with no
    # default, because a course without a deadline should store NULL rather than a
    # sentinel that some later query has to remember to exclude.
    ("courses", "deadline", "VARCHAR(10)"),
    ("courses", "deadline_label", "VARCHAR(200)"),
    # Work-it-out mode: the one move a guided reply withheld. The worked example of the
    # shape study planning's own columns do not exercise, a NOT NULL column with a
    # constant default, and the matched pair above is exactly what it needs:
    # models.TutorMessage.ask carries server_default=text("''") and this definition
    # carries the same default, so upgraded == fresh and every row already in the table
    # backfills to '' rather than to NULL.
    ("tutor_messages", "ask", "TEXT NOT NULL DEFAULT ''"),
)


def _add_missing_columns() -> None:
    """Apply every ADDED_COLUMNS entry the database does not already have.

    THIS HELPER'S CEILING, AND IT MUST NOT GROW PAST IT: ADD COLUMN WITH A CONSTANT
    DEFAULT, AND NOTHING ELSE. A drop, a rename, a type change, a new index on an
    existing table, and a new constraint are all outside it. SQLite cannot express any
    of them as an ALTER, so faking one here means a rebuild-and-copy dance with real
    failure modes, and a helper that pretends otherwise is worse than no helper because
    it looks like it worked. Any of those needs a real migration tool, and reaching that
    point is the signal to add one rather than to extend this.

    THE ONE DDL SHAPE THAT PASSES CI AND BRICKS EVERY POPULATED INSTALL, measured:

        ADD COLUMN x TEXT NOT NULL                rows=0 ACCEPTED   rows=1 REJECTED
        ADD COLUMN x TEXT NOT NULL DEFAULT ''     rows=0 ACCEPTED   rows=1 ACCEPTED

    So the danger is the MISSING DEFAULT, not NOT NULL as such. A NOT NULL column with a
    constant default is completely safe and old rows read back as that default. A NOT
    NULL column without one is accepted against a developer's empty scratch database,
    passes every schema comparison, and then raises "Cannot add a NOT NULL column with
    default value NULL" on the next boot of every install that has ever been used. The
    seeded base in test_tutor_migration.py is the only thing that can see it, which is
    why the seeding there is load-bearing rather than hygiene.

    Reads the module-level `engine` at CALL TIME rather than capturing it, matching
    init_db. Both migration tests monkeypatch app.db.engine to point at a database they
    built by hand, and a captured engine would migrate the wrong file and still pass.

    Existence is checked with inspect(engine).get_columns rather than raw PRAGMA or
    ADD COLUMN IF NOT EXISTS: the first is SQLite-only SQL in a codebase that keeps a
    Postgres path open, and the second is Postgres-only syntax that SQLite rejects.
    Idempotent by construction, so a second boot adds nothing; an unconditional ALTER
    would pass everything on the first run and raise "duplicate column name" on the
    next start, which the developer who wrote it never sees.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    for table, column, definition in ADDED_COLUMNS:
        if table not in tables:
            # create_all just built it from the current models, so it is already the
            # right shape. ALTERing a table that does not exist would raise.
            continue
        if column in {existing["name"] for existing in inspector.get_columns(table)}:
            continue
        with engine.begin() as connection:
            connection.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            )


def init_db() -> None:
    from app import models  # noqa: F401  (register models with Base)

    Base.metadata.create_all(engine)
    # AFTER create_all, and the order is load-bearing. create_all is what brings a brand
    # new table into existence; only then is it meaningful to ask an existing one which
    # columns it is missing.
    _add_missing_columns()


def get_session():
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
