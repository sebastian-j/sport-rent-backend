from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.passwords import hash_password
from app.models import (
    CartItem,
    LoyaltyTransaction,
    LoyaltyTransactionType,
    Order,
    OrderStatus,
    Product,
    User,
)
from app.models.order_address import OrderAddress
from app.models.product import Instance, InstanceStatus
from tests.support import SeededUser

ORDERING_PRODUCT_ID = 9301

ORDER_ADDRESS = {
    "first_name": "Jan",
    "last_name": "Kowalski",
    "first_line": "Testowa 1",
    "postal_code": "30-001",
    "city": "Kraków",
    "country": "Polska",
}
ORDER_RECIPIENT = {"first_name": "Jan", "last_name": "Kowalski"}


def order_with_address(
    *,
    user_id: int,
    status: OrderStatus = OrderStatus.PAID,
    created_at: datetime | None = None,
) -> Order:
    return Order(
        user_id=user_id,
        status=status,
        total_price=Decimal("0.00"),
        payment_code=uuid4(),
        created_at=created_at,
        recipient_first_name="Jan",
        recipient_last_name="Kowalski",
        address=OrderAddress(
            first_name="Jan",
            last_name="Kowalski",
            first_line="Testowa 1",
            city="Kraków",
            postal_code="30-001",
            country="Polska",
        ),
    )


