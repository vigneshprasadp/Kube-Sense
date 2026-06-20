from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database.db import get_db
from models.forecast import DBForecast, Forecast

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])


@router.get("", response_model=List[Forecast])
def get_all_forecasts(db: Session = Depends(get_db)):
    """
    Return all forecast records ordered by most-recent first.
    Used by the frontend Forecast dashboard tab.
    """
    return db.query(DBForecast).order_by(DBForecast.id.desc()).all()


@router.get("/active", response_model=List[Forecast])
def get_active_forecasts(
    minutes: int = Query(default=10, description="Look-back window in minutes"),
    db: Session = Depends(get_db),
):
    """
    Return forecasts generated within the last N minutes.
    Useful for the 'live predictions' banner on the dashboard.
    """
    since = datetime.utcnow() - timedelta(minutes=minutes)
    return (
        db.query(DBForecast)
        .filter(DBForecast.timestamp >= since)
        .order_by(DBForecast.timestamp.desc())
        .all()
    )


@router.get("/critical", response_model=List[Forecast])
def get_critical_forecasts(db: Session = Depends(get_db)):
    """
    Return only Critical-severity forecasts (breach expected within 15 min).
    """
    since = datetime.utcnow() - timedelta(minutes=15)
    return (
        db.query(DBForecast)
        .filter(
            DBForecast.severity == "Critical",
            DBForecast.timestamp >= since,
        )
        .order_by(DBForecast.minutes_to_breach.asc())
        .all()
    )


@router.get("/summary")
def get_forecast_summary(db: Session = Depends(get_db)):
    """
    Return an aggregated summary of the latest forecast per resource type.
    """
    since = datetime.utcnow() - timedelta(minutes=10)
    rows  = db.query(DBForecast).filter(DBForecast.timestamp >= since).all()

    summary = {
        "cpu":             [],
        "storage":         [],
        "network_latency": [],
        "network_loss":    [],
    }
    seen = set()
    for row in rows:
        key = (row.resource_type, row.service_name)
        if key not in seen:
            seen.add(key)
            bucket = summary.get(row.resource_type)
            if bucket is not None:
                bucket.append({
                    "service_name":      row.service_name,
                    "current_value":     row.current_value,
                    "predicted_value":   row.predicted_value,
                    "threshold":         row.threshold,
                    "minutes_to_breach": row.minutes_to_breach,
                    "trend_slope":       row.trend_slope,
                    "r_squared":         row.r_squared,
                    "severity":          row.severity,
                    "message":           row.message,
                    "timestamp":         row.timestamp.isoformat(),
                })

    return summary
