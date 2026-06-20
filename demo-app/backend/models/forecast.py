from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, DateTime
from database.db import Base


# ─── SQLAlchemy Model ────────────────────────────────────────────────────────

class DBForecast(Base):
    __tablename__ = "forecasts"

    id               = Column(Integer, primary_key=True, index=True)
    resource_type    = Column(String, index=True, nullable=False)   # cpu | storage | network
    service_name     = Column(String, index=True, nullable=False)   # frontend, backend, database …
    current_value    = Column(Float, nullable=False)                # Latest observed value
    predicted_value  = Column(Float, nullable=False)                # Predicted value at saturation horizon
    threshold        = Column(Float, nullable=False)                # Saturation threshold (90 % / 85 % / etc.)
    minutes_to_breach= Column(Float, nullable=True)                 # Estimated minutes until threshold crossed
    trend_slope      = Column(Float, nullable=True)                 # Linear regression slope (units / interval)
    r_squared        = Column(Float, nullable=True)                 # Model fit quality (0-1)
    message          = Column(String, nullable=False)
    severity         = Column(String, nullable=False, default="Info") # Info | Warning | Critical
    timestamp        = Column(DateTime, default=datetime.utcnow)


# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class ForecastBase(BaseModel):
    resource_type:     str
    service_name:      str
    current_value:     float
    predicted_value:   float
    threshold:         float
    minutes_to_breach: Optional[float] = None
    trend_slope:       Optional[float] = None
    r_squared:         Optional[float] = None
    message:           str
    severity:          str


class ForecastCreate(ForecastBase):
    pass


class Forecast(ForecastBase):
    id:        int
    timestamp: datetime

    class Config:
        orm_mode       = True
        from_attributes = True
