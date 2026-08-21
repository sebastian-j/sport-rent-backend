from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db_session
from app.models import Category
from app.schemas.category import CategoryResponse
from app.schemas.subcategory import SubcategoryResponse
from app.services.image import get_image_as_base64

router = APIRouter(prefix="/categories", tags=["categories"])


def _to_subcategory_response(subcategory) -> SubcategoryResponse:
    return SubcategoryResponse(
        name=subcategory.name,
        image=get_image_as_base64(subcategory.image) if subcategory.image else None,
        slug=subcategory.slug,
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

    return CategoryResponse(
        name=category.name,
        image=get_image_as_base64(category.image) or category.image,
        slug=category.slug,
        subcategories=[
            _to_subcategory_response(subcategory)
            for subcategory in category.subcategories
        ],
    )


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

    return [
        CategoryResponse(
            name=category.name,
            image=get_image_as_base64(category.image) if category.image else None,
            slug=category.slug,
            subcategories=[
                _to_subcategory_response(subcategory)
                for subcategory in category.subcategories
            ],
        )
        for category in categories
    ]
