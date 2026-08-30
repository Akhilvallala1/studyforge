import logging
import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger("studyforge.db")


class Base(DeclarativeBase):
    pass


def get_engine():
    db_path = os.environ.get("STUDYFORGE_DB", "studyforge.sqlite3")
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def init_db() -> None:
    from app import models  # noqa: F401  (register models with Base)

    Base.metadata.create_all(engine)
    _create_missing_indexes()


def _create_missing_indexes() -> None:
    """Add indexes declared on models whose table already exists.

    create_all skips a table it finds, and skips that table's indexes with it. So an
    index added to a model after the table was first created never appears in a
    database that predates it, and nothing says so.

    That is tolerable for an index that only makes a query faster, and not tolerable
    for one that enforces something. The partial unique index on remediation_notes is
    what stops two simultaneous requests from both buying a model call; a database
    where it silently failed to appear has no guard at all, and the bug it prevents
    is invisible until it costs money. This project has no migration tool, so the
    gap is closed here instead.
    """
    inspector = inspect(engine)
    for table in Base.metadata.tables.values():
        if not inspector.has_table(table.name):
            continue  # create_all just made it, indexes included
        existing = {index["name"] for index in inspector.get_indexes(table.name)}
        for index in table.indexes:
            if index.name in existing:
                continue
            logger.info("creating missing index %s on %s", index.name, table.name)
            index.create(engine, checkfirst=True)


def get_session():
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
