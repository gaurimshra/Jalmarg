from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class HotspotBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    baseline_risk: float = 0.0
    current_risk: float = 0.0
    risk_level: str = "LOW"
    status: str = "ACTIVE"
    source_kind: str = "SYSTEM"
    is_simulated: bool = False

class HotspotOut(HotspotBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

class ReportBase(BaseModel):
    hotspot_id: Optional[int] = None
    description: Optional[str] = None
    latitude: float
    longitude: float
    image_path: Optional[str] = None
    sha256_hash: Optional[str] = None
    perceptual_hash: Optional[str] = None
    trust_score: float = 0.0
    verification_status: str = "PENDING"
    water_detected: Optional[bool] = None
    severity: Optional[str] = None
    depth_min_cm: Optional[float] = None
    depth_max_cm: Optional[float] = None
    depth_confidence: Optional[float] = None
    analysis_source: Optional[str] = None
    source_kind: str = "CITIZEN"
    is_simulated: bool = False

class ReportCreate(BaseModel):
    description: Optional[str] = None
    latitude: float
    longitude: float
    image_path: Optional[str] = None
    source_kind: str = "CITIZEN"
    is_simulated: bool = False

class ReportOut(ReportBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

class AgentEventBase(BaseModel):
    report_id: Optional[int] = None
    hotspot_id: Optional[int] = None
    agent_name: str
    tool_name: str
    event_type: str
    summary: str
    source_kind: str = "SYSTEM"
    status: str = "SUCCESS"
    duration_ms: Optional[int] = None

class AgentEventOut(AgentEventBase):
    id: int
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

class DispatchPlanOut(BaseModel):
    id: int
    hotspot_id: int
    priority: str
    suggested_action: str
    explanation: str
    supporting_evidence_summary: Optional[str] = None
    status: str
    proposed_at: Optional[datetime]
    approved_at: Optional[datetime]
    approved_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
class DispatchPlanStatusUpdate(BaseModel):
    status: str
    approved_by: str = "DEMO AUTHORITY USER"

# ── Weather schemas ───────────────────────────────────────────────────────────

class WeatherSnapshotOut(BaseModel):
    id: int
    hotspot_id: Optional[int]
    coordinates: str
    retrieval_time: Optional[datetime]
    forecast_timestamp: Optional[datetime]
    precipitation_values: Optional[float]
    precipitation_probability: Optional[float]
    precip_next_3h: Optional[float]
    wind_speed: Optional[float]
    source_kind: str
    cache_key: Optional[str]
    is_cached: bool
    is_demo: bool
    # Human-readable source label for the frontend
    data_source: str = "live"
    model_config = ConfigDict(from_attributes=True)

# ── Risk schemas ──────────────────────────────────────────────────────────────

class RiskRecordOut(BaseModel):
    id: int
    hotspot_id: int
    calculated_at: Optional[datetime]
    risk_score: float
    risk_category: str
    rainfall_signal: float
    flood_evidence_signal: float
    baseline_signal: float
    corroboration_signal: float
    calculation_version: str
    data_sources: Optional[str]       # JSON string
    uncertainty_note: Optional[str]
    is_demo: bool
    model_config = ConfigDict(from_attributes=True)

class RiskRefreshResponse(BaseModel):
    hotspot_id: int
    risk_record: RiskRecordOut
    hotspot_name: str
    hotspot_current_risk: float
    hotspot_risk_level: str
    data_source: str  # "live" | "cached" | "demo" | "local_calculation"