@pytest_asyncio.fixture
async def clean_up_orders(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[None]:
    yield

    async with test_session_factory.begin() as session:
        await session.execute(delete(Order).where(Order.user_id == test_user.id))


@pytest_asyncio.fixture
async def ordering_product(
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[Product]:
    async with test_session_factory.begin() as session:
        product = Product(
            id=ORDERING_PRODUCT_ID,
            name="Rower do testów zamówień",
            description="",
            price=50,
            slug="rower-testowy-orders",
            visibility_status=True,
            instances=[Instance(status=InstanceStatus.AVAILABLE)],
        )
        session.add(product)

    try:
        yield product
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(
                delete(LoyaltyTransaction).where(
                    LoyaltyTransaction.user_id == test_user.id
                )
            )
            await session.execute(delete(Order).where(Order.user_id == test_user.id))
            await session.execute(
                delete(Product).where(Product.id == ORDERING_PRODUCT_ID)
            )


async def add_ordering_product_to_cart(
    client: AsyncClient,
    headers: dict[str, str],
) -> None:
    response = await client.post(
        "/cart/items",
        headers=headers,
        json={
            "product_slug": "rower-testowy-orders",
            "quantity": 1,
            "size": None,
            "start_date": (date.today() + timedelta(days=2)).isoformat(),
            "end_date": (date.today() + timedelta(days=4)).isoformat(),
        },
    )
    assert response.status_code == 201


async def seed_loyalty_checkout_state(
    test_session_factory: async_sessionmaker[AsyncSession],
    user_id: int,
    *,
    qualifying_spend: Decimal = Decimal("500.00"),
    balance: int = 100,
) -> None:
    async with test_session_factory.begin() as session:
        if qualifying_spend > 0:
            session.add(
                Order(
                    user_id=user_id,
                    status=OrderStatus.FINISHED,
                    total_price=qualifying_spend,
                    recipient_first_name="Jan",
                    recipient_last_name="Kowalski",
                )
            )
        if balance != 0:
            session.add(
                LoyaltyTransaction(
                    user_id=user_id,
                    type=LoyaltyTransactionType.ADJUSTMENT,
                    amount=balance,
                )
            )


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


@pytest.mark.parametrize(
    ("query", "invalid_parameter"),
    [
        ({"page": 0}, "page"),
        ({"pageSize": 0}, "pageSize"),
        ({"pageSize": 101}, "pageSize"),
    ],
)
async def test_orders_list_rejects_invalid_pagination(
    client: AsyncClient,
    test_user: SeededUser,
    query: dict[str, int],
    invalid_parameter: str,
) -> None:
    headers = await authorization_headers(client, test_user)

    response = await client.get("/orders", params=query, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == invalid_parameter


async def test_empty_orders_list_returns_empty_page(
    client: AsyncClient,
    test_user: SeededUser,
) -> None:
    headers = await authorization_headers(client, test_user)

    response = await client.get("/orders", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "pageSize": 10,
        "total": 0,
        "totalPages": 0,
    }


async def test_orders_list_returns_requested_page_and_metadata(
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_up_orders: None,
) -> None:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    async with test_session_factory.begin() as session:
        session.add_all(
            [
                order_with_address(
                    user_id=test_user.id,
                    created_at=created_at + timedelta(days=index),
                )
                for index in range(12)
            ]
        )

    headers = await authorization_headers(client, test_user)

    first_response = await client.get(
        "/orders",
        params={"page": 1, "pageSize": 10},
        headers=headers,
    )
    second_response = await client.get(
        "/orders",
        params={"page": 2, "pageSize": 10},
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_page = first_response.json()
    second_page = second_response.json()

    assert len(first_page["items"]) == 10
    assert first_page["page"] == 1
    assert first_page["pageSize"] == 10
    assert first_page["total"] == 12
    assert first_page["totalPages"] == 2

    assert len(second_page["items"]) == 2
    assert second_page["page"] == 2
    assert second_page["pageSize"] == 10
    assert second_page["total"] == 12
    assert second_page["totalPages"] == 2

    first_page_ids = [item["id"] for item in first_page["items"]]
    second_page_ids = [item["id"] for item in second_page["items"]]
    assert not set(first_page_ids) & set(second_page_ids)
    assert first_page_ids == sorted(first_page_ids, reverse=True)
    assert second_page_ids == sorted(second_page_ids, reverse=True)

    for item in first_page["items"]:
        assert item["user_id"] == test_user.id
        assert item["status"] == OrderStatus.PAID.value
        assert item["address"]["city"] == "Kraków"
        assert "created_at" in item


async def test_get_order_returns_details(
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_up_orders: None,
) -> None:
    async with test_session_factory.begin() as session:
        order = order_with_address(user_id=test_user.id)
        session.add(order)
        await session.flush()
        order_id = order.id

    headers = await authorization_headers(client, test_user)

    response = await client.get(f"/orders/{order_id}", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == order_id
    assert payload["user_id"] == test_user.id
    assert payload["status"] == OrderStatus.PAID.value
    assert payload["used_points"] is False
    assert payload["total_price"] == 0.0
    assert payload["discount"] == 0.0
    assert payload["recipient"] == {
        "first_name": "Jan",
        "last_name": "Kowalski",
    }
    assert payload["instances"] == []
    assert payload["address"] == {
        "first_name": "Jan",
        "last_name": "Kowalski",
        "first_line": "Testowa 1",
        "second_line": None,
        "postal_code": "30-001",
        "city": "Kraków",
        "country": "Polska",
        "company": None,
        "nip": None,
    }
    assert "created_at" in payload


async def test_get_order_returns_404_when_missing(
    client: AsyncClient,
    test_user: SeededUser,
) -> None:
    headers = await authorization_headers(client, test_user)

    response = await client.get("/orders/999999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


async def test_get_order_returns_404_for_other_users_order(
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_up_orders: None,
) -> None:
    other_user_id = 9201
    async with test_session_factory.begin() as session:
        session.add(
            User(
                id=other_user_id,
                email="other.orders@example.com",
                password_hash=hash_password("Other-user-password-123!"),
            )
        )
        order = order_with_address(user_id=other_user_id)
        session.add(order)
        await session.flush()
        order_id = order.id

    try:
        headers = await authorization_headers(client, test_user)

        response = await client.get(f"/orders/{order_id}", headers=headers)

        assert response.status_code == 404
        assert response.json()["detail"] == "Order not found"
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(delete(Order).where(Order.id == order_id))
            await session.execute(delete(User).where(User.id == other_user_id))


async def test_creates_order_without_redeeming_points(
    client: AsyncClient,
    test_user: SeededUser,
    ordering_product: Product,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    headers = await authorization_headers(client, test_user)
    await add_ordering_product_to_cart(client, headers)

    response = await client.post(
        "/orders",
        headers=headers,
        json={"recipient": ORDER_RECIPIENT, "address": ORDER_ADDRESS},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == OrderStatus.UNPAID.value
    assert payload["total_price"] == 100.0
    assert payload["discount"] == 0.0
    assert payload["used_points"] is False

    async with test_session_factory() as session:
        order = await session.get(Order, payload["id"])
        assert order is not None
        assert order.total_price == Decimal("100.00")
        assert (
            await session.scalar(
                select(func.count(CartItem.id)).where(CartItem.user_id == test_user.id)
            )
            == 0
        )


async def test_creates_order_with_requested_loyalty_points(
    client: AsyncClient,
    test_user: SeededUser,
    ordering_product: Product,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    headers = await authorization_headers(client, test_user)
    await add_ordering_product_to_cart(client, headers)
    await seed_loyalty_checkout_state(test_session_factory, test_user.id)

    response = await client.post(
        "/orders",
        headers=headers,
        json={
            "recipient": ORDER_RECIPIENT,
            "address": ORDER_ADDRESS,
            "points_to_spend": 20,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["total_price"] == 90.0
    assert payload["discount"] == 10.0
    assert payload["used_points"] is True

    async with test_session_factory() as session:
        order = await session.get(Order, payload["id"])
        transaction = await session.scalar(
            select(LoyaltyTransaction).where(
                LoyaltyTransaction.order_id == payload["id"],
                LoyaltyTransaction.type == LoyaltyTransactionType.SPEND,
            )
        )
        assert order is not None
        assert order.total_price == Decimal("90.00")
        assert transaction is not None
        assert transaction.amount == -20


async def test_rejects_points_before_loyalty_program_unlock(
    client: AsyncClient,
    test_user: SeededUser,
    ordering_product: Product,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    headers = await authorization_headers(client, test_user)
    await add_ordering_product_to_cart(client, headers)
    await seed_loyalty_checkout_state(
        test_session_factory,
        test_user.id,
        qualifying_spend=Decimal("499.99"),
    )

    response = await client.post(
        "/orders",
        headers=headers,
        json={
            "recipient": ORDER_RECIPIENT,
            "address": ORDER_ADDRESS,
            "points_to_spend": 1,
        },
    )

    assert response.status_code == 422
    assert "requires 500.00" in response.json()["detail"]


async def test_rejects_points_above_thirty_percent_order_limit(
    client: AsyncClient,
    test_user: SeededUser,
    ordering_product: Product,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    headers = await authorization_headers(client, test_user)
    await add_ordering_product_to_cart(client, headers)
    await seed_loyalty_checkout_state(test_session_factory, test_user.id)

    response = await client.post(
        "/orders",
        headers=headers,
        json={
            "recipient": ORDER_RECIPIENT,
            "address": ORDER_ADDRESS,
            "points_to_spend": 61,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == ("Maximum redeemable points: 60, requested: 61")


async def test_rejects_points_above_available_balance(
    client: AsyncClient,
    test_user: SeededUser,
    ordering_product: Product,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    headers = await authorization_headers(client, test_user)
    await add_ordering_product_to_cart(client, headers)
    await seed_loyalty_checkout_state(
        test_session_factory,
        test_user.id,
        balance=10,
    )

    response = await client.post(
        "/orders",
        headers=headers,
        json={
            "recipient": ORDER_RECIPIENT,
            "address": ORDER_ADDRESS,
            "points_to_spend": 20,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Insufficient loyalty points: available 10, requested 20"
    )
