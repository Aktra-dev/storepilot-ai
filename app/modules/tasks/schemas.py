"""
Tasks — Pydantic schemas.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.modules.tasks.models import TaskPriority, TaskStatus


class TaskResponse(BaseModel):
    id: UUID
    finding_id: UUID
    title: str
    description: Optional[str] = None
    priority: TaskPriority
    assigned_role: Optional[str] = None
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApproveTaskRequest(BaseModel):
    manager_id: UUID
    note: Optional[str] = None


class RejectTaskRequest(BaseModel):
    manager_id: UUID
    note: Optional[str] = None
