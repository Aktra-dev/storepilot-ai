"""
Sales — Pydantic schemas.

Defines request/response DTOs for sales CRUD operations, plus the
existing analysis schemas used by SalesAnomalyService/AI pipeline.
"""

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# =========================================================================
# PART 1: CRUD Schemas (for sales transaction CRUD operations)
# =========================================================================

class SaleCreate(BaseModel):
    """Schema for recording a new sale."""
    product_id: uuid.UUID = Field(..., description="Product being sold")
    quantity: int = Field(..., gt=0, description="Quantity sold")
    total_amount: float = Field(..., ge=0, description="Total amount (price × qty)")
    sale_date: date = Field(default_factory=date.today, description="Date of sale")


class SaleUpdate(BaseModel):
    """Schema for updating a sale record. All fields optional."""
    quantity: Optional[int] = Field(default=None, gt=0)
    total_amount: Optional[float] = Field(default=None, ge=0)
    sale_date: Optional[date] = Field(default=None)


class SaleResponse(BaseModel):
    """Public sale data returned by the API."""
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    total_amount: float
    sale_date: date

    model_config = {"from_attributes": True}


class SaleWithProductResponse(SaleResponse):
    """Sale response with product info."""
    product_name: Optional[str] = None
    product_sku: Optional[str] = None


class SalesSummary(BaseModel):
    """Aggregated sales summary."""
    total_sales: int = 0
    total_revenue: float = 0
    average_per_day: Optional[float] = None
    top_products: list[dict] = []


# =========================================================================
# PART 2: Analysis Schemas (used by SalesAnomalyService & AI pipeline)
# =========================================================================

class AnomalyStatus(str, Enum):
    DROP_CRITICAL = "DROP_CRITICAL"
    DROP_HIGH = "DROP_HIGH"
    DROP_MEDIUM = "DROP_MEDIUM"
    SPIKE = "SPIKE"
    NORMAL = "NORMAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SalesAnomalyResult(BaseModel):
    status: AnomalyStatus
    recent_average: Optional[float] = None
    historical_average: Optional[float] = None
    percentage_change: Optional[float] = None
    confidence: float
    note: Optional[str] = None
