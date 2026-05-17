"""
models.py — SQLAlchemy ORM models for the Tender Intelligence Platform.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Tender(Base):
    __tablename__ = "tenders"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tender_id = Column(String(100), unique=True, index=True, nullable=False)

    # ── Basic Metadata (from scraper) ────────────────────────────────────────
    title = Column(String(500))
    organization = Column(String(300))
    department = Column(String(300))
    published_date = Column(String(50))
    closing_date = Column(String(50))
    detail_url = Column(String(1000))
    pdf_url = Column(String(1000))
    status = Column(String(50), default="active")  # active / expired / awarded

    # ── AI-Extracted Fields ──────────────────────────────────────────────────
    tender_type = Column(String(200))
    budget = Column(String(200))
    budget_numeric = Column(Float, default=0.0)   # For sorting/filtering
    deadline = Column(String(200))
    emd_amount = Column(String(200))
    emd_numeric = Column(Float, default=0.0)
    required_experience = Column(String(500))
    eligibility_criteria = Column(Text)
    summary = Column(Text)
    pdf_text = Column(Text)                        # Extracted PDF content

    # ── Analysis Results ──────────────────────────────────────────────────────
    risk_level = Column(String(50))                # Low / Medium / High
    match_score = Column(String(10))               # "0"–"100" as string for compat
    match_score_num = Column(Float, default=0.0)   # Numeric for sorting
    recommendation = Column(String(50))            # Go / No-Go / Review
    match_reason = Column(Text)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Raw Storage ───────────────────────────────────────────────────────────
    raw_data = Column(JSON)

    def __repr__(self):
        return f"<Tender {self.tender_id}: {self.title[:50] if self.title else 'N/A'}>"
