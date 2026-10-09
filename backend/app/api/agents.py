from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db import crud
from app.schemas import pydantic_schemas

router = APIRouter()

@router.get("/", response_model=List[pydantic_schemas.AgentEventOut])
def get_agent_events(db: Session = Depends(get_db)):
    return crud.list_agent_events(db, limit=100)
