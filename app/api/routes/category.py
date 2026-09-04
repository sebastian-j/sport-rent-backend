from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.category import CategoryResponse
from app.services import category as category_service

router = APIRouter(prefix="/categories", tags=["categories"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def not_found(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.get("/random", response_model=CategoryResponse)
async def get_random_category(session: DatabaseSession) -> CategoryResponse:
    try:
        return await category_service.get_random_category(session)
    except category_service.CategoryNotFoundError as error:
        raise not_found(error) from error


@router.get("", response_model=list[CategoryResponse])
async def get_categories(session: DatabaseSession) -> list[CategoryResponse]:
    return await category_service.get_categories(session)
