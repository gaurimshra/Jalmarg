from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db, SessionLocal, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import io
from PIL import Image

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_workflow.db"
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

def teardown_module():
    Base.metadata.drop_all(bind=engine)
    import os
    try:
        if os.path.exists("./test_workflow.db"):
            os.remove("./test_workflow.db")
    except Exception:
        pass

def create_dummy_image():
    img = Image.new('RGB', (100, 100), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

def test_invalid_file_rejection():
    # Submit non-image txt file
    response = client.post(
        "/api/reports/",
        data={"latitude": 10.0, "longitude": 10.0},
        files={"image": ("test.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 400
    assert "Invalid image format" in response.json()["detail"]

def test_valid_image_upload():
    img_bytes = create_dummy_image()
    response = client.post(
        "/api/reports/",
        data={"latitude": 28.6, "longitude": 77.2, "description": "Test report"},
        files={"image": ("test.jpg", img_bytes, "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["latitude"] == 28.6
    # Verification details should be updated
    assert data["verification_status"] == "PENDING_ADDITIONAL_EVIDENCE" # Since it has no GPS metadata and trust score is low
    
    # Check vision defaults fallback
    assert data["analysis_source"] == "Fallback (No API Key)" or "Gemini" in data["analysis_source"]

def test_duplicate_image_detection():
    # Upload same image twice
    img_bytes = create_dummy_image()
    res1 = client.post(
        "/api/reports/",
        data={"latitude": 28.6, "longitude": 77.2},
        files={"image": ("dupe1.jpg", img_bytes, "image/jpeg")}
    )
    res2 = client.post(
        "/api/reports/",
        data={"latitude": 28.6, "longitude": 77.2},
        files={"image": ("dupe2.jpg", img_bytes, "image/jpeg")}
    )
    assert res2.status_code == 200
    assert res2.json()["verification_status"] == "REJECTED_DUPLICATE"

def test_agent_events_created():
    events = client.get("/api/agent-events/")
    assert events.status_code == 200
    data = events.json()
    assert len(data) > 0
    # Must have INGESTION and VERIFICATION events
    event_types = [e["event_type"] for e in data]
    assert "INGESTION" in event_types
    assert "VERIFICATION" in event_types
    assert "VISION_ANALYSIS" in event_types
