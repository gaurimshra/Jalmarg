import pytest
import httpx
from datetime import datetime, timezone, timedelta
from app.services import weather_service
from app.db import crud
import respx

@pytest.fixture
def dummy_weather_snap():
    return {
        "id": 1,
        "hotspot_id": 1,
        "coordinates": "28.123,77.456",
        "retrieval_time": datetime.now(timezone.utc),
        "forecast_timestamp": datetime.now(timezone.utc),
        "precipitation_values": 0.5,
        "precipitation_probability": 10.0,
        "precip_next_3h": 1.5,
        "wind_speed": 10.0,
        "source_kind": "OPEN_METEO",
        "cache_key": "28.123_77.456_20261010_10",
        "is_demo": False
    }

class MockSnapshot:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


@pytest.mark.asyncio
async def test_fetch_weather_cached(mocker):
    # If cached entry exists and is fresh, no network call should be made
    snap = MockSnapshot(
        id=1, hotspot_id=1, coordinates="28.123,77.456",
        retrieval_time=datetime.now(timezone.utc),
        forecast_timestamp=datetime.now(timezone.utc),
        precipitation_values=0.5, precipitation_probability=10.0,
        precip_next_3h=1.5, wind_speed=10.0,
        source_kind="OPEN_METEO", cache_key="cache_key", is_demo=False
    )
    mocker.patch("app.db.crud.get_weather_snapshot_by_cache_key", return_value=snap)
    spy = mocker.spy(weather_service, "_call_open_meteo")
    
    result = await weather_service.fetch_weather(None, 1, 28.123, 77.456)
    
    assert spy.call_count == 0
    assert result["is_cached"] is True
    assert result["data_source"] == "cached"
    assert result["precipitation_values"] == 0.5


@respx.mock
@pytest.mark.asyncio
async def test_fetch_weather_live_success(mocker):
    mocker.patch("app.db.crud.get_weather_snapshot_by_cache_key", return_value=None)
    mock_save = mocker.patch("app.db.crud.save_weather_snapshot")
    mock_save.return_value = MockSnapshot(
        id=1, hotspot_id=1, coordinates="28.123,77.456",
        retrieval_time=datetime.now(timezone.utc),
        forecast_timestamp=datetime.now(timezone.utc),
        precipitation_values=4.2, precipitation_probability=50.0,
        precip_next_3h=10.0, wind_speed=15.0,
        source_kind="OPEN_METEO", cache_key="cache_key", is_demo=False
    )
    
    # Mock Open Meteo response
    now_iso = datetime.now(timezone.utc).isoformat()
    respx.get(weather_service.OPEN_METEO_URL).mock(return_value=httpx.Response(200, json={
        "hourly": {
            "time": [now_iso, (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()],
            "precipitation": [4.2, 5.8],
            "precipitation_probability": [50.0, 60.0],
            "windspeed_10m": [15.0, 16.0]
        }
    }))
    
    result = await weather_service.fetch_weather(None, 1, 28.123, 77.456)
    
    assert result["is_cached"] is False
    assert result["data_source"] == "live"
    assert result["is_demo"] is False
    assert result["precipitation_values"] == 4.2


@respx.mock
@pytest.mark.asyncio
async def test_fetch_weather_network_failure(mocker):
    mocker.patch("app.db.crud.get_weather_snapshot_by_cache_key", return_value=None)
    
    # Simulate network failure to hit the demo fallback
    respx.get(weather_service.OPEN_METEO_URL).mock(side_effect=httpx.NetworkError("Network unreachable"))
    
    result = await weather_service.fetch_weather(None, 2, 28.123, 77.456)
    
    assert result["is_cached"] is False
    assert result["is_demo"] is True
    assert result["data_source"] == "demo"
    assert result["_fallback_reason"] == "network_error"
    # Hotspot 2 has a specific demo fallback in weather_service: 4.2
    assert result["precipitation_values"] == 4.2
