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

from app.core.database import get_db
from app.modules.tasks.models import TaskStatus
from app.modules.tasks.schemas import ApproveTaskRequest, RejectTaskRequest, TaskResponse
from app.modules.tasks.service import TaskService

router = APIRouter()


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(db=db)


@router.get("", response_model=List[TaskResponse])
def list_tasks(
    status: Optional[TaskStatus] = Query(default=None),
    service: TaskService = Depends(get_task_service),
):
    return service.list_tasks(status=status)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: uuid.UUID, service: TaskService = Depends(get_task_service)):
    return service.get_task(task_id)


@router.post("/{task_id}/approve", response_model=TaskResponse)
def approve_task(
    task_id: uuid.UUID,
    payload: ApproveTaskRequest,
    service: TaskService = Depends(get_task_service),
):
    return service.approve_task(task_id, manager_id=payload.manager_id, note=payload.note)


@router.post("/{task_id}/reject", response_model=TaskResponse)
def reject_task(
    task_id: uuid.UUID,
    payload: RejectTaskRequest,
    service: TaskService = Depends(get_task_service),
):
    return service.reject_task(task_id, manager_id=payload.manager_id, note=payload.note)


@router.post("/{task_id}/start", response_model=TaskResponse)
def start_task(task_id: uuid.UUID, service: TaskService = Depends(get_task_service)):
    return service.start_task(task_id)


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: uuid.UUID, service: TaskService = Depends(get_task_service)):
    return service.complete_task(task_id)
