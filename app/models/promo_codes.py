from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DiscountType(StrEnum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_AMOUNT = "FIXED_AMOUNT"


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, name="promo_discount_type"),
        nullable=False,
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )
    minimum_order_value: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    max_uses: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    orders: Mapped[list[Order]] = relationship(
        back_populates="promo_code",
    )

    __table_args__ = (
        CheckConstraint(
            "(discount_type = 'PERCENTAGE' "
            "AND discount_value > 0 "
            "AND discount_value <= 1) "
            "OR (discount_type = 'FIXED_AMOUNT' "
            "AND discount_value > 0)",
            name="check_promo_discount_value",
        ),
        CheckConstraint(
            "minimum_order_value IS NULL OR minimum_order_value >= 0",
            name="check_promo_minimum_order_value",
        ),
        CheckConstraint(
            "usage_count >= 0",
            name="check_promo_usage_count",
        ),
        CheckConstraint(
            "max_uses IS NULL OR max_uses > 0",
            name="check_promo_max_uses",
        ),
        CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_from <= valid_until",
            name="check_promo_validity_dates",
        ),
    )


if TYPE_CHECKING:
    from app.models.order import Order
