from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Category, Product
from seed_products import seed_products


async def test_seed_products_assigns_images_matching_category_names(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory.begin() as session:
        await session.execute(delete(Product))
        await session.execute(delete(Category))
        session.add(
            Category(
                name="Rowery i akcesoria",
                slug="rowery-i-akcesoria",
                image=None,
            )
        )

    try:
        await seed_products(test_session_factory)

        async with test_session_factory() as session:
            categories = list(
                await session.scalars(select(Category).order_by(Category.slug))
            )
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(delete(Product))
            await session.execute(delete(Category))

    images_by_slug = {category.slug: category.image for category in categories}

    assert images_by_slug == {
        "namioty": None,
        "namioty-osobowe": ("assets/categories/pictures/namioty-osobowe.png"),
        "nosidelka-turystyczne": (
            "assets/categories/pictures/nosidelka-turystyczne.png"
        ),
        "przyczepki-rowerowe": ("assets/categories/pictures/przyczepki-rowerowe.png"),
        "rowery-i-akcesoria": ("assets/categories/pictures/rowery-i-akcesoria.png"),
        "sprzet-wodny": "assets/categories/pictures/sprzet-wodny.png",
        "via-ferraty-i-wspinanie": (
            "assets/categories/pictures/via-ferraty-i-wspinanie.png"
        ),
    }
