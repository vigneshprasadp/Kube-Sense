from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from models.rca import DBRootCauseReport, RootCauseReport

router = APIRouter(prefix="/api/rca", tags=["rca"])

@router.get("", response_model=List[RootCauseReport])
def get_historical_reports(db: Session = Depends(get_db)):
    """
    Retrieve all historical root cause analysis reports.
    """
    return db.query(DBRootCauseReport).order_by(DBRootCauseReport.id.desc()).all()

@router.get("/active", response_model=Optional[RootCauseReport])
def get_active_report(db: Session = Depends(get_db)):
    """
    Retrieve the most recent root cause analysis report generated in the last 5 minutes.
    """
    time_limit = datetime.utcnow() - timedelta(minutes=5)
    report = db.query(DBRootCauseReport).filter(
        DBRootCauseReport.timestamp >= time_limit
    ).order_by(DBRootCauseReport.id.desc()).first()
    return report
