from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderAddress(Base):
    __tablename__ = "order_addresses"

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    first_line: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    second_line: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    postal_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    nip: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    order: Mapped[Order] = relationship(
        back_populates="address",
    )


if TYPE_CHECKING:
    from app.models.order import Order
