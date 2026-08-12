from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Product


@pytest_asyncio.fixture
async def empty_product_database(
    empty_auth_database: None,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[None]:
    async with test_session_factory.begin() as session:
        await session.execute(delete(Product))

    yield

    async with test_session_factory.begin() as session:
        await session.execute(delete(Product))


async def test_empty_product_facets(
    client: AsyncClient,
    empty_product_database: None,
) -> None:
    response = await client.get("/product/count")

    assert response.status_code == 200
    assert response.json() == {
        "categories": [],
        "total": 0,
        "price": {
            "min": 0,
            "max": 0,
        },
    }


async def test_product_facets_return_minimum_and_maximum_visible_price(
    client: AsyncClient,
    empty_product_database: None,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory.begin() as session:
        session.add_all(
            [
                Product(
                    name="Najtańszy produkt",
                    slug="najtanszy-produkt-facets",
                    price=18,
                    visibility_status=True,
                ),
                Product(
                    name="Produkt pośredni",
                    slug="produkt-posredni-facets",
                    price=50,
                    visibility_status=True,
                ),
                Product(
                    name="Najdroższy produkt",
                    slug="najdrozszy-produkt-facets",
                    price=179,
                    visibility_status=True,
                ),
                Product(
                    name="Ukryty produkt",
                    slug="ukryty-produkt-facets",
                    price=999,
                    visibility_status=False,
                ),
            ]
        )

    response = await client.get("/product/count")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["price"] == {
        "min": 18,
        "max": 179,
    }
