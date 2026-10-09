from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db import crud
from app.schemas import pydantic_schemas

router = APIRouter()

@router.get("/", response_model=List[pydantic_schemas.HotspotOut])
def get_hotspots(db: Session = Depends(get_db)):
    # simple listing function in crud, let's write it inline here or in crud
    hotspots = db.query(crud.models.Hotspot).all()
    return hotspots

@router.get("/{hotspot_id}", response_model=pydantic_schemas.HotspotOut)
def get_hotspot(hotspot_id: int, db: Session = Depends(get_db)):
    hotspot = crud.get_hotspot(db, hotspot_id)
    if not hotspot:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    return hotspot
