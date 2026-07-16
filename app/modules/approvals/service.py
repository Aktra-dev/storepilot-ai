"""
Approvals — business logic.
"""

import uuid
from typing import Optional, List

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.approvals.models import Approval, ApprovalStatus
from app.modules.approvals.schemas import ApprovalCreateRequest
from app.modules.tasks.models import Task, TaskStatus


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: ApprovalCreateRequest) -> Approval:
        """Create an approval record (approve or reject a task)."""
        task = self.db.query(Task).filter(Task.id == data.task_id).first()
        if not task:
            raise NotFoundException(f"Task {data.task_id} not found")

        # Validate state transition based on approval status
        if data.status == ApprovalStatus.APPROVED:
            if task.status != TaskStatus.PENDING_APPROVAL:
                raise ValidationException(
                    f"Cannot approve task in status '{task.status.value}'. "
                    "Task must be PENDING_APPROVAL."
                )
            task.status = TaskStatus.APPROVED
        elif data.status == ApprovalStatus.REJECTED:
            if task.status != TaskStatus.PENDING_APPROVAL:
                raise ValidationException(
                    f"Cannot reject task in status '{task.status.value}'. "
                    "Task must be PENDING_APPROVAL."
                )
            task.status = TaskStatus.REJECTED

        approval = Approval(
            id=uuid.uuid4(),
            task_id=data.task_id,
            manager_id=data.manager_id,
            status=data.status,
            note=data.note,
        )
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def get(self, approval_id: uuid.UUID) -> Approval:
        approval = self.db.query(Approval).filter(Approval.id == approval_id).first()
        if not approval:
            raise NotFoundException(f"Approval {approval_id} not found")
        return approval

    def list_by_task(self, task_id: uuid.UUID) -> List[Approval]:
        return (
            self.db.query(Approval)
            .filter(Approval.task_id == task_id)
            .order_by(Approval.created_at.asc())
            .all()
        )

    def list_by_manager(self, manager_id: uuid.UUID) -> List[Approval]:
        return (
            self.db.query(Approval)
            .filter(Approval.manager_id == manager_id)
            .order_by(Approval.created_at.desc())
            .all()
        )