"""
Unit tests for SalesAnomalyService.

Pure unit tests — no database, no HTTP. Deterministic inputs, exact
expected status/percentage_change asserted.
"""

from app.modules.sales.schemas import AnomalyStatus
from app.modules.sales.service import SalesAnomalyService

service = SalesAnomalyService()


def test_critical_sales_drop():
    # historical avg = 10/day, recent avg = 2/day -> -80% (<= -70 -> DROP_CRITICAL)
    result = service.assess_sales_anomaly(
        recent_sales=[2, 2, 2],
        historical_sales=[10] * 14,
    )
    assert result.status == AnomalyStatus.DROP_CRITICAL
    assert result.percentage_change == -80


def test_high_sales_drop():
    # historical avg = 10/day, recent avg = 5/day -> -50% (<= -40 -> DROP_HIGH)
    result = service.assess_sales_anomaly(
        recent_sales=[5, 5, 5],
        historical_sales=[10] * 14,
    )
    assert result.status == AnomalyStatus.DROP_HIGH
    assert result.percentage_change == -50


def test_medium_sales_drop():
    # historical avg = 10/day, recent avg = 8/day -> -20% (<= -20 -> DROP_MEDIUM)
    result = service.assess_sales_anomaly(
        recent_sales=[8, 8, 8],
        historical_sales=[10] * 14,
    )
    assert result.status == AnomalyStatus.DROP_MEDIUM
    assert result.percentage_change == -20


def test_sales_spike():
    # historical avg = 10/day, recent avg = 25/day -> +150% (>= 100 -> SPIKE)
    result = service.assess_sales_anomaly(
        recent_sales=[25, 25, 25],
        historical_sales=[10] * 14,
    )
    assert result.status == AnomalyStatus.SPIKE
    assert result.percentage_change == 150


def test_normal_sales():
    # historical avg = 10/day, recent avg = 9/day -> -10% (no threshold met -> NORMAL)
    result = service.assess_sales_anomaly(
        recent_sales=[9, 9, 9],
        historical_sales=[10] * 14,
    )
    assert result.status == AnomalyStatus.NORMAL
    assert result.percentage_change == -10


def test_zero_historical_sales_with_recent_sales_is_spike():
    # historical_average == 0, recent has sales -> SPIKE, percentage undefined
    result = service.assess_sales_anomaly(
        recent_sales=[5, 5, 5],
        historical_sales=[0] * 14,
    )
    assert result.status == AnomalyStatus.SPIKE
    assert result.percentage_change is None
    assert result.historical_average == 0


def test_zero_historical_and_zero_recent_is_normal():
    # Both periods have zero sales -> nothing changed -> NORMAL, not an error
    result = service.assess_sales_anomaly(
        recent_sales=[0, 0, 0],
        historical_sales=[0] * 14,
    )
    assert result.status == AnomalyStatus.NORMAL
    assert result.percentage_change == 0


def test_insufficient_data_empty_recent():
    result = service.assess_sales_anomaly(
        recent_sales=[],
        historical_sales=[10] * 14,
    )
    assert result.status == AnomalyStatus.INSUFFICIENT_DATA


def test_insufficient_data_too_few_historical_days():
    # Only 2 historical days provided, below MIN_HISTORICAL_DAYS_REQUIRED (3)
    result = service.assess_sales_anomaly(
        recent_sales=[5, 5, 5],
        historical_sales=[10, 10],
    )
    assert result.status == AnomalyStatus.INSUFFICIENT_DATA


def test_insufficient_data_none_inputs():
    result = service.assess_sales_anomaly(recent_sales=None, historical_sales=None)
    assert result.status == AnomalyStatus.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# Confidence indicator (data completeness)
# ---------------------------------------------------------------------------

def test_confidence_is_full_with_complete_data():
    # 3 recent days + 14 historical days = full expected periods -> confidence 1.0
    result = service.assess_sales_anomaly(
        recent_sales=[9, 9, 9],
        historical_sales=[10] * 14,
    )
    assert result.confidence == 1.0


def test_confidence_is_lower_with_partial_historical_data():
    # 3 recent days (full) + 7 historical days (half of 14) -> confidence ~0.75
    result = service.assess_sales_anomaly(
        recent_sales=[9, 9, 9],
        historical_sales=[10, 10, 10, 10, 10, 10, 10],
    )
    assert 0 < result.confidence < 1.0
