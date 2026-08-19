import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_factory
from app.models.category import Category
from app.models.product import Product
from app.models.subcategory import Subcategory
from scripts.seeds.utils import find_image, slugify

PRODUCTS_FILE_PATH = Path("app/assets/mock_products.json")
SUBCATEGORY_IMAGES_DIRECTORY = Path("app/assets/subcategories/pictures")
SUBCATEGORY_IMAGES_STORAGE_PATH = Path("assets/subcategories/pictures")

EXTRA_SUBCATEGORIES = [
    ("Namioty na hak", "Namioty"),
    ("Sanki śnieżne", "Via ferraty i wspinanie"),
    ("Narty skiturowe", "Via ferraty i wspinanie"),
    ("Sprzęt lawinowy", "Via ferraty i wspinanie"),
]


async def seed_subcategories(
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> None:
    with PRODUCTS_FILE_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    products_data = data.get("products", [])

    async with session_factory() as session:
        subcategory_entries = {
            (p["subcategory"], p["category"])
            for p in products_data
            if p.get("subcategory") and p.get("category")
        }
        subcategory_entries.update(EXTRA_SUBCATEGORIES)

        for sc_name, c_name in sorted(subcategory_entries):
            category = await session.scalar(
                select(Category).where(Category.name == c_name)
            )
            if category is None:
                print(
                    f"Warning: category '{c_name}' not found, "
                    f"skipping subcategory '{sc_name}'"
                )
                continue

            subcategory = await session.scalar(
                select(Subcategory).where(
                    Subcategory.name == sc_name,
                    Subcategory.category_id == category.id,
                )
            )
            subcategory_image = find_image(
                sc_name, SUBCATEGORY_IMAGES_DIRECTORY, SUBCATEGORY_IMAGES_STORAGE_PATH
            )

            if subcategory is None:
                subcategory = Subcategory(
                    name=sc_name,
                    slug=slugify(sc_name),
                    category_id=category.id,
                    image=subcategory_image,
                )
                session.add(subcategory)
                await session.flush()
            elif subcategory_image is not None:
                subcategory.image = subcategory_image

        await session.flush()

        subcategory_map: dict[str, Subcategory] = {}
        for sc_name, _ in subcategory_entries:
            sc = await session.scalar(
                select(Subcategory).where(Subcategory.name == sc_name)
            )
            if sc is not None:
                subcategory_map[sc_name] = sc

        updated = 0
        for p_data in products_data:
            sc_name = p_data.get("subcategory")
            if not sc_name or sc_name not in subcategory_map:
                continue

            product = await session.scalar(
                select(Product).where(Product.slug == p_data["slug"])
            )
            if product is not None and product.subcategory_id is None:
                product.subcategory_id = subcategory_map[sc_name].id
                updated += 1

        await session.commit()
        print(f"Successfully seeded {len(subcategory_entries)} subcategories.")
        print(f"Assigned subcategories to {updated} products.")


if __name__ == "__main__":
    asyncio.run(seed_subcategories())
