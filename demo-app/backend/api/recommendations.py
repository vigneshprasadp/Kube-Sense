import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from models.rca import DBRootCauseReport
from models.recommendation import DBRecommendation, RecommendationReport
from recommendation.recommendation_engine import generate_recommendation

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

def format_recommendation_response(db_rec: DBRecommendation) -> dict:
    """
    Helper to deserialize JSON list strings stored in the DB back into Python lists
    for Pydantic validation.
    """
    if not db_rec:
        return None
    
    # Safely load recommended_fixes list
    try:
        fixes = json.loads(db_rec.recommended_fixes)
        if not isinstance(fixes, list):
            fixes = [str(fixes)]
    except Exception:
        fixes = [db_rec.recommended_fixes] if db_rec.recommended_fixes else []

    # Safely load preventive_measures list
    try:
        prev = json.loads(db_rec.preventive_measures)
        if not isinstance(prev, list):
            prev = [str(prev)]
    except Exception:
        prev = [db_rec.preventive_measures] if db_rec.preventive_measures else []
        
    return {
        "id": db_rec.id,
        "rca_id": db_rec.rca_id,
        "root_cause": db_rec.root_cause,
        "severity": db_rec.severity,
        "affected_services": db_rec.affected_services,
        "explanation": db_rec.explanation,
        "recommended_fixes": fixes,
        "preventive_measures": prev,
        "timestamp": db_rec.timestamp
    }

@router.post("/generate", response_model=RecommendationReport)
async def trigger_generation(rca_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Generate SRE recommendation narrative for a specific RCA report (or the latest report).
    """
    # 1. Fetch RCA report
    if rca_id:
        rca_report = db.query(DBRootCauseReport).filter(DBRootCauseReport.id == rca_id).first()
        if not rca_report:
            raise HTTPException(status_code=404, detail=f"RCA Report with ID {rca_id} not found.")
    else:
        # Fall back to latest RCA report
        rca_report = db.query(DBRootCauseReport).order_by(DBRootCauseReport.id.desc()).first()
        if not rca_report:
            raise HTTPException(status_code=400, detail="No RCA reports found in database to generate recommendations for.")
            
    # 2. Call engine to generate and save recommendation
    try:
        db_rec = await generate_recommendation(rca_report, db)
        return format_recommendation_response(db_rec)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendation: {str(e)}")

@router.get("/latest", response_model=Optional[RecommendationReport])
def get_latest_recommendation(db: Session = Depends(get_db)):
    """
    Retrieve the most recent generated recommendation report.
    """
    db_rec = db.query(DBRecommendation).order_by(DBRecommendation.id.desc()).first()
    if not db_rec:
        return None
    return format_recommendation_response(db_rec)

@router.get("", response_model=List[RecommendationReport])
def get_all_recommendations(db: Session = Depends(get_db)):
    """
    Retrieve all historical recommendation reports.
    """
    recs = db.query(DBRecommendation).order_by(DBRecommendation.id.desc()).all()
    return [format_recommendation_response(r) for r in recs]
