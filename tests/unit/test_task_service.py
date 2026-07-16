"""
Unit tests for TaskService -- task state transitions and approval.

Uses a real (temp file) SQLite session so approve/reject can be verified
to actually persist the Approval record (manager + note), not just
change an in-memory status.
"""

import os
import tempfile
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models_registry  # noqa: F401  (registers every model)
from app.core.database import Base
from app.core.exceptions import NotFoundException
from app.modules.approvals.models import Approval, ApprovalStatus
from app.modules.auth.models import User, UserRole
from app.modules.operational_analysis.models import (
    AnalysisStatus,
    FindingType,
    OperationalAnalysis,
    OperationalFinding,
    Severity,
)
from app.modules.tasks.models import Task, TaskPriority, TaskStatus
from app.modules.tasks.service import InvalidTaskTransitionException, TaskService


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


def _make_task(db, status: TaskStatus = TaskStatus.PENDING_APPROVAL) -> Task:
    analysis = OperationalAnalysis(
        status=AnalysisStatus.COMPLETED, summary="test", ai_provider="fallback"
    )
    db.add(analysis)
    db.flush()

    finding = OperationalFinding(
        analysis_id=analysis.id,
        finding_type=FindingType.STOCKOUT,
        severity=Severity.HIGH,
        title="Test finding",
        description="d",
        confidence=0.8,
    )
    db.add(finding)
    db.flush()

    task = Task(
        finding_id=finding.id,
        title="Test task",
        description="d",
        priority=TaskPriority.HIGH,
        assigned_role="inventory_staff",
        status=status,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _make_manager(db) -> User:
    manager = User(
        name="Manager",
        email=f"manager-{uuid.uuid4()}@test.com",
        password_hash="x",
        role=UserRole.MANAGER,
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)
    return manager


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------

def test_approve_pending_task_succeeds(db_session):
    task = _make_task(db_session)
    manager = _make_manager(db_session)
    service = TaskService(db=db_session)

    updated = service.approve_task(task.id, manager_id=manager.id, note="Looks good")

    assert updated.status == TaskStatus.APPROVED

    approval = db_session.query(Approval).filter_by(task_id=task.id).first()
    assert approval is not None
    assert approval.status == ApprovalStatus.APPROVED
    assert approval.manager_id == manager.id
    assert approval.note == "Looks good"


def test_approve_non_pending_task_fails(db_session):
    task = _make_task(db_session, status=TaskStatus.APPROVED)
    manager = _make_manager(db_session)
    service = TaskService(db=db_session)

    with pytest.raises(InvalidTaskTransitionException):
        service.approve_task(task.id, manager_id=manager.id)


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------

def test_reject_pending_task_succeeds(db_session):
    task = _make_task(db_session)
    manager = _make_manager(db_session)
    service = TaskService(db=db_session)

    updated = service.reject_task(task.id, manager_id=manager.id, note="Not needed")

    assert updated.status == TaskStatus.REJECTED

    approval = db_session.query(Approval).filter_by(task_id=task.id).first()
    assert approval.status == ApprovalStatus.REJECTED
    assert approval.note == "Not needed"


def test_reject_already_completed_task_fails(db_session):
    task = _make_task(db_session, status=TaskStatus.COMPLETED)
    manager = _make_manager(db_session)
    service = TaskService(db=db_session)

    with pytest.raises(InvalidTaskTransitionException):
        service.reject_task(task.id, manager_id=manager.id)


# ---------------------------------------------------------------------------
# Start -- requirement #2: REJECTED task cannot be started
# ---------------------------------------------------------------------------

def test_start_approved_task_succeeds(db_session):
    task = _make_task(db_session, status=TaskStatus.APPROVED)
    service = TaskService(db=db_session)

    updated = service.start_task(task.id)

    assert updated.status == TaskStatus.IN_PROGRESS


def test_start_rejected_task_cannot_be_started(db_session):
    task = _make_task(db_session, status=TaskStatus.REJECTED)
    service = TaskService(db=db_session)

    with pytest.raises(InvalidTaskTransitionException):
        service.start_task(task.id)


def test_start_pending_task_fails_until_approved(db_session):
    task = _make_task(db_session, status=TaskStatus.PENDING_APPROVAL)
    service = TaskService(db=db_session)

    with pytest.raises(InvalidTaskTransitionException):
        service.start_task(task.id)


# ---------------------------------------------------------------------------
# Complete -- requirement #3: COMPLETED task cannot be changed again
# ---------------------------------------------------------------------------

def test_complete_in_progress_task_succeeds(db_session):
    task = _make_task(db_session, status=TaskStatus.IN_PROGRESS)
    service = TaskService(db=db_session)

    updated = service.complete_task(task.id)

    assert updated.status == TaskStatus.COMPLETED
    assert updated.completed_at is not None


def test_complete_already_completed_task_fails(db_session):
    task = _make_task(db_session, status=TaskStatus.COMPLETED)
    service = TaskService(db=db_session)

    with pytest.raises(InvalidTaskTransitionException):
        service.complete_task(task.id)


def test_complete_pending_task_fails(db_session):
    task = _make_task(db_session, status=TaskStatus.PENDING_APPROVAL)
    service = TaskService(db=db_session)

    with pytest.raises(InvalidTaskTransitionException):
        service.complete_task(task.id)


# ---------------------------------------------------------------------------
# List / Get
# ---------------------------------------------------------------------------

def test_get_nonexistent_task_raises_not_found(db_session):
    service = TaskService(db=db_session)

    with pytest.raises(NotFoundException):
        service.get_task(uuid.uuid4())


def test_list_tasks_filters_by_status(db_session):
    _make_task(db_session, status=TaskStatus.PENDING_APPROVAL)
    _make_task(db_session, status=TaskStatus.APPROVED)
    service = TaskService(db=db_session)

    pending = service.list_tasks(status=TaskStatus.PENDING_APPROVAL)
    assert len(pending) == 1
    assert pending[0].status == TaskStatus.PENDING_APPROVAL

    all_tasks = service.list_tasks()
    assert len(all_tasks) == 2
