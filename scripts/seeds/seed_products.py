import asyncio
import json
import re
import unicodedata
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

PRODUCTS_FILE_PATH = Path("app/assets/mock_products.json")
CATEGORY_IMAGES_DIRECTORY = Path("app/assets/categories/pictures")
CATEGORY_IMAGES_STORAGE_PATH = Path("assets/categories/pictures")


def slugify(text: str) -> str:
    text = text.translate(str.maketrans({"ł": "l", "Ł": "L"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def find_category_image(category_name: str) -> str | None:
    if not CATEGORY_IMAGES_DIRECTORY.is_dir():
        return None

    category_slug = slugify(category_name)
    matching_images = sorted(
        path
        for path in CATEGORY_IMAGES_DIRECTORY.iterdir()
        if path.is_file() and slugify(path.stem) == category_slug
    )

    if not matching_images:
        return None

    return (CATEGORY_IMAGES_STORAGE_PATH / matching_images[0].name).as_posix()


async def seed_products(
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> None:
    with PRODUCTS_FILE_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    products_data = data.get("products", [])

    async with session_factory() as session:
        category_names = sorted(
            {p.get("category") for p in products_data if p.get("category")}
        )
        category_map = {}

        for c_name in category_names:
            category = await session.scalar(
                select(Category).where(Category.name == c_name)
            )
            category_image = find_category_image(c_name)

            if category is None:
                category = Category(
                    name=c_name,
                    slug=slugify(c_name),
                    image=category_image,
                )
                session.add(category)
                await session.flush()  # to get id
            elif category_image is not None:
                category.image = category_image

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
            image_alts = p_data.get("imageAlts", [])
            if len(images) != len(image_alts):
                raise ValueError(
                    f"Product {p_data['slug']} must define one alt per image"
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
