"""initial schema

Revision ID: manual_001
Revises: 
Create Date: auto-generated

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'manual_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables will be created by SQLAlchemy Base.metadata.create_all()
    # This is a placeholder - run 'alembic revision --autogenerate -m "initial"' properly
    pass


def downgrade() -> None:
    pass
