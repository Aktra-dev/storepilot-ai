"""
Product Master Data — SQLAlchemy ORM model.

Note: current_stock / min_stock_threshold / expiry_date live directly on
this table. This is deliberate for MVP scope — Inventory Monitoring and
Expiry Risk Detection both read from these same columns instead of a
separate "inventory" table, avoiding duplicate state to keep in sync.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
