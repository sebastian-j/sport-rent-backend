"""add addresses

Revision ID: b9f4f2c8a61d
Revises: e7ecc88b201f
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9f4f2c8a61d"
down_revision: str | Sequence[str] | None = "e7ecc88b201f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

order_status_enum = sa.Enum(
    "PENDING",
    "UNPAID",
    "PAID",
    "GIVEN_OUT",
    "FINISHED",
    "CANCELLED",
    name="order_status",
)


def upgrade() -> None:
    op.create_table(
        "addresses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("first_line", sa.String(length=255), nullable=False),
        sa.Column("second_line", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("nip", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "users",
        sa.Column("first_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("default_address_id", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_users_default_address_id",
        "users",
        ["default_address_id"],
    )
    op.create_foreign_key(
        "fk_users_default_address_id_addresses",
        "users",
        "addresses",
        ["default_address_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            order_status_enum,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("payment_code", sa.Uuid(), nullable=True),
        sa.Column(
            "used_points",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_orders_user_id"),
        "orders",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "order_addresses",
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("first_line", sa.String(length=255), nullable=False),
        sa.Column("second_line", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("nip", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("order_id"),
    )


def downgrade() -> None:
    op.drop_table("order_addresses")
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_table("orders")
    order_status_enum.drop(op.get_bind(), checkfirst=True)
    op.drop_constraint(
        "fk_users_default_address_id_addresses",
        "users",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_users_default_address_id",
        "users",
        type_="unique",
    )
    op.drop_column("users", "default_address_id")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
    op.drop_table("addresses")
