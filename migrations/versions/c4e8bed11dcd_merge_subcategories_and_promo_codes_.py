"""merge subcategories and promo codes heads

Revision ID: c4e8bed11dcd
Revises: 3a246e6caff5, 5900780bbfe7
Create Date: 2026-08-20 10:55:54.680236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8bed11dcd'
down_revision: Union[str, Sequence[str], None] = ('3a246e6caff5', '5900780bbfe7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
