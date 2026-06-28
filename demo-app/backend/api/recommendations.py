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
    from models.chaos_event import DBChaosEvent
    # 1. Fetch RCA report
    if rca_id:
        rca_report = db.query(DBRootCauseReport).filter(DBRootCauseReport.id == rca_id).first()
        if not rca_report:
            raise HTTPException(status_code=404, detail=f"RCA Report with ID {rca_id} not found.")
    else:
        # Check if there is an active chaos — prefer its RCA if available
        active_chaos = db.query(DBChaosEvent).filter(
            DBChaosEvent.status == "active"
        ).order_by(DBChaosEvent.id.desc()).first()

        if active_chaos:
            rca_report = db.query(DBRootCauseReport).filter(
                DBRootCauseReport.timestamp >= active_chaos.start_time
            ).order_by(DBRootCauseReport.id.desc()).first()

        if not active_chaos or not rca_report:
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
async def get_latest_recommendation(db: Session = Depends(get_db)):
    """
    Retrieve the most recent generated recommendation report, matched to the
    most recent RCA so that the explanation always reflects the current incident.
    If no recommendation exists for the latest RCA, dynamically generate it.
    """
    # First try to find recommendation tied to the most recent RCA report
    latest_rca = db.query(DBRootCauseReport).order_by(DBRootCauseReport.id.desc()).first()
    if latest_rca:
        # Look for a recommendation linked to this RCA
        db_rec = db.query(DBRecommendation).filter(
            DBRecommendation.rca_id == latest_rca.id
        ).order_by(DBRecommendation.id.desc()).first()
        if db_rec:
            return format_recommendation_response(db_rec)
        # Also check by root_cause string match (for recommendations created before rca_id linking)
        db_rec = db.query(DBRecommendation).filter(
            DBRecommendation.root_cause == latest_rca.root_cause
        ).order_by(DBRecommendation.id.desc()).first()
        if db_rec:
            return format_recommendation_response(db_rec)
            
        # Dynamically generate on-the-fly if not found
        try:
            db_rec = await generate_recommendation(latest_rca, db)
            if db_rec:
                return format_recommendation_response(db_rec)
        except Exception as e:
            print(f"[Recommendation API] Failed to dynamically generate recommendation: {e}")
            
    # Fallback: absolute latest recommendation row
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
