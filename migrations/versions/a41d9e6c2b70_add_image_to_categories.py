"""add image to categories

Revision ID: a41d9e6c2b70
Revises: df5516f1fa2e
Create Date: 2026-07-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a41d9e6c2b70"
down_revision: str | Sequence[str] | None = "df5516f1fa2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("image", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("categories", "image")
