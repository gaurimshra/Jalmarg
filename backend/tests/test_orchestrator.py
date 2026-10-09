import pytest
from app.services import orchestrator
from app.schemas.pydantic_schemas import AgentEventBase
from app.db import crud
import mock

def mock_verify_report(report_id):
    return '{"verification_status": "VERIFIED", "trust_score": 0.95}'

def mock_estimate_water_severity(report_id):
    return '{"severity": "CRITICAL"}'

async def mock_get_rainfall_forecast(hotspot_id):
    return '{"precipitation_values": 20.0}'

def mock_calculate_hotspot_risk(hotspot_id):
    return '{"risk_category": "CRITICAL", "risk_score": 90.0}'

async def mock_compare_routes(origin_lat, origin_lng, dest_lat, dest_lng, vehicle_type):
    return '{"safe_routes_available": 1, "total_routes": 3, "fastest_exposure": 25.0}'

@pytest.mark.asyncio
async def test_deterministic_fallback_process(mocker):
    # Mock crud
    mocker.patch("app.db.crud.create_agent_event")
    mocker.patch("app.db.crud.get_nearby_hotspots", return_value=[mock.Mock(id=1)])
    mocker.patch("app.db.crud.update_report_analysis")
    
    # Mock tools
    mocker.patch("app.services.orchestrator.verify_report", side_effect=mock_verify_report)
    mocker.patch("app.services.orchestrator.estimate_water_severity", side_effect=mock_estimate_water_severity)
    mocker.patch("app.services.orchestrator.get_rainfall_forecast", side_effect=mock_get_rainfall_forecast)
    mocker.patch("app.services.orchestrator.calculate_hotspot_risk", side_effect=mock_calculate_hotspot_risk)
    mocker.patch("app.services.orchestrator.compare_routes", side_effect=mock_compare_routes)
    mocker.patch("app.services.orchestrator.propose_dispatch_plan", return_value='{"status": "ok"}')

    await orchestrator.deterministic_fallback_process(None, report_id=10, lat=28.6, lon=77.2)

    # Basic validations that everything ran
    assert crud.create_agent_event.call_count >= 5
    
    # Find the FALLBACK_INIT event
    calls = crud.create_agent_event.call_args_list
    fallback_init = any(c[0][1].event_type == "FALLBACK_INIT" for c in calls)
    assert fallback_init

@pytest.mark.asyncio
async def test_tool_registration_mocked(mocker):
    # Verify strands agent executes tools
    from strands import Agent
    from strands.models import GeminiModel

    class FakeResponse:
        def __init__(self, content):
            self.content = content

    class FakeAgent(Agent):
        async def run(self, input):
            return FakeResponse("Mocked Response")
    
    mocker.patch("app.services.orchestrator.Agent", new=FakeAgent)
    mocker.patch("app.db.crud.create_agent_event")

    await orchestrator.agentic_llm_process(None, 100)

    # Verify agentic init event
    calls = crud.create_agent_event.call_args_list
    assert any(c[0][1].event_type == "AGENTIC_INIT" for c in calls)
    assert any(c[0][1].event_type == "CONCLUSION" for c in calls)
