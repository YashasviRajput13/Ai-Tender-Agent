"""
db_tool.py — CrewAI Database Storage Tool (fixed imports).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from db import get_db, init_db
from models import Tender


class DatabaseToolInput(BaseModel):
    tender_data: str = Field(description="JSON string of fully analyzed and matched tender data.")


class DatabaseStorageTool(BaseTool):
    name: str = "Tender Database Storage Tool"
    description: str = "Saves fully processed and ranked tender information into the SQLite database."
    args_schema: Type[BaseModel] = DatabaseToolInput

    def _run(self, tender_data: str) -> str:
        try:
            init_db()
            # Strip markdown fences
            clean = tender_data.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[-2] if "```" in clean[3:] else clean[3:]
                clean = clean.lstrip("json").strip()

            data = json.loads(clean)
            db = next(get_db())

            try:
                tid = data.get("tender_id", "AGENT-" + str(hash(data.get("title", "")))[:8])
                existing = db.query(Tender).filter(Tender.tender_id == tid).first()
                if existing:
                    return f"Tender {tid} already exists."

                record = Tender(
                    tender_id=tid,
                    title=data.get("title", data.get("tender_type", "Unknown")),
                    organization=data.get("organization", "Unknown"),
                    tender_type=data.get("tender_type", ""),
                    budget=data.get("budget", ""),
                    budget_numeric=float(data.get("budget_numeric", 0) or 0),
                    deadline=data.get("deadline", ""),
                    emd_amount=data.get("emd_amount", ""),
                    required_experience=data.get("required_experience", ""),
                    eligibility_criteria=data.get("eligibility_criteria", ""),
                    risk_level=data.get("risk_level", ""),
                    summary=data.get("summary", ""),
                    match_score=str(data.get("match_score", "")),
                    match_score_num=float(data.get("match_score", 0) or 0),
                    recommendation=data.get("recommendation", ""),
                    match_reason=data.get("reason", data.get("match_reason", "")),
                    raw_data=data,
                )
                db.add(record)
                db.commit()
                return f"Saved tender {tid} to database."
            finally:
                db.close()

        except json.JSONDecodeError as e:
            return f"JSON parse error: {e}"
        except Exception as e:
            return f"Database error: {e}"
