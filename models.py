from sqlalchemy import Column, Integer, String, Float, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Tender(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(String, unique=True, index=True)
    title = Column(String)
    organization = Column(String)
    tender_type = Column(String)
    budget = Column(String)
    deadline = Column(String)
    emd_amount = Column(String)
    required_experience = Column(String)
    eligibility_criteria = Column(Text)
    risk_level = Column(String)
    summary = Column(Text)
    
    # Analysis results
    match_score = Column(String)
    recommendation = Column(String)
    match_reason = Column(Text)
    
    # Raw JSON data for flexibility
    raw_data = Column(JSON)
