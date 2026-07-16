"""
Product Master Data — Pydantic schemas.

Defines request/response DTOs for product CRUD operations.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class ProductCreate(BaseModel):
    """Schema for creating a new product."""
    sku: str = Field(..., min_length=1, max_length=64, description="Stock Keeping Unit")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    category: Optional[str] = Field(default=None, max_length=100, description="Product category")
    minimum_stock: int = Field(default=0, ge=0, description="Minimum stock threshold")


class ProductUpdate(BaseModel):
    """Schema for updating an existing product. All fields optional."""
    sku: Optional[str] = Field(default=None, min_length=1, max_length=64)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    minimum_stock: Optional[int] = Field(default=None, ge=0)


class ProductListParams(BaseModel):
    """Query parameters for listing products."""
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)
    category: Optional[str] = Field(default=None)
    search: Optional[str] = Field(default=None, description="Search by SKU or name")


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class ProductResponse(BaseModel):
    """Public product data returned by the API."""
    id: uuid.UUID
    sku: str
    name: str
    category: Optional[str]
    minimum_stock: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    """Paginated list of products."""
    items: list[ProductResponse]
    total: int
    skip: int
    limit: int
