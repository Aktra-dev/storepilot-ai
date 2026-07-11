"""
One-off script to create all database tables from the SQLAlchemy models.

For this project's scope, a plain create_all() script is used instead of
Alembic migrations — simpler for a 7-day timeline, no migration history
needed yet. Run it once after DATABASE_URL is set correctly:

    python create_tables.py
"""

from app.core.database import Base, engine

# Import every module that defines models so their tables are registered
# on Base.metadata before create_all() runs. Modules with no tables yet
# (auth, inventory, approvals, ai_engine) are intentionally not imported.
from app.shared import models as shared_models  # noqa: F401
from app.modules.products import models as products_models  # noqa: F401
from app.modules.sales import models as sales_models  # noqa: F401
from app.modules.operational_analysis import (  # noqa: F401
    models as operational_analysis_models,
)
from app.modules.tasks import models as tasks_models  # noqa: F401


def main() -> None:
    print("Creating tables on:", engine.url.render_as_string(hide_password=True))
    Base.metadata.create_all(bind=engine)
    print("Done. Tables now registered:")
    for table in Base.metadata.sorted_tables:
        print(f" - {table.name}")


if __name__ == "__main__":
    main()
