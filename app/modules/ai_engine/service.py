"""
AI Operational Analysis — orchestration service.

Takes structured output from InventoryRiskService and SalesAnomalyService
(never raw data) and asks the configured AIProvider to interpret it.
Every response is parsed as JSON and validated against
AIOperationalAnalysisResult before being trusted. On failure, retries up
to MAX_RETRIES times; if the AI still fails, falls back to
RuleBasedFallbackService so a result is always returned.

Security note: this service never logs the raw prompt/response content
or any exception message that could contain a leaked API key — only the
exception *type* is logged, and nothing is ever raised back to the
caller as a raw traceback.
"""

import logging
from typing import List, Optional, Tuple

from pydantic import ValidationError

from app.modules.ai_engine.exceptions import AIResponseError
from app.modules.ai_engine.fallback_service import RuleBasedFallbackService
from app.modules.ai_engine.json_parser import parse_ai_json
from app.modules.ai_engine.prompts import build_operational_analysis_prompt
from app.modules.ai_engine.provider_base import AIProvider
from app.modules.ai_engine.schemas import AIOperationalAnalysisResult, ProductSalesAnomaly
from app.modules.inventory.schemas import InventoryRiskResult

logger = logging.getLogger("storepilot.ai_engine")


class AIOperationalAnalysisService:
    MAX_RETRIES = 2  # total attempts = MAX_RETRIES + 1 (1 initial + 2 retries)

    def __init__(
        self,
        provider: AIProvider,
        fallback_service: Optional[RuleBasedFallbackService] = None,
    ):
        self._provider = provider
        self._fallback_service = fallback_service or RuleBasedFallbackService()

    def analyze(
        self,
        inventory_risks: List[InventoryRiskResult],
        sales_anomalies: List[ProductSalesAnomaly],
    ) -> Tuple[AIOperationalAnalysisResult, str]:
        """
        Returns (result, provider_used) where provider_used is "ai" if the
        AI provider succeeded, or "fallback" if rule-based fallback was used.
        """
        prompt = build_operational_analysis_prompt(inventory_risks, sales_anomalies)
        total_attempts = self.MAX_RETRIES + 1

        for attempt in range(1, total_attempts + 1):
            try:
                raw_response = self._provider.generate(prompt)
                parsed = parse_ai_json(raw_response)
                result = AIOperationalAnalysisResult.model_validate(parsed)
                return result, "ai"
            except (AIResponseError, ValidationError) as exc:
                logger.warning(
                    "AI response attempt %d/%d rejected: %s",
                    attempt, total_attempts, type(exc).__name__,
                )
            except Exception as exc:
                # Any unexpected provider-level failure (timeout, connection
                # error, etc.) is treated the same way. Never re-raise the
                # raw exception to the caller.
                logger.warning(
                    "AI provider attempt %d/%d raised an unexpected error: %s",
                    attempt, total_attempts, type(exc).__name__,
                )

        logger.warning(
            "AI provider failed after %d attempt(s), using rule-based fallback.",
            total_attempts,
        )
        result = self._fallback_service.generate(inventory_risks, sales_anomalies)
        return result, "fallback"
