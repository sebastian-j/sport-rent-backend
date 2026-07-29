import asyncio
import random

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.product import Favorite, Product
from app.models.user import User


async def seed_favorites():
    async with async_session_factory() as session:
        result_users = await session.execute(select(User).limit(10))
        users = result_users.scalars().all()

        result_products = await session.execute(select(Product).limit(20))
        products = result_products.scalars().all()

        if not users or not products:
            print("You need at least 1 product and 1 user in the database.")
            return

        favorites_added = 0
        for user in users:
            k = min(random.randint(2, 5), len(products))
            fav_products = random.sample(products, k)

            for prod in fav_products:
                existing = await session.execute(
                    select(Favorite).where(
                        Favorite.user_id == user.id, Favorite.product_slug == prod.slug
                    )
                )
                if not existing.scalars().first():
                    fav = Favorite(user_id=user.id, product_slug=prod.slug)
                    session.add(fav)
                    favorites_added += 1

        await session.commit()
        print(f"Successfully seeded {favorites_added} records in the favorites table.")


if __name__ == "__main__":
    asyncio.run(seed_favorites())
