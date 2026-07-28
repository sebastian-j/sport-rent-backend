"""Merge multiple heads

Revision ID: 5cadb342fe8b
Revises: 8b9c0d1e2f3a
Create Date: 2026-07-28 12:07:34.247980

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '5cadb342fe8b'
down_revision: Union[str, Sequence[str], None] = ('8b9c0d1e2f3a', 'b9f4f2c8a61d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
