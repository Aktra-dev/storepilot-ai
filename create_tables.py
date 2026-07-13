"""
One-off script to create all database tables from the SQLAlchemy models.

Plain create_all() is used instead of Alembic migrations — simpler for
this project's 7-day scope, no migration history needed yet.

Usage:
    python create_tables.py            # create any missing tables
    python create_tables.py --reset    # drop known tables first, then recreate
                                        # (use this after a schema change)
"""

import sys

from app import models_registry  # noqa: F401  (registers every model)
from app.core.database import Base, engine


def main() -> None:
    if "--reset" in sys.argv:
        print("Dropping existing tables (only ones defined in current models)...")
        Base.metadata.drop_all(bind=engine)

    print("Creating tables on:", engine.url.render_as_string(hide_password=True))
    Base.metadata.create_all(bind=engine)

    print("Done. Tables now registered:")
    for table in Base.metadata.sorted_tables:
        print(f" - {table.name}")


if __name__ == "__main__":
    main()
