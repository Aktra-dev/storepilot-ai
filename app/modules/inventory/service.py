"""
Inventory — business logic.

Two services coexist here:
1. InventoryService  — CRUD + stock management (DB operations)
2. InventoryRiskService — pure rule engine for stockout/expiry risk (no DB)
"""

import uuid
from datetime import date
from typing import Optional, List, Sequence

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.inventory.models import Inventory
from app.modules.inventory.schemas import (
    ExpiryRiskResult,
    InventoryCreate,
    InventoryRiskResult,
    InventoryUpdate,
    RiskLevel,
    StockAdjustment,
    StockoutRiskResult,
)
from app.modules.products.models import Product


class InventoryService:
    """Inventory CRUD and stock management."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, data: InventoryCreate) -> Inventory:
        """Add a new inventory/batch record."""
        # Verify product exists
        product = self.db.query(Product).filter(Product.id == data.product_id).first()
        if not product:
            raise NotFoundException(f"Product {data.product_id} not found")

        inv = Inventory(
            id=uuid.uuid4(),
            product_id=data.product_id,
            quantity=data.quantity,
            expiry_date=data.expiry_date,
        )
        self.db.add(inv)
        self.db.commit()
        self.db.refresh(inv)
        return inv

    def get(self, inventory_id: uuid.UUID) -> Inventory:
        """Get inventory record by ID."""
        inv = self.db.query(Inventory).filter(Inventory.id == inventory_id).first()
        if not inv:
            raise NotFoundException(f"Inventory record {inventory_id} not found")
        return inv

    def get_latest_by_product(self, product_id: uuid.UUID) -> Optional[Inventory]:
        """Get the most recently updated inventory record for a product."""
        return (
            self.db.query(Inventory)
            .filter(Inventory.product_id == product_id)
            .order_by(Inventory.updated_at.desc())
            .first()
        )

    def list_by_product(self, product_id: uuid.UUID) -> List[Inventory]:
        """List all inventory records for a product (newest first)."""
        return (
            self.db.query(Inventory)
            .filter(Inventory.product_id == product_id)
            .order_by(Inventory.updated_at.desc())
            .all()
        )

    def update(self, inventory_id: uuid.UUID, data: InventoryUpdate) -> Inventory:
        """Update inventory record."""
        inv = self.get(inventory_id)

        if data.quantity is not None:
            inv.quantity = data.quantity
        if data.expiry_date is not None:
            inv.expiry_date = data.expiry_date

        self.db.commit()
        self.db.refresh(inv)
        return inv

    def delete(self, inventory_id: uuid.UUID) -> None:
        """Delete inventory record."""
        inv = self.get(inventory_id)
        self.db.delete(inv)
        self.db.commit()

    # ------------------------------------------------------------------
    # Stock Queries
    # ------------------------------------------------------------------

    def get_total_stock(self, product_id: uuid.UUID) -> int:
        """Sum of all inventory quantities for a product."""
        result = (
            self.db.query(func.coalesce(func.sum(Inventory.quantity), 0))
            .filter(Inventory.product_id == product_id)
            .scalar()
        )
        return int(result or 0)

    def get_stock_by_expiry(self, product_id: uuid.UUID) -> List[Inventory]:
        """Get inventory records for a product, sorted by expiry date (soonest first)."""
        return (
            self.db.query(Inventory)
            .filter(Inventory.product_id == product_id)
            .order_by(Inventory.expiry_date.asc().nullslast())
            .all()
        )

    # ------------------------------------------------------------------
    # Stock Adjustment
    # ------------------------------------------------------------------

    def adjust_stock(self, inventory_id: uuid.UUID, adjustment: StockAdjustment) -> Inventory:
        """
        Adjust stock by positive or negative amount.

        Raises:
            ValidationException: If adjustment would result in negative stock.
        """
        inv = self.get(inventory_id)
        new_quantity = inv.quantity + adjustment.quantity_change

        if new_quantity < 0:
            raise ValidationException(
                f"Cannot reduce stock below zero. Current: {inv.quantity}, "
                f"requested change: {adjustment.quantity_change}"
            )

        inv.quantity = new_quantity
        self.db.commit()
        self.db.refresh(inv)
        return inv


# =========================================================================
# InventoryRiskService (pure rule engine — no DB access, no I/O)
# =========================================================================

class InventoryRiskService:
    """
    Deterministic rule engine for stockout/expiry risk.
    No AI, no database access — pure computation.
    Kept here because it describes inventory risk, not DB rows.
    """

    # --- Stockout thresholds, in estimated days remaining ---
    STOCKOUT_CRITICAL_DAYS = 1
    STOCKOUT_HIGH_DAYS = 3
    STOCKOUT_MEDIUM_DAYS = 7

    # --- Expiry thresholds, in days until expiry ---
    EXPIRY_CRITICAL_DAYS = 1
    EXPIRY_HIGH_DAYS = 3
    EXPIRY_MEDIUM_DAYS = 7

    def assess_stockout_risk(
        self,
        current_stock: Optional[int],
        recent_sales_quantities: Optional[Sequence[int]],
    ) -> StockoutRiskResult:
        """
        estimated_days_remaining = current_stock / average_daily_sales
        """
        if current_stock is None:
            return StockoutRiskResult(
                risk_level=RiskLevel.INVALID_DATA,
                current_stock=None,
                note="current_stock is missing",
            )
        if current_stock < 0:
            return StockoutRiskResult(
                risk_level=RiskLevel.INVALID_DATA,
                current_stock=current_stock,
                note="current_stock cannot be negative",
            )

        if not recent_sales_quantities:
            return StockoutRiskResult(
                risk_level=RiskLevel.NO_SALES_DATA,
                current_stock=current_stock,
                average_daily_sales=0,
                note="No recent sales data available",
            )

        average_daily_sales = sum(recent_sales_quantities) / len(recent_sales_quantities)

        if average_daily_sales == 0:
            return StockoutRiskResult(
                risk_level=RiskLevel.NO_SALES_DATA,
                current_stock=current_stock,
                average_daily_sales=0,
                note="Average daily sales is zero",
            )

        estimated_days_remaining = current_stock / average_daily_sales

        if estimated_days_remaining <= self.STOCKOUT_CRITICAL_DAYS:
            risk_level = RiskLevel.CRITICAL
        elif estimated_days_remaining <= self.STOCKOUT_HIGH_DAYS:
            risk_level = RiskLevel.HIGH
        elif estimated_days_remaining <= self.STOCKOUT_MEDIUM_DAYS:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return StockoutRiskResult(
            risk_level=risk_level,
            current_stock=current_stock,
            average_daily_sales=round(average_daily_sales, 2),
            estimated_days_remaining=round(estimated_days_remaining, 2),
        )

    def assess_expiry_risk(
        self,
        expiry_date: Optional[date],
        reference_date: Optional[date] = None,
    ) -> ExpiryRiskResult:
        """
        days_to_expiry = expiry_date - reference_date (default: today)
        """
        if expiry_date is None:
            return ExpiryRiskResult(
                risk_level=RiskLevel.NO_EXPIRY_DATA,
                note="Product has no expiry date",
            )

        from datetime import date as date_cls
        today = reference_date or date_cls.today()
        days_to_expiry = (expiry_date - today).days

        if days_to_expiry <= self.EXPIRY_CRITICAL_DAYS:
            risk_level = RiskLevel.CRITICAL
        elif days_to_expiry <= self.EXPIRY_HIGH_DAYS:
            risk_level = RiskLevel.HIGH
        elif days_to_expiry <= self.EXPIRY_MEDIUM_DAYS:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return ExpiryRiskResult(
            risk_level=risk_level,
            expiry_date=expiry_date,
            days_to_expiry=days_to_expiry,
        )

    def assess_product_risk(
        self,
        current_stock: Optional[int],
        recent_sales_quantities: Optional[Sequence[int]],
        expiry_date: Optional[date],
        product_id: Optional[str] = None,
        reference_date: Optional[date] = None,
    ) -> InventoryRiskResult:
        """Convenience: run both checks and return combined result."""
        return InventoryRiskResult(
            product_id=product_id,
            stockout_risk=self.assess_stockout_risk(current_stock, recent_sales_quantities),
            expiry_risk=self.assess_expiry_risk(expiry_date, reference_date),
        )