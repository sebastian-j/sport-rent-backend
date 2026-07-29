from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.models.product import Favorite, Product
from app.schemas.favorites import FavoritesResponse

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoritesResponse])
async def get_favorites(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
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


@router.post("/{product_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def add_to_favorites(
    product_slug: str,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    product = await session.scalar(select(Product).where(Product.slug == product_slug))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if await session.scalar(
        select(Favorite).where(
            Favorite.user_id == user_id, Favorite.product_slug == product.slug
        )
    ):
        return

    favorite = Favorite(user_id=user_id, product_slug=product.slug)
    session.add(favorite)
    await session.commit()


@router.delete("/{product_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_favorites(
    product_slug: str,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    product = await session.scalar(select(Product).where(Product.slug == product_slug))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    favorite = await session.scalar(
        select(Favorite).where(
            Favorite.user_id == user_id, Favorite.product_slug == product.slug
        )
    )
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    await session.delete(favorite)
    await session.commit()
