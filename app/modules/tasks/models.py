"""
Tasks — SQLAlchemy ORM model.

A task is generated from one OperationalFinding, and can go through
zero or more Approval records (see app/modules/approvals/models.py) as
a manager reviews it.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.approvals.models import Approval
    from app.modules.operational_analysis.models import OperationalFinding


class TaskPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"  # renamed in Step 7: task always
    # waits for manager approval before it can move to IN_PROGRESS
    APPROVED = "approved"  # added in Step 8
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"  # added in Step 8
    CANCELLED = "cancelled"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("operational_findings.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(
        SAEnum(TaskPriority, name="task_priority_enum"),
        nullable=False,
        default=TaskPriority.MEDIUM,
    )
    assigned_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, name="task_status_enum"),
        nullable=False,
        default=TaskStatus.PENDING_APPROVAL,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    finding: Mapped["OperationalFinding"] = relationship(back_populates="tasks")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="task")
