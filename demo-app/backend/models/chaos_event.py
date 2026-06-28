from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime
from database.db import Base

# SQLAlchemy Model
class DBChaosEvent(Base):
    __tablename__ = "chaos_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True, nullable=False)     # cpu, memory, storage, network, pod_crash
    target_service = Column(String, index=True, nullable=False)   # frontend, backend, database
    severity = Column(String, nullable=False, default="medium")   # low, medium, high
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="active")     # active, stopped
    chaos_metadata = Column('metadata', String, nullable=True)                      # JSON-serialized metadata string

# Pydantic Schemas
class ChaosEventBase(BaseModel):
    event_type: str
    target_service: str
    severity: Optional[str] = "medium"

class ChaosEventCreate(ChaosEventBase):
    pass

class ChaosEventStart(BaseModel):
    type: str
    target: str
    severity: Optional[str] = "medium"

class ChaosEventStop(BaseModel):
    event_id: str

class ChaosEvent(ChaosEventBase):
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    metadata: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True
