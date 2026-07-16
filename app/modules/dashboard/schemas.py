"""
Dashboard — Pydantic schemas.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.modules.operational_analysis.models import AnalysisStatus, FindingType, Severity


class RecentAnalysisSummary(BaseModel):
    id: UUID
    status: AnalysisStatus
    summary: Optional[str] = None
    ai_provider: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingSummary(BaseModel):
    id: UUID
    finding_type: FindingType
    product_id: Optional[UUID] = None
    severity: Severity
    title: str
    description: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardSummary(BaseModel):
    store_status: str
    critical_findings: int
    high_findings: int
    pending_approvals: int
    active_tasks: int
    completed_tasks: int
    recent_analysis: Optional[RecentAnalysisSummary] = None
    top_operational_risks: List[FindingSummary]
