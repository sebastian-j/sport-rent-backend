"""merge_heads

Revision ID: 1ede6f19bcdd
Revises: 987f483293d7, a41d9e6c2b70
Create Date: 2026-07-29 16:34:52.698928

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ede6f19bcdd'
down_revision: Union[str, Sequence[str], None] = ('987f483293d7', 'a41d9e6c2b70')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
