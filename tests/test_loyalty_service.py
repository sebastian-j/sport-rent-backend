from decimal import Decimal

import pytest

from app.services.loyalty import (
    InvalidLoyaltyPointsAmountError,
    LoyaltyPointsRedemptionLimitError,
    LoyaltyProgramLockedError,
    calculate_earned_points,
    calculate_max_redeemable_points,
    calculate_points_discount,
    validate_points_redemption,
)


def test_allows_order_without_points_redemption_while_program_is_locked() -> None:
    validate_points_redemption(0, Decimal("100.00"), Decimal("0.00"))


@pytest.mark.parametrize("points", [1, 50, 60])
def test_allows_any_positive_points_after_program_unlock(points: int) -> None:
    validate_points_redemption(points, Decimal("100.00"), Decimal("500.00"))


def test_rejects_points_redemption_before_program_unlock() -> None:
    with pytest.raises(LoyaltyProgramLockedError) as error:
        validate_points_redemption(1, Decimal("100.00"), Decimal("499.99"))

    assert error.value.current_spend == Decimal("499.99")
    assert error.value.required_spend == Decimal("500.00")


def test_unlocks_program_at_exact_spend_threshold() -> None:
    validate_points_redemption(1, Decimal("100.00"), Decimal("500.00"))


def test_rejects_points_above_order_limit() -> None:
    with pytest.raises(LoyaltyPointsRedemptionLimitError) as error:
        validate_points_redemption(61, Decimal("100.00"), Decimal("500.00"))

    assert error.value.maximum == 60
    assert error.value.requested == 61


def test_rejects_points_above_limit_for_inexpensive_order() -> None:
    with pytest.raises(LoyaltyPointsRedemptionLimitError) as error:
        validate_points_redemption(50, Decimal("50.00"), Decimal("500.00"))

    assert error.value.maximum == 30


@pytest.mark.parametrize("points", [False, 0.0])
def test_zero_redemption_still_requires_integer(points: object) -> None:
    with pytest.raises(InvalidLoyaltyPointsAmountError):
        validate_points_redemption(  # type: ignore[arg-type]
            points,
            Decimal("100.00"),
            Decimal("500.00"),
        )


@pytest.mark.parametrize(
    ("order_value", "expected_points"),
    [
        (Decimal("0.00"), 0),
        (Decimal("1.00"), 0),
        (Decimal("99.99"), 59),
        (Decimal("100.00"), 60),
        (Decimal("250.00"), 150),
    ],
)
def test_calculates_max_redeemable_points(
    order_value: Decimal,
    expected_points: int,
) -> None:
    assert calculate_max_redeemable_points(order_value) == expected_points


def test_max_redeemable_points_rejects_negative_order_value() -> None:
    with pytest.raises(ValueError, match="Order value cannot be negative"):
        calculate_max_redeemable_points(Decimal("-0.01"))


@pytest.mark.parametrize(
    ("points", "expected_discount"),
    [
        (0, Decimal("0.00")),
        (1, Decimal("0.50")),
        (10, Decimal("5.00")),
        (25, Decimal("12.50")),
        (50, Decimal("25.00")),
    ],
)
def test_calculates_points_discount(
    points: int,
    expected_discount: Decimal,
) -> None:
    assert calculate_points_discount(points) == expected_discount


@pytest.mark.parametrize("points", [True, 1.5, "10"])
def test_points_discount_requires_integer(points: object) -> None:
    with pytest.raises(ValueError, match="Points must be an integer"):
        calculate_points_discount(points)  # type: ignore[arg-type]


def test_points_discount_rejects_negative_points() -> None:
    with pytest.raises(ValueError, match="Points cannot be negative"):
        calculate_points_discount(-1)


@pytest.mark.parametrize(
    ("cash_paid", "expected_points"),
    [
        (Decimal("0.00"), 0),
        (Decimal("9.99"), 0),
        (Decimal("10.00"), 1),
        (Decimal("19.99"), 1),
        (Decimal("100.00"), 10),
        (Decimal("250.00"), 25),
    ],
)
def test_calculates_earned_points(
    cash_paid: Decimal,
    expected_points: int,
) -> None:
    assert calculate_earned_points(cash_paid) == expected_points


def test_rejects_negative_cash_paid() -> None:
    with pytest.raises(ValueError, match="Cash paid cannot be negative"):
        calculate_earned_points(Decimal("-0.01"))
