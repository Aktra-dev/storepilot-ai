"""
Inventory — API routes (CRUD + stock management).

Endpoints:
    POST   /inventory               Add inventory record (manager)
    GET    /inventory               List records (filter by product)
    GET    /inventory/alerts        Get low stock & near expiry alerts
    GET    /inventory/stock/{id}    Get total stock for a product
    GET    /inventory/{id}          Get record by ID
    PATCH  /inventory/{id}          Update record (manager)
    POST   /inventory/{id}/adjust   Adjust stock +/-
    DELETE /inventory/{id}          Delete record (manager)
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user, get_current_manager
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.inventory.models import Inventory
from app.modules.inventory.schemas import (
    InventoryCreate,
    InventoryResponse,
    InventoryUpdate,
    StockAdjustment,
    StockStatusResponse,
)
from app.modules.inventory.service import InventoryService
from app.modules.products.models import Product

router = APIRouter()


def get_inventory_service(db: Session = Depends(get_db)) -> InventoryService:
    return InventoryService(db=db)


@router.post(
    "",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new inventory/batch record",
)
def create_inventory(
    payload: InventoryCreate,
    current_user: User = Depends(get_current_active_user),
    service: InventoryService = Depends(get_inventory_service),
):
    """Create a new inventory record for a product. Staff or manager (real-time data entry)."""
    return service.create(payload)


@router.get(
    "",
    response_model=List[InventoryResponse],
    summary="List inventory records",
)
def list_inventory(
    product_id: Optional[UUID] = Query(default=None, description="Filter by product"),
    current_user: User = Depends(get_current_active_user),
    service: InventoryService = Depends(get_inventory_service),
):
    """List inventory records, optionally filtered by product."""
    if product_id:
        return service.list_by_product(product_id)
    return service.db.query(Inventory).order_by(Inventory.updated_at.desc()).all()


@router.get(
    "/stock/{product_id}",
    response_model=StockStatusResponse,
    summary="Get total stock status for a product",
)
def get_product_stock(
    product_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: InventoryService = Depends(get_inventory_service),
):
    """Return aggregated stock info for a product."""
    product = service.db.query(Product).filter(Product.id == product_id).first()
    if not product:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(f"Product {product_id} not found")

    total_qty = service.get_total_stock(product_id)
    latest = service.get_latest_by_product(product_id)

    return StockStatusResponse(
        product_id=product.id,
        product_name=product.name,
        product_sku=product.sku,
        total_quantity=total_qty,
        min_stock=product.minimum_stock,
        has_inventory_records=latest is not None,
    )


@router.get(
    "/{inventory_id}",
    response_model=InventoryResponse,
    summary="Get inventory record by ID",
)
def get_inventory(
    inventory_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: InventoryService = Depends(get_inventory_service),
):
    """Get a single inventory record by ID."""
    return service.get(inventory_id)


@router.patch(
    "/{inventory_id}",
    response_model=InventoryResponse,
    summary="Update inventory record",
)
def update_inventory(
    inventory_id: UUID,
    payload: InventoryUpdate,
    current_user: User = Depends(get_current_manager),
    service: InventoryService = Depends(get_inventory_service),
):
    """Update an inventory record. Requires manager role."""
    return service.update(inventory_id, payload)


@router.post(
    "/{inventory_id}/adjust",
    response_model=InventoryResponse,
    summary="Adjust stock quantity (+/-)",
)
def adjust_stock(
    inventory_id: UUID,
    payload: StockAdjustment,
    current_user: User = Depends(get_current_active_user),
    service: InventoryService = Depends(get_inventory_service),
):
    """
    Adjust stock by positive (restock) or negative (sell/remove) amount.
    Prevents negative stock. Staff or manager (real-time data entry).
    """
    return service.adjust_stock(inventory_id, payload)


@router.delete(
    "/{inventory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete inventory record",
)
def delete_inventory(
    inventory_id: UUID,
    current_user: User = Depends(get_current_manager),
    service: InventoryService = Depends(get_inventory_service),
):
    """Delete an inventory record. Requires manager role."""
    service.delete(inventory_id)