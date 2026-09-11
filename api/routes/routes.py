from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from api.schemas import RouteListResponse, ErrorResponse
from api.services import route_service

router = APIRouter(tags=["Routes"])


@router.get(
    "/routes",
    response_model=RouteListResponse,
    summary="Get route-level analysis",
    responses={
        500: {"model": ErrorResponse, "description": "Internal error."},
    },
)
def get_routes() -> RouteListResponse:
    try:
        return route_service.get_routes()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Route analysis failed: {exc}",
        )