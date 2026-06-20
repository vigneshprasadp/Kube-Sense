from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from models.alert import DBAlert, Alert, DBNetworkAlert, NetworkAlert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("", response_model=List[Alert])
def get_alerts(db: Session = Depends(get_db)):
    return db.query(DBAlert).order_by(DBAlert.id.desc()).all()

@router.get("/network", response_model=List[NetworkAlert])
def get_network_alerts(db: Session = Depends(get_db)):
    return db.query(DBNetworkAlert).order_by(DBNetworkAlert.id.desc()).all()
