from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, DateTime
from database.db import Base

class DBRootCauseReport(Base):
    __tablename__ = "root_causes"

    id = Column(Integer, primary_key=True, index=True)
    root_cause = Column(String, index=True, nullable=False)
    affected_services = Column(String, nullable=False)  # Comma-separated list of affected services
    severity = Column(String, nullable=False)           # Critical, Warning, Info
    confidence_score = Column(Float, nullable=False)    # Value between 0.0 and 1.0
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class RootCauseReportBase(BaseModel):
    root_cause: str
    affected_services: str
    severity: str
    confidence_score: float
    message: str

class RootCauseReportCreate(RootCauseReportBase):
    pass

class RootCauseReport(RootCauseReportBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True
        from_attributes = True
