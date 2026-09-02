from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatus(enum.StrEnum):
    PENDING = "PENDING"
    UNPAID = "UNPAID"
    PAID = "PAID"
    GIVEN_OUT = "GIVEN_OUT"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
        nullable=False,
    )
    payment_code: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    used_points: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )
    points_to_spend: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    promo_code_id: Mapped[int | None] = mapped_column(
        ForeignKey("promo_codes.id"),
        index=True,
        nullable=True,
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    recipient_first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    recipient_last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    user: Mapped[User] = relationship(
        back_populates="orders",
    )
    promo_code: Mapped[PromoCode | None] = relationship(
        back_populates="orders",
    )
    address: Mapped[OrderAddress] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    instances: Mapped[list[OrderInstance]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    loyalty_transactions: Mapped[list[LoyaltyTransaction]] = relationship(
        back_populates="order",
    )
    payment: Mapped[Payment | None] = relationship(
        back_populates="order",
        uselist=False,
    )


class OrderInstance(Base):
    __tablename__ = "order_instances"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    instance_id: Mapped[int] = mapped_column(
        ForeignKey("instances.id", ondelete="RESTRICT"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    order: Mapped[Order] = relationship(
        back_populates="instances",
    )
    instance: Mapped[Instance] = relationship()


if TYPE_CHECKING:
    from app.models.loyalty_transaction import LoyaltyTransaction
    from app.models.order_address import OrderAddress
    from app.models.payment import Payment
    from app.models.product import Instance
    from app.models.promo_codes import PromoCode
    from app.models.user import User
