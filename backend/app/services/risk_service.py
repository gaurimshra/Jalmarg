"""
risk_service.py
───────────────
Deterministic, testable flood-risk calculation engine for JalMarg.

Formula  (version v1 — prototype assumptions, not validated science)
─────────────────────────────────────────────────────────────────────
RISK = 0.40 * RAINFALL_SIGNAL
     + 0.30 * RECENT_FLOOD_EVIDENCE
     + 0.20 * HOTSPOT_BASELINE
     + 0.10 * CORROBORATION_SIGNAL

Each component is normalised to 0–100 before weighting.

Normalisation rules  (documented here and mirrored in tests)
─────────────────────────────────────────────────────────────
RAINFALL_SIGNAL
    min(precip_mm / MAX_PRECIP_MM, 1.0) * 100
    MAX_PRECIP_MM = 30   →   30 mm/hr or more saturates the signal.
    Rationale: 30 mm/hr is "very heavy" rain per IMD classification.

RECENT_FLOOD_EVIDENCE
    For each report where water_detected=True (and not REJECTED_DUPLICATE):
        contribution = trust_score * time_decay(hours_old)
        time_decay   = exp(-hours_old / EVIDENCE_HALFLIFE_HOURS)
        EVIDENCE_HALFLIFE_HOURS = 12   →   a 12-hour-old report contributes
                                           ~37% of its original weight.
    Reports older than MAX_EVIDENCE_AGE_HOURS (48) contribute 0.
    Raw sum is clamped to [0, RAW_CLAMP] then scaled to [0, 100].
    RAW_CLAMP = 3.0  →  three simultaneous perfect-trust fresh reports
                         saturate the evidence signal.

HOTSPOT_BASELINE
    hotspot.baseline_risk  (already stored on 0–100 scale)

CORROBORATION_SIGNAL
    Requires ≥ 2 distinct eligible reports (VERIFIED or VERIFIED_PARTIAL)
    to produce signal > 0.  A single unverified report is capped at 30/100.
    Multiple REJECTED_DUPLICATE reports contribute zero — this prevents
    bot spam from inflating the corroboration score.
    eligible_count = # reports with status in {VERIFIED, VERIFIED_PARTIAL}
    if eligible_count == 0:
        signal = 0
    elif eligible_count == 1:
        signal = min(30.0, trust_score_of_first * 100)
    else:
        signal = min(100.0, eligible_count * 20.0)

Report freshness
────────────────
All report queries use get_reports_for_risk() which excludes REJECTED_DUPLICATE
and filters to the last 48 hours.  The exponential decay further reduces
the influence of observations that are many hours old.

Anti-spam guarantee
───────────────────
Even if 100 reports are submitted with identical images, they will all be
flagged REJECTED_DUPLICATE by the verification service and excluded from both
RECENT_FLOOD_EVIDENCE and CORROBORATION_SIGNAL.

Trust and corroboration
────────────────────────
Trust scores (0–1) come from image_verification.py.  High-trust reports have
more influence on flood evidence, but corroboration caps are applied regardless
of trust to prevent a single high-trust source from dominating.
"""

import json
import logging
import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import crud

logger = logging.getLogger(__name__)

# ── Formula weights (must sum to 1.0) ────────────────────────────────────────
W_RAINFALL = 0.40
W_FLOOD_EVIDENCE = 0.30
W_BASELINE = 0.20
W_CORROBORATION = 0.10

# ── Normalisation parameters ──────────────────────────────────────────────────
MAX_PRECIP_MM = 30.0          # mm/hr that saturates RAINFALL_SIGNAL
EVIDENCE_HALFLIFE_HOURS = 12.0 # exponential decay half-life for report freshness
MAX_EVIDENCE_AGE_HOURS = 48.0  # reports older than this contribute 0
RAW_EVIDENCE_CLAMP = 3.0      # 3 simultaneous high-trust fresh reports → 100

CALCULATION_VERSION = "v1"


# ── Public API ────────────────────────────────────────────────────────────────

