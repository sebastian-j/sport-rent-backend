from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Product, ProductAccessory

SOURCE_SLUG = "accessory-test-source"
FIRST_ACCESSORY_SLUG = "accessory-test-first"
SECOND_ACCESSORY_SLUG = "accessory-test-second"
HIDDEN_ACCESSORY_SLUG = "accessory-test-hidden"
TEST_SLUGS = {
    SOURCE_SLUG,
    FIRST_ACCESSORY_SLUG,
    SECOND_ACCESSORY_SLUG,
    HIDDEN_ACCESSORY_SLUG,
}


@pytest_asyncio.fixture
async def accessory_products(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[None]:
    async with test_session_factory.begin() as session:
        await session.execute(delete(Product).where(Product.slug.in_(TEST_SLUGS)))
        source = Product(
            name="Test source",
            slug=SOURCE_SLUG,
            price=100,
            visibility_status=True,
        )
        first_accessory = Product(
            name="First accessory",
            slug=FIRST_ACCESSORY_SLUG,
            price=10,
            visibility_status=True,
        )
        second_accessory = Product(
            name="Second accessory",
            slug=SECOND_ACCESSORY_SLUG,
            price=20,
            visibility_status=True,
        )
        hidden_accessory = Product(
            name="Hidden accessory",
            slug=HIDDEN_ACCESSORY_SLUG,
            price=30,
            visibility_status=False,
        )
        session.add_all([source, first_accessory, second_accessory, hidden_accessory])
        await session.flush()
        session.add_all(
            [
                ProductAccessory(
                    product_id=source.id,
                    accessory_id=second_accessory.id,
                    display_order=1,
                ),
                ProductAccessory(
                    product_id=source.id,
                    accessory_id=first_accessory.id,
                    display_order=0,
                ),
                ProductAccessory(
                    product_id=source.id,
                    accessory_id=hidden_accessory.id,
                    display_order=2,
                ),
            ]
        )

    try:
        yield
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(delete(Product).where(Product.slug.in_(TEST_SLUGS)))


async def test_product_accessories_are_visible_and_ordered(
    client: AsyncClient,
    accessory_products: None,
) -> None:
    response = await client.get(f"/product/{SOURCE_SLUG}/accessories")

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()] == [
        FIRST_ACCESSORY_SLUG,
        SECOND_ACCESSORY_SLUG,
    ]


async def test_product_accessories_return_not_found_for_unknown_product(
    client: AsyncClient,
) -> None:
    response = await client.get("/product/unknown-product/accessories")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}
