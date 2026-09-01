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
# Migrations
# --------------------------------------------------------------------------
#
# THIS IS THE PROJECT'S FIRST MIGRATION, and whatever it looks like is what every
# later one will copy. So: what it is for, why it is shaped this way, and what a
# future column has to do.
#
# WHY IT HAS TO EXIST. Base.metadata.create_all is checkfirst=True. It creates a
# table it cannot find and leaves a table it finds ALONE, forever; it cannot ALTER.
# Adding a table is therefore free, and every schema change so far has been one. A
# COLUMN added to a table that already shipped is not free, and it fails
# asymmetrically in the worst possible direction: a fresh install is perfect, and an
# existing install BOOTS FINE and then raises on the first query touching the mapper.
# `deadline` on courses is the first such column in this project. Without the step
# below, an upgraded install answers GET /courses with
# "no such column: courses.deadline" and THE COURSE LIST BREAKS, not the deadline
# feature: every read through the Course mapper emits every mapped column, so a
# column the database lacks takes down everything that reads that table.
# backend/tests/test_tutor_migration.py's header describes this asymmetry in full,
# and backend/tests/test_planning_migration.py proves this particular step ran.
#
# WHY THE GUARD IS IN PYTHON AND NOT IN SQL. The obvious spelling is
# ALTER TABLE ... ADD COLUMN IF NOT EXISTS, and it does not exist in SQLite (it is
# Postgres syntax), so it would violate the SQLite-only rule and fail on the default
# database. Asking the inspector first is the portable form of the same question.
#
# THE RULES A FUTURE COLUMN MUST FOLLOW, all three learned the hard way:
#
#   1. NULLABLE. SQLite ACCEPTS `ADD COLUMN ... NOT NULL` against an EMPTY table and
#      REJECTS it against a table holding even one row. A NOT NULL column therefore
#      passes on a developer's scratch database and raises on every install that has
#      ever been used. If a value is genuinely required, add it nullable, backfill
#      it, and enforce non-null in the application.
#
#   2. NO DEFAULT CLAUSE. `ADD COLUMN deadline VARCHAR(10)` with no default produces
#      a schema BYTE-IDENTICAL to what create_all builds fresh. Adding DEFAULT ''
#      does not: sqlite records dflt_value "''" where create_all records None, the
#      upgraded and fresh schemas stop comparing equal, and the migration test fails
#      for a reason nobody would guess from its message. Column defaults belong in
#      the mapped_column (a Python-side default), which is where the rest of this
#      codebase already puts them.
#
#   3. THE DDL TYPE MUST MATCH WHAT create_all EMITS for the mapped type, spelled the
#      same way: String(10) is VARCHAR(10), Integer is INTEGER, DateTime is DATETIME,
#      Float is FLOAT, Boolean is BOOLEAN, Text is TEXT, JSON is JSON. A mismatch
#      leaves upgraded and fresh installs on different types, which is exactly the
#      divergence this whole mechanism exists to prevent.
#
# APPEND TO _ADDED_COLUMNS, NEVER EDIT OR REMOVE A ROW. A database in the wild can be
# at any point in this history, and deleting an entry means the install that never got
# that column never will. Entries are cheap: each one costs a dictionary lookup on a
# schema read that has already happened.

# (table, column, DDL type) for every column added to a table that already shipped.
_ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    # Study planning: the learner's exam date and what they call it.
    ("courses", "deadline", "VARCHAR(10)"),
    ("courses", "deadline_label", "VARCHAR(200)"),
)


def _add_missing_columns() -> None:
    """ALTER in any column of _ADDED_COLUMNS the database does not have yet.

    Reads the module-level `engine` at CALL TIME rather than capturing it, matching
    init_db. The migration tests monkeypatch app.db.engine to point at a database they
    built by hand, and a captured engine would quietly migrate the wrong file.

    Idempotent by construction: the inspector is asked what the table already has, so
    a second boot adds nothing. An unconditional ALTER would pass every test on the
    first run and raise "duplicate column name" on the next start, which is a failure
    the developer who wrote it never sees.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    for table, column, ddl_type in _ADDED_COLUMNS:
        if table not in tables:
            # create_all just built it from the current models, so it is already the
            # right shape. Nothing to add, and ALTERing a table that does not exist
            # would raise.
            continue
        if column in {existing["name"] for existing in inspector.get_columns(table)}:
            continue
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def init_db() -> None:
    from app import models  # noqa: F401  (register models with Base)

    Base.metadata.create_all(engine)
    # AFTER create_all, and the order is load-bearing. create_all is what brings a
    # brand new table into existence; only then is it meaningful to ask an existing
    # one which columns it is missing.
    _add_missing_columns()


def get_session():
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
