import pytest
from app.services import route_service
from unittest.mock import MagicMock
import httpx
# pyrefly: ignore [missing-import]
import respx

class MockHotspot:
    def __init__(self, name, lat, lng, risk):
        self.name = name
        self.latitude = lat
        self.longitude = lng
        self.current_risk = risk

def mock_get_all_hotspots(db):
    return [
        MockHotspot("High Risk Area", 28.6200, 77.2150, 95.0), # lies perfectly on the demo_1 route
        MockHotspot("Low Risk Area", 29.000, 77.000, 10.0) # far away and low risk
    ]


@pytest.mark.asyncio
@respx.mock
async def test_route_osrm_success(mocker):
    # Mock OSMR public response
    respx.get(url__startswith=route_service.OSRM_BASE_URL).mock(return_value=httpx.Response(200, json={
        "routes": [
            {"geometry": {"type": "LineString", "coordinates": [[1,1], [2,2]]}, "duration": 100, "distance": 1000}
        ]
    }))
    mocker.patch("app.db.crud.get_all_hotspots", side_effect=mock_get_all_hotspots)
    
    candidates = await route_service.get_route_candidates(None, 1, 1, 2, 2, "Hatchback", "fastest")
    
    assert len(candidates) == 1
    assert candidates[0]["source"] == "OSRM"
    assert candidates[0]["is_simulated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_route_fallback_demo(mocker):
    # Mock OSMR failure
    respx.get(url__startswith=route_service.OSRM_BASE_URL).mock(side_effect=httpx.NetworkError("unreachable"))
    mocker.patch("app.db.crud.get_all_hotspots", side_effect=mock_get_all_hotspots)
    
    candidates = await route_service.get_route_candidates(None, 1, 1, 2, 2, "Hatchback", "fastest")
    
    assert len(candidates) == 2
    assert candidates[0]["source"] == "DEMO Fallback"
    assert candidates[0]["is_simulated"] is True


@pytest.mark.asyncio
async def test_route_exposure_and_vehicle_scoring(mocker):
    # Directly test the DEMO fallback to ensure exposure score uses shapely correctly
    mocker.patch("app.db.crud.get_all_hotspots", side_effect=mock_get_all_hotspots)
    # Patch httpx so it goes straight to the exception handler fallback
    mocker.patch("httpx.AsyncClient.get", side_effect=Exception("Failed"))

    # Hatchback (vulnerability 0.9)
    hatchback_cands = await route_service.get_route_candidates(None, 0, 0, 0, 0, "Hatchback", "safest")
    # demo_1 passes exactly over 77.2150, 28.6200 where the High Risk Area is
    demo1_h = next(c for c in hatchback_cands if c["id"] == "demo_1")
    assert demo1_h["exposure_score"] > 30.0 # High penalty
    
    # SUV (vulnerability 0.4)
    suv_cands = await route_service.get_route_candidates(None, 0, 0, 0, 0, "SUV", "safest")
    demo1_s = next(c for c in suv_cands if c["id"] == "demo_1")
    
    # SUV should have a much lower exposure score than Hatchback on the exact same route with the same flood
    assert demo1_s["exposure_score"] < demo1_h["exposure_score"]
