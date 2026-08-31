from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    LoyaltyTransaction,
    LoyaltyTransactionType,
    Order,
    OrderStatus,
)
from app.services.loyalty import (
    MAX_LOYALTY_POINTS_AMOUNT,
    InsufficientLoyaltyPointsError,
    InvalidLoyaltyPointsAmountError,
    apply_loyalty_for_cancelled_order,
    apply_loyalty_for_paid_order,
    earn_points,
    get_balance,
    get_lifetime_qualifying_spend,
    spend_points,
)
from tests.support import SeededUser


@pytest_asyncio.fixture
async def clean_loyalty_transactions(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[None]:
    async def clear_loyalty_data() -> None:
        async with test_session_factory.begin() as session:
            await session.execute(
                delete(LoyaltyTransaction).where(
                    LoyaltyTransaction.user_id == test_user.id
                )
            )
            await session.execute(delete(Order).where(Order.user_id == test_user.id))

    await clear_loyalty_data()

    try:
        yield
    finally:
        await clear_loyalty_data()


async def authorization_headers(
    client: AsyncClient,
    user: SeededUser,
) -> dict[str, str]:
    response = await client.post(
        "/auth/login",
        json={"email": user.email, "password": user.password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_loyalty_balance_uses_current_user_transactions(
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        session.add_all(
            [
                LoyaltyTransaction(
                    user_id=test_user.id,
                    type=LoyaltyTransactionType.ADJUSTMENT,
                    amount=150,
                ),
                LoyaltyTransaction(
                    user_id=test_user.id,
                    type=LoyaltyTransactionType.ADJUSTMENT,
                    amount=-40,
                ),
            ]
        )

    response = await client.get(
        "/loyalty",
        headers=await authorization_headers(client, test_user),
    )

    assert response.status_code == 200
    assert response.json() == {"balance": 110}


async def test_empty_loyalty_history_returns_empty_page(
    client: AsyncClient,
    test_user: SeededUser,
    clean_loyalty_transactions: None,
) -> None:
    response = await client.get(
        "/loyalty/history",
        headers=await authorization_headers(client, test_user),
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "balance": 0,
        "page": 1,
        "pageSize": 10,
        "total": 0,
        "totalPages": 0,
    }


async def test_loyalty_history_returns_requested_page_and_metadata(
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    async with test_session_factory.begin() as session:
        session.add_all(
            [
                LoyaltyTransaction(
                    user_id=test_user.id,
                    type=LoyaltyTransactionType.ADJUSTMENT,
                    amount=index + 1,
                    description=f"Adjustment {index + 1}",
                    created_at=created_at + timedelta(days=index),
                )
                for index in range(12)
            ]
        )

    headers = await authorization_headers(client, test_user)
    first_response = await client.get(
        "/loyalty/history",
        params={"page": 1, "pageSize": 10},
        headers=headers,
    )
    second_response = await client.get(
        "/loyalty/history",
        params={"page": 2, "pageSize": 10},
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_page = first_response.json()
    second_page = second_response.json()
    assert len(first_page["items"]) == 10
    assert first_page["balance"] == 78
    assert first_page["total"] == 12
    assert first_page["totalPages"] == 2
    assert len(second_page["items"]) == 2
    assert second_page["page"] == 2
    assert second_page["balance"] == 78

    first_page_ids = [item["id"] for item in first_page["items"]]
    second_page_ids = [item["id"] for item in second_page["items"]]
    assert not set(first_page_ids) & set(second_page_ids)
    assert first_page_ids == sorted(first_page_ids, reverse=True)
    assert second_page_ids == sorted(second_page_ids, reverse=True)


@pytest.mark.parametrize(
    ("query", "invalid_parameter"),
    [
        ({"page": 0}, "page"),
        ({"pageSize": 0}, "pageSize"),
        ({"pageSize": 101}, "pageSize"),
    ],
)
async def test_loyalty_history_rejects_invalid_pagination(
    client: AsyncClient,
    test_user: SeededUser,
    query: dict[str, int],
    invalid_parameter: str,
) -> None:
    response = await client.get(
        "/loyalty/history",
        params=query,
        headers=await authorization_headers(client, test_user),
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == invalid_parameter


async def test_spend_points_creates_negative_transaction(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.PAID,
            total_price=Decimal("0.00"),
        )
        session.add_all(
            [
                order,
                LoyaltyTransaction(
                    user_id=test_user.id,
                    type=LoyaltyTransactionType.ADJUSTMENT,
                    amount=100,
                ),
            ]
        )
        await session.flush()
        transaction = await spend_points(
            session,
            test_user.id,
            order.id,
            60,
            description="Payment for order",
        )

    assert transaction.type is LoyaltyTransactionType.SPEND
    assert transaction.amount == -60

    async with test_session_factory() as session:
        assert await get_balance(session, test_user.id) == 40


async def test_earn_points_creates_positive_transaction(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.PAID,
            total_price=Decimal("0.00"),
        )
        session.add(order)
        await session.flush()
        transaction = await earn_points(
            session,
            test_user.id,
            order.id,
            75,
            description="Points for order",
        )

    assert transaction.type is LoyaltyTransactionType.EARN
    assert transaction.amount == 75

    async with test_session_factory() as session:
        assert await get_balance(session, test_user.id) == 75


async def test_loyalty_history_survives_order_deletion(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.PAID,
            total_price=Decimal("0.00"),
        )
        session.add(order)
        await session.flush()
        transaction = await earn_points(
            session,
            test_user.id,
            order.id,
            100,
            description="Points for deleted order",
        )
        order_id = order.id
        transaction_id = transaction.id

    async with test_session_factory.begin() as session:
        await session.execute(delete(Order).where(Order.id == order_id))

    async with test_session_factory() as session:
        transaction = await session.get(LoyaltyTransaction, transaction_id)
        assert transaction is not None
        assert transaction.order_id is None
        assert await get_balance(session, test_user.id) == 100


@pytest.mark.parametrize(
    ("amount", "expected_message"),
    [
        (True, "Loyalty points amount must be an integer"),
        (1.5, "Loyalty points amount must be an integer"),
        ("100", "Loyalty points amount must be an integer"),
        (0, "Loyalty points amount must be positive"),
        (-1, "Loyalty points amount must be positive"),
        (
            MAX_LOYALTY_POINTS_AMOUNT + 1,
            f"Loyalty points amount must not exceed {MAX_LOYALTY_POINTS_AMOUNT}",
        ),
    ],
)
async def test_earn_points_rejects_invalid_amount(
    test_session_factory: async_sessionmaker[AsyncSession],
    amount: object,
    expected_message: str,
) -> None:
    async with test_session_factory() as session:
        with pytest.raises(InvalidLoyaltyPointsAmountError) as exception_info:
            await earn_points(session, 1, 1, amount)  # type: ignore[arg-type]

    assert str(exception_info.value) == expected_message


async def test_earn_points_accepts_maximum_integer_amount(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.PAID,
            total_price=Decimal("0.00"),
        )
        session.add(order)
        await session.flush()
        transaction = await earn_points(
            session,
            test_user.id,
            order.id,
            MAX_LOYALTY_POINTS_AMOUNT,
        )

    assert transaction.amount == MAX_LOYALTY_POINTS_AMOUNT


async def test_spend_points_rejects_amount_above_balance(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.PAID,
            total_price=Decimal("0.00"),
        )
        session.add_all(
            [
                order,
                LoyaltyTransaction(
                    user_id=test_user.id,
                    type=LoyaltyTransactionType.ADJUSTMENT,
                    amount=40,
                ),
            ]
        )

    async with test_session_factory() as session:
        with pytest.raises(InsufficientLoyaltyPointsError) as exception_info:
            await spend_points(session, test_user.id, order.id, 50)
        await session.rollback()

    assert exception_info.value.available == 40
    assert exception_info.value.requested == 50

    async with test_session_factory() as session:
        assert await get_balance(session, test_user.id) == 40


async def test_lifetime_qualifying_spend_uses_only_completed_payments(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        session.add_all(
            [
                Order(
                    user_id=test_user.id,
                    status=status,
                    total_price=total_price,
                )
                for status, total_price in (
                    (OrderStatus.PAID, Decimal("100.00")),
                    (OrderStatus.GIVEN_OUT, Decimal("150.00")),
                    (OrderStatus.FINISHED, Decimal("250.00")),
                    (OrderStatus.PENDING, Decimal("1000.00")),
                    (OrderStatus.UNPAID, Decimal("1000.00")),
                    (OrderStatus.CANCELLED, Decimal("1000.00")),
                )
            ]
        )

    async with test_session_factory() as session:
        total = await get_lifetime_qualifying_spend(session, test_user.id)

    assert total == Decimal("500.00")


@pytest.mark.parametrize(
    ("total_price", "expected_points"),
    [
        (Decimal("9.99"), 0),
        (Decimal("10.00"), 1),
        (Decimal("475.00"), 47),
    ],
)
async def test_applies_loyalty_points_for_paid_order_total(
    total_price: Decimal,
    expected_points: int,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.PAID,
            total_price=total_price,
        )
        session.add(order)
        await session.flush()

        transaction = await apply_loyalty_for_paid_order(session, order)

        if expected_points == 0:
            assert transaction is None
        else:
            assert transaction is not None
            assert transaction.type is LoyaltyTransactionType.EARN
            assert transaction.amount == expected_points

    async with test_session_factory() as session:
        assert await get_balance(session, test_user.id) == expected_points


async def test_apply_loyalty_for_paid_order_is_idempotent(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.PAID,
            total_price=Decimal("100.00"),
        )
        session.add(order)
        await session.flush()

        first_transaction = await apply_loyalty_for_paid_order(session, order)
        second_transaction = await apply_loyalty_for_paid_order(session, order)

        assert first_transaction is not None
        assert second_transaction is not None
        assert second_transaction.id == first_transaction.id

    async with test_session_factory() as session:
        assert await get_balance(session, test_user.id) == 10


async def test_rejects_applying_loyalty_to_unpaid_order(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.UNPAID,
            total_price=Decimal("100.00"),
        )
        session.add(order)
        await session.flush()

        with pytest.raises(
            ValueError,
            match="Loyalty can only be applied to a paid order",
        ):
            await apply_loyalty_for_paid_order(session, order)


async def test_cancelled_order_refunds_spent_and_reverses_earned_points(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.CANCELLED,
            total_price=Decimal("100.00"),
        )
        order.loyalty_transactions.extend(
            [
                LoyaltyTransaction(
                    user_id=test_user.id,
                    type=LoyaltyTransactionType.SPEND,
                    amount=-20,
                ),
                LoyaltyTransaction(
                    user_id=test_user.id,
                    type=LoyaltyTransactionType.EARN,
                    amount=10,
                ),
            ]
        )
        session.add(order)
        await session.flush()

        first_result = await apply_loyalty_for_cancelled_order(session, order)
        second_result = await apply_loyalty_for_cancelled_order(session, order)

        assert [
            (transaction.type, transaction.amount) for transaction in first_result
        ] == [
            (LoyaltyTransactionType.REFUND, 20),
            (LoyaltyTransactionType.REVERSAL, -10),
        ]
        assert [transaction.id for transaction in second_result] == [
            transaction.id for transaction in first_result
        ]

    async with test_session_factory() as session:
        assert await get_balance(session, test_user.id) == 0


async def test_cancelled_order_without_loyalty_transactions_has_no_effects(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.CANCELLED,
            total_price=Decimal("100.00"),
        )
        session.add(order)
        await session.flush()

        assert await apply_loyalty_for_cancelled_order(session, order) == []


async def test_rejects_reversing_loyalty_for_non_cancelled_order(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_loyalty_transactions: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = Order(
            user_id=test_user.id,
            status=OrderStatus.PAID,
            total_price=Decimal("100.00"),
        )
        session.add(order)
        await session.flush()

        with pytest.raises(
            ValueError,
            match="Loyalty can only be reversed for a cancelled order",
        ):
            await apply_loyalty_for_cancelled_order(session, order)
