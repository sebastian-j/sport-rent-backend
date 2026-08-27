from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.passwords import hash_password
from app.models import Order, OrderStatus, User
from app.models.order_address import OrderAddress
from tests.support import SeededUser


def order_with_address(
    *,
    user_id: int,
    status: OrderStatus = OrderStatus.PAID,
    created_at: datetime | None = None,
) -> Order:
    return Order(
        user_id=user_id,
        status=status,
        payment_code=uuid4(),
        created_at=created_at,
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


async def test_empty_orders_list_returns_empty_array(
    client: AsyncClient,
    test_user: SeededUser,
) -> None:
    headers = await authorization_headers(client, test_user)

    response = await client.get("/orders", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


async def test_list_orders_returns_user_orders_newest_first(
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
                for index in range(3)
            ]
        )

    headers = await authorization_headers(client, test_user)

    response = await client.get("/orders", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3

    ids = [item["id"] for item in payload]
    assert ids == sorted(ids, reverse=True)

    for item in payload:
        assert item["user_id"] == test_user.id
        assert item["status"] == OrderStatus.PAID.value
        assert item["used_points"] is False
        assert item["total_price"] == 0.0
        assert item["discount"] == 0.0
        assert item["instances"] == []
        assert item["address"]["first_line"] == "Testowa 1"
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
