"""
Operational Analysis — OperationalWorkflowService.

Orchestrates the full autonomous operation workflow:
    load store data -> InventoryRiskService -> SalesAnomalyService
    -> combine findings -> AIOperationalAnalysisService -> validate
    -> persist analysis + findings + tasks (one DB transaction)

Tasks are always created as PENDING_APPROVAL. This service NEVER
executes a task -- only a manager approving it (a separate Approval
record, see app/modules/approvals) can move it forward. That approval
step is intentionally outside this workflow's responsibility.
"""

import logging
import uuid
from datetime import date, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.modules.ai_engine.schemas import ProductSalesAnomaly
from app.modules.ai_engine.service import AIOperationalAnalysisService
from app.modules.inventory.models import Inventory
from app.modules.inventory.schemas import InventoryRiskResult
from app.modules.inventory.service import InventoryRiskService
from app.modules.operational_analysis.models import (
    AnalysisStatus,
    FindingType,
    OperationalAnalysis,
    OperationalFinding,
    Severity,
)
from app.modules.products.models import Product
from app.modules.sales.models import Sale
from app.modules.sales.service import SalesAnomalyService
from app.modules.tasks.models import Task, TaskPriority, TaskStatus

logger = logging.getLogger("storepilot.operational_analysis")

RECENT_PERIOD_DAYS = 3
HISTORICAL_PERIOD_DAYS = 14

# --- AI/fallback output values (uppercase, from ai_engine.schemas) -> DB enums ---
_AI_SEVERITY_TO_DB = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
}

_AI_FINDING_TYPE_TO_DB = {
    "STOCKOUT": FindingType.STOCKOUT,
    "EXPIRY": FindingType.EXPIRY,
    "SALES_ANOMALY": FindingType.SALES_ANOMALY,
    "OPERATIONAL": FindingType.OPERATIONAL,
}

# TaskPriority (DB) has no "URGENT" level -- URGENT maps to the most
# severe existing option, CRITICAL.
_AI_PRIORITY_TO_DB = {
    "URGENT": TaskPriority.CRITICAL,
    "HIGH": TaskPriority.HIGH,
    "MEDIUM": TaskPriority.MEDIUM,
    "LOW": TaskPriority.LOW,
}


