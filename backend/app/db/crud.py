from sqlalchemy.orm import Session
from . import models
from app.schemas import pydantic_schemas

def get_report(db: Session, report_id: int):
    return db.query(models.Report).filter(models.Report.id == report_id).first()

def create_report(db: Session, report: pydantic_schemas.ReportCreate):
    db_report = models.Report(**report.model_dump())
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

def update_report_analysis(db: Session, report_id: int, analysis_data: dict):
    db_report = get_report(db, report_id)
    if db_report:
        for key, value in analysis_data.items():
            setattr(db_report, key, value)
        db.commit()
        db.refresh(db_report)
    return db_report

def get_nearby_hotspots(db: Session, lat: float, lon: float, radius: float = 0.05):
    # Simplified bounding box query for nearby hotspots
    return db.query(models.Hotspot).filter(
        models.Hotspot.latitude.between(lat - radius, lat + radius),
        models.Hotspot.longitude.between(lon - radius, lon + radius)
    ).all()

def list_recent_reports(db: Session, limit: int = 50):
    return db.query(models.Report).order_by(models.Report.created_at.desc()).limit(limit).all()

def create_agent_event(db: Session, event: pydantic_schemas.AgentEventBase):
    db_event = models.AgentEvent(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def list_agent_events(db: Session, limit: int = 50):
    return db.query(models.AgentEvent).order_by(models.AgentEvent.created_at.desc()).limit(limit).all()

def list_priority_hotspots(db: Session, limit: int = 10):
    return db.query(models.Hotspot).filter(
        models.Hotspot.risk_level.in_(["HIGH", "CRITICAL"])
    ).order_by(models.Hotspot.current_risk.desc()).limit(limit).all()

def get_hotspot(db: Session, hotspot_id: int):
    return db.query(models.Hotspot).filter(models.Hotspot.id == hotspot_id).first()

def calculate_and_update_hotspot_state(db: Session, hotspot_id: int):
    hotspot = get_hotspot(db, hotspot_id)
    if not hotspot:
        return None
    # Simplified calculation for demonstration
    reports = db.query(models.Report).filter(models.Report.hotspot_id == hotspot_id).all()
    # Assuming each report adds a little to the risk if water detected
    report_factor = sum(1.5 for r in reports if r.water_detected)
    new_risk = min(100.0, hotspot.baseline_risk + report_factor)
    hotspot.current_risk = new_risk
    if new_risk > 80:
        hotspot.risk_level = "CRITICAL"
    elif new_risk > 50:
        hotspot.risk_level = "HIGH"
    elif new_risk > 20:
        hotspot.risk_level = "MODERATE"
    else:
        hotspot.risk_level = "LOW"
    db.commit()
    db.refresh(hotspot)
    return hotspot

# ── Weather snapshot helpers ──────────────────────────────────────────────────

def get_latest_weather_snapshot(db: Session, hotspot_id: int):
    """Return the most recent WeatherSnapshot for this hotspot, or None."""
    return (
        db.query(models.WeatherSnapshot)
        .filter(models.WeatherSnapshot.hotspot_id == hotspot_id)
        .order_by(models.WeatherSnapshot.retrieval_time.desc())
        .first()
    )

def get_weather_snapshot_by_cache_key(db: Session, cache_key: str):
    """Lookup by cache key for TTL-based deduplication."""
    return (
        db.query(models.WeatherSnapshot)
        .filter(models.WeatherSnapshot.cache_key == cache_key)
        .order_by(models.WeatherSnapshot.retrieval_time.desc())
        .first()
    )

def save_weather_snapshot(db: Session, data: dict) -> models.WeatherSnapshot:
    """Persist a new WeatherSnapshot row and return it."""
    snap = models.WeatherSnapshot(**data)
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap

# ── Risk record helpers ───────────────────────────────────────────────────────

def get_latest_risk_record(db: Session, hotspot_id: int):
    """Return the most recent HotspotRiskRecord for this hotspot, or None."""
    return (
        db.query(models.HotspotRiskRecord)
        .filter(models.HotspotRiskRecord.hotspot_id == hotspot_id)
        .order_by(models.HotspotRiskRecord.calculated_at.desc())
        .first()
    )

def get_risk_history(db: Session, hotspot_id: int, limit: int = 10):
    """Return recent risk records ordered newest-first."""
    return (
        db.query(models.HotspotRiskRecord)
        .filter(models.HotspotRiskRecord.hotspot_id == hotspot_id)
        .order_by(models.HotspotRiskRecord.calculated_at.desc())
        .limit(limit)
        .all()
    )

def save_risk_record(db: Session, data: dict) -> models.HotspotRiskRecord:
    """Persist a new HotspotRiskRecord and return it."""
    rec = models.HotspotRiskRecord(**data)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec

def get_reports_for_risk(db: Session, hotspot_id: int, max_age_hours: float = 48.0):
    """
    Return reports for a hotspot that are fresher than max_age_hours.
    Excludes REJECTED_DUPLICATE entries (they must not inflate corroboration).
    """
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    return (
        db.query(models.Report)
        .filter(
            models.Report.hotspot_id == hotspot_id,
            models.Report.verification_status != "REJECTED_DUPLICATE",
            models.Report.created_at >= cutoff,
        )
        .all()
    )

def update_hotspot_risk_from_record(db: Session, hotspot_id: int, risk_score: float, risk_category: str):
    """Propagate a calculated risk score to the live Hotspot row."""
    hotspot = get_hotspot(db, hotspot_id)
    if hotspot:
        hotspot.current_risk = risk_score
        hotspot.risk_level = risk_category
        db.commit()
        db.refresh(hotspot)
    return hotspot

# ── Dispatch Plan helpers ───────────────────────────────────────────────────

def create_dispatch_plan(db: Session, data: dict):
    plan = models.DispatchPlan(**data)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

def list_dispatch_plans(db: Session, limit: int = 50):
    return db.query(models.DispatchPlan).order_by(models.DispatchPlan.proposed_at.desc()).limit(limit).all()

def update_dispatch_plan_status(db: Session, plan_id: int, status: str, approved_by: str):
    from datetime import datetime
    plan = db.query(models.DispatchPlan).filter(models.DispatchPlan.id == plan_id).first()
    if plan:
        plan.status = status
        plan.approved_by = approved_by
        if status in ["APPROVED", "REJECTED"]:
            plan.approved_at = datetime.utcnow()
        db.commit()
        db.refresh(plan)
    return plan
