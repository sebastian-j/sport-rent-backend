from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product, ProductSize
    from app.models.user import User


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    product_size_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_sizes.id", ondelete="RESTRICT"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_cart_item_quantity_positive"),
        CheckConstraint("start_date <= end_date", name="check_cart_item_date_range"),
        UniqueConstraint(
            "user_id",
            "product_id",
            "product_size_id",
            "start_date",
            "end_date",
            name="uq_cart_item_term",
            postgresql_nulls_not_distinct=True,
        ),
    )

    user: Mapped[User] = relationship(back_populates="cart_items")
    product: Mapped[Product] = relationship(back_populates="cart_items")
    product_size: Mapped[ProductSize | None] = relationship(back_populates="cart_items")
