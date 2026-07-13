"""
Central import point for every SQLAlchemy model.

Cross-module `relationship()` calls (e.g. Product -> "Inventory",
Task -> "Approval") reference each other by class name string to avoid
circular imports between modules. Those strings are only resolved once
every mapped class has actually been imported somewhere. Importing this
one module guarantees that — it's used by create_tables.py, seed_data.py,
and anywhere else that needs the full schema available.
"""

from app.core.database import Base  # noqa: F401
from app.modules.approvals.models import Approval  # noqa: F401
from app.modules.auth.models import User  # noqa: F401
from app.modules.inventory.models import Inventory  # noqa: F401
from app.modules.operational_analysis.models import (  # noqa: F401
    OperationalAnalysis,
    OperationalFinding,
)
from app.modules.products.models import Product  # noqa: F401
from app.modules.sales.models import Sale  # noqa: F401
from app.modules.tasks.models import Task  # noqa: F401
