"""
Inventory — Pydantic schemas.

This file contains two types of schemas:
1. CRUD Schemas: For inventory record CRUD operations (Create, Update, Response)
2. Risk Schemas: Output contracts for InventoryRiskService (used by AI analysis pipeline)
"""

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# =========================================================================
# PART 1: CRUD Schemas (for inventory record CRUD operations)
# =========================================================================

class InventoryCreate(BaseModel):
    """Schema for adding a new inventory/batch record."""
    product_id: uuid.UUID = Field(..., description="Product ID")
    quantity: int = Field(..., ge=0, description="Quantity/stock count")
    expiry_date: Optional[date] = Field(default=None, description="Expiry date (if perishable)")


class InventoryUpdate(BaseModel):
    """Schema for updating an inventory record."""
    quantity: Optional[int] = Field(default=None, ge=0)
    expiry_date: Optional[date] = Field(default=None)


class StockAdjustment(BaseModel):
    """Schema for stock adjustment (increase or decrease)."""
    quantity_change: int = Field(
        ...,
        description="Positive = add stock, negative = remove stock",
    )
    reason: Optional[str] = Field(default=None, max_length=255)


class InventoryResponse(BaseModel):
    """Public inventory record data."""
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    expiry_date: Optional[date]
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryWithProductResponse(InventoryResponse):
    """Inventory record with product info."""
    product_sku: Optional[str] = None
    product_name: Optional[str] = None


class StockStatusResponse(BaseModel):
    """Current stock status for a product."""
    product_id: uuid.UUID
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    total_quantity: int
    min_stock: int
    has_inventory_records: bool


class StockAlert(BaseModel):
    """Stock alert info (low stock or near expiry)."""
    product_id: uuid.UUID
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    alert_type: str  # "low_stock" or "near_expiry"
    current_quantity: int
    min_stock: int
    days_to_expiry: Optional[int] = None


# =========================================================================
# PART 2: Risk Schemas (used by InventoryRiskService & AI pipeline)
# These are kept here because they describe inventory risk *results*,
# not database rows — but they're imported by multiple modules.
# =========================================================================

class RiskLevel(str, Enum):
    """Severity levels shared by both stockout and expiry risk."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    # Special statuses — not a severity, but "we can't classify this yet"
    NO_SALES_DATA = "NO_SALES_DATA"
    NO_EXPIRY_DATA = "NO_EXPIRY_DATA"
    INVALID_DATA = "INVALID_DATA"


class StockoutRiskResult(BaseModel):
    risk_level: RiskLevel
    current_stock: Optional[int] = None
    average_daily_sales: Optional[float] = None
    estimated_days_remaining: Optional[float] = None
    note: Optional[str] = None


class ExpiryRiskResult(BaseModel):
    risk_level: RiskLevel
    expiry_date: Optional[date] = None
    days_to_expiry: Optional[int] = None
    note: Optional[str] = None


class InventoryRiskResult(BaseModel):
    """Combined result for one product — stockout risk + expiry risk."""

    product_id: Optional[str] = None
    stockout_risk: StockoutRiskResult
    expiry_risk: ExpiryRiskResult
