from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import json
from database.db import get_db, init_db
from database.models import Tender

class DatabaseToolInput(BaseModel):
    tender_data: str = Field(description="JSON string containing the fully analyzed and matched tender data.")

class DatabaseStorageTool(BaseTool):
    name: str = "Tender Database Storage Tool"
    description: str = "Saves the fully processed and matched tender information into the database."
    args_schema: Type[BaseModel] = DatabaseToolInput

    def _run(self, tender_data: str) -> str:
        """Save tender data to database."""
        try:
            # Ensure DB tables exist
            init_db()
            
            # Clean JSON if it has markdown formatting
            if tender_data.startswith("```json"):
                tender_data = tender_data.replace("```json", "", 1)
            if tender_data.endswith("```"):
                tender_data = tender_data[:-3]
            
            data = json.loads(tender_data.strip())
            
            # Use a session
            db_generator = get_db()
            db = next(db_generator)
            
            try:
                # Check if it already exists
                existing = db.query(Tender).filter(Tender.tender_id == data.get("tender_id", "mock-id")).first()
                if existing:
                    return f"Tender {data.get('tender_id')} already exists in database."
                
                # Create new record
                new_tender = Tender(
                    tender_id=data.get("tender_id", "mock-id"),
                    title=data.get("tender_type", "Unknown"), # Map tender_type to title for mock
                    organization=data.get("organization", "Unknown"),
                    tender_type=data.get("tender_type", ""),
                    budget=data.get("budget", ""),
                    deadline=data.get("deadline", ""),
                    emd_amount=data.get("emd_amount", ""),
                    required_experience=data.get("required_experience", ""),
                    eligibility_criteria=data.get("eligibility_criteria", ""),
                    risk_level=data.get("risk_level", ""),
                    summary=data.get("summary", ""),
                    match_score=str(data.get("match_score", "")),
                    recommendation=data.get("recommendation", ""),
                    match_reason=data.get("reason", ""),
                    raw_data=data
                )
                
                db.add(new_tender)
                db.commit()
                return f"Successfully saved tender {new_tender.tender_id} to database."
                
            finally:
                db_generator.close()
                
        except Exception as e:
            return f"Error saving to database: {str(e)}"
