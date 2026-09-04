from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db_session
from app.models import Category
from app.models.subcategory import Subcategory
from app.schemas.category import CategoryResponse
from app.schemas.subcategory import SubcategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])


def _to_subcategory_response(subcategory: Subcategory) -> SubcategoryResponse:
    return SubcategoryResponse(
        name=subcategory.name,
        image=subcategory.image,
        slug=subcategory.slug,
    )


def _to_category_response(category: Category) -> CategoryResponse:
    return CategoryResponse(
        name=category.name,
        image=category.image,
        slug=category.slug,
        subcategories=[
            _to_subcategory_response(subcategory)
            for subcategory in category.subcategories
        ],
    )


@router.get("/random", response_model=CategoryResponse)
async def get_random_category(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategoryResponse:
    category = await session.scalar(
        select(Category)
        .where(Category.image.is_not(None))
        .options(selectinload(Category.subcategories))
        .order_by(func.random())
        .limit(1)
    )

    if category is None or category.image is None:
        raise HTTPException(
            status_code=404,
            detail="No categories with images found",
        )

    return _to_category_response(category)


@router.get("", response_model=list[CategoryResponse])
async def get_categories(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CategoryResponse]:
    categories = (
        await session.scalars(
            select(Category)
            .options(selectinload(Category.subcategories))
            .order_by(Category.id)
        )
    ).all()

    return [_to_category_response(category) for category in categories]
