from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.route_schemas import RouteCompareRequest, RouteCompareResponse
from app.services import route_service

router = APIRouter()

@router.post("/compare", response_model=RouteCompareResponse, summary="Compare routes with flood awareness")
async def compare_routes(
    request: RouteCompareRequest,
    db: Session = Depends(get_db)
):
    try:
        candidates = await route_service.get_route_candidates(
            db,
            origin_lat=request.origin.lat,
            origin_lng=request.origin.lng,
            dest_lat=request.destination.lat,
            dest_lng=request.destination.lng,
            vehicle_type=request.vehicle_type,
            strategy=request.strategy
        )
        return RouteCompareResponse(
            candidates=candidates,
            request_timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
