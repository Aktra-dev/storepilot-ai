"""
Sales — API routes (CRUD + summary endpoints).

Endpoints:
    POST   /sales              Record a sale (staff+)
    GET    /sales              List sales (filter by product, date)
    GET    /sales/summary      Aggregated sales summary
    GET    /sales/daily        Daily totals (for charts)
    GET    /sales/{id}         Get sale by ID
    PATCH  /sales/{id}         Update sale (manager)
    DELETE /sales/{id}         Delete/void sale (manager)
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user, get_current_manager
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.sales.schemas import SaleCreate, SaleResponse, SaleUpdate
from app.modules.sales.service import SalesService

router = APIRouter()


def get_sales_service(db: Session = Depends(get_db)) -> SalesService:
    return SalesService(db=db)


@router.post(
    "",
    response_model=SaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new sale",
)
def create_sale(
    payload: SaleCreate,
    current_user: User = Depends(get_current_active_user),
    service: SalesService = Depends(get_sales_service),
):
    """Record a new sale transaction."""
    return service.create(payload)


@router.get(
    "",
    response_model=List[SaleResponse],
    summary="List sales with filters",
)
def list_sales(
    product_id: Optional[UUID] = Query(default=None, description="Filter by product"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    service: SalesService = Depends(get_sales_service),
):
    """List sales with optional filters."""
    from datetime import date as date_type
    sd = date_type.fromisoformat(start_date) if start_date else None
    ed = date_type.fromisoformat(end_date) if end_date else None
    return service.list(product_id=product_id, start_date=sd, end_date=ed, skip=skip, limit=limit)


@router.get(
    "/summary",
    summary="Get aggregated sales summary",
)
def get_sales_summary(
    product_id: Optional[UUID] = Query(default=None),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    service: SalesService = Depends(get_sales_service),
):
    """Get total revenue, count, average per day, and top products."""
    from datetime import date as date_type
    sd = date_type.fromisoformat(start_date) if start_date else None
    ed = date_type.fromisoformat(end_date) if end_date else None
    return service.get_summary(product_id=product_id, start_date=sd, end_date=ed)


@router.get(
    "/daily",
    summary="Get daily sales totals (for charts)",
)
def get_daily_sales(
    product_id: Optional[UUID] = Query(default=None),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    service: SalesService = Depends(get_sales_service),
):
    """Get daily sales totals for charting."""
    from datetime import date as date_type
    sd = date_type.fromisoformat(start_date) if start_date else None
    ed = date_type.fromisoformat(end_date) if end_date else None
    return service.get_daily_totals(product_id=product_id, start_date=sd, end_date=ed, limit=limit)


@router.get(
    "/{sale_id}",
    response_model=SaleResponse,
    summary="Get sale by ID",
)
def get_sale(
    sale_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: SalesService = Depends(get_sales_service),
):
    """Get a single sale record by ID."""
    return service.get(sale_id)


@router.patch(
    "/{sale_id}",
    response_model=SaleResponse,
    summary="Update a sale",
)
def update_sale(
    sale_id: UUID,
    payload: SaleUpdate,
    current_user: User = Depends(get_current_manager),
    service: SalesService = Depends(get_sales_service),
):
    """Update a sale record. Requires manager role."""
    return service.update(sale_id, payload)


@router.delete(
    "/{sale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete/void a sale",
)
def delete_sale(
    sale_id: UUID,
    current_user: User = Depends(get_current_manager),
    service: SalesService = Depends(get_sales_service),
):
    """Delete (void) a sale record. Requires manager role."""
    service.delete(sale_id)