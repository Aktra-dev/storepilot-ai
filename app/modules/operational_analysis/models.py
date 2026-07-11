"""
Operational Analysis — SQLAlchemy ORM models.

Owns the two tables produced by the analysis pipeline:
- RiskSignal: output of Risk Detection (stockout/expiry) + Sales Anomaly
  Detection.
- AIAnalysisLog: audit trail of each AI Operational Analysis run (which
  provider answered, and what it returned). Kept here rather than in
  `ai_engine` because this is analysis *output data*, not AI logic itself
  — `ai_engine` will own the provider abstraction/logic when it's built.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskType(str, enum.Enum):
    STOCKOUT = "stockout"
    EXPIRY = "expiry"
    SALES_ANOMALY = "sales_anomaly"


class RiskStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class AnalysisStatus(str, enum.Enum):
    SUCCESS = "success"
    FALLBACK_USED = "fallback_used"
    FAILED = "failed"


class RiskSignal(Base):
    __tablename__ = "risk_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )

    risk_type: Mapped[RiskType] = mapped_column(
        SAEnum(RiskType, name="risk_type_enum"), nullable=False
    )
    severity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[RiskStatus] = mapped_column(
        SAEnum(RiskStatus, name="risk_status_enum"),
        nullable=False,
        default=RiskStatus.OPEN,
    )


class AIAnalysisLog(Base):
    __tablename__ = "ai_analysis_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False
    )

    input_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[AnalysisStatus] = mapped_column(
        SAEnum(AnalysisStatus, name="analysis_status_enum"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
