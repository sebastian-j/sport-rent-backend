from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Product, ProductAccessory


class ProductNotFoundError(ValueError):
    pass


async def get_suggested_accessories(
    session: AsyncSession,
    product_slug: str,
) -> list[Product]:
    product_id = await session.scalar(
        select(Product.id).where(
            Product.slug == product_slug,
            Product.visibility_status.is_(True),
        )
    )
    if product_id is None:
        raise ProductNotFoundError(f"Product {product_slug!r} not found")

    accessories = await session.scalars(
        select(Product)
        .join(
            ProductAccessory,
            ProductAccessory.accessory_id == Product.id,
        )
        .options(
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.manufacturer),
            selectinload(Product.sizes),
        )
        .where(
            ProductAccessory.product_id == product_id,
            Product.visibility_status.is_(True),
        )
        .order_by(ProductAccessory.display_order, Product.id)
    )
    return list(accessories.unique())
