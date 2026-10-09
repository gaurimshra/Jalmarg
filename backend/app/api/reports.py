from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
from app.db.database import get_db
from app.db import crud
from app.schemas import pydantic_schemas
from app.services.orchestrator import process_report_upload

router = APIRouter()

@router.get("/", response_model=List[pydantic_schemas.ReportOut])
def get_reports(db: Session = Depends(get_db)):
    return crud.list_recent_reports(db, limit=100)

@router.get("/{report_id}", response_model=pydantic_schemas.ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = crud.get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.post("/", response_model=pydantic_schemas.ReportOut)
async def submit_report(
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: Optional[str] = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Validate file
    if not image.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Safe extension check
    ext = os.path.splitext(image.filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png']:
        raise HTTPException(status_code=400, detail="Invalid image format. Supported formats: .jpg, .jpeg, .png")
    
    # Limit upload size
    contents = image.file.read()
    if len(contents) > 10 * 1024 * 1024: # 10MB
        raise HTTPException(status_code=400, detail="File too large (limit 10MB)")

    # Save logic
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'uploads'))
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(data_dir, safe_filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    report = await process_report_upload(db, contents, file_path, latitude, longitude, description)
    return report
