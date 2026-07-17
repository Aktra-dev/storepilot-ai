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

from app.core.auth import get_current_manager
from app.core.config import settings
from app.core.database import get_db
from app.modules.ai_engine.mock_provider import MockAIProvider
from app.modules.ai_engine.provider_base import AIProvider
from app.modules.ai_engine.service import AIOperationalAnalysisService
from app.modules.auth.models import User
from app.modules.operational_analysis.schemas import AnalysisDetailResponse, AnalyzeResponse
from app.modules.operational_analysis.service import OperationalWorkflowService

router = APIRouter()


def get_ai_provider() -> AIProvider:
    """
    AI_PROVIDER=anthropic + AI_API_KEY set -> real Claude API calls.
    Anything else (default: "fallback") -> MockAIProvider(responses=[]),
    which always raises, so AIOperationalAnalysisService falls straight
    through to RuleBasedFallbackService. That's expected, documented
    behavior for environments without an AI key configured yet.
    """
    if settings.AI_PROVIDER == "anthropic" and settings.AI_API_KEY:
        from app.modules.ai_engine.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
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
    current_user: User = Depends(get_current_manager),
    workflow: OperationalWorkflowService = Depends(get_workflow_service),
):
    """Run the AI autonomous analysis. Manager only."""
    return workflow.run_analysis()


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_manager),
    workflow: OperationalWorkflowService = Depends(get_workflow_service),
):
    """View a past analysis result. Manager only (Operational Analysis / AI Findings menu)."""
    return workflow.get_analysis(analysis_id)
