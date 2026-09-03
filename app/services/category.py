from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category
from app.models.subcategory import Subcategory
from app.schemas.category import CategoryResponse
from app.schemas.subcategory import SubcategoryResponse


class CategoryNotFoundError(LookupError):
    pass


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


async def get_random_category(session: AsyncSession) -> CategoryResponse:
    category = await session.scalar(
        select(Category)
        .where(Category.image.is_not(None))
        .options(selectinload(Category.subcategories))
        .order_by(func.random())
        .limit(1)
    )

    if category is None or category.image is None:
        raise CategoryNotFoundError("No categories with images found")

    return _to_category_response(category)


async def get_categories(session: AsyncSession) -> list[CategoryResponse]:
    categories = (
        await session.scalars(
            select(Category)
            .options(selectinload(Category.subcategories))
            .order_by(Category.id)
        )
    ).all()

    return [_to_category_response(category) for category in categories]
