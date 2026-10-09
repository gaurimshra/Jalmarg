"""
weather.py  — FastAPI router for weather and risk endpoints.

Endpoints
─────────
GET  /api/weather/{hotspot_id}                    → latest cached snapshot
POST /api/weather/{hotspot_id}/refresh            → force live fetch
POST /api/hotspots/{hotspot_id}/recalculate-risk  → run risk engine
GET  /api/hotspots/{hotspot_id}/risk-history      → last N risk records

Every response includes a `data_source` field so the frontend can
display "LIVE", "CACHED", or "DEMO DATA" labels accurately.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import crud
from app.schemas.pydantic_schemas import (
    WeatherSnapshotOut,
    RiskRecordOut,
    RiskRefreshResponse,
)
from app.services import weather_service, risk_service

router = APIRouter()


# ── Weather endpoints ─────────────────────────────────────────────────────────

@router.get(
    "/{hotspot_id}",
    response_model=WeatherSnapshotOut,
    summary="Get latest weather snapshot for a hotspot",
)
async def get_weather(hotspot_id: int, db: Session = Depends(get_db)):
    """
    Returns the most recent stored weather snapshot for the hotspot.
    `data_source` will be "live", "cached", or "demo".
    Does NOT trigger a new fetch — use /refresh for that.
    """
    hotspot = crud.get_hotspot(db, hotspot_id)
    if hotspot is None:
        raise HTTPException(status_code=404, detail="Hotspot not found")

    cached = weather_service.get_cached_weather(db, hotspot_id)
    if cached is None:
        # No snapshot yet — trigger a live fetch transparently
        cached = await weather_service.fetch_weather(
            db, hotspot_id, hotspot.latitude, hotspot.longitude
        )
        if cached is None:
            raise HTTPException(status_code=503, detail="Weather data unavailable")

    return _weather_dict_to_schema(cached)


@router.post(
    "/{hotspot_id}/refresh",
    response_model=WeatherSnapshotOut,
    summary="Force-refresh weather from Open-Meteo",
)
async def refresh_weather(hotspot_id: int, db: Session = Depends(get_db)):
    """
    Bypasses the cache and fetches a fresh forecast from Open-Meteo.
    Falls back to demo data with `data_source: "demo"` if the network is unavailable.
    """
    hotspot = crud.get_hotspot(db, hotspot_id)
    if hotspot is None:
        raise HTTPException(status_code=404, detail="Hotspot not found")

    result = await weather_service.fetch_weather(
        db, hotspot_id, hotspot.latitude, hotspot.longitude, force_refresh=True
    )
    return _weather_dict_to_schema(result)


# ── Risk endpoints ────────────────────────────────────────────────────────────

@router.post(
    "/hotspots/{hotspot_id}/recalculate-risk",
    response_model=RiskRefreshResponse,
    summary="Recalculate flood risk for a hotspot",
)
async def recalculate_risk(hotspot_id: int, db: Session = Depends(get_db)):
    """
    Runs the risk engine using the latest stored weather snapshot plus
    eligible recent reports.  Persists a HotspotRiskRecord and updates
    the Hotspot.current_risk / risk_level fields.

    `data_source` explains whether weather came from live/cached/demo.
    """
    hotspot = crud.get_hotspot(db, hotspot_id)
    if hotspot is None:
        raise HTTPException(status_code=404, detail="Hotspot not found")

    # Retrieve weather — use cached if available; fetch otherwise
    weather = weather_service.get_cached_weather(db, hotspot_id)
    if weather is None:
        weather = await weather_service.fetch_weather(
            db, hotspot_id, hotspot.latitude, hotspot.longitude
        )

    precip_mm = weather.get("precipitation_values", 0.0) or 0.0
    w_source = weather.get("data_source", "local_calculation")
    is_demo = weather.get("is_demo", False)

    try:
        risk = risk_service.calculate_risk(
            db,
            hotspot_id,
            weather_precip_mm=precip_mm,
            is_demo=is_demo,
            weather_data_source=w_source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Re-fetch hotspot to reflect updated values
    db.refresh(hotspot)

    risk_record_out = RiskRecordOut(
        id=risk["id"],
        hotspot_id=risk["hotspot_id"],
        calculated_at=risk["calculated_at"],
        risk_score=risk["risk_score"],
        risk_category=risk["risk_category"],
        rainfall_signal=risk["rainfall_signal"],
        flood_evidence_signal=risk["flood_evidence_signal"],
        baseline_signal=risk["baseline_signal"],
        corroboration_signal=risk["corroboration_signal"],
        calculation_version=risk["calculation_version"],
        data_sources=risk["data_sources"],
        uncertainty_note=risk["uncertainty_note"],
        is_demo=risk["is_demo"],
    )

    overall_source = "demo" if is_demo else w_source
    return RiskRefreshResponse(
        hotspot_id=hotspot_id,
        risk_record=risk_record_out,
        hotspot_name=hotspot.name,
        hotspot_current_risk=hotspot.current_risk,
        hotspot_risk_level=hotspot.risk_level,
        data_source=overall_source,
    )


@router.get(
    "/hotspots/{hotspot_id}/risk-history",
    response_model=List[RiskRecordOut],
    summary="Get recent risk calculation records for a hotspot",
)
def get_risk_history(
    hotspot_id: int, limit: int = 10, db: Session = Depends(get_db)
):
    """Returns up to `limit` (default 10) recent risk records, newest first."""
    hotspot = crud.get_hotspot(db, hotspot_id)
    if hotspot is None:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    records = crud.get_risk_history(db, hotspot_id, limit=limit)
    return [_risk_record_to_schema(r) for r in records]


# ── Schema helpers ────────────────────────────────────────────────────────────

def _weather_dict_to_schema(d: dict) -> WeatherSnapshotOut:
    """Convert the weather service dict to a Pydantic model."""
    return WeatherSnapshotOut(
        id=d.get("id") or 0,
        hotspot_id=d.get("hotspot_id"),
        coordinates=d.get("coordinates", ""),
        retrieval_time=d.get("retrieval_time"),
        forecast_timestamp=d.get("forecast_timestamp"),
        precipitation_values=d.get("precipitation_values", 0.0),
        precipitation_probability=d.get("precipitation_probability"),
        precip_next_3h=d.get("precip_next_3h"),
        wind_speed=d.get("wind_speed"),
        source_kind=d.get("source_kind", "OPEN_METEO"),
        cache_key=d.get("cache_key"),
        is_cached=d.get("is_cached", False),
        is_demo=d.get("is_demo", False),
        data_source=d.get("data_source", "live"),
    )


def _risk_record_to_schema(r) -> RiskRecordOut:
    return RiskRecordOut(
        id=r.id,
        hotspot_id=r.hotspot_id,
        calculated_at=r.calculated_at,
        risk_score=r.risk_score,
        risk_category=r.risk_category,
        rainfall_signal=r.rainfall_signal,
        flood_evidence_signal=r.flood_evidence_signal,
        baseline_signal=r.baseline_signal,
        corroboration_signal=r.corroboration_signal,
        calculation_version=r.calculation_version,
        data_sources=r.data_sources,
        uncertainty_note=r.uncertainty_note,
        is_demo=r.is_demo,
    )
