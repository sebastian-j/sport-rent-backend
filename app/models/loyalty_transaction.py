from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LoyaltyTransactionType(enum.StrEnum):
    EARN = "EARN"
    SPEND = "SPEND"
    REFUND = "REFUND"
    REVERSAL = "REVERSAL"
    ADJUSTMENT = "ADJUSTMENT"


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id"),
        nullable=True,
    )
    type: Mapped[LoyaltyTransactionType] = mapped_column(
        Enum(LoyaltyTransactionType, name="loyalty_transaction_type"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="loyalty_transactions")
    order: Mapped[Order | None] = relationship(back_populates="loyalty_transactions")

    __table_args__ = (
        CheckConstraint(
            "(type IN ('EARN', 'REFUND') AND amount > 0) "
            "OR (type IN ('SPEND', 'REVERSAL') AND amount < 0) "
            "OR (type = 'ADJUSTMENT' AND amount <> 0)",
            name="check_loyalty_transaction_amount_sign",
        ),
        UniqueConstraint(
            "order_id",
            "type",
            name="uq_loyalty_transaction_order_type",
        ),
        Index(
            "ix_loyalty_transactions_user_created_at",
            "user_id",
            "created_at",
            "id",
        ),
    )


if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User
