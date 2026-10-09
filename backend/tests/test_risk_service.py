import pytest
from datetime import datetime, timezone, timedelta
from app.services import risk_service

class MockReport:
    def __init__(self, **kwargs):
        self.water_detected = True
        self.trust_score = 1.0
        self.verification_status = "VERIFIED"
        self.created_at = datetime.now(timezone.utc)
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_rainfall_signal_normalization():
    # 0 mm -> 0
    assert risk_service._rainfall_signal(0.0) == 0.0
    # 15 mm -> 50
    assert risk_service._rainfall_signal(15.0) == 50.0
    # >= 30 mm -> 100
    assert risk_service._rainfall_signal(30.0) == 100.0
    assert risk_service._rainfall_signal(50.0) == 100.0


def test_flood_evidence_decay():
    now = datetime.now(timezone.utc)
    # Fresh report with 1.0 trust = 1/3 of max (since RAW_EVIDENCE_CLAMP is 3) -> 33.33 points
    r_fresh = MockReport(created_at=now, trust_score=1.0)
    score1 = risk_service._flood_evidence_signal([r_fresh], now)
    assert abs(score1 - 33.33) < 0.1

    # 12 hours old (half-life) -> should contribute ~ 33.33 * 0.367 (exp(-1)) = 12.26
    r_half = MockReport(created_at=now - timedelta(hours=12), trust_score=1.0)
    score_half = risk_service._flood_evidence_signal([r_half], now)
    assert abs(score_half - 12.26) < 0.1

    # Older than 48 hours -> 0
    r_old = MockReport(created_at=now - timedelta(hours=49), trust_score=1.0)
    assert risk_service._flood_evidence_signal([r_old], now) == 0.0


def test_corroboration_signal():
    r1 = MockReport(verification_status="VERIFIED", trust_score=1.0)
    r2 = MockReport(verification_status="VERIFIED_PARTIAL", trust_score=0.8)
    r3 = MockReport(verification_status="UNVERIFIED", trust_score=0.5)

    # 0 eligible
    assert risk_service._corroboration_signal([r3]) == 0.0
    
    # 1 eligible
    assert risk_service._corroboration_signal([r1]) == 30.0  # capped at 30

    # 2 eligible
    assert risk_service._corroboration_signal([r1, r2]) == 40.0  # 2 * 20
    
    # 5 eligible -> 100
    assert risk_service._corroboration_signal([r1, r1, r1, r1, r1]) == 100.0
    
    # duplicate rejects shouldn't contribute
    r_dup = MockReport(verification_status="REJECTED_DUPLICATE", trust_score=1.0)
    assert risk_service._corroboration_signal([r1, r_dup]) == 30.0


def test_score_to_category():
    assert risk_service._score_to_category(20) == "LOW"
    assert risk_service._score_to_category(40) == "MODERATE"
    assert risk_service._score_to_category(60) == "HIGH"
    assert risk_service._score_to_category(85) == "CRITICAL"
