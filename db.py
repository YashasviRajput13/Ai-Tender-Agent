"""
db.py — Database engine and session management.
SQLite (dev) / PostgreSQL (prod) via SQLAlchemy.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Import Base from models (flat root structure) ────────────────────────────
from models import Base  # noqa: E402  (root-level import)

# ── Database path ─────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tenders.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables (idempotent — safe to call multiple times)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Yield a database session; always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
