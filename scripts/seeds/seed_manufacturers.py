import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_factory
from app.models.manufacturer import Manufacturer
from app.models.product import Product
from scripts.seeds.utils import slugify

PRODUCTS_FILE_PATH = Path("app/assets/mock_products.json")


async def seed_manufacturers(
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> None:
    with PRODUCTS_FILE_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    products_data = data.get("products", [])

    async with session_factory() as session:
        manufacturer_names = sorted(
            {p["manufacturer"] for p in products_data if p.get("manufacturer")}
        )
        manufacturer_map: dict[str, Manufacturer] = {}

        for name in manufacturer_names:
            manufacturer = await session.scalar(
                select(Manufacturer).where(Manufacturer.name == name)
            )
            if manufacturer is None:
                manufacturer = Manufacturer(name=name, slug=slugify(name))
                session.add(manufacturer)
                await session.flush()
            manufacturer_map[name] = manufacturer

        updated = 0
        for p_data in products_data:
            manufacturer_name = p_data.get("manufacturer")
            if not manufacturer_name or manufacturer_name not in manufacturer_map:
                continue

            product = await session.scalar(
                select(Product).where(Product.id == p_data["id"])
            )
            if product is not None and product.manufacturer_id is None:
                product.manufacturer_id = manufacturer_map[manufacturer_name].id
                updated += 1

        await session.commit()
        print(f"Successfully seeded {len(manufacturer_names)} manufacturers.")
        print(f"Assigned manufacturers to {updated} products.")


if __name__ == "__main__":
    asyncio.run(seed_manufacturers())
