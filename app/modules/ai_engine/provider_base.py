"""
AI Provider abstraction.

Every AI provider (a real LLM API client, or a mock used in tests) must
implement this interface. Business logic (AIOperationalAnalysisService)
depends only on this abstract interface, never on a concrete provider —
so the underlying model/API can be swapped without touching orchestration
logic, retry logic, or validation.
"""

from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Given a prompt, return the raw text response from the model.
        Implementations must NOT log or expose any API key/credential
        used to make the call.
        """
        raise NotImplementedError
