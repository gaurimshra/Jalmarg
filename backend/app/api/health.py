from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    # Database check could be pinging the DB; for now, we just indicate it's not setup yet
    db_available = False
    try:
        # We will add actual DB import and ping here when DB is built
        pass
    except Exception:
        pass

    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "demo_mode": settings.DEMO_MODE,
        "database_available": db_available
    }
