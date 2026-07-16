"""
Sales — CRUD business logic (SalesService).

SalesAnomalyService (pure anomaly analysis, no DB) stays in a separate
class within this module. SalesService handles all DB operations.
"""

import uuid
from datetime import date, timedelta
from typing import Optional, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.products.models import Product
from app.modules.sales.models import Sale
from app.modules.sales.schemas import SaleCreate, SaleUpdate, AnomalyStatus, SalesAnomalyResult


class SalesService:
    """CRUD + summary for sales records."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(self, data: SaleCreate) -> Sale:
        """Record a new sale transaction."""
        product = self.db.query(Product).filter(Product.id == data.product_id).first()
        if not product:
            raise ValidationException(f"Product {data.product_id} not found")

        sale = Sale(
            id=uuid.uuid4(),
            product_id=data.product_id,
            quantity=data.quantity,
            total_amount=data.total_amount,
            sale_date=data.sale_date,
        )
        self.db.add(sale)
        self.db.commit()
        self.db.refresh(sale)
        return sale

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get(self, sale_id: uuid.UUID) -> Sale:
        """Get a single sale record by ID."""
        sale = self.db.query(Sale).filter(Sale.id == sale_id).first()
        if not sale:
            raise NotFoundException(f"Sale {sale_id} not found")
        return sale

    def get_list(
        self,
        product_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Sale]:
        """List sales with optional filters."""
        query = self.db.query(Sale)

        if product_id:
            query = query.filter(Sale.product_id == product_id)
        if start_date:
            query = query.filter(Sale.sale_date >= start_date)
        if end_date:
            query = query.filter(Sale.sale_date <= end_date)

        return query.order_by(Sale.sale_date.desc()).offset(skip).limit(limit).all()

    def list_by_product(self, product_id: uuid.UUID) -> List[Sale]:
        """List all sales for a specific product (newest first)."""
        return (
            self.db.query(Sale)
            .filter(Sale.product_id == product_id)
            .order_by(Sale.sale_date.desc())
            .all()
        )

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(self, sale_id: uuid.UUID, data: SaleUpdate) -> Sale:
        """Update a sale record."""
        sale = self.get(sale_id)

        if data.quantity is not None:
            sale.quantity = data.quantity
        if data.total_amount is not None:
            sale.total_amount = data.total_amount
        if data.sale_date is not None:
            sale.sale_date = data.sale_date

        self.db.commit()
        self.db.refresh(sale)
        return sale

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(self, sale_id: uuid.UUID) -> None:
        """Delete a sale record."""
        sale = self.get(sale_id)
        self.db.delete(sale)
        self.db.commit()

    # ------------------------------------------------------------------
    # AGGREGATES / SUMMARIES
    # ------------------------------------------------------------------

    def get_summary(
        self,
        product_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """
        Get aggregated sales summary (total revenue, count, average per day).
        """
        query = self.db.query(Sale)

        if product_id:
            query = query.filter(Sale.product_id == product_id)
        if start_date:
            query = query.filter(Sale.sale_date >= start_date)
        if end_date:
            query = query.filter(Sale.sale_date <= end_date)

        # Total revenue and count
        result = query.with_entities(
            func.coalesce(func.sum(Sale.total_amount), 0),
            func.count(Sale.id),
        ).first()

        total_revenue = float(result[0])
        total_count = int(result[1])

        # Average per day (only if date range provided or at least one sale)
        average_per_day = None
        if total_count > 0:
            date_range_query = query.with_entities(
                func.min(Sale.sale_date),
                func.max(Sale.sale_date),
            ).first()
            if date_range_query[0] and date_range_query[1]:
                days = (date_range_query[1] - date_range_query[0]).days + 1
                if days > 0:
                    average_per_day = round(total_count / days, 2)

        # Top products by revenue
        top_products = (
            self.db.query(
                Sale.product_id,
                func.sum(Sale.total_amount).label("revenue"),
                func.count(Sale.id).label("sales_count"),
            )
            .group_by(Sale.product_id)
            .order_by(func.sum(Sale.total_amount).desc())
            .limit(5)
            .all()
        )

        return {
            "total_sales": total_count,
            "total_revenue": total_revenue,
            "average_per_day": average_per_day,
            "top_products": [
                {
                    "product_id": str(tp.product_id),
                    "revenue": float(tp.revenue),
                    "sales_count": tp.sales_count,
                }
                for tp in top_products
            ],
        }

    def get_daily_totals(
        self,
        product_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 30,
    ) -> List[dict]:
        """
        Get daily sales totals (for charts/graphs).

        Returns list of dicts with date, total_amount, and total_quantity.
        """
        today = date.today()
        if not start_date:
            start_date = today - timedelta(days=limit - 1)
        if not end_date:
            end_date = today

        query = self.db.query(
            Sale.sale_date,
            func.sum(Sale.total_amount).label("total_amount"),
            func.sum(Sale.quantity).label("total_quantity"),
            func.count(Sale.id).label("transaction_count"),
        ).filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date,
        )

        if product_id:
            query = query.filter(Sale.product_id == product_id)

        results = query.group_by(Sale.sale_date).order_by(Sale.sale_date.asc()).all()

        return [
            {
                "date": r.sale_date.isoformat(),
                "total_amount": float(r.total_amount),
                "total_quantity": int(r.total_quantity),
                "transaction_count": r.transaction_count,
            }
            for r in results
        ]


# =========================================================================
# SalesAnomalyService (pure rule engine — no DB, no I/O)
# =========================================================================

class SalesAnomalyService:
    """
    Deterministic rule engine for sales anomaly detection.
    No AI, no database access — pure statistical calculation.
    """

    RECENT_PERIOD_DAYS = 3
    HISTORICAL_PERIOD_DAYS = 14
    MIN_RECENT_DAYS_REQUIRED = 1
    MIN_HISTORICAL_DAYS_REQUIRED = 3
    DROP_CRITICAL_THRESHOLD = -70
    DROP_HIGH_THRESHOLD = -40
    DROP_MEDIUM_THRESHOLD = -20
    SPIKE_THRESHOLD = 100

    def assess_sales_anomaly(
        self,
        recent_sales: Optional[List[int]],
        historical_sales: Optional[List[int]],
    ) -> SalesAnomalyResult:
        recent_sales = recent_sales or []
        historical_sales = historical_sales or []
        confidence = self._calculate_confidence(recent_sales, historical_sales)

        if (
            len(recent_sales) < self.MIN_RECENT_DAYS_REQUIRED
            or len(historical_sales) < self.MIN_HISTORICAL_DAYS_REQUIRED
        ):
            return SalesAnomalyResult(
                status=AnomalyStatus.INSUFFICIENT_DATA,
                recent_average=self._safe_average(recent_sales),
                historical_average=self._safe_average(historical_sales),
                percentage_change=None,
                confidence=confidence,
                note="Not enough sales data to reliably detect an anomaly",
            )

        recent_average = self._safe_average(recent_sales)
        historical_average = self._safe_average(historical_sales)

        if historical_average == 0:
            if recent_average == 0:
                return SalesAnomalyResult(
                    status=AnomalyStatus.NORMAL,
                    recent_average=0,
                    historical_average=0,
                    percentage_change=0,
                    confidence=confidence,
                    note="No sales recorded in either period",
                )
            return SalesAnomalyResult(
                status=AnomalyStatus.SPIKE,
                recent_average=round(recent_average, 2),
                historical_average=0,
                percentage_change=None,
                confidence=confidence,
                note="Historical average is zero; any new sales is treated as a spike",
            )

        percentage_change = ((recent_average - historical_average) / historical_average) * 100

        if percentage_change <= self.DROP_CRITICAL_THRESHOLD:
            status = AnomalyStatus.DROP_CRITICAL
        elif percentage_change <= self.DROP_HIGH_THRESHOLD:
            status = AnomalyStatus.DROP_HIGH
        elif percentage_change <= self.DROP_MEDIUM_THRESHOLD:
            status = AnomalyStatus.DROP_MEDIUM
        elif percentage_change >= self.SPIKE_THRESHOLD:
            status = AnomalyStatus.SPIKE
        else:
            status = AnomalyStatus.NORMAL

        return SalesAnomalyResult(
            status=status,
            recent_average=round(recent_average, 2),
            historical_average=round(historical_average, 2),
            percentage_change=round(percentage_change, 2),
            confidence=confidence,
        )

    @staticmethod
    def _safe_average(values: List[int]) -> float:
        return sum(values) / len(values) if values else 0

    @staticmethod
    def _calculate_confidence(recent_sales: List[int], historical_sales: List[int]) -> float:
        recent_comp = min(len(recent_sales) / 3, 1.0)
        hist_comp = min(len(historical_sales) / 14, 1.0)
        return round((recent_comp + hist_comp) / 2, 2)
