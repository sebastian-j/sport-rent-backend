"""merge loyalty transactions and manufacturers heads

Revision ID: 2c75ee6bd327
Revises: 7f3c9a1b2d4e, d8c43f1c3890
Create Date: 2026-08-24 15:14:30.673628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c75ee6bd327'
down_revision: Union[str, Sequence[str], None] = ('7f3c9a1b2d4e', 'd8c43f1c3890')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
