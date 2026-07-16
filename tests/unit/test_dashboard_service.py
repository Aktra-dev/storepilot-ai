"""
Unit tests for DashboardService.

Uses a real (temp file) SQLite session. Covers: empty database handling,
correct counts/store_status with data, severity-based sorting, and that
inventory-risks / sales-anomalies / recent-findings each scope their
results correctly.
"""

import os
import tempfile
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models_registry  # noqa: F401  (registers every model)
from app.core.database import Base
from app.modules.dashboard.service import DashboardService
from app.modules.operational_analysis.models import (
    AnalysisStatus,
    FindingType,
    OperationalAnalysis,
    OperationalFinding,
    Severity,
)
from app.modules.tasks.models import Task, TaskPriority, TaskStatus


@pytest.fixture()
def db_session():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    yield session

    session.close()
    engine.dispose()
    os.remove(path)


def _make_analysis(db, created_at=None) -> OperationalAnalysis:
    analysis = OperationalAnalysis(
        status=AnalysisStatus.COMPLETED, summary="test run", ai_provider="fallback"
    )
    db.add(analysis)
    db.flush()
    if created_at is not None:
        analysis.created_at = created_at
        db.flush()
    return analysis


def _make_finding(
    db,
    analysis_id,
    finding_type=FindingType.STOCKOUT,
    severity=Severity.HIGH,
    confidence=0.8,
) -> OperationalFinding:
    finding = OperationalFinding(
        analysis_id=analysis_id,
        finding_type=finding_type,
        severity=severity,
        title=f"{finding_type.value} finding",
        description="d",
        confidence=confidence,
    )
    db.add(finding)
    db.flush()
    return finding


def _make_task(db, finding_id, status=TaskStatus.PENDING_APPROVAL) -> Task:
    task = Task(
        finding_id=finding_id,
        title="Test task",
        description="d",
        priority=TaskPriority.HIGH,
        assigned_role="inventory_staff",
        status=status,
    )
    db.add(task)
    db.flush()
    return task


# ---------------------------------------------------------------------------
# Empty database handling
# ---------------------------------------------------------------------------

def test_summary_on_empty_database(db_session):
    service = DashboardService(db=db_session)

    summary = service.get_summary()

    assert summary["store_status"] == "NORMAL"
    assert summary["critical_findings"] == 0
    assert summary["high_findings"] == 0
    assert summary["pending_approvals"] == 0
    assert summary["active_tasks"] == 0
    assert summary["completed_tasks"] == 0
    assert summary["recent_analysis"] is None
    assert summary["top_operational_risks"] == []


def test_inventory_risks_on_empty_database(db_session):
    assert DashboardService(db=db_session).get_inventory_risks() == []


def test_sales_anomalies_on_empty_database(db_session):
    assert DashboardService(db=db_session).get_sales_anomalies() == []


def test_recent_findings_on_empty_database(db_session):
    assert DashboardService(db=db_session).get_recent_findings() == []


# ---------------------------------------------------------------------------
# Summary with data
# ---------------------------------------------------------------------------

def test_summary_reflects_critical_status_and_counts(db_session):
    analysis = _make_analysis(db_session)
    _make_finding(db_session, analysis.id, FindingType.STOCKOUT, Severity.CRITICAL)
    _make_finding(db_session, analysis.id, FindingType.EXPIRY, Severity.HIGH)
    finding = _make_finding(db_session, analysis.id, FindingType.SALES_ANOMALY, Severity.MEDIUM)

    _make_task(db_session, finding.id, TaskStatus.PENDING_APPROVAL)
    _make_task(db_session, finding.id, TaskStatus.IN_PROGRESS)
    _make_task(db_session, finding.id, TaskStatus.COMPLETED)
    _make_task(db_session, finding.id, TaskStatus.COMPLETED)
    db_session.commit()

    service = DashboardService(db=db_session)
    summary = service.get_summary()

    assert summary["store_status"] == "CRITICAL"
    assert summary["critical_findings"] == 1
    assert summary["high_findings"] == 1
    assert summary["pending_approvals"] == 1
    assert summary["active_tasks"] == 1
    assert summary["completed_tasks"] == 2
    assert summary["recent_analysis"].id == analysis.id
    # Top risks sorted worst-first: CRITICAL, then HIGH, then MEDIUM
    severities = [f.severity for f in summary["top_operational_risks"]]
    assert severities == [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM]


def test_summary_is_attention_when_findings_exist_but_none_critical(db_session):
    analysis = _make_analysis(db_session)
    _make_finding(db_session, analysis.id, FindingType.EXPIRY, Severity.MEDIUM)
    db_session.commit()

    summary = DashboardService(db=db_session).get_summary()

    assert summary["store_status"] == "ATTENTION"
    assert summary["critical_findings"] == 0


def test_summary_uses_latest_analysis_only(db_session):
    old_analysis = _make_analysis(db_session, created_at=datetime.now() - timedelta(days=1))
    _make_finding(db_session, old_analysis.id, FindingType.STOCKOUT, Severity.CRITICAL)

    new_analysis = _make_analysis(db_session)  # created "now" -> latest
    _make_finding(db_session, new_analysis.id, FindingType.EXPIRY, Severity.MEDIUM)
    db_session.commit()

    summary = DashboardService(db=db_session).get_summary()

    # Only the newest analysis's findings should count -- 0 critical
    # (the old CRITICAL finding must NOT leak into this summary).
    assert summary["critical_findings"] == 0
    assert summary["store_status"] == "ATTENTION"
    assert summary["recent_analysis"].id == new_analysis.id


# ---------------------------------------------------------------------------
# Scoped endpoints
# ---------------------------------------------------------------------------

def test_inventory_risks_only_returns_stockout_and_expiry(db_session):
    analysis = _make_analysis(db_session)
    _make_finding(db_session, analysis.id, FindingType.STOCKOUT, Severity.CRITICAL)
    _make_finding(db_session, analysis.id, FindingType.EXPIRY, Severity.HIGH)
    _make_finding(db_session, analysis.id, FindingType.SALES_ANOMALY, Severity.HIGH)
    db_session.commit()

    results = DashboardService(db=db_session).get_inventory_risks()

    assert len(results) == 2
    assert all(f.finding_type in (FindingType.STOCKOUT, FindingType.EXPIRY) for f in results)
    assert results[0].severity == Severity.CRITICAL  # worst first


def test_sales_anomalies_only_returns_sales_anomaly_type(db_session):
    analysis = _make_analysis(db_session)
    _make_finding(db_session, analysis.id, FindingType.STOCKOUT, Severity.CRITICAL)
    _make_finding(db_session, analysis.id, FindingType.SALES_ANOMALY, Severity.HIGH)
    db_session.commit()

    results = DashboardService(db=db_session).get_sales_anomalies()

    assert len(results) == 1
    assert results[0].finding_type == FindingType.SALES_ANOMALY


def test_recent_findings_spans_multiple_analyses_and_respects_limit(db_session):
    analysis1 = _make_analysis(db_session, created_at=datetime.now() - timedelta(days=1))
    _make_finding(db_session, analysis1.id, FindingType.STOCKOUT, Severity.HIGH)

    analysis2 = _make_analysis(db_session)
    _make_finding(db_session, analysis2.id, FindingType.EXPIRY, Severity.MEDIUM)
    _make_finding(db_session, analysis2.id, FindingType.SALES_ANOMALY, Severity.LOW)
    db_session.commit()

    results = DashboardService(db=db_session).get_recent_findings(limit=2)

    assert len(results) == 2  # respects limit
    # Most recent first
    assert results[0].created_at >= results[1].created_at
