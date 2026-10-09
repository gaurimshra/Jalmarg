import logging
import math
from datetime import datetime
from typing import List, Dict, Any
import httpx
from shapely.geometry import LineString, Point

from app.db import crud
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"
REQUEST_TIMEOUT_SECONDS = 10.0

# Vehicle penalties. 0 means unaffected, 1.0 means severely affected by flooded segments.
VEHICLE_VULNERABILITY = {
    "Bike": 1.0,
    "Hatchback": 0.9,
    "Sedan": 0.7,
    "SUV": 0.4
}

# Add a pre-defined demo fallback to bypass network issues.
DEMO_ROUTES = {
    "demo_id": {
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.2090, 28.6139],
                [77.2150, 28.6200],
                [77.2210, 28.6250],
            ]
        },
        "duration": 600,
        "distance": 2500
    },
    "demo_id_2": {
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.2090, 28.6139],
                [77.2000, 28.6300],
                [77.2210, 28.6250],
            ]
        },
        "duration": 900,
        "distance": 3200
    }
}


async def get_route_candidates(db: Session, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, vehicle_type: str, strategy: str) -> List[Dict[str, Any]]:
    """
    Fetch routes from OSRM, calculate flood exposure, and rank candidates.
    """
    candidates = []
    try:
        url = f"{OSRM_BASE_URL}/{origin_lng},{origin_lat};{dest_lng},{dest_lat}?overview=full&geometries=geojson&alternatives=true"
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.get(url)
            
        if resp.status_code == 200:
            data = resp.json()
            routes = data.get("routes", [])
            for idx, r in enumerate(routes):
                candidates.append({
                    "id": f"osrm_route_{idx}",
                    "geometry": r["geometry"],
                    "duration_sec": r.get("duration", 0),
                    "distance_meters": r.get("distance", 0),
                    "source": "OSRM",
                    "is_simulated": False
                })
        else:
            raise Exception("OSRM returned non-200 status")
            
    except Exception as e:
        logger.warning(f"OSRM Route fetch failed, using fallback: {e}")
        candidates = [
            {
                "id": "demo_1",
                "geometry": DEMO_ROUTES["demo_id"]["geometry"],
                "duration_sec": DEMO_ROUTES["demo_id"]["duration"],
                "distance_meters": DEMO_ROUTES["demo_id"]["distance"],
                "source": "DEMO Fallback",
                "is_simulated": True
            },
            {
                "id": "demo_2",
                "geometry": DEMO_ROUTES["demo_id_2"]["geometry"],
                "duration_sec": DEMO_ROUTES["demo_id_2"]["duration"],
                "distance_meters": DEMO_ROUTES["demo_id_2"]["distance"],
                "source": "DEMO Fallback",
                "is_simulated": True
            }
        ]

    if not candidates:
        return []

    # Assess Flood Exposure using Shapely and Hotspots
    hotspots = crud.get_all_hotspots(db)
    # Consider only moderate/high/critical risk
    active_hotspots = [h for h in hotspots if h.current_risk > 30.0]

    vulnerability = VEHICLE_VULNERABILITY.get(vehicle_type, 0.7)

    processed_candidates = []
    for c in candidates:
        geometry = c["geometry"]
        exposure_score = 0.0
        hazards = []
        
        # Convert geojson coordinates to shapely LineString
        coords = geometry.get("coordinates", [])
        if len(coords) > 1:
            line = LineString(coords)
            for h in active_hotspots:
                point = Point(h.longitude, h.latitude)
                # Compute approximate straight-line distance in degrees (naive approach for demonstration)
                # Real implementation would reproject or use haversine, but this serves Shapely evaluation
                dist = line.distance(point)
                # If hotspot is within approx 500m (roughly 0.005 degrees)
                if dist < 0.005:
                    penalty = (h.current_risk / 100.0) * 50.0 * vulnerability * (1 - (dist / 0.005))
                    exposure_score += penalty
                    if penalty > 5.0:
                        hazards.append({"name": h.name, "risk": h.current_risk})
        
        exposure_score = min(exposure_score, 100.0)
        
        processed_candidates.append({
            "id": c["id"],
            "geometry": geometry,
            "duration_sec": c["duration_sec"],
            "distance_meters": c["distance_meters"],
            "source": c["source"],
            "is_simulated": c["is_simulated"],
            "exposure_score": round(exposure_score, 1),
            "hazards": hazards
        })

    # Ranking logic
    if not processed_candidates:
        return []
        
    # Sort by duration first to establish baseline fastest
    processed_candidates.sort(key=lambda x: x["duration_sec"])
    fastest = processed_candidates[0]
    fastest["ranking"] = "Fastest Route"
    fastest["explanation"] = f"Expected duration {int(fastest['duration_sec']//60)} mins."

    # Look for a safer alternative if fastest is hazardous
    for c in processed_candidates[1:]:
        if c["exposure_score"] < fastest["exposure_score"] - 10:
            c["ranking"] = "Safer Alternative"
            c["explanation"] = f"Adds {int((c['duration_sec'] - fastest['duration_sec'])//60)} mins but avoids critical flood hazards."
        else:
            c["ranking"] = "Alternative"
            c["explanation"] = "Standard alternative."

    # If strategy is safest, re-sort to put the safer one first
    if strategy == "safest":
        processed_candidates.sort(key=lambda x: x["exposure_score"])

    return processed_candidates
