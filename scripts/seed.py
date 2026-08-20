import asyncio

from app.db.session import engine
from scripts.seeds.seed_favorites import seed_favorites
from scripts.seeds.seed_orders import seed_orders
from scripts.seeds.seed_products import seed_products
from scripts.seeds.seed_subcategories import seed_subcategories
from scripts.seeds.seed_users import seed_users


async def main() -> None:
    try:
        await seed_users()
        await seed_products()
        await seed_favorites()
        await seed_orders()
        await seed_subcategories()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