class OperationalWorkflowService:
    def __init__(
        self,
        db: Session,
        ai_service: AIOperationalAnalysisService,
        reference_date: Optional[date] = None,
    ):
        self.db = db
        self.ai_service = ai_service
        self.inventory_risk_service = InventoryRiskService()
        self.sales_anomaly_service = SalesAnomalyService()
        self.reference_date = reference_date or date.today()

    # ------------------------------------------------------------------
    # Steps 1-4: load store data, run deterministic engines
    # ------------------------------------------------------------------

    def _load_product_signals(
        self,
    ) -> Tuple[List[InventoryRiskResult], List[ProductSalesAnomaly]]:
        products = self.db.query(Product).all()
        inventory_risks: List[InventoryRiskResult] = []
        sales_anomalies: List[ProductSalesAnomaly] = []

        recent_start = self.reference_date - timedelta(days=RECENT_PERIOD_DAYS - 1)
        historical_start = recent_start - timedelta(days=HISTORICAL_PERIOD_DAYS)
        historical_end = recent_start - timedelta(days=1)

        for product in products:
            latest_inventory = (
                self.db.query(Inventory)
                .filter(Inventory.product_id == product.id)
                .order_by(Inventory.updated_at.desc())
                .first()
            )
            current_stock = latest_inventory.quantity if latest_inventory else None
            expiry_date = latest_inventory.expiry_date if latest_inventory else None

            recent_sales = (
                self.db.query(Sale)
                .filter(
                    Sale.product_id == product.id,
                    Sale.sale_date >= recent_start,
                    Sale.sale_date <= self.reference_date,
                )
                .all()
            )
            historical_sales = (
                self.db.query(Sale)
                .filter(
                    Sale.product_id == product.id,
                    Sale.sale_date >= historical_start,
                    Sale.sale_date <= historical_end,
                )
                .all()
            )
            recent_quantities = [s.quantity for s in recent_sales]
            historical_quantities = [s.quantity for s in historical_sales]

            inventory_risks.append(
                self.inventory_risk_service.assess_product_risk(
                    current_stock=current_stock,
                    recent_sales_quantities=recent_quantities,
                    expiry_date=expiry_date,
                    product_id=str(product.id),
                    reference_date=self.reference_date,
                )
            )

            sales_result = self.sales_anomaly_service.assess_sales_anomaly(
                recent_sales=recent_quantities,
                historical_sales=historical_quantities,
            )
            sales_anomalies.append(
                ProductSalesAnomaly(product_id=str(product.id), result=sales_result)
            )

        return inventory_risks, sales_anomalies

    # ------------------------------------------------------------------
    # Full workflow: POST /api/operations/analyze
    # ------------------------------------------------------------------

    def run_analysis(self) -> dict:
        # Steps 1-4: deterministic, read-only -- safe to run outside any
        # DB write transaction.
        inventory_risks, sales_anomalies = self._load_product_signals()

        # Step 5-6: AI interpretation + validation (retry + fallback are
        # handled inside the AI service itself).
        ai_result, provider_used = self.ai_service.analyze(inventory_risks, sales_anomalies)

        # Steps 7-10: persist everything in a single transaction.
        try:
            analysis = OperationalAnalysis(
                status=AnalysisStatus.COMPLETED,
                summary=ai_result.summary,
                ai_provider=provider_used,
            )
            self.db.add(analysis)
            self.db.flush()  # need analysis.id for the findings' FK

            saved_findings: List[OperationalFinding] = []
            for finding in ai_result.findings:
                db_finding = OperationalFinding(
                    analysis_id=analysis.id,
                    finding_type=_AI_FINDING_TYPE_TO_DB[finding.type.value],
                    product_id=self._safe_uuid(finding.product_id),
                    severity=_AI_SEVERITY_TO_DB[finding.severity.value],
                    title=finding.title,
                    description=finding.description,
                    confidence=finding.confidence,
                )
                self.db.add(db_finding)
                saved_findings.append(db_finding)
            self.db.flush()  # need each finding.id for the tasks' FK

            seen_tasks = set()
            created_tasks_count = 0
            for ai_task in ai_result.tasks:
                if ai_task.source_finding_index >= len(saved_findings):
                    # AI referenced a finding index that doesn't exist --
                    # skip this task rather than fail the whole save.
                    logger.warning(
                        "AI task referenced out-of-range finding index %d, skipping",
                        ai_task.source_finding_index,
                    )
                    continue

                finding_id = saved_findings[ai_task.source_finding_index].id

                # Avoid duplicate tasks for the same finding+title within
                # this analysis run.
                dedup_key = (finding_id, ai_task.title)
                if dedup_key in seen_tasks:
                    continue
                seen_tasks.add(dedup_key)

                self.db.add(
                    Task(
                        finding_id=finding_id,
                        title=ai_task.title,
                        description=ai_task.description,
                        priority=_AI_PRIORITY_TO_DB[ai_task.priority.value],
                        assigned_role=ai_task.assigned_role.value,
                        # ALWAYS pending approval -- this workflow never
                        # executes a task itself.
                        status=TaskStatus.PENDING_APPROVAL,
                    )
                )
                created_tasks_count += 1

            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.exception("Failed to persist operational analysis; rolled back.")
            raise AppException(
                message="Failed to save operational analysis results",
                status_code=500,
            ) from exc

        return {
            "analysis_id": analysis.id,
            "store_status": ai_result.store_status.value,
            "summary": ai_result.summary,
            "findings_count": len(saved_findings),
            "proposed_tasks_count": created_tasks_count,
        }

    # ------------------------------------------------------------------
    # GET /api/operations/{analysis_id}
    # ------------------------------------------------------------------

    def get_analysis(self, analysis_id: uuid.UUID) -> dict:
        analysis = self.db.query(OperationalAnalysis).filter_by(id=analysis_id).first()
        if not analysis:
            raise NotFoundException(f"Operational analysis {analysis_id} not found")

        findings = (
            self.db.query(OperationalFinding).filter_by(analysis_id=analysis_id).all()
        )
        finding_ids = [f.id for f in findings]
        tasks = (
            self.db.query(Task).filter(Task.finding_id.in_(finding_ids)).all()
            if finding_ids
            else []
        )

        return {
            "analysis": analysis,
            "findings": findings,
            "proposed_tasks": tasks,
        }

    @staticmethod
    def _safe_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
        if not value:
            return None
        try:
            return uuid.UUID(value)
        except (ValueError, AttributeError):
            return None
