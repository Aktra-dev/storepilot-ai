"""
Operational Analysis — Pydantic schemas (API request/response DTOs).

store_status is intentionally NOT a database column — it's fully
derivable from the persisted findings' severities (see service.py), so
there's nothing to keep in sync or get stale.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.modules.operational_analysis.models import AnalysisStatus, FindingType, Severity
from app.modules.tasks.models import TaskPriority, TaskStatus


class AnalyzeResponse(BaseModel):
    analysis_id: UUID
    store_status: str
    summary: str
    findings_count: int
    proposed_tasks_count: int


class FindingDetail(BaseModel):
    id: UUID
    finding_type: FindingType
    product_id: Optional[UUID] = None
    severity: Severity
    title: str
    description: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskDetail(BaseModel):
    id: UUID
    finding_id: UUID
    title: str
    description: Optional[str] = None
    priority: TaskPriority
    assigned_role: Optional[str] = None
    status: TaskStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisDetail(BaseModel):
    id: UUID
    status: AnalysisStatus
    summary: Optional[str] = None
    ai_provider: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisDetailResponse(BaseModel):
    analysis: AnalysisDetail
    findings: List[FindingDetail]
    proposed_tasks: List[TaskDetail]


class AnalysisStatusResponse(BaseModel):
    """Summary of the most recent operational analysis run.

    Used by GET /api/operations/status so the frontend can show a
    lightweight "last analysis" indicator without fetching full
    findings/tasks detail.
    """

    last_analysis: Optional[datetime] = None
    total_findings: int = 0
    status: Optional[AnalysisStatus] = None
