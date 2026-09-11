from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from api.schemas import QualityResponse, ErrorResponse
from api.services import quality_service

router = APIRouter(tags=["Quality"])


@router.get(
    "/quality",
    response_model=QualityResponse,
    summary="Get data quality report",
    responses={
        500: {"model": ErrorResponse, "description": "Internal error."},
    },
)
def get_quality() -> QualityResponse:
    try:
        return quality_service.assess_quality()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quality assessment failed: {exc}",
        )