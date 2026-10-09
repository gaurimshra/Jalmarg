"""
weather_service.py
──────────────────
Fetches hourly precipitation forecasts from the Open-Meteo public API
(no API key required for the free tier endpoint).

Cache strategy
──────────────
We store every successful response as a WeatherSnapshot row with a
cache_key = "<lat3dp>_<lon3dp>_<YYYYMMDD_HH>".  If a fresh snapshot
(≤ CACHE_TTL_MINUTES old) already exists for that key we return it
without making a network call.

Error handling
──────────────
Network errors, timeouts, and malformed responses are caught and logged.
When the live fetch fails we return a clearly-labelled demo fallback so
the rest of the system never receives None.

Open-Meteo endpoint being used
───────────────────────────────
https://api.open-meteo.com/v1/forecast
  ?latitude=<lat>
  &longitude=<lon>
  &hourly=precipitation,precipitation_probability,windspeed_10m
  &forecast_days=2
  &timezone=auto
"""

import json
import logging
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy.orm import Session

from app.db import crud

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_MINUTES = 30
REQUEST_TIMEOUT_SECONDS = 10.0
# Number of upcoming hourly slots to sum for precip_next_3h
NEXT_HOURS = 3

# ── Demo fallback values (clearly labelled, not real forecasts) ───────────────
# These are synthetic numbers used ONLY when a live fetch fails.
_DEMO_PRECIP = {
    # hotspot_id → mm  (rough illustrative values by location)
    1: 18.5,   # Minto Bridge — storm scenario
    2: 4.2,    # ITO — light rain
    3: 21.0,   # Pul Prahladpur — heavy rain
    4: 0.0,    # Zakhira — clear sky
    5: 6.0,    # IFFCO Chowk — drizzle
    6: 0.2,    # Subroto Park — trace
    7: 1.0,    # Dhaula Kuan — trace
    8: 0.5,    # Rajiv Chowk — trace
}
_DEFAULT_DEMO_PRECIP = 2.0


# ── Public API ────────────────────────────────────────────────────────────────

