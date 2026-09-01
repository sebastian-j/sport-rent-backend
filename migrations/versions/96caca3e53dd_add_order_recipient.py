"""add order recipient

Revision ID: 96caca3e53dd
Revises: 8efa54233655
Create Date: 2026-08-31 15:20:59.039771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96caca3e53dd'
down_revision: Union[str, Sequence[str], None] = '8efa54233655'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("recipient_first_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_last_name", sa.String(length=100), nullable=True),
    )

    op.execute(
        """
        UPDATE orders AS o
        SET recipient_first_name = oa.first_name,
            recipient_last_name = oa.last_name
        FROM order_addresses AS oa
        WHERE oa.order_id = o.id
          AND oa.first_name IS NOT NULL
          AND oa.last_name IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE orders AS o
        SET recipient_first_name = u.first_name,
            recipient_last_name = u.last_name
        FROM users AS u
        WHERE o.user_id = u.id
          AND o.recipient_first_name IS NULL
          AND u.first_name IS NOT NULL
          AND u.last_name IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE orders
        SET recipient_first_name = 'Unknown',
            recipient_last_name = 'User'
        WHERE recipient_first_name IS NULL
        """
    )

    op.alter_column("orders", "recipient_first_name", nullable=False)
    op.alter_column("orders", "recipient_last_name", nullable=False)


def downgrade() -> None:
    op.drop_column("orders", "recipient_last_name")
    op.drop_column("orders", "recipient_first_name")
