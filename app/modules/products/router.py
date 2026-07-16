"""
Product Master Data — API routes.

Endpoints:
    POST   /products              Create product (manager)
    GET    /products              List products (paginated)
    GET    /products/all          List all products (no pagination)
    GET    /products/search       Search by name/SKU
    GET    /products/{id}         Get product by ID
    PATCH  /products/{id}         Update product (manager)
    DELETE /products/{id}         Delete product (manager)
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user, get_current_manager
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.products.schemas import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.modules.products.service import ProductService

router = APIRouter()


# =========================================================================
# Helper: get service instance
# =========================================================================

def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db=db)


# =========================================================================
# ENDPOINTS
# =========================================================================

@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_manager),
    service: ProductService = Depends(get_product_service),
):
    """Create a new product. Requires manager role."""
    return service.create(payload)


@router.get(
    "",
    response_model=List[ProductResponse],
    summary="List products (paginated)",
)
def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
):
    """Return paginated list of products."""
    items, total = service.get_list(skip=skip, limit=limit)
    return items


@router.get(
    "/all",
    response_model=List[ProductResponse],
    summary="List all products (no pagination)",
)
def list_all_products(
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
):
    """Return all products without pagination (for dropdowns, etc.)."""
    return service.list_all()


@router.get(
    "/search",
    response_model=List[ProductResponse],
    summary="Search products by name or SKU",
)
def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
):
    """Search products by name or SKU (for autocomplete)."""
    return service.search(q)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
)
def get_product(
    product_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
):
    """Get a single product by ID."""
    return service.get(product_id)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    current_user: User = Depends(get_current_manager),
    service: ProductService = Depends(get_product_service),
):
    """Update a product. Requires manager role."""
    return service.update(product_id, payload)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
)
def delete_product(
    product_id: UUID,
    current_user: User = Depends(get_current_manager),
    service: ProductService = Depends(get_product_service),
):
    """Delete a product. Requires manager role."""
    service.delete(product_id)