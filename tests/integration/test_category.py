from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Category


async def test_random_category_returns_category_with_image(
    client: AsyncClient,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    categories = (
        Category(
            name="Rowery",
            slug="rowery",
            image="missing/rowery.jpg",
        ),
        Category(
            name="Namioty",
            slug="namioty",
            image="missing/namioty.jpg",
        ),
        Category(
            name="Bez zdjęcia",
            slug="bez-zdjecia",
            image=None,
        ),
    )

    async with test_session_factory.begin() as session:
        session.add_all(categories)

    try:
        response = await client.get("/categories/random")
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(delete(Category))

    assert response.status_code == 200
    assert response.json() in (
        {
            "name": "Rowery",
            "image": "missing/rowery.jpg",
            "slug": "rowery",
            "subcategories": [],
        },
        {
            "name": "Namioty",
            "image": "missing/namioty.jpg",
            "slug": "namioty",
            "subcategories": [],
        },
    )


async def test_random_category_returns_not_found_without_category_images(
    client: AsyncClient,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory.begin() as session:
        session.add(
            Category(
                name="Bez zdjęcia",
                slug="bez-zdjecia",
                image=None,
            )
        )

    try:
        response = await client.get("/categories/random")
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(delete(Category))

    assert response.status_code == 404
    assert response.json() == {"detail": "No categories with images found"}
