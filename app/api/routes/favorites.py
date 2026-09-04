from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.schemas.favorites import FavoritesResponse
from app.services import favorites as favorites_service

router = APIRouter(prefix="/favorites", tags=["favorites"])

CurrentUser = Annotated[int, Depends(get_current_user_id)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def not_found(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.get("", response_model=list[FavoritesResponse])
async def get_favorites(
    user_id: CurrentUser,
    session: DatabaseSession,
):
    return await favorites_service.get_favorites(session, user_id)


@router.post("/{product_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def add_to_favorites(
    product_slug: str,
    user_id: CurrentUser,
    session: DatabaseSession,
):
    try:
        await favorites_service.add_to_favorites(session, user_id, product_slug)
    except favorites_service.ProductNotFoundError as error:
        raise not_found(error) from error


@router.delete("/{product_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_favorites(
    product_slug: str,
    user_id: CurrentUser,
    session: DatabaseSession,
):
    try:
        await favorites_service.remove_from_favorites(session, user_id, product_slug)
    except (
        favorites_service.ProductNotFoundError,
        favorites_service.FavoriteNotFoundError,
    ) as error:
        raise not_found(error) from error
