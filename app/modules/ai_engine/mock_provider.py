"""
Mock AI provider — testing only.

Returns a queue of pre-configured canned responses, one per call. Lets
tests simulate any scenario deterministically: a valid response, invalid
JSON, a response missing a required field, "fails once then succeeds"
(retry), or "fails every time" (fallback).
"""

from typing import List

from app.modules.ai_engine.provider_base import AIProvider


class MockAIProvider(AIProvider):
    def __init__(self, responses: List[str]):
        self._responses = list(responses)
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        self.call_count += 1
        if not self._responses:
            raise RuntimeError("MockAIProvider: no more canned responses configured")
        return self._responses.pop(0)
