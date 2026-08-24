import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_factory
from app.models.category import Category
from scripts.seeds.utils import find_image, slugify

PRODUCTS_FILE_PATH = Path("app/assets/mock_products.json")
CATEGORY_IMAGES_DIRECTORY = Path("app/assets/categories/pictures")
CATEGORY_IMAGES_STORAGE_PATH = Path("assets/categories/pictures")


async def seed_categories(
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> None:
    with PRODUCTS_FILE_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    products_data = data.get("products", [])

    async with session_factory() as session:
        category_names = sorted(
            {p.get("category") for p in products_data if p.get("category")}
        )

        for c_name in category_names:
            category = await session.scalar(
                select(Category).where(Category.name == c_name)
            )
            category_image = find_image(
                c_name, CATEGORY_IMAGES_DIRECTORY, CATEGORY_IMAGES_STORAGE_PATH
            )

            if category is None:
                category = Category(
                    name=c_name,
                    slug=slugify(c_name),
                    image=category_image,
                )
                session.add(category)
                await session.flush()
            elif category_image is not None:
                category.image = category_image

        await session.commit()
        print(f"Successfully seeded {len(category_names)} categories.")


if __name__ == "__main__":
    asyncio.run(seed_categories())
