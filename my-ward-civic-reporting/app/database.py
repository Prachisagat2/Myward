from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config

_connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(config.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_columns() -> None:
    """Add columns introduced after the first release to an existing database."""
    inspector = inspect(engine)
    if "complaints" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("complaints")}
    with engine.begin() as conn:
        if "category_source" not in existing:
            conn.execute(text(
                "ALTER TABLE complaints ADD COLUMN category_source VARCHAR(10) NOT NULL DEFAULT 'citizen'"))
        if "ai_confidence" not in existing:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN ai_confidence FLOAT"))
