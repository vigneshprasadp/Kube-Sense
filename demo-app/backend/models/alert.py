from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, DateTime
from database.db import Base

# SQLAlchemy Database Model for Alerts
class DBAlert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    pod_name = Column(String, index=True, nullable=False)
    cpu_value = Column(Float, nullable=False)
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Pydantic Schemas for validation and serialization
class AlertBase(BaseModel):
    pod_name: str
    cpu_value: float
    message: str

class AlertCreate(AlertBase):
    pass

class Alert(AlertBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True
        from_attributes = True


# SQLAlchemy Database Model for Network Alerts
class DBNetworkAlert(Base):
    __tablename__ = "network_alerts"

    id = Column(Integer, primary_key=True, index=True)
    source_service = Column(String, index=True, nullable=False)
    target_service = Column(String, index=True, nullable=False)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    z_score = Column(Float, nullable=True)
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas for validation and serialization
class NetworkAlertBase(BaseModel):
    source_service: str
    target_service: str
    metric_name: str
    metric_value: float
    z_score: float | None = None
    message: str


class NetworkAlertCreate(NetworkAlertBase):
    pass


class NetworkAlert(NetworkAlertBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True
        from_attributes = True

