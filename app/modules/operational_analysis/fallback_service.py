"""
Rule-based fallback for AI Operational Analysis.

Used only when the AI provider fails (invalid JSON, invalid schema, or
any error) after all retries. Builds the exact same
AIOperationalAnalysisResult shape directly from the structured
inventory/sales inputs using fixed rules — no AI call involved, so it
always succeeds and is always available.
"""

from typing import List

from app.modules.ai_engine.schemas import (
    AIFinding,
    AIOperationalAnalysisResult,
    AITask,
    AssignedRole,
    FindingType,
    ProductSalesAnomaly,
    SeverityLevel,
    StoreStatus,
    TaskPriority,
)
from app.modules.inventory.schemas import InventoryRiskResult, RiskLevel
from app.modules.sales.schemas import AnomalyStatus

_RISK_TO_SEVERITY = {
    RiskLevel.CRITICAL: SeverityLevel.CRITICAL,
    RiskLevel.HIGH: SeverityLevel.HIGH,
    RiskLevel.MEDIUM: SeverityLevel.MEDIUM,
}

_ANOMALY_TO_SEVERITY = {
    AnomalyStatus.DROP_CRITICAL: SeverityLevel.CRITICAL,
    AnomalyStatus.DROP_HIGH: SeverityLevel.HIGH,
    AnomalyStatus.DROP_MEDIUM: SeverityLevel.MEDIUM,
    AnomalyStatus.SPIKE: SeverityLevel.MEDIUM,
}

_SEVERITY_TO_PRIORITY = {
    SeverityLevel.CRITICAL: TaskPriority.URGENT,
    SeverityLevel.HIGH: TaskPriority.HIGH,
    SeverityLevel.MEDIUM: TaskPriority.MEDIUM,
    SeverityLevel.LOW: TaskPriority.LOW,
}

# Confidence is capped lower than a real AI read, since this is a fixed
# rule mapping rather than genuine interpretation of the situation.
_RULE_BASED_CONFIDENCE = 0.6


class RuleBasedFallbackService:
    def generate(
        self,
        inventory_risks: List[InventoryRiskResult],
        sales_anomalies: List[ProductSalesAnomaly],
    ) -> AIOperationalAnalysisResult:
        findings: List[AIFinding] = self._build_findings(inventory_risks, sales_anomalies)
        tasks: List[AITask] = self._build_tasks(findings)
        store_status = self._determine_store_status(findings)

        summary = (
            f"{len(findings)} issue(s) detected by rule-based fallback analysis."
            if findings
            else "No operational issues detected."
        )

        return AIOperationalAnalysisResult(
            summary=summary,
            store_status=store_status,
            findings=findings,
            tasks=tasks,
        )

    def _build_findings(
        self,
        inventory_risks: List[InventoryRiskResult],
        sales_anomalies: List[ProductSalesAnomaly],
    ) -> List[AIFinding]:
        findings: List[AIFinding] = []

        for risk in inventory_risks:
            stockout = risk.stockout_risk
            product_label = risk.product_name or risk.product_id or "unknown"
            if stockout.risk_level in _RISK_TO_SEVERITY:
                findings.append(
                    AIFinding(
                        type=FindingType.STOCKOUT,
                        product_id=risk.product_id,
                        severity=_RISK_TO_SEVERITY[stockout.risk_level],
                        title=f"Stockout risk for {product_label}",
                        description=(
                            f"Estimated {stockout.estimated_days_remaining} day(s) of "
                            f"stock remaining at current sales pace."
                        ),
                        recommended_action="Reorder stock as soon as possible.",
                        confidence=_RULE_BASED_CONFIDENCE,
                    )
                )

            expiry = risk.expiry_risk
            if expiry.risk_level in _RISK_TO_SEVERITY:
                findings.append(
                    AIFinding(
                        type=FindingType.EXPIRY,
                        product_id=risk.product_id,
                        severity=_RISK_TO_SEVERITY[expiry.risk_level],
                        title=f"Expiry risk for {product_label}",
                        description=f"Product expires in {expiry.days_to_expiry} day(s).",
                        recommended_action="Prioritize selling or discounting this batch.",
                        confidence=_RULE_BASED_CONFIDENCE,
                    )
                )

        for entry in sales_anomalies:
            result = entry.result
            entry_label = entry.product_name or entry.product_id
            if result.status in _ANOMALY_TO_SEVERITY:
                findings.append(
                    AIFinding(
                        type=FindingType.SALES_ANOMALY,
                        product_id=entry.product_id,
                        severity=_ANOMALY_TO_SEVERITY[result.status],
                        title=f"Sales anomaly for {entry_label}",
                        description=(
                            f"Sales changed by {result.percentage_change}% compared "
                            f"to the historical average."
                        ),
                        recommended_action="Investigate the cause of this sales change.",
                        confidence=round(result.confidence * 0.8, 2),
                    )
                )

        return findings

    def _build_tasks(self, findings: List[AIFinding]) -> List[AITask]:
        tasks: List[AITask] = []
        for index, finding in enumerate(findings):
            role = (
                AssignedRole.MANAGER
                if finding.type == FindingType.SALES_ANOMALY
                else AssignedRole.INVENTORY_STAFF
            )
            tasks.append(
                AITask(
                    title=f"Follow up: {finding.title}",
                    description=finding.recommended_action,
                    priority=_SEVERITY_TO_PRIORITY[finding.severity],
                    assigned_role=role,
                    source_finding_index=index,
                )
            )
        return tasks

    def _determine_store_status(self, findings: List[AIFinding]) -> StoreStatus:
        if any(f.severity == SeverityLevel.CRITICAL for f in findings):
            return StoreStatus.CRITICAL
        if findings:
            return StoreStatus.ATTENTION
        return StoreStatus.NORMAL
