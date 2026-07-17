"""
Operational Analysis — SQLAlchemy ORM models.

OperationalAnalysis = one run of the AI Operational Analysis step.
OperationalFinding  = one individual signal produced by that run (e.g.
one stockout risk, one expiry risk, one sales anomaly), optionally tied
to a specific product.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.products.models import Product
    from app.modules.tasks.models import Task


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingType(str, enum.Enum):
    STOCKOUT = "stockout"
    EXPIRY = "expiry"
    SALES_ANOMALY = "sales_anomaly"
    OPERATIONAL = "operational"  # general operational finding from the AI


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OperationalAnalysis(Base):
    __tablename__ = "operational_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        SAEnum(AnalysisStatus, name="analysis_status_enum"),
        nullable=False,
        default=AnalysisStatus.PENDING,
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    findings: Mapped[list["OperationalFinding"]] = relationship(back_populates="analysis")


class OperationalFinding(Base):
    __tablename__ = "operational_findings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("operational_analyses.id"), nullable=False
    )
    finding_type: Mapped[FindingType] = mapped_column(
        SAEnum(FindingType, name="finding_type_enum"), nullable=False
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    severity: Mapped[Severity] = mapped_column(
        SAEnum(Severity, name="severity_enum"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analysis: Mapped["OperationalAnalysis"] = relationship(back_populates="findings")
    product: Mapped[Optional["Product"]] = relationship(back_populates="findings")
    tasks: Mapped[list["Task"]] = relationship(back_populates="finding")
