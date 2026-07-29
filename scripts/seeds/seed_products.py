import asyncio
import json
import re
import unicodedata

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.product import Category, Product, ProductImage, ProductSize


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


async def seed_products():
    with open("../../app/assets/mock_products.json", encoding="utf-8") as f:
        data = json.load(f)

    products_data = data.get("products", [])

    async with async_session_factory() as session:
        category_names = list(
            set(p.get("category") for p in products_data if p.get("category"))
        )
        category_map = {}

        for c_name in category_names:
            result = await session.execute(
                select(Category).where(Category.name == c_name)
            )
            category = result.scalars().first()
            if not category:
                category = Category(name=c_name, slug=slugify(c_name))
                session.add(category)
                await session.flush()  # to get id
            category_map[c_name] = category

        for p_data in products_data:
            category_id = None
            if p_data.get("category"):
                category_id = category_map[p_data.get("category")].id

            result = await session.execute(
                select(Product).where(Product.id == p_data["id"])
            )
            if result.scalars().first():
                continue

            product = Product(
                id=p_data["id"],
                name=p_data["name"],
                slug=p_data["slug"],
                price=p_data.get("price"),
                description=p_data.get("description"),
                category_id=category_id,
                visibility_status=True,
            )

            images = p_data.get("images", [])
            alt = p_data.get("alt")
            for i, img_path in enumerate(images):
                product_img = ProductImage(
                    image=img_path, alt_text=alt, display_order=i
                )
                product.images.append(product_img)

            sizes = p_data.get("sizes", [])
            for s_data in sizes:
                size = ProductSize(
                    size=s_data["size"],
                    description=s_data.get("description"),
                )
                product.sizes.append(size)

            session.add(product)

        await session.commit()
        print(f"Successfully seeded {len(products_data)} products.")


if __name__ == "__main__":
    asyncio.run(seed_products())
