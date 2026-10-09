from typing import List, Optional
from pydantic import BaseModel


class Coordinates(BaseModel):
    lat: float
    lng: float


class RouteCompareRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates
    vehicle_type: str
    strategy: str = "fastest"  # or "safest"


class RouteCandidate(BaseModel):
    id: str
    geometry: dict          # GeoJSON LineString
    duration_sec: float
    distance_meters: float
    source: str             # "OSRM", "DEMO", etc.
    is_simulated: bool
    exposure_score: float   # 0 to 100
    ranking: str            # "Fastest", "Safer Alternative"
    explanation: str
    hazards: List[dict]     # list of hotspots or reports near the route


class RouteCompareResponse(BaseModel):
    candidates: List[RouteCandidate]
    request_timestamp: str
