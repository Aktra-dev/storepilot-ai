"""
Unit tests for InventoryRiskService.

Pure unit tests — no database, no FastAPI app, no HTTP. The service is
deterministic, so every test gives fixed inputs and asserts an exact
expected risk_level (and, where relevant, the calculated numbers).
"""

from datetime import date, timedelta

from app.modules.inventory.schemas import RiskLevel
from app.modules.inventory.service import InventoryRiskService

service = InventoryRiskService()


# ---------------------------------------------------------------------------
# Stockout risk
# ---------------------------------------------------------------------------

def test_stockout_critical():
    # current_stock=5, avg_daily_sales=5 -> estimated_days_remaining=1 (<=1 -> CRITICAL)
    result = service.assess_stockout_risk(
        current_stock=5,
        recent_sales_quantities=[5, 5, 5],
    )
    assert result.risk_level == RiskLevel.CRITICAL
    assert result.estimated_days_remaining == 1
    assert result.average_daily_sales == 5


def test_stockout_high():
    # current_stock=9, avg_daily_sales=3 -> estimated_days_remaining=3 (<=3 -> HIGH)
    result = service.assess_stockout_risk(
        current_stock=9,
        recent_sales_quantities=[3, 3, 3],
    )
    assert result.risk_level == RiskLevel.HIGH
    assert result.estimated_days_remaining == 3


def test_stockout_medium():
    # current_stock=20, avg_daily_sales=4 -> estimated_days_remaining=5 (<=7 -> MEDIUM)
    result = service.assess_stockout_risk(
        current_stock=20,
        recent_sales_quantities=[4, 4, 4],
    )
    assert result.risk_level == RiskLevel.MEDIUM
    assert result.estimated_days_remaining == 5


def test_stockout_low():
    # current_stock=100, avg_daily_sales=2 -> estimated_days_remaining=50 (>7 -> LOW)
    result = service.assess_stockout_risk(
        current_stock=100,
        recent_sales_quantities=[2, 2, 2],
    )
    assert result.risk_level == RiskLevel.LOW


def test_stockout_zero_sales_no_division_by_zero():
    # All recorded sales are zero -> average_daily_sales == 0.
    # Must NOT raise ZeroDivisionError, must return NO_SALES_DATA instead.
    result = service.assess_stockout_risk(
        current_stock=50,
        recent_sales_quantities=[0, 0, 0],
    )
    assert result.risk_level == RiskLevel.NO_SALES_DATA
    assert result.estimated_days_remaining is None


def test_stockout_empty_sales_list():
    # No sales records at all (empty list) -> treated as missing data.
    result = service.assess_stockout_risk(
        current_stock=50,
        recent_sales_quantities=[],
    )
    assert result.risk_level == RiskLevel.NO_SALES_DATA
    assert result.estimated_days_remaining is None


def test_stockout_missing_sales_none():
    # recent_sales_quantities=None (e.g. product never queried before)
    result = service.assess_stockout_risk(
        current_stock=50,
        recent_sales_quantities=None,
    )
    assert result.risk_level == RiskLevel.NO_SALES_DATA


def test_stockout_missing_current_stock():
    result = service.assess_stockout_risk(
        current_stock=None,
        recent_sales_quantities=[5, 5, 5],
    )
    assert result.risk_level == RiskLevel.INVALID_DATA


def test_stockout_negative_current_stock():
    result = service.assess_stockout_risk(
        current_stock=-10,
        recent_sales_quantities=[5, 5, 5],
    )
    assert result.risk_level == RiskLevel.INVALID_DATA


# ---------------------------------------------------------------------------
# Expiry risk
# ---------------------------------------------------------------------------

def test_expiry_expired_product():
    # expiry_date already in the past -> CRITICAL
    today = date(2026, 7, 11)
    expiry_date = today - timedelta(days=2)
    result = service.assess_expiry_risk(expiry_date=expiry_date, reference_date=today)
    assert result.risk_level == RiskLevel.CRITICAL
    assert result.days_to_expiry == -2


def test_expiry_critical_boundary():
    # expiry in exactly 1 day -> CRITICAL
    today = date(2026, 7, 11)
    expiry_date = today + timedelta(days=1)
    result = service.assess_expiry_risk(expiry_date=expiry_date, reference_date=today)
    assert result.risk_level == RiskLevel.CRITICAL


def test_expiry_near_expiry_high():
    # expiry in 3 days -> HIGH
    today = date(2026, 7, 11)
    expiry_date = today + timedelta(days=3)
    result = service.assess_expiry_risk(expiry_date=expiry_date, reference_date=today)
    assert result.risk_level == RiskLevel.HIGH


def test_expiry_medium():
    # expiry in 7 days -> MEDIUM
    today = date(2026, 7, 11)
    expiry_date = today + timedelta(days=7)
    result = service.assess_expiry_risk(expiry_date=expiry_date, reference_date=today)
    assert result.risk_level == RiskLevel.MEDIUM


def test_expiry_low():
    # expiry in 30 days -> LOW
    today = date(2026, 7, 11)
    expiry_date = today + timedelta(days=30)
    result = service.assess_expiry_risk(expiry_date=expiry_date, reference_date=today)
    assert result.risk_level == RiskLevel.LOW


def test_expiry_missing_expiry_date():
    # Non-perishable product / missing data -> NO_EXPIRY_DATA, not a crash
    result = service.assess_expiry_risk(expiry_date=None)
    assert result.risk_level == RiskLevel.NO_EXPIRY_DATA


# ---------------------------------------------------------------------------
# Combined result
# ---------------------------------------------------------------------------

def test_assess_product_risk_combines_both():
    today = date(2026, 7, 11)
    result = service.assess_product_risk(
        current_stock=5,
        recent_sales_quantities=[5, 5, 5],
        expiry_date=today + timedelta(days=2),
        product_id="SKU-001",
        reference_date=today,
    )
    assert result.product_id == "SKU-001"
    assert result.stockout_risk.risk_level == RiskLevel.CRITICAL
    assert result.expiry_risk.risk_level == RiskLevel.HIGH
