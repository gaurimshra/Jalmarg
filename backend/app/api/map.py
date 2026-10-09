from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import crud

router = APIRouter()

@router.get("/overview")
def get_map_overview(db: Session = Depends(get_db)):
    hotspots = db.query(crud.models.Hotspot).all()
    # Serialize to standard json easily usable by frontend (GeoJSON like or simple points array)
    results = []
    for h in hotspots:
        results.append({
            "id": h.id,
            "name": h.name,
            "coordinates": [h.longitude, h.latitude], # standard [lng, lat] for maplibre
            "risk_level": h.risk_level,
            "current_risk": h.current_risk,
            "is_simulated": h.is_simulated
        })
    return {"data": results}
