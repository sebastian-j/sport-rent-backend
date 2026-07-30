"""empty message

Revision ID: 55cbf0e94771
Revises: 1ede6f19bcdd, f3a6b2c9d1e4
Create Date: 2026-07-29 17:05:02.614314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55cbf0e94771'
down_revision: Union[str, Sequence[str], None] = ('1ede6f19bcdd', 'f3a6b2c9d1e4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
