"""recreate products

Revision ID: 8b9c0d1e2f3a
Revises: 6eb68702b34d
Create Date: 2026-07-27 14:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8b9c0d1e2f3a"
down_revision: str | Sequence[str] | None = "6eb68702b34d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop existing tables
    op.drop_table("product_sizes")
    op.drop_index(op.f("ix_products_slug"), table_name="products")
    op.drop_index(op.f("ix_products_id"), table_name="products")
    op.drop_index(op.f("ix_products_category"), table_name="products")
    op.drop_table("products")

    # Create new tables
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("meta_description", sa.String(length=255), nullable=True),
        sa.Column("visibility_status", sa.Boolean(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("price > 0", name="check_price_positive"),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_slug"), "products", ["slug"], unique=True)

    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("image", sa.String(length=255), nullable=True),
        sa.Column("alt_text", sa.String(length=255), nullable=True),
        sa.Column("display_order", sa.SmallInteger(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id", "display_order", name="uix_product_display_order"
        ),
    )

    op.create_table(
        "product_sizes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("size", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "size", name="uix_product_size"),
    )

    # Create Enum for instances status
    instance_status = postgresql.ENUM(
        "AVAILABLE",
        "MAINTENANCE",
        "BROKEN",
        "RETIRED",
        name="instancestatus",
        create_type=False,
    )
    instance_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "instances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("status", instance_status, server_default="AVAILABLE", nullable=True),
        sa.Column("size", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("favorites")
    op.drop_table("instances")
    op.drop_table("product_sizes")
    op.drop_table("product_images")
    op.drop_index(op.f("ix_products_slug"), table_name="products")
    op.drop_table("products")
    op.drop_table("categories")

    instance_status = postgresql.ENUM(
        "AVAILABLE",
        "MAINTENANCE",
        "BROKEN",
        "RETIRED",
        name="instancestatus",
        create_type=False,
    )
    instance_status.drop(op.get_bind(), checkfirst=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("images", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("alt", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_products_category"),
        "products",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_products_id"),
        "products",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_products_slug"),
        "products",
        ["slug"],
        unique=True,
    )
    op.create_table(
        "product_sizes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("size", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
