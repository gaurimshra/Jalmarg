import json
from sqlalchemy.orm import Session
from app.db import crud
import logging

# Strands tools
from strands import tool
from typing import Annotated

# internal services
from app.services.image_verification import verify_image_evidence as raw_verify_image
from app.services.gemini_vision import analyze_waterlogging_image
from app.services.weather_service import fetch_weather
from app.services.risk_service import calculate_risk
from app.services.route_service import get_route_candidates

logger = logging.getLogger(__name__)

# To use DB within tools, we can either pass db around via context or inject it.
# Since strands tool context isn't fully configured here without a deeper look, 
# we'll inject a global or pass it explicitly to the orchestrator instead.
# For isolation, let's create factory functions that return the bound tool, OR
# use a module level session variable that the orchestrator binds.

_db_session: Session = None

def set_tool_db_session(db: Session):
    global _db_session
    _db_session = db

@tool(description="Verify a report's image metadata and perceptual hashes to detect tampering or deduplication.")
def verify_report(report_id: int) -> str:
    """Verifies image authenticity of a report."""
    if not _db_session:
        return json.dumps({"error": "DB session not injected"})
        
    report = crud.get_report(_db_session, report_id)
    if not report:
        return json.dumps({"error": f"Report {report_id} not found."})
        
    # Run deterministic verification
    ver_results = raw_verify_image(_db_session, None, report.latitude, report.longitude)
    
    # Save the result
    analysis_data = {
        "verification_status": ver_results.get("status"),
        "trust_score": ver_results.get("trust_score"),
        "sha256_hash": ver_results.get("sha256_hash", ""),
        "perceptual_hash": ver_results.get("perceptual_hash", "")
    }
    crud.update_report_analysis(_db_session, report.id, analysis_data)
    
    return json.dumps(analysis_data)


@tool(description="Estimate the visible water depth, severity, and context from a report's image.")
def estimate_water_severity(report_id: int) -> str:
    """Invokes vision models to deduce severity from the report image."""
    if not _db_session:
        return json.dumps({"error": "DB session not injected"})
        
    report = crud.get_report(_db_session, report_id)
    if not report or not report.image_path:
        return json.dumps({"error": "Report/Image not found."})
        
    vision_res = analyze_waterlogging_image(report.image_path)
    
    vision_update = {
        "water_detected": vision_res.get("water_detected"),
        "severity": vision_res.get("severity"),
        "depth_min_cm": vision_res.get("depth_min_cm"),
        "depth_max_cm": vision_res.get("depth_max_cm"),
        "depth_confidence": vision_res.get("depth_confidence"),
        "analysis_source": vision_res.get("analysis_source", "Gemini API")
    }
    crud.update_report_analysis(_db_session, report.id, vision_update)
    
    return json.dumps(vision_res)


@tool(description="Retrieve live weather and precipitation forecast for a given hotspot.")
async def get_rainfall_forecast(hotspot_id: int) -> str:
    """Gets weather data via Open Meteo API safely."""
    if not _db_session:
        return json.dumps({"error": "DB session not injected"})
        
    hotspot = crud.get_hotspot(_db_session, hotspot_id)
    if not hotspot:
        return json.dumps({"error": "Hotspot not found"})
        
    await fetch_weather(_db_session, hotspot_id, hotspot.latitude, hotspot.longitude, force_refresh=False)
    weather = crud.get_latest_weather_snapshot(_db_session, hotspot_id)
    
    if weather:
        return json.dumps({
            "precipitation_values": weather.precipitation_values,
            "precip_next_3h": weather.precip_next_3h,
            "source_kind": weather.source_kind
        })
    return json.dumps({"error": "Weather fetch failed"})


@tool(description="Calculate the quantitative deterministic risk profile for a flood hotspot.")
def calculate_hotspot_risk(hotspot_id: int) -> str:
    """Updates composite risk based on weather and recent verified reports."""
    if not _db_session:
        return json.dumps({"error": "DB session not injected"})
    
    recent_weather = crud.get_latest_weather_snapshot(_db_session, hotspot_id)
    recent_reports = crud.get_recent_reports_for_hotspot(_db_session, hotspot_id)
    hotspot = crud.get_hotspot(_db_session, hotspot_id)
    
    record = calculate_risk(hotspot_id, hotspot.risk_level if hotspot else "LOW", recent_weather, recent_reports)
    
    # Commit the changes to DB via crud helper
    crud.calculate_and_update_hotspot_state(_db_session, hotspot_id)
    
    return json.dumps({
        "risk_score": record.risk_score,
        "risk_category": record.risk_category,
        "rainfall_signal": record.rainfall_signal,
        "flood_evidence_signal": record.flood_evidence_signal,
        "corroboration_signal": record.corroboration_signal
    })


@tool(description="Determine if critical routes are flooded by checking origin/dest combinations.")
async def compare_routes(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, vehicle_type: str) -> str:
    """Yields exposure penalty scores for paths to check if intervention is requested on major arteries."""
    if not _db_session:
        return json.dumps({"error": "DB session not injected"})
        
    cands = await get_route_candidates(_db_session, origin_lat, origin_lng, dest_lat, dest_lng, vehicle_type, "safest")
    
    safe_cands = [c for c in cands if c["exposure_score"] < 20]
    return json.dumps({
        "total_routes": len(cands),
        "safe_routes_available": len(safe_cands),
        "fastest_exposure": cands[0]["exposure_score"] if cands else 0.0
    })

@tool(description="Recommend a dispatch or emergency deployment response based on accumulated severity/risk.")
def propose_dispatch_plan(hotspot_id: int, rationale: str, suggested_action: str) -> str:
    """Final action proposal marking an incident requiring structural response."""
    if not _db_session:
        return json.dumps({"error": "DB session not injected"})
        
    plan = crud.create_dispatch_plan(_db_session, {
        "hotspot_id": hotspot_id,
        "priority": "HIGH",
        "suggested_action": suggested_action,
        "explanation": rationale,
        "status": "PROPOSED"
    })
    
    # We will log it clearly to the generic events timeline so human supervisors see the dispatch recommendation.
    crud.create_agent_event(_db_session, crud.AgentEventBase(
        report_id=None,
        hotspot_id=hotspot_id,
        agent_name="DispatcherAgent",
        tool_name="propose_dispatch_plan",
        event_type="DISPATCH",
        summary=f"Recommend dispatch to Hotspot #{hotspot_id}. {rationale}"
    ))
    return json.dumps({"status": "Dispatch plan logged to authority dashboard successfully.", "plan_id": plan.id})

@tool(description="Retrieve public civic documentation related to municipal flooding protocols.")
async def retrieve_civic_guidance(query: str, rationale: str) -> str:
    """Uses Tinyfish API to fetch context on emergency preparedness/rules."""
    from app.services.tinyfish_service import retrieve_and_summarize
    
    res = await retrieve_and_summarize(query)
    
    if _db_session and not res.get("error"):
        crud.create_agent_event(_db_session, crud.AgentEventBase(
            report_id=None,
            agent_name="CivicKnowledgeAgent",
            tool_name="retrieve_civic_guidance",
            event_type="CIVIC_GUIDANCE",
            summary=json.dumps({
                "rationale": rationale,
                "title": res.get("title"),
                "url": res.get("url"),
                "content_preview": res.get("content_preview")
            })
        ))
        
    return json.dumps(res)
