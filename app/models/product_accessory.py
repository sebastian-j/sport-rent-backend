from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class ProductAccessory(Base):
    __tablename__ = "product_accessories"

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    accessory_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )

    product: Mapped[Product] = relationship(
        foreign_keys=[product_id],
        back_populates="accessory_links",
    )
    accessory: Mapped[Product] = relationship(
        foreign_keys=[accessory_id],
        back_populates="suggested_for_links",
    )

    __table_args__ = (
        CheckConstraint(
            "product_id <> accessory_id",
            name="check_product_accessory_not_self",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="check_product_accessory_display_order_nonnegative",
        ),
        UniqueConstraint(
            "product_id",
            "display_order",
            name="uq_product_accessory_display_order",
        ),
    )
