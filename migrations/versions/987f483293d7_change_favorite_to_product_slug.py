"""change favorite to product_slug

Revision ID: 987f483293d7
Revises: df5516f1fa2e
Create Date: 2026-07-28 15:24:16.724307

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "987f483293d7"
down_revision: str | Sequence[str] | None = "df5516f1fa2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "favorites",
        sa.Column("product_slug", sa.String(length=255), nullable=True),
    )

    favorites = sa.table(
        "favorites",
        sa.column("product_id", sa.Integer()),
        sa.column("product_slug", sa.String(length=255)),
    )
    products = sa.table(
        "products",
        sa.column("id", sa.Integer()),
        sa.column("slug", sa.String(length=255)),
    )
    op.execute(
        favorites.update().values(
            product_slug=sa.select(products.c.slug)
            .where(products.c.id == favorites.c.product_id)
            .scalar_subquery()
        )
    )
    op.alter_column(
        "favorites",
        "product_slug",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.drop_constraint(
        op.f("favorites_product_id_fkey"), "favorites", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("favorites_product_slug_fkey"),
        "favorites",
        "products",
        ["product_slug"],
        ["slug"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )
    op.drop_column("favorites", "product_id")


def downgrade() -> None:
    op.add_column(
        "favorites",
        sa.Column("product_id", sa.Integer(), autoincrement=False, nullable=True),
    )

    favorites = sa.table(
        "favorites",
        sa.column("product_id", sa.Integer()),
        sa.column("product_slug", sa.String(length=255)),
    )
    products = sa.table(
        "products",
        sa.column("id", sa.Integer()),
        sa.column("slug", sa.String(length=255)),
    )
    op.execute(
        favorites.update().values(
            product_id=sa.select(products.c.id)
            .where(products.c.slug == favorites.c.product_slug)
            .scalar_subquery()
        )
    )
    op.alter_column(
        "favorites",
        "product_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_constraint(
        op.f("favorites_product_slug_fkey"),
        "favorites",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("favorites_product_id_fkey"),
        "favorites",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("favorites", "product_slug")
