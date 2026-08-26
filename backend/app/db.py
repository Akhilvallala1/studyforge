import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


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


def get_session():
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