def calculate_risk(
    db: Session,
    hotspot_id: int,
    weather_precip_mm: float = 0.0,
    is_demo: bool = False,
    weather_data_source: str = "local_calculation",
) -> dict:
    """
    Compute a composite flood-risk score for *hotspot_id*.

    Parameters
    ----------
    db                  : SQLAlchemy session
    hotspot_id          : target hotspot
    weather_precip_mm   : current precipitation in mm (from weather service)
    is_demo             : flag the record as demo data
    weather_data_source : "live" | "cached" | "demo" | "local_calculation"

    Returns a dict with all signals, final score, category, and metadata.
    Persists a HotspotRiskRecord and updates the Hotspot row.
    """
    hotspot = crud.get_hotspot(db, hotspot_id)
    if hotspot is None:
        raise ValueError(f"Hotspot {hotspot_id} not found")

    reports = crud.get_reports_for_risk(db, hotspot_id, max_age_hours=MAX_EVIDENCE_AGE_HOURS)
    now_utc = datetime.now(timezone.utc)

    # ── 1. Rainfall signal ────────────────────────────────────────────────
    rainfall_signal = _rainfall_signal(weather_precip_mm)

    # ── 2. Flood evidence signal ──────────────────────────────────────────
    flood_evidence_signal = _flood_evidence_signal(reports, now_utc)

    # ── 3. Baseline signal ────────────────────────────────────────────────
    baseline_signal = float(hotspot.baseline_risk)  # already 0–100

    # ── 4. Corroboration signal ───────────────────────────────────────────
    corroboration_signal = _corroboration_signal(reports)

    # ── 5. Composite score ────────────────────────────────────────────────
    raw_score = (
        W_RAINFALL       * rainfall_signal
      + W_FLOOD_EVIDENCE * flood_evidence_signal
      + W_BASELINE       * baseline_signal
      + W_CORROBORATION  * corroboration_signal
    )
    risk_score = round(min(max(raw_score, 0.0), 100.0), 2)
    risk_category = _score_to_category(risk_score)

    # ── 6. Uncertainty note ───────────────────────────────────────────────
    notes = []
    if is_demo or weather_data_source == "demo":
        notes.append("Weather data is illustrative demo — not a real forecast.")
    if not reports:
        notes.append("No recent corroborating reports found (last 48 h).")
    stale_count = sum(1 for r in reports if _hours_old(r, now_utc) > 24)
    if stale_count > 0 and stale_count == len(reports):
        notes.append("All corroborating reports are >24 h old; flood evidence is decayed.")
    uncertainty_note = " ".join(notes) if notes else None

    # ── 7. Data sources ───────────────────────────────────────────────────
    data_sources = json.dumps({
        "weather": weather_data_source,
        "reports_count": len(reports),
        "hotspot_baseline": "database",
        "calculation_version": CALCULATION_VERSION,
    })

    # ── 8. Persist ────────────────────────────────────────────────────────
    record_data = {
        "hotspot_id": hotspot_id,
        "risk_score": risk_score,
        "risk_category": risk_category,
        "rainfall_signal": round(rainfall_signal, 2),
        "flood_evidence_signal": round(flood_evidence_signal, 2),
        "baseline_signal": round(baseline_signal, 2),
        "corroboration_signal": round(corroboration_signal, 2),
        "calculation_version": CALCULATION_VERSION,
        "data_sources": data_sources,
        "uncertainty_note": uncertainty_note,
        "is_demo": is_demo,
    }
    record = crud.save_risk_record(db, record_data)
    crud.update_hotspot_risk_from_record(db, hotspot_id, risk_score, risk_category)

    return {
        "id": record.id,
        "hotspot_id": hotspot_id,
        "calculated_at": record.calculated_at,
        "risk_score": risk_score,
        "risk_category": risk_category,
        "rainfall_signal": record.rainfall_signal,
        "flood_evidence_signal": record.flood_evidence_signal,
        "baseline_signal": record.baseline_signal,
        "corroboration_signal": record.corroboration_signal,
        "calculation_version": CALCULATION_VERSION,
        "data_sources": data_sources,
        "uncertainty_note": uncertainty_note,
        "is_demo": is_demo,
    }


# ── Signal component functions (pure, testable) ───────────────────────────────

def _rainfall_signal(precip_mm: float) -> float:
    """
    Normalise precipitation to 0–100.
    30 mm/hr or above saturates the signal at 100.
    """
    return min(precip_mm / MAX_PRECIP_MM, 1.0) * 100.0


def _flood_evidence_signal(reports: list, now_utc: datetime) -> float:
    """
    Compute a trust-weighted, time-decayed flood evidence score (0–100).

    Only reports with water_detected=True are considered.
    REJECTED_DUPLICATE reports are already excluded by the CRUD query.
    """
    raw = 0.0
    for r in reports:
        if not r.water_detected:
            continue
        hours = _hours_old(r, now_utc)
        if hours > MAX_EVIDENCE_AGE_HOURS:
            continue
        decay = math.exp(-hours / EVIDENCE_HALFLIFE_HOURS)
        trust = float(r.trust_score) if r.trust_score else 0.0
        raw += trust * decay

    # Clamp raw accumulator then scale to 100
    return min(raw / RAW_EVIDENCE_CLAMP, 1.0) * 100.0


def _corroboration_signal(reports: list) -> float:
    """
    Corroboration requires ≥2 independently verified reports.

    Anti-spam guarantee:
    - REJECTED_DUPLICATE already excluded by query.
    - Single unverified report capped at 30/100.
    - Each verified report beyond 1 adds 20 points, capped at 100.
    """
    verified_statuses = {"VERIFIED", "VERIFIED_PARTIAL"}
    eligible = [r for r in reports if r.verification_status in verified_statuses]

    if not eligible:
        return 0.0
    if len(eligible) == 1:
        trust = float(eligible[0].trust_score) if eligible[0].trust_score else 0.0
        return min(trust * 50.0, 30.0)   # single report: max 30/100

    return min(len(eligible) * 20.0, 100.0)


def _score_to_category(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 55:
        return "HIGH"
    if score >= 30:
        return "MODERATE"
    return "LOW"


def _hours_old(report, now_utc: datetime) -> float:
    """Return the age of a report in decimal hours."""
    created = report.created_at
    if created is None:
        return MAX_EVIDENCE_AGE_HOURS  # treat as maximally old
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    delta = now_utc - created
    return delta.total_seconds() / 3600.0
