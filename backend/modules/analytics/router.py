"""Analytics module — FastAPI router.

Exposes REST endpoints for:
    * Retrieving GridMind analytics for a simulation run.
    * Retrieving a baseline-vs-GridMind comparison.
    * Triggering analytics calculation on demand.

Follows the project's existing API conventions (prefix, response models,
error handling via HTTPException).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.common.database import get_db_session
from backend.common.schemas.enums import AnalyticsMode
from backend.modules.analytics.schemas import (
    AnalyticsRequest,
    AnalyticsResponse,
    ComparisonResponse,
)
from backend.modules.analytics.service import AnalyticsService


router = APIRouter(prefix="/analytics", tags=["analytics"])


def _get_service(db: Session = Depends(get_db_session)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get(
    "/{simulation_run_id}",
    response_model=AnalyticsResponse,
    summary="Get GridMind analytics for a simulation run",
)
def get_analytics(
    simulation_run_id: int,
    service: AnalyticsService = Depends(_get_service),
) -> AnalyticsResponse:
    """Retrieve (or calculate on-the-fly) GridMind metrics for the given
    simulation run.
    """
    try:
        metrics = service.get_analytics(simulation_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AnalyticsResponse(
        success=True,
        message="GridMind analytics retrieved",
        simulation_run_id=simulation_run_id,
        mode=AnalyticsMode.GRIDMIND,
        metrics=metrics,
    )


@router.get(
    "/{simulation_run_id}/comparison",
    response_model=ComparisonResponse,
    summary="Get baseline vs GridMind comparison",
)
def get_comparison(
    simulation_run_id: int,
    service: AnalyticsService = Depends(_get_service),
) -> ComparisonResponse:
    """Run the baseline controller under the same scenario, calculate metrics
    for both controllers, and return a side-by-side comparison with
    improvement deltas.
    """
    try:
        comparison = service.get_comparison(simulation_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ComparisonResponse(
        success=True,
        message="Baseline vs GridMind comparison complete",
        comparison=comparison,
    )


@router.post(
    "/{simulation_run_id}/calculate",
    response_model=AnalyticsResponse,
    summary="Trigger analytics calculation and persist results",
)
def calculate_analytics(
    simulation_run_id: int,
    service: AnalyticsService = Depends(_get_service),
) -> AnalyticsResponse:
    """Calculate GridMind metrics for the given simulation run and persist
    the results to the ``analytics_results`` table.
    """
    try:
        metrics = service.calculate_and_persist(simulation_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AnalyticsResponse(
        success=True,
        message="Analytics calculated and persisted",
        simulation_run_id=simulation_run_id,
        mode=AnalyticsMode.GRIDMIND,
        metrics=metrics,
    )
