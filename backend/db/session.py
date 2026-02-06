from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models import Base


metadata_engine = create_engine(settings.metadata_db_url, future=True)
SessionLocal = sessionmaker(bind=metadata_engine, autoflush=False, autocommit=False, future=True)


def init_metadata_db() -> None:
    Base.metadata.create_all(bind=metadata_engine)


@contextmanager
def db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
