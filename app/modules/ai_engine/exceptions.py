"""
AI response processing errors.

Kept distinct from Pydantic's ValidationError so the orchestration
service (service.py) can catch "this AI response is unusable" uniformly,
whether it failed at the JSON-parsing stage or the schema-validation
stage — without ever needing to inspect or expose the raw exception
internals to the caller.
"""


class AIResponseError(Exception):
    """Base class for AI response processing errors."""


class AIResponseParseError(AIResponseError):
    """Raised when the AI response is not valid JSON."""
