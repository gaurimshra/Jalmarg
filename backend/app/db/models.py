from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Hotspot(Base):
    __tablename__ = "hotspots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    baseline_risk = Column(Float, default=0.0)
    current_risk = Column(Float, default=0.0)
    risk_level = Column(String, default="LOW") # LOW, MODERATE, HIGH, CRITICAL
    status = Column(String, default="ACTIVE") # ACTIVE, INACTIVE
    source_kind = Column(String, default="SYSTEM")
    is_simulated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reports = relationship("Report", back_populates="hotspot")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id"), nullable=True)
    description = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    image_path = Column(String, nullable=True)
    sha256_hash = Column(String, nullable=True)
    perceptual_hash = Column(String, nullable=True)
    trust_score = Column(Float, default=0.0)
    verification_status = Column(String, default="PENDING")
    water_detected = Column(Boolean, nullable=True)
    severity = Column(String, nullable=True)
    depth_min_cm = Column(Float, nullable=True)
    depth_max_cm = Column(Float, nullable=True)
    depth_confidence = Column(Float, nullable=True)
    analysis_source = Column(String, nullable=True)
    source_kind = Column(String, default="CITIZEN")
    is_simulated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    hotspot = relationship("Hotspot", back_populates="reports")

class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id"), nullable=True)
    coordinates = Column(String, nullable=False)
    retrieval_time = Column(DateTime(timezone=True), server_default=func.now())
    forecast_timestamp = Column(DateTime(timezone=True), nullable=True)
    # Precipitation at nearest forecast hour (mm)
    precipitation_values = Column(Float, default=0.0)
    # Probability of precipitation (0–100 %)
    precipitation_probability = Column(Float, nullable=True)
    # Accumulated precipitation next 3 forecast hours (mm)
    precip_next_3h = Column(Float, nullable=True)
    # Wind speed at 10m (km/h)
    wind_speed = Column(Float, nullable=True)
    source_kind = Column(String, default="OPEN_METEO")
    error_or_status = Column(String, nullable=True)
    # Cache metadata
    cache_key = Column(String, nullable=True, index=True)
    is_cached = Column(Boolean, default=False)
    is_demo = Column(Boolean, default=False)

class HotspotRiskRecord(Base):
    """Persisted output of the risk engine for one hotspot at a point in time."""
    __tablename__ = "hotspot_risk_records"

    id = Column(Integer, primary_key=True, index=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id"), nullable=False)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    # Final composite score 0–100
    risk_score = Column(Float, nullable=False)
    # LOW / MODERATE / HIGH / CRITICAL
    risk_category = Column(String, nullable=False)
    # Individual normalised signal components (each 0–100)
    rainfall_signal = Column(Float, default=0.0)
    flood_evidence_signal = Column(Float, default=0.0)
    baseline_signal = Column(Float, default=0.0)
    corroboration_signal = Column(Float, default=0.0)
    # Engine version tag — bump when formula changes
    calculation_version = Column(String, default="v1")
    # JSON-encoded list of source descriptors
    data_sources = Column(Text, nullable=True)
    # Human-readable caveat (e.g. stale data, demo mode)
    uncertainty_note = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False)

class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id"), nullable=True)
    agent_name = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    source_kind = Column(String, default="SYSTEM")
    status = Column(String, default="SUCCESS")
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DispatchPlan(Base):
    __tablename__ = "dispatch_plans"

    id = Column(Integer, primary_key=True, index=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id"), nullable=False)
    priority = Column(String, default="LOW")
    suggested_action = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    supporting_evidence_summary = Column(Text, nullable=True)
    status = Column(String, default="PROPOSED") # PROPOSED, APPROVED, REJECTED
    proposed_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String, nullable=True)
