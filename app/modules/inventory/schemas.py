"""
Inventory Monitoring — Pydantic schemas.

Structured output contract for InventoryRiskService (see service.py).
Kept separate from the SQLAlchemy models (models.py) — these describe
the *result* of a risk calculation, not a database table.
"""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel


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
