"""
Real AI provider — Anthropic Claude API.

Implements the AIProvider interface (see provider_base.py) so it can be
dropped into AIOperationalAnalysisService without touching orchestration,
retry, or fallback logic.

Requires:
    pip install anthropic
    AI_PROVIDER=anthropic
    AI_API_KEY=sk-ant-...
    AI_MODEL=claude-sonnet-4-5-20250929   (optional, has a default below)

Security: the API key is only ever read from settings (env var) and is
never logged. Only exception *types* are logged upstream in service.py.
"""

from anthropic import Anthropic

from app.core.config import settings
from app.modules.ai_engine.provider_base import AIProvider

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 2048


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._client = Anthropic(api_key=api_key or settings.AI_API_KEY)
        self._model = model or getattr(settings, "AI_MODEL", None) or DEFAULT_MODEL

    def generate(self, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        # response.content is a list of content blocks; we only ever send
        # plain text prompts and expect a plain text (JSON-in-text) reply.
        return "".join(
            block.text for block in response.content if block.type == "text"
        )
