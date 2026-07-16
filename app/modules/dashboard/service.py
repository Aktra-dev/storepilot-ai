"""
Dashboard — business logic.

Strictly read-only. This service NEVER calls InventoryRiskService,
SalesAnomalyService, or AIOperationalAnalysisService -- it only reads
whatever the last OperationalWorkflowService.run_analysis() call already
persisted. Opening the dashboard never triggers a new analysis.

Query efficiency notes:
- Counts (findings by severity, tasks by status) use SQL-level
  func.count(...) with a filter, never "fetch everything and len() it
  in Python".
- Severity is a native Postgres enum, but its Python-declaration order
  (CRITICAL, HIGH, MEDIUM, LOW) only maps to a meaningful "worst first"
  DB-level ORDER BY on Postgres, and even then only ascending -- and it
  doesn't hold on SQLite (used in tests), where the enum is stored as
  plain text and would sort alphabetically instead. To stay correct and
  portable across dialects, severity-based ranking is done in Python on
  the (already narrowly filtered, typically small) result set rather
  than relied on via ORDER BY.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.operational_analysis.models import (
    FindingType,
    OperationalAnalysis,
    OperationalFinding,
    Severity,
)
from app.modules.tasks.models import Task, TaskStatus

_SEVERITY_RANK = {
    Severity.CRITICAL: 4,
    Severity.HIGH: 3,
    Severity.MEDIUM: 2,
    Severity.LOW: 1,
}

DEFAULT_TOP_RISKS_LIMIT = 5
DEFAULT_RECENT_FINDINGS_LIMIT = 20


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # GET /api/dashboard
    # ------------------------------------------------------------------

    def get_summary(self, top_risks_limit: int = DEFAULT_TOP_RISKS_LIMIT) -> dict:
        latest_analysis = self._get_latest_analysis()

        # Task counts are global (across all analyses), since the
        # approval/task backlog naturally accumulates over time -- they
        # are NOT scoped to just the latest analysis run.
        pending_approvals = self._count_tasks_by_status(TaskStatus.PENDING_APPROVAL)
        active_tasks = self._count_tasks_by_status(TaskStatus.IN_PROGRESS)
        completed_tasks = self._count_tasks_by_status(TaskStatus.COMPLETED)

        if latest_analysis is None:
            # Handle empty database: no analysis has ever run yet.
            return {
                "store_status": "NORMAL",
                "critical_findings": 0,
                "high_findings": 0,
                "pending_approvals": pending_approvals,
                "active_tasks": active_tasks,
                "completed_tasks": completed_tasks,
                "recent_analysis": None,
                "top_operational_risks": [],
            }

        critical_count = self._count_findings_by_severity(latest_analysis.id, Severity.CRITICAL)
        high_count = self._count_findings_by_severity(latest_analysis.id, Severity.HIGH)
        total_findings = self._count_findings(latest_analysis.id)

        if critical_count > 0:
            store_status = "CRITICAL"
        elif total_findings > 0:
            store_status = "ATTENTION"
        else:
            store_status = "NORMAL"

        return {
            "store_status": store_status,
            "critical_findings": critical_count,
            "high_findings": high_count,
            "pending_approvals": pending_approvals,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "recent_analysis": latest_analysis,
            "top_operational_risks": self._get_top_risks(latest_analysis.id, top_risks_limit),
        }

    # ------------------------------------------------------------------
    # GET /api/dashboard/inventory-risks
    # ------------------------------------------------------------------

    def get_inventory_risks(self) -> List[OperationalFinding]:
        latest_analysis = self._get_latest_analysis()
        if latest_analysis is None:
            return []

        findings = (
            self.db.query(OperationalFinding)
            .filter(
                OperationalFinding.analysis_id == latest_analysis.id,
                OperationalFinding.finding_type.in_(
                    [FindingType.STOCKOUT, FindingType.EXPIRY]
                ),
            )
            .all()
        )
        return self._sort_by_severity(findings)

    # ------------------------------------------------------------------
    # GET /api/dashboard/sales-anomalies
    # ------------------------------------------------------------------

    def get_sales_anomalies(self) -> List[OperationalFinding]:
        latest_analysis = self._get_latest_analysis()
        if latest_analysis is None:
            return []

        findings = (
            self.db.query(OperationalFinding)
            .filter(
                OperationalFinding.analysis_id == latest_analysis.id,
                OperationalFinding.finding_type == FindingType.SALES_ANOMALY,
            )
            .all()
        )
        return self._sort_by_severity(findings)

    # ------------------------------------------------------------------
    # GET /api/dashboard/recent-findings
    # ------------------------------------------------------------------

    def get_recent_findings(
        self, limit: int = DEFAULT_RECENT_FINDINGS_LIMIT
    ) -> List[OperationalFinding]:
        # Spans ALL analyses (recent history), unlike the other
        # dashboard endpoints which are scoped to the latest run only.
        return (
            self.db.query(OperationalFinding)
            .order_by(OperationalFinding.created_at.desc())
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_latest_analysis(self) -> Optional[OperationalAnalysis]:
        return (
            self.db.query(OperationalAnalysis)
            .order_by(OperationalAnalysis.created_at.desc())
            .first()
        )

    def _count_findings(self, analysis_id: UUID) -> int:
        return (
            self.db.query(func.count(OperationalFinding.id))
            .filter(OperationalFinding.analysis_id == analysis_id)
            .scalar()
        ) or 0

    def _count_findings_by_severity(self, analysis_id: UUID, severity: Severity) -> int:
        return (
            self.db.query(func.count(OperationalFinding.id))
            .filter(
                OperationalFinding.analysis_id == analysis_id,
                OperationalFinding.severity == severity,
            )
            .scalar()
        ) or 0

    def _count_tasks_by_status(self, status: TaskStatus) -> int:
        return (
            self.db.query(func.count(Task.id)).filter(Task.status == status).scalar()
        ) or 0

    def _get_top_risks(self, analysis_id: UUID, limit: int) -> List[OperationalFinding]:
        findings = (
            self.db.query(OperationalFinding)
            .filter(OperationalFinding.analysis_id == analysis_id)
            .all()
        )
        return self._sort_by_severity(findings)[:limit]

    @staticmethod
    def _sort_by_severity(findings: List[OperationalFinding]) -> List[OperationalFinding]:
        return sorted(
            findings,
            key=lambda f: (_SEVERITY_RANK.get(f.severity, 0), f.confidence or 0),
            reverse=True,
        )
