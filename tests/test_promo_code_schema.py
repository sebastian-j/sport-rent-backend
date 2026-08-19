from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.promo_codes import DiscountType
from app.schemas.promo_code import PromoCodeCreate


def test_promo_code_create_normalizes_code() -> None:
    request = PromoCodeCreate(
        code="  sport10  ",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("0.10"),
    )

    assert request.code == "SPORT10"


def test_promo_code_create_allows_fixed_discount_greater_than_one() -> None:
    request = PromoCodeCreate(
        code="MINUS20",
        discount_type=DiscountType.FIXED_AMOUNT,
        discount_value=Decimal("20.00"),
    )

    assert request.discount_value == Decimal("20.00")


def test_promo_code_create_rejects_percentage_greater_than_one() -> None:
    with pytest.raises(
        ValidationError,
        match="Percentage discount cannot be greater than 1",
    ):
        PromoCodeCreate(
            code="INVALID",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("1.01"),
        )


def test_promo_code_create_rejects_empty_code() -> None:
    with pytest.raises(ValidationError, match="Code cannot be empty"):
        PromoCodeCreate(
            code="   ",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("0.10"),
        )


def test_promo_code_create_rejects_invalid_validity_dates() -> None:
    with pytest.raises(ValidationError, match="valid_until must be after valid_from"):
        PromoCodeCreate(
            code="EXPIRED",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("0.10"),
            valid_from=datetime(2026, 8, 20, tzinfo=UTC),
            valid_until=datetime(2026, 8, 19, tzinfo=UTC),
        )
