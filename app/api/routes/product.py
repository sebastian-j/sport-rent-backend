from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_optional_current_user_id
from app.db.session import get_db_session
from app.models.category import Category
from app.models.product import Favorite, Product
from app.schemas.product import (
    CategoryResponse,
    ProductAvailabilityResponse,
    ProductQueryParams,
    ProductResponse,
    PriceFacetResponse,
    ProductFacetsResponse,
)
from app.services.image import convert_images_to_base64

router = APIRouter(prefix="/product", tags=["product"])


@router.get("", response_model=list[ProductResponse])
async def get_products(
    params: Annotated[ProductQueryParams, Query()],
    user_id: Annotated[int | None, Depends(get_optional_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    sort = params.sort
    order = params.order
    min_price = params.minPrice
    max_price = params.maxPrice
    categories = params.category
    search_query = params.query
    page = params.page
    page_size = params.pageSize

    product_query = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.sizes),
        )
        .where(Product.visibility_status.is_(True))
    )

    if min_price is not None:
        product_query = product_query.where(Product.price >= min_price)
    if max_price is not None:
        product_query = product_query.where(Product.price <= max_price)
    if search_query:
        product_query = product_query.where(Product.name.ilike(f"%{search_query}%"))
    if categories:
        product_query = product_query.outerjoin(Product.category).where(
            Category.name.in_(categories)
        )

    if sort and order:
        is_desc = order == "desc"
        if sort == "price":
            product_query = product_query.order_by(
                Product.price.desc() if is_desc else Product.price.asc(),
                Product.id.asc(),
            )
        elif sort == "name":
            product_query = product_query.order_by(
                Product.name.desc() if is_desc else Product.name.asc(), Product.id.asc()
            )
    else:
        product_query = product_query.order_by(Product.id.asc())

    start_index = (page - 1) * page_size
    product_query = product_query.offset(start_index).limit(page_size)

    paginated_products = (await session.scalars(product_query)).unique().all()

    favorites_set = set()
    if user_id is not None:
        favorites_set = set(
            await session.scalars(
                select(Favorite.product_slug).where(Favorite.user_id == user_id)
            )
        )

    results = []
    for p in paginated_products:
        sorted_images = sorted(p.images, key=lambda x: x.display_order)
        valid_images = [img for img in sorted_images if img.image]
        images_paths = [img.image for img in valid_images]
        images_alts = [img.alt_text or "" for img in valid_images]
        sizes = (
            [{"size": s.size, "description": s.description} for s in p.sizes]
            if p.sizes
            else None
        )

        results.append(
            ProductResponse(
                id=p.id,
                name=p.name,
                slug=p.slug,
                price=p.price,
                description=p.description,
                category=p.category.name if p.category else None,
                images=convert_images_to_base64(images_paths),
                imageAlts=images_alts,
                sizes=sizes,
                isFavorite=p.slug in favorites_set,
            )
        )

    return results


@router.get("/count", response_model=ProductFacetsResponse)
async def get_categories_count(
    params: Annotated[ProductQueryParams, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    min_price = params.minPrice
    max_price = params.maxPrice
    search_query = params.query
    selected_categories = params.category

    base_query = select(Product).where(Product.visibility_status.is_(True))

    if min_price is not None:
        base_query = base_query.where(Product.price >= min_price)
    if max_price is not None:
        base_query = base_query.where(Product.price <= max_price)
    if search_query:
        base_query = base_query.where(Product.name.ilike(f"%{search_query}%"))
    if selected_categories:
        base_query = base_query.join(Product.category).where(
            Category.name.in_(selected_categories)
        )

    category_query = (
        select(Category.name, func.count(Product.id))
        .select_from(Product)
        .outerjoin(Product.category)
        .where(Product.visibility_status.is_(True))
    )
    if min_price is not None:
        category_query = category_query.where(Product.price >= min_price)
    if max_price is not None:
        category_query = category_query.where(Product.price <= max_price)
    if search_query:
        category_query = category_query.where(Product.name.ilike(f"%{search_query}%"))

    category_query = category_query.group_by(Category.name)
    category_results = (await session.execute(category_query)).all()

    categories = [
        CategoryResponse(name=row[0] if row[0] else "Bez kategorii", count=row[1])
        for row in category_results
    ]

    total_count_query = select(func.count()).select_from(base_query.subquery())
    total_count = await session.scalar(total_count_query) or 0

    price_query = select(
        func.min(Product.price),
        func.max(Product.price),
    ).where(Product.visibility_status.is_(True))

    if search_query:
        price_query = price_query.where(
            Product.name.ilike(f"%{search_query}%")
        )
    if selected_categories:
        price_query = price_query.join(Product.category).where(
            Category.name.in_(selected_categories)
        )

    price_min, price_max = (
        await session.execute(price_query)
    ).one()

    return ProductFacetsResponse(
        categories=categories,
        total=total_count,
        price=PriceFacetResponse(
            min=price_min or 0,
            max=price_max or 0,
        ),
    )



@router.get("/{product_slug}", response_model=ProductResponse)
async def get_product(
    product_slug: str,
    user_id: Annotated[int | None, Depends(get_optional_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    p = await session.scalar(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.sizes),
        )
        .where(Product.slug == product_slug, Product.visibility_status.is_(True))
    )

    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    is_favorite = False
    if user_id is not None:
        is_favorite = (
            await session.scalar(
                select(Favorite).where(
                    Favorite.user_id == user_id,
                    Favorite.product_slug == product_slug,
                )
            )
            is not None
        )

    sorted_images = sorted(p.images, key=lambda x: x.display_order)
    valid_images = [img for img in sorted_images if img.image]
    images_paths = [img.image for img in valid_images]
    images_alts = [img.alt_text or "" for img in valid_images]
    sizes = (
        [{"size": s.size, "description": s.description} for s in p.sizes]
        if p.sizes
        else None
    )

    return ProductResponse(
        id=p.id,
        name=p.name,
        slug=p.slug,
        price=p.price,
        description=p.description,
        category=p.category.name if p.category else None,
        images=convert_images_to_base64(images_paths),
        imageAlts=images_alts,
        sizes=sizes,
        isFavorite=is_favorite,
    )


@router.get("/{product_slug}/availability", response_model=ProductAvailabilityResponse)
async def get_product_availability(product_slug: str, start_date: str, end_date: str):
    return ProductAvailabilityResponse(available=True)
