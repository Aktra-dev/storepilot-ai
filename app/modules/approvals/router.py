"""
Human/Manager Approval — API routes.

Mounted under /api/v1/approvals via app/api/v1/router.py.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_manager
from app.core.database import get_db
from app.modules.approvals.models import Approval
from app.modules.approvals.schemas import ApprovalCreateRequest, ApprovalResponse
from app.modules.approvals.service import ApprovalService
from app.modules.auth.models import User

router = APIRouter()

def get_approval_service(db: Session = Depends(get_db)) -> ApprovalService:
    return ApprovalService(db=db)

@router.post(
    "",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create approval (approve/reject task)",
)
def create_approval(
    payload: ApprovalCreateRequest,
    current_user: User = Depends(get_current_manager),
    service: ApprovalService = Depends(get_approval_service),
):
    """
    Manager approves or rejects a task.

    - **status**: "approved" or "rejected"
    - **note**: optional comment
    - Requires manager role.
    """
    return service.create(payload)

@router.get(
    "/task/{task_id}",
    response_model=List[ApprovalResponse],
    summary="Get all approvals for a task",
)
def get_task_approvals(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_manager),
    service: ApprovalService = Depends(get_approval_service),
):
    """Return approval history for a task. Manager only."""
    return service.list_by_task(task_id)

@router.get(
    "/my-approvals",
    response_model=List[ApprovalResponse],
    summary="Get my approvals (manager)",
)
def get_my_approvals(
    current_user: User = Depends(get_current_manager),
    service: ApprovalService = Depends(get_approval_service),
):
    """Return all approvals made by current manager."""
    return service.list_by_manager(current_user.id)

@router.get(
    "/{approval_id}",
    response_model=ApprovalResponse,
    summary="Get approval by ID",
)
def get_approval(
    approval_id: uuid.UUID,
    current_user: User = Depends(get_current_manager),
    service: ApprovalService = Depends(get_approval_service),
):
    """Get single approval record. Manager only."""
    return service.get(approval_id)