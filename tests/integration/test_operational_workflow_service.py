"""
Integration tests for OperationalWorkflowService.

Uses a real (temp file) SQLite database and a real SQLAlchemy Session
-- not mocked -- to verify the full workflow: loading data, running the
deterministic engines, persisting analysis/findings/tasks in one
transaction, rolling back on failure, and reading it all back via
get_analysis().
"""

import json
import os
import tempfile
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models_registry  # noqa: F401  (registers every model)
from app.core.database import Base
from app.core.exceptions import AppException, NotFoundException
from app.modules.ai_engine.mock_provider import MockAIProvider
from app.modules.ai_engine.service import AIOperationalAnalysisService
from app.modules.inventory.models import Inventory
from app.modules.operational_analysis.models import OperationalAnalysis
from app.modules.operational_analysis.service import OperationalWorkflowService
from app.modules.products.models import Product
from app.modules.sales.models import Sale
from app.modules.tasks.models import Task, TaskStatus


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


def _seed_critical_stockout_product(db) -> Product:
    """A product with very low stock and steady sales -> CRITICAL stockout."""
    today = date.today()
    product = Product(sku="SKU-TEST-001", name="Test Product", category="Test", minimum_stock=10)
    db.add(product)
    db.flush()

    db.add(Inventory(product_id=product.id, quantity=2, expiry_date=None))

    # 3 recent days + 14 historical days, all at 5/day -> stockout critical,
    # but no sales anomaly (flat trend).
    for days_ago in range(17):
        db.add(
            Sale(
                product_id=product.id,
                quantity=5,
                total_amount=50000,
                sale_date=today - timedelta(days=days_ago),
            )
        )
    db.commit()
    return product


def _fallback_ai_service() -> AIOperationalAnalysisService:
    # Empty responses -> provider fails immediately -> forces the
    # rule-based fallback path, deterministically, every time.
    return AIOperationalAnalysisService(provider=MockAIProvider(responses=[]))


# ---------------------------------------------------------------------------
# Happy path: persistence + PENDING_APPROVAL
# ---------------------------------------------------------------------------

def test_run_analysis_persists_findings_and_creates_pending_approval_tasks(db_session):
    _seed_critical_stockout_product(db_session)

    workflow = OperationalWorkflowService(db=db_session, ai_service=_fallback_ai_service())
    result = workflow.run_analysis()

    assert result["findings_count"] >= 1
    assert result["proposed_tasks_count"] >= 1
    assert result["store_status"] in ("ATTENTION", "CRITICAL")

    analysis = (
        db_session.query(OperationalAnalysis).filter_by(id=result["analysis_id"]).first()
    )
    assert analysis is not None

    tasks = db_session.query(Task).all()
    assert len(tasks) == result["proposed_tasks_count"]
    # Requirement: tasks must ALWAYS be PENDING_APPROVAL, never auto-run.
    assert all(t.status == TaskStatus.PENDING_APPROVAL for t in tasks)


def test_get_analysis_returns_analysis_findings_and_tasks(db_session):
    _seed_critical_stockout_product(db_session)
    workflow = OperationalWorkflowService(db=db_session, ai_service=_fallback_ai_service())

    result = workflow.run_analysis()
    detail = workflow.get_analysis(result["analysis_id"])

    assert detail["analysis"].id == result["analysis_id"]
    assert len(detail["findings"]) == result["findings_count"]
    assert len(detail["proposed_tasks"]) == result["proposed_tasks_count"]


def test_get_analysis_not_found_raises(db_session):
    workflow = OperationalWorkflowService(db=db_session, ai_service=_fallback_ai_service())

    with pytest.raises(NotFoundException):
        workflow.get_analysis(uuid.uuid4())


def test_run_analysis_with_no_products_is_normal_with_no_findings(db_session):
    workflow = OperationalWorkflowService(db=db_session, ai_service=_fallback_ai_service())

    result = workflow.run_analysis()

    assert result["store_status"] == "NORMAL"
    assert result["findings_count"] == 0
    assert result["proposed_tasks_count"] == 0


# ---------------------------------------------------------------------------
# Transaction rollback on save failure
# ---------------------------------------------------------------------------

def test_run_analysis_rolls_back_on_save_failure(db_session, monkeypatch):
    _seed_critical_stockout_product(db_session)
    workflow = OperationalWorkflowService(db=db_session, ai_service=_fallback_ai_service())

    def broken_commit():
        raise RuntimeError("Simulated DB failure during save")

    # Fail at the final commit -- by then analysis/findings/tasks have all
    # been added+flushed within the transaction, so this proves a failure
    # at the very last step still rolls back everything, not just part of it.
    monkeypatch.setattr(db_session, "commit", broken_commit)

    with pytest.raises(AppException):
        workflow.run_analysis()

    # Rollback must mean NOTHING was persisted -- no orphaned analysis row.
    assert db_session.query(OperationalAnalysis).count() == 0


# ---------------------------------------------------------------------------
# Duplicate task avoidance
# ---------------------------------------------------------------------------

def test_duplicate_tasks_for_same_finding_are_deduplicated(db_session):
    product = _seed_critical_stockout_product(db_session)

    valid_ai_response = json.dumps(
        {
            "summary": "Stock critical for SKU-TEST-001.",
            "store_status": "CRITICAL",
            "findings": [
                {
                    "type": "STOCKOUT",
                    "product_id": str(product.id),
                    "severity": "CRITICAL",
                    "title": "Stock critical",
                    "description": "Very low stock.",
                    "recommended_action": "Reorder now",
                    "confidence": 0.9,
                }
            ],
            "tasks": [
                {
                    "title": "Reorder now",
                    "description": "First copy of this task.",
                    "priority": "URGENT",
                    "assigned_role": "INVENTORY_STAFF",
                    "source_finding_index": 0,
                },
                {
                    "title": "Reorder now",  # duplicate: same finding + title
                    "description": "Second, duplicate copy.",
                    "priority": "URGENT",
                    "assigned_role": "INVENTORY_STAFF",
                    "source_finding_index": 0,
                },
            ],
        }
    )
    ai_service = AIOperationalAnalysisService(
        provider=MockAIProvider(responses=[valid_ai_response])
    )
    workflow = OperationalWorkflowService(db=db_session, ai_service=ai_service)

    result = workflow.run_analysis()

    assert result["proposed_tasks_count"] == 1  # duplicate was skipped
    assert db_session.query(Task).count() == 1
