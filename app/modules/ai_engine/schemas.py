"""
AI Engine — Pydantic schemas.

Defines the exact contract the AI's JSON output must satisfy
(AIOperationalAnalysisResult), plus the input contract this module
accepts from InventoryRiskService / SalesAnomalyService.

Pydantic already rejects invalid enum values and missing required
fields by default — that's exactly what we want here, no extra code
needed for that part.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.sales.schemas import SalesAnomalyResult


# ---------------------------------------------------------------------------
# Enums (match the schema given in the STEP 6 spec exactly)
# ---------------------------------------------------------------------------

class FindingType(str, Enum):
    STOCKOUT = "STOCKOUT"
    EXPIRY = "EXPIRY"
    SALES_ANOMALY = "SALES_ANOMALY"
    OPERATIONAL = "OPERATIONAL"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StoreStatus(str, Enum):
    NORMAL = "NORMAL"
    ATTENTION = "ATTENTION"
    CRITICAL = "CRITICAL"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class AssignedRole(str, Enum):
    STORE_STAFF = "STORE_STAFF"
    INVENTORY_STAFF = "INVENTORY_STAFF"
    MANAGER = "MANAGER"


# ---------------------------------------------------------------------------
# AI output contract
# ---------------------------------------------------------------------------

class AIFinding(BaseModel):
    type: FindingType
    product_id: Optional[str] = None
    severity: SeverityLevel
    title: str
    description: str
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)


class AITask(BaseModel):
    title: str
    description: str
    priority: TaskPriority
    assigned_role: AssignedRole
    source_finding_index: int


class AIOperationalAnalysisResult(BaseModel):
    summary: str
    store_status: StoreStatus
    findings: List[AIFinding]
    tasks: List[AITask]


# ---------------------------------------------------------------------------
# Input contract (what this module accepts, never raw data)
# ---------------------------------------------------------------------------

class ProductSalesAnomaly(BaseModel):
    """Associates a SalesAnomalyResult (Step 5) with the product it's for."""

    product_id: str
    result: SalesAnomalyResult
