"""
Sales — business logic.

SalesAnomalyService is a deterministic rule engine: given plain daily
sales quantities for a recent period and a historical period, it
classifies whether the recent period is a drop, a spike, or normal.
Purely statistical (average + percentage change) — no AI involved here.
AI only interprets the result later, downstream in the pipeline.
"""

from typing import Optional, Sequence

from app.modules.sales.schemas import AnomalyStatus, SalesAnomalyResult


class SalesAnomalyService:
    # --- Expected period lengths (in days), used for confidence scoring ---
    RECENT_PERIOD_DAYS = 3
    HISTORICAL_PERIOD_DAYS = 14

    # --- Minimum data required before we trust the calculation at all ---
    MIN_RECENT_DAYS_REQUIRED = 1
    MIN_HISTORICAL_DAYS_REQUIRED = 3

    # --- Anomaly thresholds, in percentage change ---
    DROP_CRITICAL_THRESHOLD = -70
    DROP_HIGH_THRESHOLD = -40
    DROP_MEDIUM_THRESHOLD = -20
    SPIKE_THRESHOLD = 100

    def assess_sales_anomaly(
        self,
        recent_sales: Optional[Sequence[int]],
        historical_sales: Optional[Sequence[int]],
    ) -> SalesAnomalyResult:
        """
        percentage_change = (recent_average - historical_average) / historical_average * 100

        Handles: insufficient data (too few days in either period) and
        historical_average == 0 (division by zero).
        """
        recent_sales = recent_sales or []
        historical_sales = historical_sales or []

        confidence = self._calculate_confidence(recent_sales, historical_sales)

        # --- Insufficient data guard ---
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

        # --- Historical average is zero: avoid division by zero ---
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
                note=(
                    "Historical average is zero; any new sales is treated as a "
                    "spike, but percentage_change is undefined"
                ),
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
    def _safe_average(values: Sequence[int]) -> float:
        return sum(values) / len(values) if values else 0

    def _calculate_confidence(
        self,
        recent_sales: Sequence[int],
        historical_sales: Sequence[int],
    ) -> float:
        """
        Confidence reflects how complete the input data is relative to the
        expected period lengths — not how "normal" the result looks. Full
        3 recent days + full 14 historical days -> confidence 1.0.
        """
        recent_completeness = min(len(recent_sales) / self.RECENT_PERIOD_DAYS, 1.0)
        historical_completeness = min(
            len(historical_sales) / self.HISTORICAL_PERIOD_DAYS, 1.0
        )
        return round((recent_completeness + historical_completeness) / 2, 2)
