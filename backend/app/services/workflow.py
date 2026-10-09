import os
from sqlalchemy.orm import Session
from app.db import crud
from app.schemas.pydantic_schemas import ReportCreate, AgentEventBase
from app.services.image_verification import verify_image_evidence
from app.services.gemini_vision import analyze_waterlogging_image
from datetime import datetime

def process_report_upload(db: Session, image_bytes: bytes, image_path: str, lat: float, lon: float, description: str = None):
    # 1. Create Base Report
    report_data = ReportCreate(
        description=description,
        latitude=lat,
        longitude=lon,
        image_path=image_path
    )
    report = crud.create_report(db, report_data)

    # 2. Add System Event (Ingestion)
    crud.create_agent_event(db, AgentEventBase(
        report_id=report.id,
        agent_name="System",
        tool_name="ingest_report",
        event_type="INGESTION",
        summary="Received report and saved image."
    ))

    # 3. Image Verification
    ver_results = verify_image_evidence(db, image_bytes, lat, lon)
    
    analysis_data = {
        "sha256_hash": ver_results.get("sha256_hash"),
        "perceptual_hash": ver_results.get("perceptual_hash"),
        "trust_score": ver_results.get("trust_score"),
        "verification_status": ver_results.get("status")
    }
    crud.update_report_analysis(db, report.id, analysis_data)

    crud.create_agent_event(db, AgentEventBase(
        report_id=report.id,
        agent_name="VerificationAgent",
        tool_name="verify_image_evidence",
        event_type="VERIFICATION",
        summary=f"Verification complete: {ver_results.get('status')}. Reasons: {', '.join(ver_results.get('explanation', []))}"
    ))

    # 4. Vision Analysis
    vision_res = analyze_waterlogging_image(image_path)
    vision_update = {
        "water_detected": vision_res["water_detected"],
        "severity": vision_res["severity"],
        "depth_min_cm": vision_res["depth_min_cm"],
        "depth_max_cm": vision_res["depth_max_cm"],
        "depth_confidence": vision_res["depth_confidence"],
        "analysis_source": vision_res.get("analysis_source")
    }
    crud.update_report_analysis(db, report.id, vision_update)

    crud.create_agent_event(db, AgentEventBase(
        report_id=report.id,
        agent_name="VisionAgent",
        tool_name="analyze_waterlogging_image",
        event_type="VISION_ANALYSIS",
        summary=f"Vision complete: {vision_res.get('status')}. {vision_res.get('explanation', '')}"
    ))
    
    # 5. Hotspot Association
    hotspots = crud.get_nearby_hotspots(db, lat, lon, radius=0.01)
    if hotspots:
        assoc = hotspots[0]
        crud.update_report_analysis(db, report.id, {"hotspot_id": assoc.id})
        crud.calculate_and_update_hotspot_state(db, assoc.id)

    # Re-fetch report
    db.refresh(report)
    return report
