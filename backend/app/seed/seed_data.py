import os
import json
from sqlalchemy.orm import Session
from app.db import models
from app.db.database import get_db, engine

def seed_database():
    # Only create tables if they don't exist
    models.Base.metadata.create_all(bind=engine)
    
    db = next(get_db())
    
    seed_dir = os.path.dirname(__file__)
    
    # Seed Hotspots safely (Idempotent)
    hotspots_file = os.path.join(seed_dir, 'hotspots.json')
    if os.path.exists(hotspots_file):
        with open(hotspots_file, 'r', encoding='utf-8') as f:
            hotspots_data = json.load(f)
            for h_data in hotspots_data:
                existing = db.query(models.Hotspot).filter(models.Hotspot.id == h_data['id']).first()
                if not existing:
                    new_hotspot = models.Hotspot(**h_data)
                    db.add(new_hotspot)
        db.commit()
    
    # Seed Reports safely (Idempotent)
    reports_file = os.path.join(seed_dir, 'demo_reports.json')
    if os.path.exists(reports_file):
        with open(reports_file, 'r', encoding='utf-8') as f:
            reports_data = json.load(f)
            for r_data in reports_data:
                existing = db.query(models.Report).filter(models.Report.id == r_data['id']).first()
                if not existing:
                    new_report = models.Report(**r_data)
                    db.add(new_report)
        db.commit()

    # Seed one Dispatch Plan for demonstration
    existing_plan = db.query(models.DispatchPlan).filter(models.DispatchPlan.hotspot_id == 1).first()
    if not existing_plan:
        plan = models.DispatchPlan(
            hotspot_id=1,
            priority="CRITICAL",
            suggested_action="Deploy pumps to Minto Bridge and detour traffic via CP.",
            explanation="Multiple verified reports indicate severe waterlogging exceeding safe vehicle crossing depth.",
            status="PROPOSED"
        )
        db.add(plan)
        db.commit()

    # Seed Demo Weather Scenarios
    existing_weather = db.query(models.WeatherSnapshot).filter(models.WeatherSnapshot.is_demo == True).first()
    if not existing_weather:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        demo_snapshots = [
            models.WeatherSnapshot(
                hotspot_id=1, coordinates="28.6328,77.2289", forecast_timestamp=now,
                precipitation_values=28.0, precipitation_probability=95.0, precip_next_3h=45.0, wind_speed=15.0,
                source_kind="DEMO_SCENARIO", is_demo=True
            ),
            models.WeatherSnapshot(
                hotspot_id=3, coordinates="28.5020,77.2941", forecast_timestamp=now,
                precipitation_values=22.0, precipitation_probability=90.0, precip_next_3h=35.0, wind_speed=12.0,
                source_kind="DEMO_SCENARIO", is_demo=True
            ),
            models.WeatherSnapshot(
                hotspot_id=4, coordinates="28.6657,77.1652", forecast_timestamp=now,
                precipitation_values=0.0, precipitation_probability=10.0, precip_next_3h=0.0, wind_speed=5.0,
                source_kind="DEMO_SCENARIO", is_demo=True
            ),
            models.WeatherSnapshot(
                hotspot_id=2, coordinates="28.6277,77.2405", forecast_timestamp=now,
                precipitation_values=5.0, precipitation_probability=40.0, precip_next_3h=8.0, wind_speed=8.0,
                source_kind="DEMO_SCENARIO", is_demo=True
            )
        ]
        for snap in demo_snapshots:
            db.add(snap)
        db.commit()

        # Recalculate risk for all to populate HotspotRiskRecord and update hotspot risk states
        from app.services.risk_service import calculate_risk
        from app.services.weather_service import _DEMO_PRECIP
        for hid in [1, 2, 3, 4, 5, 6, 7, 8]:
            try:
                precip = demo_snapshots[0].precipitation_values if hid == 1 else (demo_snapshots[1].precipitation_values if hid == 3 else (demo_snapshots[2].precipitation_values if hid == 4 else (demo_snapshots[3].precipitation_values if hid == 2 else _DEMO_PRECIP.get(hid, 2.0))))
                calculate_risk(db, hid, weather_precip_mm=precip, is_demo=True, weather_data_source="demo")
            except Exception as e:
                print(f"Failed to calculate seed risk for hotspot {hid}: {e}")

if __name__ == "__main__":
    print("Seeding database...")
    seed_database()
    print("Seeding complete.")
