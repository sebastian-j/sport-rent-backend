"""add product accessories

Revision ID: dfc9d79dd1ed
Revises: c4e8bed11dcd
Create Date: 2026-08-24 10:46:59.390217

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "dfc9d79dd1ed"
down_revision: str | Sequence[str] | None = "2c75ee6bd327"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "product_accessories",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("accessory_id", sa.Integer(), nullable=False),
        sa.Column(
            "display_order",
            sa.SmallInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.CheckConstraint(
            "product_id <> accessory_id",
            name="check_product_accessory_not_self",
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name="check_product_accessory_display_order_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["accessory_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("product_id", "accessory_id"),
        sa.UniqueConstraint(
            "product_id",
            "display_order",
            name="uq_product_accessory_display_order",
        ),
    )
    op.create_index(
        "ix_product_accessories_accessory_id",
        "product_accessories",
        ["accessory_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_product_accessories_accessory_id",
        table_name="product_accessories",
    )
    op.drop_table("product_accessories")
