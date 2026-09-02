"""add total price to orders

Revision ID: cbcd56097ca8
Revises: 8efa54233655
Create Date: 2026-08-31 13:24:00.678794

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cbcd56097ca8"
down_revision: str | Sequence[str] | None = "96caca3e53dd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "orders",
        sa.Column(
            "total_price",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.alter_column(
        "orders",
        "total_price",
        server_default=None,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("orders", "total_price")
