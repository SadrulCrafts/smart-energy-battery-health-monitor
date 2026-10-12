"""
database.py
-----------
Stage 3, Step 2: SQLite database connection.

The database is a single file: backend/data/monitor.db
It is created automatically when the API starts. It is NOT committed to Git.
"""

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent      # .../backend
DATA_DIR = BACKEND_DIR / "data"
DATABASE_FILE = DATA_DIR / "monitor.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE.as_posix()}"

# check_same_thread=False lets FastAPI use the connection from different threads
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# A "session" is one conversation with the database (read / write / commit)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Parent class for all database tables."""


def init_db():
    """Create the data folder and all tables (safe to call every start-up)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    from . import models  # noqa: F401  (importing registers the tables on Base)
    Base.metadata.create_all(bind=engine)


def database_is_reachable():
    """Return True if a trivial query succeeds."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - any failure means "not reachable"
        return False


def get_db():
    """Give one session to an API request and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()