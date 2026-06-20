from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database.db import Base

class DBRecommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    rca_id = Column(Integer, ForeignKey("root_causes.id"), nullable=True)
    root_cause = Column(String, index=True, nullable=False)
    severity = Column(String, nullable=False)
    affected_services = Column(String, nullable=False)
    explanation = Column(String, nullable=False)
    recommended_fixes = Column(String, nullable=False)  # JSON-serialized list of strings
    preventive_measures = Column(String, nullable=False) # JSON-serialized list of strings
    timestamp = Column(DateTime, default=datetime.utcnow)

class RecommendationBase(BaseModel):
    rca_id: Optional[int] = None
    root_cause: str
    severity: str
    affected_services: str
    explanation: str
    recommended_fixes: List[str]
    preventive_measures: List[str]

class RecommendationCreate(RecommendationBase):
    pass

class RecommendationReport(RecommendationBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True
        from_attributes = True
