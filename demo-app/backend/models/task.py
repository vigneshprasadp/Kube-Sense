from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime
from database.db import Base

# SQLAlchemy Database Model definition
class DBTask(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, default="")
    category = Column(String, default="General")
    priority = Column(String, default="Medium")
    status = Column(String, default="To Do")
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Schemas for validation
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = "General"
    priority: Optional[str] = "Medium"
    status: Optional[str] = "To Do"

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None

class Task(TaskBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
