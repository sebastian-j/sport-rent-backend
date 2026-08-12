from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Order, OrderStatus
from tests.support import SeededUser


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


@pytest.mark.parametrize(
    ("query", "invalid_parameter"),
    [
        ({"page": 0}, "page"),
        ({"pageSize": 0}, "pageSize"),
        ({"pageSize": 101}, "pageSize"),
    ],
)
async def test_user_history_rejects_invalid_pagination(
    client: AsyncClient,
    test_user: SeededUser,
    query: dict[str, int],
    invalid_parameter: str,
) -> None:
    headers = await authorization_headers(client, test_user)

    response = await client.get("/user/history", params=query, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == invalid_parameter


async def test_empty_user_history_returns_empty_page(
    client: AsyncClient,
    test_user: SeededUser,
) -> None:
    headers = await authorization_headers(client, test_user)

    response = await client.get("/user/history", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "pageSize": 10,
        "total": 0,
        "totalPages": 0,
    }


async def test_user_history_returns_requested_page_and_metadata(
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    clean_up_orders: None,
) -> None:
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    async with test_session_factory.begin() as session:
        session.add_all(
            [
                Order(
                    user_id=test_user.id,
                    status=OrderStatus.PAID,
                    created_at=created_at + timedelta(days=index),
                )
                for index in range(12)
            ]
        )

    headers = await authorization_headers(client, test_user)

    first_response = await client.get(
        "/user/history",
        params={"page": 1, "pageSize": 10},
        headers=headers,
    )
    second_response = await client.get(
        "/user/history",
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
