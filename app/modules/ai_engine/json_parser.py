"""
JSON parser for raw AI responses.

Every AI response must go through this before touching business logic.
Tolerates the common real-world case where a model wraps its JSON in a
markdown code fence (```json ... ```) despite being told not to.
"""

import json
import re

from app.modules.ai_engine.exceptions import AIResponseParseError

_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def parse_ai_json(raw_text: str) -> dict:
    if not raw_text or not raw_text.strip():
        raise AIResponseParseError("AI response is empty")

    text = raw_text.strip()

    fence_match = _FENCE_PATTERN.match(text)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIResponseParseError(f"AI response is not valid JSON: {exc}") from exc
