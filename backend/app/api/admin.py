from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db import crud
from app.schemas import pydantic_schemas

router = APIRouter()

@router.get("/priority-hotspots", response_model=List[pydantic_schemas.HotspotOut])
def get_priority_hotspots(db: Session = Depends(get_db)):
    return crud.list_priority_hotspots(db)

@router.get("/dispatch-plans", response_model=List[pydantic_schemas.DispatchPlanOut])
def get_dispatch_plans(db: Session = Depends(get_db)):
    return crud.list_dispatch_plans(db)

@router.patch("/dispatch-plans/{plan_id}/status", response_model=pydantic_schemas.DispatchPlanOut)
def update_dispatch_plan_status(
    plan_id: int, 
    update: pydantic_schemas.DispatchPlanStatusUpdate,
    db: Session = Depends(get_db)
):
    from fastapi import HTTPException
    plan = crud.update_dispatch_plan_status(db, plan_id, update.status, update.approved_by)
    if not plan:
        raise HTTPException(status_code=404, detail="Dispatch plan not found")
    
    # Also log an event when human takes action
    crud.create_agent_event(db, pydantic_schemas.AgentEventBase(
        hotspot_id=plan.hotspot_id,
        agent_name="DEMO AUTHORITY USER",
        tool_name="human_approval",
        event_type="HUMAN_ACTION",
        summary=f"Human {update.status} dispatch plan #{plan_id}.",
        source_kind="HUMAN"
    ))
    return plan
