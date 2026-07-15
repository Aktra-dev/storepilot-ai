"""
Operations workflow API routes.

Mounted directly at /api/operations (not under the versioned /api/v1
prefix) to match the exact paths required by the workflow spec:
    POST /api/operations/analyze
    GET  /api/operations/{analysis_id}

Business logic lives entirely in OperationalWorkflowService -- these
routes only wire up dependencies and call it.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.ai_engine.mock_provider import MockAIProvider
from app.modules.ai_engine.provider_base import AIProvider
from app.modules.ai_engine.service import AIOperationalAnalysisService
from app.modules.operational_analysis.schemas import AnalysisDetailResponse, AnalyzeResponse
from app.modules.operational_analysis.service import OperationalWorkflowService

router = APIRouter()


def get_ai_provider() -> AIProvider:
    # NOTE: no real, API-calling AI provider exists yet (see Step 6 --
    # ai_engine intentionally ships with only the abstraction + a mock).
    # Until a real provider is wired in here, every call falls straight
    # through to RuleBasedFallbackService inside AIOperationalAnalysisService
    # -- this is expected, documented behavior, not a bug.
    return MockAIProvider(responses=[])


def get_ai_service(
    provider: AIProvider = Depends(get_ai_provider),
) -> AIOperationalAnalysisService:
    return AIOperationalAnalysisService(provider=provider)


def get_workflow_service(
    db: Session = Depends(get_db),
    ai_service: AIOperationalAnalysisService = Depends(get_ai_service),
) -> OperationalWorkflowService:
    return OperationalWorkflowService(db=db, ai_service=ai_service)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_store(
    workflow: OperationalWorkflowService = Depends(get_workflow_service),
):
    return workflow.run_analysis()


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis(
    analysis_id: uuid.UUID,
    workflow: OperationalWorkflowService = Depends(get_workflow_service),
):
    return workflow.get_analysis(analysis_id)
