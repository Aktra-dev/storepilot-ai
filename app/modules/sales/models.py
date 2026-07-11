"""
Sales Records — SQLAlchemy ORM model.

One row per recorded sale, used as the raw input for Sales Anomaly
Detection (see operational_analysis module).
"""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SalesRecord(Base):
    __tablename__ = "sales_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )

    quantity_sold: Mapped[int] = mapped_column(Integer, nullable=False)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
