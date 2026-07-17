"""
Task Management & Human Approval -- API routes.

Mounted directly at /api/tasks (not under the versioned /api/v1 prefix)
to match the exact paths in the STEP 8 spec. All business logic lives
in TaskService -- these routes only wire up dependencies and call it.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user, get_current_manager
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.tasks.models import TaskStatus
from app.modules.tasks.schemas import ApproveTaskRequest, RejectTaskRequest, TaskResponse
from app.modules.tasks.service import TaskService

router = APIRouter()


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(db=db)


@router.get("", response_model=List[TaskResponse])
def list_tasks(
    status: Optional[TaskStatus] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
):
    return service.list_tasks(status=status)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
):
    return service.get_task(task_id)


@router.post("/{task_id}/approve", response_model=TaskResponse)
def approve_task(
    task_id: uuid.UUID,
    payload: ApproveTaskRequest,
    current_user: User = Depends(get_current_manager),
    service: TaskService = Depends(get_task_service),
):
    """Approve a task. Manager only — manager identity comes from the JWT,
    never from the request body."""
    return service.approve_task(task_id, manager_id=current_user.id, note=payload.note)


@router.post("/{task_id}/reject", response_model=TaskResponse)
def reject_task(
    task_id: uuid.UUID,
    payload: RejectTaskRequest,
    current_user: User = Depends(get_current_manager),
    service: TaskService = Depends(get_task_service),
):
    """Reject a task. Manager only — manager identity comes from the JWT,
    never from the request body."""
    return service.reject_task(task_id, manager_id=current_user.id, note=payload.note)


@router.post("/{task_id}/start", response_model=TaskResponse)
def start_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
):
    """Staff marks a task as started (real-time execution on the ground)."""
    return service.start_task(task_id)


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
):
    """Staff marks a task as completed (real-time execution on the ground)."""
    return service.complete_task(task_id)
