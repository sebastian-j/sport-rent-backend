"""drop image from manufacturers

Revision ID: 7f3c9a1b2d4e
Revises: 02e0c951b616
Create Date: 2026-08-24 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3c9a1b2d4e'
down_revision: Union[str, Sequence[str], None] = '02e0c951b616'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('manufacturers', 'image')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('manufacturers', sa.Column('image', sa.String(length=255), nullable=True))
