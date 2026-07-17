"""
AI Engine — API routes.

Currently exposes a single manager-only endpoint used to verify the
configured AI provider is reachable (correct AI_API_KEY, model name,
etc.) without running a full operational analysis or writing anything
to the database. The actual analysis workflow lives in
operational_analysis/operations_router.py (POST /api/operations/analyze),
which is the one that persists results — this endpoint is purely a
connectivity check.
"""

from fastapi import APIRouter, Depends

from app.core.auth import get_current_manager
from app.core.config import settings
from app.modules.auth.models import User

router = APIRouter()


@router.get("/status", summary="Check AI provider connectivity")
def check_ai_status(current_user: User = Depends(get_current_manager)):
    """
    Verifies the configured AI provider can actually be reached.

    - AI_PROVIDER=fallback -> always reports fallback mode, no external
      call is made (there's nothing to test).
    - AI_PROVIDER=anthropic -> sends a minimal prompt to confirm
      AI_API_KEY / AI_MODEL are valid and the API is reachable.

    Never exposes the raw exception message (could leak request
    internals) or the API key itself — only a safe, generic status.
    """
    if settings.AI_PROVIDER != "anthropic":
        return {
            "provider": settings.AI_PROVIDER,
            "status": "fallback_mode",
            "message": "AI_PROVIDER is set to 'fallback' — rule-based analysis only, no AI calls are made.",
        }

    if not settings.AI_API_KEY:
        return {
            "provider": "anthropic",
            "status": "misconfigured",
            "message": "AI_PROVIDER is 'anthropic' but AI_API_KEY is empty.",
        }

    from app.modules.ai_engine.anthropic_provider import AnthropicProvider

    try:
        provider = AnthropicProvider()
        provider.generate("Respond with exactly one word: OK")
        return {
            "provider": "anthropic",
            "model": settings.AI_MODEL,
            "status": "connected",
            "message": "Successfully reached the Anthropic API.",
        }
    except Exception:
        # Only the exception type may ever be surfaced — never the raw
        # message, which could contain request/response internals.
        return {
            "provider": "anthropic",
            "status": "error",
            "message": "Could not reach the Anthropic API. Check AI_API_KEY and AI_MODEL.",
        }