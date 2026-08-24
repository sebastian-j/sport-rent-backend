import json

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Product, ProductAccessory
from scripts.seeds.seed_product_accessories import (
    ACCESSORY_SLUGS_BY_PRODUCT,
    seed_product_accessories,
)
from scripts.seeds.seed_products import PRODUCTS_FILE_PATH


def test_mock_product_accessory_suggestions_reference_existing_products() -> None:
    with PRODUCTS_FILE_PATH.open(encoding="utf-8") as products_file:
        product_slugs = {
            product["slug"] for product in json.load(products_file)["products"]
        }

    assert set(ACCESSORY_SLUGS_BY_PRODUCT) <= product_slugs
    for product_slug, accessory_slugs in ACCESSORY_SLUGS_BY_PRODUCT.items():
        assert accessory_slugs
        assert len(accessory_slugs) == len(set(accessory_slugs))
        assert product_slug not in accessory_slugs
        assert set(accessory_slugs) <= product_slugs


async def test_seed_product_accessories_adds_links_and_is_idempotent(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    all_slugs = set(ACCESSORY_SLUGS_BY_PRODUCT)
    for accessory_slugs in ACCESSORY_SLUGS_BY_PRODUCT.values():
        all_slugs.update(accessory_slugs)

    async with test_session_factory.begin() as session:
        await session.execute(delete(Product).where(Product.slug.in_(all_slugs)))
        session.add_all(
            [
                Product(
                    name=slug,
                    slug=slug,
                    price=1,
                    visibility_status=True,
                )
                for slug in sorted(all_slugs)
            ]
        )

    try:
        first_result = await seed_product_accessories(test_session_factory)
        second_result = await seed_product_accessories(test_session_factory)

        expected_count = sum(
            len(accessory_slugs)
            for accessory_slugs in ACCESSORY_SLUGS_BY_PRODUCT.values()
        )
        assert first_result == expected_count
        assert second_result == 0

        async with test_session_factory() as session:
            link_count = await session.scalar(
                select(func.count()).select_from(ProductAccessory)
            )
        assert link_count == expected_count
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(delete(Product).where(Product.slug.in_(all_slugs)))
