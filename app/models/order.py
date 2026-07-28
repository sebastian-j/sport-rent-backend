from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Uuid, func
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
        server_default="false",
        nullable=False,
    )
    user: Mapped[User] = relationship(
        back_populates="orders",
    )
    address: Mapped[OrderAddress] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )


if TYPE_CHECKING:
    from app.models.order_address import OrderAddress
    from app.models.user import User
