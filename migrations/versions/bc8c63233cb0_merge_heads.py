"""merge heads

Revision ID: bc8c63233cb0
Revises: 55cbf0e94771, c4f7a1d29e63
Create Date: 2026-07-30 13:54:55.347457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc8c63233cb0'
down_revision: Union[str, Sequence[str], None] = ('55cbf0e94771', 'c4f7a1d29e63')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
