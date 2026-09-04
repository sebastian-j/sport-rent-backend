import asyncio

from app.db.session import engine
from scripts.seeds.seed_categories import seed_categories
from scripts.seeds.seed_favorites import seed_favorites
from scripts.seeds.seed_loyalty_transactions import seed_loyalty_transactions
from scripts.seeds.seed_manufacturers import seed_manufacturers
from scripts.seeds.seed_orders import seed_orders
from scripts.seeds.seed_product_accessories import seed_product_accessories
from scripts.seeds.seed_products import seed_products
from scripts.seeds.seed_subcategories import seed_subcategories
from scripts.seeds.seed_users import seed_users


async def main() -> None:
    try:
        await seed_users()
        await seed_categories()
        await seed_loyalty_transactions()
        await seed_products()
        await seed_manufacturers()
        await seed_product_accessories()
        await seed_subcategories()
        await seed_favorites()
        await seed_orders()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
