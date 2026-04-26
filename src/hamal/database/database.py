"""Database connection and session management."""

import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from hamal.core.config import get_database_path
from hamal.database.models import Base

# Global engine and session factory
_ENGINE = None
_SESSION_LOCAL = None
_ENGINE_LOCK = threading.Lock()


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _ENGINE  # pylint: disable=global-statement
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                db_path = get_database_path()
                _ENGINE = create_engine(
                    f"sqlite:///{db_path}",
                    echo=False,  # Set to True for SQL debugging
                    connect_args={"check_same_thread": False}  # Required for SQLite with threads
                )
    return _ENGINE


def get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _SESSION_LOCAL  # pylint: disable=global-statement
    if _SESSION_LOCAL is None:
        with _ENGINE_LOCK:
            if _SESSION_LOCAL is None:
                engine = get_engine()
                _SESSION_LOCAL = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return _SESSION_LOCAL


def init_database():
    """Initialize the database, creating tables if they don't exist."""
    print(f"[Database] Initializing... (Path: {get_database_path()})")
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("[Database] Schema check/creation completed.")

    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(projects)"))
        columns = [row[1] for row in result]

        columns_to_add = {
            "auto_start": "BOOLEAN DEFAULT 0 NOT NULL",
            "schedule_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "schedule_start": "VARCHAR(5)",
            "schedule_stop": "VARCHAR(5)",
            "schedule_days": "TEXT",
        }

        for col_name, col_def in columns_to_add.items():
            if col_name not in columns:
                try:
                    conn.execute(text(f"ALTER TABLE projects ADD COLUMN {col_name} {col_def}"))
                    print(f"[Database] Migrated: added '{col_name}' column.")
                except Exception as e:
                    print(f"[Database] Error adding '{col_name}': {e}")
                    raise

        conn.commit()


def get_session() -> Session:
    """Get a new database session. Caller is responsible for closing it."""
    factory = get_session_factory()
    return factory()
