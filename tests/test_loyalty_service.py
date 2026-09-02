from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.loyalty_transaction import (
    LoyaltyTransaction,
    LoyaltyTransactionType,
)
from app.services.loyalty import (
    InvalidLoyaltyPointsAmountError,
    LoyaltyPointsRedemptionLimitError,
    LoyaltyProgramLockedError,
    calculate_balance_from_transactions,
    calculate_earned_points,
    calculate_max_redeemable_points,
    calculate_points_discount,
    calculate_points_expiration,
    validate_points_redemption,
)


def _transaction(
    transaction_id: int,
    amount: int,
    created_at: datetime,
    *,
    expires_at: datetime | None = None,
    transaction_type: LoyaltyTransactionType = LoyaltyTransactionType.ADJUSTMENT,
    order_id: int | None = None,
) -> LoyaltyTransaction:
    return LoyaltyTransaction(
        id=transaction_id,
        user_id=1,
        order_id=order_id,
        type=transaction_type,
        amount=amount,
        created_at=created_at,
        expires_at=expires_at,
    )


def test_calculates_balance_from_non_expiring_transactions() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    transactions = [
        _transaction(1, 150, now),
        _transaction(2, -40, now + timedelta(hours=1)),
    ]

    assert (
        calculate_balance_from_transactions(
            transactions,
            as_of=now + timedelta(hours=2),
        )
        == 110
    )


def test_spends_points_from_oldest_lot_first() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    transactions = [
        _transaction(1, 10, now, expires_at=now + timedelta(days=10)),
        _transaction(2, 20, now, expires_at=now + timedelta(days=20)),
        _transaction(3, -15, now + timedelta(days=5)),
    ]

    assert (
        calculate_balance_from_transactions(
            transactions,
            as_of=now + timedelta(days=11),
        )
        == 15
    )


def test_does_not_include_points_expiring_at_balance_date() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    expires_at = now + timedelta(days=10)
    transactions = [
        _transaction(1, 10, now, expires_at=expires_at),
    ]

    assert calculate_balance_from_transactions(transactions, as_of=expires_at) == 0


def test_ignores_transactions_created_after_balance_date() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    transactions = [
        _transaction(1, 10, now),
        _transaction(2, 20, now + timedelta(days=2)),
    ]

    assert (
        calculate_balance_from_transactions(
            transactions,
            as_of=now + timedelta(days=1),
        )
        == 10
    )


def test_later_credit_first_covers_negative_balance() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    transactions = [
        _transaction(1, -10, now),
        _transaction(2, 6, now + timedelta(days=1)),
    ]

    assert (
        calculate_balance_from_transactions(
            transactions,
            as_of=now + timedelta(days=2),
        )
        == -4
    )


def test_refund_restores_points_to_their_original_fifo_lots() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    transactions = [
        _transaction(
            1,
            10,
            now,
            expires_at=now + timedelta(days=10),
            transaction_type=LoyaltyTransactionType.EARN,
            order_id=1,
        ),
        _transaction(
            2,
            20,
            now + timedelta(days=1),
            expires_at=now + timedelta(days=20),
            transaction_type=LoyaltyTransactionType.EARN,
            order_id=2,
        ),
        _transaction(
            3,
            -15,
            now + timedelta(days=5),
            transaction_type=LoyaltyTransactionType.SPEND,
            order_id=3,
        ),
        _transaction(
            4,
            15,
            now + timedelta(days=6),
            transaction_type=LoyaltyTransactionType.REFUND,
            order_id=3,
        ),
    ]

    assert (
        calculate_balance_from_transactions(
            transactions,
            as_of=now + timedelta(days=11),
        )
        == 20
    )


def test_refund_does_not_reactivate_already_expired_points() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    transactions = [
        _transaction(
            1,
            10,
            now,
            expires_at=now + timedelta(days=10),
            transaction_type=LoyaltyTransactionType.EARN,
            order_id=1,
        ),
        _transaction(
            2,
            -10,
            now + timedelta(days=5),
            transaction_type=LoyaltyTransactionType.SPEND,
            order_id=2,
        ),
        _transaction(
            3,
            10,
            now + timedelta(days=11),
            transaction_type=LoyaltyTransactionType.REFUND,
            order_id=2,
        ),
    ]

    assert (
        calculate_balance_from_transactions(
            transactions,
            as_of=now + timedelta(days=12),
        )
        == 0
    )


@pytest.mark.parametrize(
    ("earned_at", "expected_expiration"),
    [
        (
            datetime(2026, 1, 15, 12, 30, tzinfo=UTC),
            datetime(2027, 1, 15, 12, 30, tzinfo=UTC),
        ),
        (
            datetime(2028, 2, 29, 12, 30, tzinfo=UTC),
            datetime(2029, 2, 28, 12, 30, tzinfo=UTC),
        ),
    ],
)
def test_calculates_points_expiration_after_twelve_months(
    earned_at: datetime,
    expected_expiration: datetime,
) -> None:
    assert calculate_points_expiration(earned_at) == expected_expiration


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
