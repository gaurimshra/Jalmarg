from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db, SessionLocal
from app.db.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test DB (In-memory SQLite for tests)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def setup_module():
    Base.metadata.create_all(bind=engine)
    from app.seed.seed_data import seed_database
    # Seed data won't automatically work in memory if seed script uses main engine, 
    # but we can manually seed via test db just by calling the internal functions or endpoints
    # For now, let's just make sure DB is created.

def teardown_module():
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test.db"):
        os.remove("./test.db")

def test_db_initialization_and_seed():
    # Calling overview should be empty or seeded
    response = client.get("/api/map/overview")
    assert response.status_code == 200

def test_create_and_retrieve_report():
    # Create Report
    payload = {
        "latitude": 28.1,
        "longitude": 77.1,
        "description": "Test report",
        "is_simulated": True
    }
    response = client.post("/api/reports/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["latitude"] == 28.1
    report_id = data["id"]
    
    # Retrieve it
    get_res = client.get(f"/api/reports/{report_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == report_id

def test_hotspot_api():
    response = client.get("/api/hotspots/")
    assert response.status_code == 200

def test_agent_events():
    response = client.get("/api/agent-events/")
    assert response.status_code == 200
