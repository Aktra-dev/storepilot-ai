"""
Sales — Pydantic schemas.

Structured output contract for SalesAnomalyService (see service.py).
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AnomalyStatus(str, Enum):
    DROP_CRITICAL = "DROP_CRITICAL"
    DROP_HIGH = "DROP_HIGH"
    DROP_MEDIUM = "DROP_MEDIUM"
    SPIKE = "SPIKE"
    NORMAL = "NORMAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SalesAnomalyResult(BaseModel):
    status: AnomalyStatus
    recent_average: Optional[float] = None
    historical_average: Optional[float] = None
    percentage_change: Optional[float] = None
    confidence: float
    note: Optional[str] = None