async def fetch_weather(
    db: Session,
    hotspot_id: int,
    lat: float,
    lon: float,
    force_refresh: bool = False,
) -> dict:
    """
    Return a weather data dict for the given hotspot coordinates.

    The returned dict always contains:
        precipitation_values    float  mm at closest forecast hour
        precipitation_probability float  0–100 %
        precip_next_3h          float  mm summed over next 3 hours
        wind_speed              float  km/h
        forecast_timestamp      str ISO-8601 or None
        is_cached               bool
        is_demo                 bool
        data_source             str  "live" | "cached" | "demo"
        cache_key               str
    """
    cache_key = _build_cache_key(lat, lon)

    if not force_refresh:
        cached = crud.get_weather_snapshot_by_cache_key(db, cache_key)
        if cached and _is_fresh(cached):
            return _snapshot_to_dict(cached, is_cached=True)

    # Attempt live fetch
    try:
        raw = await _call_open_meteo(lat, lon)
        parsed = _parse_response(raw, lat, lon)
        snap_data = {
            "hotspot_id": hotspot_id,
            "coordinates": f"{lat},{lon}",
            "forecast_timestamp": parsed["forecast_timestamp"],
            "precipitation_values": parsed["precipitation_values"],
            "precipitation_probability": parsed["precipitation_probability"],
            "precip_next_3h": parsed["precip_next_3h"],
            "wind_speed": parsed["wind_speed"],
            "source_kind": "OPEN_METEO",
            "cache_key": cache_key,
            "is_cached": False,
            "is_demo": False,
        }
        snap = crud.save_weather_snapshot(db, snap_data)
        return _snapshot_to_dict(snap, is_cached=False)

    except httpx.TimeoutException:
        logger.warning("Open-Meteo timeout for hotspot %s", hotspot_id)
        return _demo_fallback(hotspot_id, lat, lon, cache_key, reason="timeout")
    except httpx.NetworkError as exc:
        logger.warning("Open-Meteo network error for hotspot %s: %s", hotspot_id, exc)
        return _demo_fallback(hotspot_id, lat, lon, cache_key, reason="network_error")
    except _WeatherParseError as exc:
        logger.warning("Open-Meteo parse error for hotspot %s: %s", hotspot_id, exc)
        return _demo_fallback(hotspot_id, lat, lon, cache_key, reason=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected weather error for hotspot %s: %s", hotspot_id, exc)
        return _demo_fallback(hotspot_id, lat, lon, cache_key, reason="unexpected")


def get_cached_weather(db: Session, hotspot_id: int) -> dict | None:
    """
    Return the latest stored snapshot for this hotspot (may be expired).
    Returns None if no snapshot has ever been stored.
    """
    snap = crud.get_latest_weather_snapshot(db, hotspot_id)
    if snap is None:
        return None
    return _snapshot_to_dict(snap, is_cached=True)


# ── Internal helpers ──────────────────────────────────────────────────────────

class _WeatherParseError(Exception):
    """Raised when the Open-Meteo response is structurally invalid."""


def _build_cache_key(lat: float, lon: float) -> str:
    """
    Key = "<lat rounded to 3dp>_<lon rounded to 3dp>_<YYYYMMDD_HH>".
    This means one cached entry per ~111m grid cell per hour.
    """
    now_utc = datetime.now(timezone.utc)
    return f"{lat:.3f}_{lon:.3f}_{now_utc.strftime('%Y%m%d_%H')}"


def _is_fresh(snap) -> bool:
    """True if the snapshot was retrieved within CACHE_TTL_MINUTES."""
    if snap.retrieval_time is None:
        return False
    rt = snap.retrieval_time
    if rt.tzinfo is None:
        rt = rt.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - rt
    return age < timedelta(minutes=CACHE_TTL_MINUTES)


async def _call_open_meteo(lat: float, lon: float) -> dict:
    """Make the HTTP request to Open-Meteo (raises httpx exceptions on failure)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,precipitation_probability,windspeed_10m",
        "forecast_days": 2,
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)

    if resp.status_code == 429:
        raise _WeatherParseError("rate_limit")
    if resp.status_code != 200:
        raise _WeatherParseError(f"http_{resp.status_code}")

    try:
        return resp.json()
    except Exception:
        raise _WeatherParseError("invalid_json")


def _parse_response(raw: dict, lat: float, lon: float) -> dict:
    """
    Extract the nearest-hour precipitation values from the Open-Meteo payload.

    Open-Meteo returns parallel arrays under `hourly`:
        time[]                      ISO-8601 strings
        precipitation[]             mm per hour
        precipitation_probability[] 0–100 %
        windspeed_10m[]             km/h

    We find the index whose timestamp is closest to now (UTC) and read
    values there, then sum the next NEXT_HOURS slots for precip_next_3h.
    """
    try:
        hourly = raw["hourly"]
        times = hourly["time"]
        precips = hourly["precipitation"]
    except KeyError as exc:
        raise _WeatherParseError(f"missing_field:{exc}") from exc

    if not times:
        raise _WeatherParseError("empty_time_array")

    now_utc = datetime.now(timezone.utc)

    # Find closest hour index
    best_idx = 0
    best_diff = float("inf")
    for i, t_str in enumerate(times):
        try:
            t = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            diff = abs((t - now_utc).total_seconds())
            if diff < best_diff:
                best_diff = diff
                best_idx = i
        except ValueError:
            continue

    def _safe(arr, idx, default=0.0):
        try:
            val = arr[idx]
            return float(val) if val is not None else default
        except (IndexError, TypeError):
            return default

    precip = _safe(precips, best_idx)
    prob_arr = hourly.get("precipitation_probability") or []
    wind_arr = hourly.get("windspeed_10m") or []
    prob = _safe(prob_arr, best_idx)
    wind = _safe(wind_arr, best_idx)

    # Sum next NEXT_HOURS slots for accumulated outlook
    next3 = sum(
        _safe(precips, best_idx + offset)
        for offset in range(1, NEXT_HOURS + 1)
    )

    forecast_ts = None
    try:
        forecast_ts = datetime.fromisoformat(times[best_idx].replace("Z", "+00:00"))
    except (ValueError, IndexError):
        pass

    return {
        "precipitation_values": round(precip, 2),
        "precipitation_probability": round(prob, 1),
        "precip_next_3h": round(next3, 2),
        "wind_speed": round(wind, 1),
        "forecast_timestamp": forecast_ts,
    }


def _snapshot_to_dict(snap, *, is_cached: bool) -> dict:
    """Convert a WeatherSnapshot ORM row to the standard return dict."""
    data_source = "demo" if snap.is_demo else ("cached" if is_cached else "live")
    # Normalise retrieval_time to tz-aware
    rt = snap.retrieval_time
    if rt and rt.tzinfo is None:
        rt = rt.replace(tzinfo=timezone.utc)
    return {
        "id": snap.id,
        "hotspot_id": snap.hotspot_id,
        "coordinates": snap.coordinates,
        "retrieval_time": rt,
        "forecast_timestamp": snap.forecast_timestamp,
        "precipitation_values": snap.precipitation_values or 0.0,
        "precipitation_probability": snap.precipitation_probability,
        "precip_next_3h": snap.precip_next_3h,
        "wind_speed": snap.wind_speed,
        "source_kind": snap.source_kind,
        "cache_key": snap.cache_key,
        "is_cached": is_cached,
        "is_demo": snap.is_demo,
        "data_source": data_source,
    }


def _demo_fallback(
    hotspot_id: int, lat: float, lon: float, cache_key: str, reason: str
) -> dict:
    """
    Return synthetic weather data clearly marked as demo.
    These values are prototype placeholders — NOT real forecasts.
    """
    precip = _DEMO_PRECIP.get(hotspot_id, _DEFAULT_DEMO_PRECIP)
    return {
        "id": None,
        "hotspot_id": hotspot_id,
        "coordinates": f"{lat},{lon}",
        "retrieval_time": datetime.now(timezone.utc),
        "forecast_timestamp": None,
        "precipitation_values": precip,
        "precipitation_probability": min(precip * 3.5, 100.0),
        "precip_next_3h": round(precip * 1.2, 2),
        "wind_speed": 12.0,
        "source_kind": "DEMO_FALLBACK",
        "cache_key": cache_key,
        "is_cached": False,
        "is_demo": True,
        "data_source": "demo",
        "_fallback_reason": reason,
    }
