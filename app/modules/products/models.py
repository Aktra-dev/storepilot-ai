"""
Product Master Data — SQLAlchemy ORM model.

Stock level and expiry now live in a separate `inventory` table (see
app/modules/inventory/models.py) — a product can have more than one
inventory/batch record over time, instead of one stock number baked
directly onto Product.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Integer, String, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.inventory.models import Inventory
    from app.modules.operational_analysis.models import OperationalFinding
    from app.modules.sales.models import Sale


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    minimum_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    inventory_records: Mapped[list["Inventory"]] = relationship(back_populates="product")
    sales_records: Mapped[list["Sale"]] = relationship(back_populates="product")
    findings: Mapped[list["OperationalFinding"]] = relationship(back_populates="product")
