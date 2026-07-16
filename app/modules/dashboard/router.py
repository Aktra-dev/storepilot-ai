"""
Dashboard -- read-only API routes.

Mounted directly at /api/dashboard (not under /api/v1), matching the
literal paths in the STEP 9 spec. Every endpoint here is read-only and
NEVER triggers a new analysis or any AI call -- see service.py.
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.dashboard.schemas import DashboardSummary, FindingSummary
from app.modules.dashboard.service import (
    DEFAULT_RECENT_FINDINGS_LIMIT,
    DashboardService,
)

router = APIRouter()


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db=db)


@router.get("", response_model=DashboardSummary)
def get_dashboard(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_summary()


@router.get("/inventory-risks", response_model=List[FindingSummary])
def get_inventory_risks(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_inventory_risks()


@router.get("/sales-anomalies", response_model=List[FindingSummary])
def get_sales_anomalies(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_sales_anomalies()


@router.get("/recent-findings", response_model=List[FindingSummary])
def get_recent_findings(
    limit: int = Query(default=DEFAULT_RECENT_FINDINGS_LIMIT, ge=1, le=100),
    service: DashboardService = Depends(get_dashboard_service),
):
    return service.get_recent_findings(limit=limit)
