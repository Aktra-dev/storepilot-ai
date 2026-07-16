"""
Approvals — Pydantic schemas.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.modules.approvals.models import ApprovalStatus


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    manager_id: uuid.UUID
    status: ApprovalStatus
    note: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalCreateRequest(BaseModel):
    """Request to create an approval (manager approves/rejects)."""
    manager_id: uuid.UUID
    status: ApprovalStatus
    note: Optional[str] = None