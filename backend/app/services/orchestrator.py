import json
import logging
from sqlalchemy.orm import Session
from app.db import crud
from app.schemas.pydantic_schemas import AgentEventBase, ReportCreate
from app.config import settings
from strands import Agent
from strands.models import GeminiModel

from app.services.agent_tools import (
    set_tool_db_session,
    verify_report,
    estimate_water_severity,
    get_rainfall_forecast,
    calculate_hotspot_risk,
    compare_routes,
    propose_dispatch_plan,
    retrieve_civic_guidance
)

logger = logging.getLogger(__name__)

# Predefined fallback logic for when Gemini isn't available
async def deterministic_fallback_process(db: Session, report_id: int, lat: float, lon: float):
    # Log fallback init
    crud.create_agent_event(db, AgentEventBase(
        report_id=report_id,
        agent_name="Supervisor",
        tool_name="init",
        event_type="FALLBACK_INIT",
        summary="LLM unavailable. Falling back to deterministic pipeline."
    ))
    
    # 1. Verify
    verify_str = verify_report(report_id)
    crud.create_agent_event(db, AgentEventBase(
        report_id=report_id,
        agent_name="Verifier",
        tool_name="verify_report",
        event_type="VERIFICATION",
        summary=f"Result: {verify_str}"
    ))

    # 2. Vision
    vision_str = estimate_water_severity(report_id)
    crud.create_agent_event(db, AgentEventBase(
        report_id=report_id,
        agent_name="DepthAgent",
        tool_name="estimate_water_severity",
        event_type="VISION_ANALYSIS",
        summary=f"Result: {vision_str}"
    ))
    
    # 3. Associate and Risk
    hotspots = crud.get_nearby_hotspots(db, lat, lon)
    if hotspots:
        hid = hotspots[0].id
        crud.update_report_analysis(db, report_id, {"hotspot_id": hid})
        
        # Weather
        w_res = await get_rainfall_forecast(hid)
        crud.create_agent_event(db, AgentEventBase(
            report_id=report_id,
            agent_name="ForecastAgent",
            tool_name="get_rainfall_forecast",
            event_type="WEATHER",
            summary=f"Result: {w_res}"
        ))

        # Risk
        r_res = calculate_hotspot_risk(hid)
        crud.create_agent_event(db, AgentEventBase(
            report_id=report_id,
            agent_name="RiskAssessor",
            tool_name="calculate_hotspot_risk",
            event_type="RISK",
            summary=f"Result: {r_res}"
        ))
        
        # Routing demo check
        route_res = await compare_routes(lat, lon, lat+0.01, lon+0.01, "Hatchback")
        crud.create_agent_event(db, AgentEventBase(
            report_id=report_id,
            agent_name="RoutingAgent",
            tool_name="compare_routes",
            event_type="ROUTING",
            summary=f"Result: {route_res}"
        ))
        
        try:
            r_dict = json.loads(r_res)
            if r_dict.get("risk_category") in ["HIGH", "CRITICAL"]:
                disp_res = propose_dispatch_plan(hid, "DETERMINISTIC rule triggered high/critical severity.", "Investigate drainage and assess pump requirement.")
        except Exception:
            pass


async def agentic_llm_process(db: Session, report_id: int):
    # Setup LLM model
    model = GeminiModel(model_id=settings.GEMINI_MODEL, client_args={"api_key": settings.GEMINI_API_KEY})
    
    tools = [
        verify_report,
        estimate_water_severity,
        get_rainfall_forecast,
        calculate_hotspot_risk,
        compare_routes,
        propose_dispatch_plan,
        retrieve_civic_guidance
    ]

    sys_prompt = f"""You are the JalMarg Supervisor Agent.
A new citizen report ID {report_id} was just uploaded.
Your workflow:
1. Verify the report via verify_report.
2. If verification passes, estimate water severity from the image via estimate_water_severity.
3. If it looks like a threat, retrieve rainfall forecast. 
4. Calculate hotspot risk to see if it escalated.
5. If the hazard lies near critical paths, compare routes.
6. Retrieve public civic guidelines using retrieve_civic_guidance if you need municipal context before an emergency call.
7. Propose a dispatch if you consider it an emergency.

Evaluate the evidence at each step and decide what to do next. Do not execute unnecessary tools if the report is fake or dry.

MAX ITERATIONS: 5
"""
    agent = Agent(model=model, system_prompt=sys_prompt, tools=tools)

    crud.create_agent_event(db, AgentEventBase(
        report_id=report_id,
        agent_name="Supervisor",
        tool_name="init",
        event_type="AGENTIC_INIT",
        summary="Strands + Gemini analyzing report workflow."
    ))
    
    try:
        # Run agent
        response = await agent.run(f"Start analysis on report_id {report_id}")
        
        crud.create_agent_event(db, AgentEventBase(
            report_id=report_id,
            agent_name="Supervisor",
            tool_name="final_decision",
            event_type="CONCLUSION",
            summary=response.content
        ))
    except Exception as e:
        logger.error(f"Agent trapped inside execution limit or failed: {e}")
        crud.create_agent_event(db, AgentEventBase(
            report_id=report_id,
            agent_name="Supervisor",
            tool_name="run",
            event_type="ERROR",
            summary=f"Agent orchestration halted: {str(e)}"
        ))


async def process_report_upload(db: Session, image_bytes: bytes, image_path: str, lat: float, lon: float, description: str = None):
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

    # Pass DB to tools 
    set_tool_db_session(db)

    # 3. Route Workload logic directly evaluating API keys
    try:
        if settings.GEMINI_API_KEY:
            await agentic_llm_process(db, report.id)
        else:
            await deterministic_fallback_process(db, report.id, lat, lon)
    except Exception as e:
        logger.error(f"Process pipeline crashed: {e}")

    # Re-fetch report
    db.refresh(report)
    return report
