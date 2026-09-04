from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Favorite, Product
from app.schemas.favorites import FavoritesResponse


class ProductNotFoundError(LookupError):
    pass


class FavoriteNotFoundError(LookupError):
    pass


async def get_favorites(session: AsyncSession, user_id: int) -> list[FavoritesResponse]:
    favorites = (
        await session.scalars(
            select(Favorite)
            .options(selectinload(Favorite.product).selectinload(Product.images))
            .where(Favorite.user_id == user_id)
        )
    ).all()

    response = []
    for fav in favorites:
        product = fav.product

        first_image = None
        if product.images:
            first_image = min(product.images, key=lambda i: i.display_order)

        response.append(
            FavoritesResponse(
                slug=product.slug,
                name=product.name,
                description=product.description or "",
                image=first_image.image if first_image else "",
                alt=first_image.alt_text if first_image else "",
                price=product.price,
            )
        )
    return response


async def add_to_favorites(
    session: AsyncSession, user_id: int, product_slug: str
) -> None:
    product = await session.scalar(select(Product).where(Product.slug == product_slug))
    if not product:
        raise ProductNotFoundError("Product not found")

    if await session.scalar(
        select(Favorite).where(
            Favorite.user_id == user_id, Favorite.product_slug == product.slug
        )
    ):
        return

    favorite = Favorite(user_id=user_id, product_slug=product.slug)
    session.add(favorite)
    await session.commit()


async def remove_from_favorites(
    session: AsyncSession, user_id: int, product_slug: str
) -> None:
    product = await session.scalar(select(Product).where(Product.slug == product_slug))
    if not product:
        raise ProductNotFoundError("Product not found")

    favorite = await session.scalar(
        select(Favorite).where(
            Favorite.user_id == user_id, Favorite.product_slug == product.slug
        )
    )
    if not favorite:
        raise FavoriteNotFoundError("Favorite not found")

    await session.delete(favorite)
    await session.commit()
