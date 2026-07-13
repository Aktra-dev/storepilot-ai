"""
Inventory Monitoring — business logic.

InventoryRiskService is a deterministic rule engine: given plain data
(stock, recent sales quantities, expiry date), it classifies stockout
and expiry risk. No AI, no database access, no I/O inside this class —
that's deliberate, so it stays fast, predictable, and trivially
unit-testable, and can run safely *before* any data reaches the AI step
in the pipeline.
"""

from datetime import date
from typing import Optional, Sequence

from app.modules.inventory.schemas import (
    ExpiryRiskResult,
    InventoryRiskResult,
    RiskLevel,
    StockoutRiskResult,
)


class InventoryRiskService:
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

        Handles: missing stock, invalid (negative) stock, missing/empty
        sales data, and average_daily_sales == 0 (division by zero).
        """
        # --- Invalid / missing stock ---
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

        # --- Missing / empty sales data ---
        if not recent_sales_quantities:
            return StockoutRiskResult(
                risk_level=RiskLevel.NO_SALES_DATA,
                current_stock=current_stock,
                average_daily_sales=0,
                note="No recent sales data available",
            )

        average_daily_sales = sum(recent_sales_quantities) / len(recent_sales_quantities)

        # --- Zero average sales: avoid division by zero ---
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

        Handles missing expiry_date (e.g. non-perishable products).
        Already-expired products fall through to CRITICAL, since
        days_to_expiry will be <= 0, which is <= EXPIRY_CRITICAL_DAYS.
        """
        if expiry_date is None:
            return ExpiryRiskResult(
                risk_level=RiskLevel.NO_EXPIRY_DATA,
                note="Product has no expiry date",
            )

        today = reference_date or date.today()
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
        """Convenience method: run both checks and return a combined result."""
        return InventoryRiskResult(
            product_id=product_id,
            stockout_risk=self.assess_stockout_risk(current_stock, recent_sales_quantities),
            expiry_risk=self.assess_expiry_risk(expiry_date, reference_date),
        )
