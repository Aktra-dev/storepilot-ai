"""
Tasks — business logic.

TaskService owns every task state transition and is the ONLY place that
is allowed to change Task.status. Every transition is checked against a
fixed state machine before being applied -- invalid transitions raise
InvalidTaskTransitionException rather than silently succeeding or
corrupting state.

State machine:
    PENDING_APPROVAL -> APPROVED   (manager approves)
    PENDING_APPROVAL -> REJECTED   (manager rejects)
    APPROVED         -> IN_PROGRESS
    IN_PROGRESS      -> COMPLETED
    REJECTED         -> (terminal -- can never be started)
    COMPLETED        -> (terminal -- can never be changed)
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.modules.approvals.models import Approval, ApprovalStatus
from app.modules.tasks.models import Task, TaskStatus


class InvalidTaskTransitionException(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=409)


class TaskService:
    # Maps current status -> set of statuses it's allowed to move to.
    _ALLOWED_TRANSITIONS = {
        TaskStatus.PENDING_APPROVAL: {TaskStatus.APPROVED, TaskStatus.REJECTED},
        TaskStatus.APPROVED: {TaskStatus.IN_PROGRESS},
        TaskStatus.IN_PROGRESS: {TaskStatus.COMPLETED},
        TaskStatus.REJECTED: set(),  # terminal: cannot be started
        TaskStatus.COMPLETED: set(),  # terminal: cannot be changed
        TaskStatus.CANCELLED: set(),
    }

    def __init__(self, db: Session):
        self.db = db

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        query = self.db.query(Task)
        if status is not None:
            query = query.filter(Task.status == status)
        return query.order_by(Task.created_at.desc()).all()

    def get_task(self, task_id: uuid.UUID) -> Task:
        task = self.db.query(Task).filter_by(id=task_id).first()
        if not task:
            raise NotFoundException(f"Task {task_id} not found")
        return task

    def approve_task(
        self,
        task_id: uuid.UUID,
        manager_id: uuid.UUID,
        note: Optional[str] = None,
    ) -> Task:
        task = self.get_task(task_id)
        self._ensure_transition_allowed(task, TaskStatus.APPROVED)

        task.status = TaskStatus.APPROVED
        self.db.add(
            Approval(
                task_id=task.id,
                manager_id=manager_id,
                status=ApprovalStatus.APPROVED,
                note=note,
            )
        )
        self.db.commit()
        self.db.refresh(task)
        return task

    def reject_task(
        self,
        task_id: uuid.UUID,
        manager_id: uuid.UUID,
        note: Optional[str] = None,
    ) -> Task:
        task = self.get_task(task_id)
        self._ensure_transition_allowed(task, TaskStatus.REJECTED)

        task.status = TaskStatus.REJECTED
        self.db.add(
            Approval(
                task_id=task.id,
                manager_id=manager_id,
                status=ApprovalStatus.REJECTED,
                note=note,
            )
        )
        self.db.commit()
        self.db.refresh(task)
        return task

    def start_task(self, task_id: uuid.UUID) -> Task:
        task = self.get_task(task_id)
        self._ensure_transition_allowed(task, TaskStatus.IN_PROGRESS)

        task.status = TaskStatus.IN_PROGRESS
        self.db.commit()
        self.db.refresh(task)
        return task

    def complete_task(self, task_id: uuid.UUID) -> Task:
        task = self.get_task(task_id)
        self._ensure_transition_allowed(task, TaskStatus.COMPLETED)

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

    def _ensure_transition_allowed(self, task: Task, target_status: TaskStatus) -> None:
        allowed = self._ALLOWED_TRANSITIONS.get(task.status, set())
        if target_status not in allowed:
            raise InvalidTaskTransitionException(
                f"Cannot move task from '{task.status.value}' to "
                f"'{target_status.value}'"
            )
