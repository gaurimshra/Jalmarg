from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend for JalMarg - Agentic AI for urban waterlogging",
    version="0.1.0",
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])

from app.api import hotspots, reports, agents, map, admin, routing
from app.api import weather as weather_router
app.include_router(map.router, prefix="/api/map", tags=["map"])
app.include_router(hotspots.router, prefix="/api/hotspots", tags=["hotspots"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(agents.router, prefix="/api/agent-events", tags=["agents"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
# Weather + risk endpoints
app.include_router(weather_router.router, prefix="/api/weather", tags=["weather"])
# Risk recalculation and history are also accessible under /api/hotspots
app.include_router(weather_router.router, prefix="/api", tags=["risk"])
app.include_router(routing.router, prefix="/api/routes", tags=["routes"])

@app.on_event("startup")
def on_startup():
    from app.seed.seed_data import seed_database
    seed_database()

@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.APP_NAME} API"}
