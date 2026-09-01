import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_factory
from app.models.category import Category
from app.models.product import (
    Instance,
    InstanceStatus,
    Product,
    ProductImage,
    ProductSize,
)
from scripts.seeds.utils import slugify, unique_slug

PRODUCTS_FILE_PATH = Path("app/assets/mock_products.json")


async def seed_products(
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> None:
    with PRODUCTS_FILE_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    products_data = data.get("products", [])

    async with session_factory() as session:
        category_names = {p.get("category") for p in products_data if p.get("category")}
        category_map: dict[str, Category] = {}

        for c_name in category_names:
            category = await session.scalar(
                select(Category).where(Category.name == c_name)
            )
            if category is None:
                print(
                    f"Warning: category '{c_name}' not found, "
                    "products in this category will have no category_id"
                )
                continue
            category_map[c_name] = category

        taken_slugs = set(await session.scalars(select(Product.slug)))

        for p_data in products_data:
            category_id = None
            if p_data.get("category"):
                category = category_map.get(p_data.get("category"))
                if category is not None:
                    category_id = category.id

            result = await session.execute(
                select(Product).where(Product.id == p_data["id"])
            )
            if result.scalars().first():
                continue

            product_slug = unique_slug(slugify(p_data["name"]), taken_slugs)
            taken_slugs.add(product_slug)

            product = Product(
                id=p_data["id"],
                name=p_data["name"],
                slug=product_slug,
                price=p_data.get("price"),
                description=p_data.get("description"),
                category_id=category_id,
                visibility_status=True,
            )

            images = p_data.get("images", [])
            image_alts = p_data.get("imageAlts", [])
            if len(images) != len(image_alts):
                raise ValueError(
                    f"Product {product_slug} must define one alt per image"
                )

            for i, img_path in enumerate(images):
                product_img = ProductImage(
                    image=img_path,
                    alt_text=image_alts[i],
                    display_order=i,
                )
                product.images.append(product_img)

            sizes = p_data.get("sizes", [])
            for s_data in sizes:
                size = ProductSize(
                    size=s_data["size"],
                    description=s_data.get("description"),
                )
                product.sizes.append(size)

            instance = Instance(
                status=InstanceStatus.AVAILABLE,
                size=sizes[0]["size"] if sizes else None,
            )
            product.instances.append(instance)

            session.add(product)

        await session.commit()
        print(f"Successfully seeded {len(products_data)} products.")


if __name__ == "__main__":
    asyncio.run(seed_products())
