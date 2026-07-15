"""
Unit tests for AIOperationalAnalysisService.

Uses MockAIProvider to simulate every scenario deterministically — no
real API calls anywhere in this file.
"""

import json

from app.modules.ai_engine.mock_provider import MockAIProvider
from app.modules.ai_engine.schemas import (
    AssignedRole,
    FindingType,
    ProductSalesAnomaly,
    SeverityLevel,
    StoreStatus,
    TaskPriority,
)
from app.modules.ai_engine.service import AIOperationalAnalysisService
from app.modules.inventory.schemas import (
    ExpiryRiskResult,
    InventoryRiskResult,
    RiskLevel,
    StockoutRiskResult,
)
from app.modules.sales.schemas import AnomalyStatus, SalesAnomalyResult

VALID_AI_RESPONSE = json.dumps(
    {
        "summary": "1 stockout risk detected on SKU-001.",
        "store_status": "ATTENTION",
        "findings": [
            {
                "type": "STOCKOUT",
                "product_id": "SKU-001",
                "severity": "HIGH",
                "title": "Low stock",
                "description": "Stock is running low based on recent sales pace.",
                "recommended_action": "Reorder soon.",
                "confidence": 0.9,
            }
        ],
        "tasks": [
            {
                "title": "Reorder SKU-001",
                "description": "Place a reorder before stock runs out.",
                "priority": "HIGH",
                "assigned_role": "INVENTORY_STAFF",
                "source_finding_index": 0,
            }
        ],
    }
)


# ---------------------------------------------------------------------------
# Valid response
# ---------------------------------------------------------------------------

def test_valid_ai_response_is_accepted():
    provider = MockAIProvider(responses=[VALID_AI_RESPONSE])
    service = AIOperationalAnalysisService(provider=provider)

    result, provider_used = service.analyze(inventory_risks=[], sales_anomalies=[])

    assert provider_used == "ai"
    assert provider.call_count == 1
    assert result.store_status == StoreStatus.ATTENTION
    assert len(result.findings) == 1
    assert result.findings[0].type == FindingType.STOCKOUT
    assert result.tasks[0].assigned_role == AssignedRole.INVENTORY_STAFF


# ---------------------------------------------------------------------------
# Invalid JSON -> retries exhausted -> fallback
# ---------------------------------------------------------------------------

def test_invalid_json_falls_back_after_retries():
    provider = MockAIProvider(responses=["not valid json", "{broken", "still not json"])
    service = AIOperationalAnalysisService(provider=provider)

    result, provider_used = service.analyze(inventory_risks=[], sales_anomalies=[])

    assert provider_used == "fallback"
    assert provider.call_count == 3  # MAX_RETRIES (2) + 1 initial attempt


# ---------------------------------------------------------------------------
# Missing required field -> retries exhausted -> fallback
# ---------------------------------------------------------------------------

def test_missing_required_field_falls_back():
    missing_summary = json.dumps(
        {
            # "summary" is missing entirely
            "store_status": "NORMAL",
            "findings": [],
            "tasks": [],
        }
    )
    provider = MockAIProvider(responses=[missing_summary, missing_summary, missing_summary])
    service = AIOperationalAnalysisService(provider=provider)

    result, provider_used = service.analyze(inventory_risks=[], sales_anomalies=[])

    assert provider_used == "fallback"


# ---------------------------------------------------------------------------
# Invalid enum value -> retries exhausted -> fallback
# ---------------------------------------------------------------------------

def test_invalid_severity_enum_falls_back():
    invalid_severity = json.dumps(
        {
            "summary": "test",
            "store_status": "NORMAL",
            "findings": [
                {
                    "type": "STOCKOUT",
                    "product_id": "SKU-001",
                    "severity": "SUPER_CRITICAL",  # not a valid SeverityLevel
                    "title": "t",
                    "description": "d",
                    "recommended_action": "a",
                    "confidence": 0.5,
                }
            ],
            "tasks": [],
        }
    )
    provider = MockAIProvider(responses=[invalid_severity] * 3)
    service = AIOperationalAnalysisService(provider=provider)

    result, provider_used = service.analyze(inventory_risks=[], sales_anomalies=[])

    assert provider_used == "fallback"


def test_confidence_out_of_range_falls_back():
    invalid_confidence = json.dumps(
        {
            "summary": "test",
            "store_status": "NORMAL",
            "findings": [
                {
                    "type": "STOCKOUT",
                    "product_id": "SKU-001",
                    "severity": "HIGH",
                    "title": "t",
                    "description": "d",
                    "recommended_action": "a",
                    "confidence": 1.5,  # out of the 0..1 range
                }
            ],
            "tasks": [],
        }
    )
    provider = MockAIProvider(responses=[invalid_confidence] * 3)
    service = AIOperationalAnalysisService(provider=provider)

    result, provider_used = service.analyze(inventory_risks=[], sales_anomalies=[])

    assert provider_used == "fallback"


# ---------------------------------------------------------------------------
# Retry success: fails once, then succeeds
# ---------------------------------------------------------------------------

def test_retry_then_success():
    provider = MockAIProvider(responses=["not valid json", VALID_AI_RESPONSE])
    service = AIOperationalAnalysisService(provider=provider)

    result, provider_used = service.analyze(inventory_risks=[], sales_anomalies=[])

    assert provider_used == "ai"
    assert provider.call_count == 2
    assert result.store_status == StoreStatus.ATTENTION


# ---------------------------------------------------------------------------
# Retry failure: fails on every attempt -> fallback
# ---------------------------------------------------------------------------

def test_retry_failure_exhausts_all_attempts():
    provider = MockAIProvider(responses=["bad", "bad", "bad"])
    service = AIOperationalAnalysisService(provider=provider)

    result, provider_used = service.analyze(inventory_risks=[], sales_anomalies=[])

    assert provider_used == "fallback"
    assert provider.call_count == AIOperationalAnalysisService.MAX_RETRIES + 1


# ---------------------------------------------------------------------------
# Fallback execution: verify it produces a correct, structured result
# ---------------------------------------------------------------------------

def test_fallback_execution_produces_valid_structured_result():
    inventory_risks = [
        InventoryRiskResult(
            product_id="SKU-001",
            stockout_risk=StockoutRiskResult(
                risk_level=RiskLevel.CRITICAL,
                current_stock=2,
                average_daily_sales=5,
                estimated_days_remaining=0.4,
            ),
            expiry_risk=ExpiryRiskResult(risk_level=RiskLevel.LOW),
        )
    ]
    sales_anomalies = [
        ProductSalesAnomaly(
            product_id="SKU-002",
            result=SalesAnomalyResult(
                status=AnomalyStatus.DROP_CRITICAL,
                recent_average=1,
                historical_average=10,
                percentage_change=-90,
                confidence=1.0,
            ),
        )
    ]

    provider = MockAIProvider(responses=["invalid", "invalid", "invalid"])
    service = AIOperationalAnalysisService(provider=provider)

    result, provider_used = service.analyze(inventory_risks, sales_anomalies)

    assert provider_used == "fallback"
    assert result.store_status == StoreStatus.CRITICAL
    # 1 stockout finding (CRITICAL) + 1 sales anomaly finding (CRITICAL);
    # the LOW expiry risk is correctly skipped (not an issue worth reporting).
    assert len(result.findings) == 2
    assert len(result.tasks) == 2
    assert result.tasks[0].priority == TaskPriority.URGENT
    assert result.findings[1].type == FindingType.SALES_ANOMALY
    assert result.tasks[1].assigned_role == AssignedRole.MANAGER
