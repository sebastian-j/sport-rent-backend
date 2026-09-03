from datetime import date

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.manufacturer import Manufacturer
from app.models.order import Order, OrderInstance, OrderStatus
from app.models.product import Favorite, Instance, InstanceStatus, Product
from app.models.subcategory import Subcategory
from app.schemas.product import (
    CategoryResponse,
    PriceFacetResponse,
    ProductAvailabilityResponse,
    ProductFacetsResponse,
    ProductQueryParams,
    ProductResponse,
)
from app.services import accessory as accessory_service


class ProductNotFoundError(LookupError):
    pass


class InvalidDateRangeError(ValueError):
    pass


async def _get_favorite_slugs(
    session: AsyncSession,
    user_id: int | None,
) -> set[str]:
    if user_id is None:
        return set()
    return set(
        await session.scalars(
            select(Favorite.product_slug).where(Favorite.user_id == user_id)
        )
    )


def _to_product_response(
    product: Product,
    favorite_slugs: set[str],
) -> ProductResponse:
    sorted_images = sorted(product.images, key=lambda image: image.display_order)
    valid_images = [image for image in sorted_images if image.image]
    sizes = (
        [{"size": size.size, "description": size.description} for size in product.sizes]
        if product.sizes
        else None
    )
    return ProductResponse(
        id=product.id,
        name=product.name,
        slug=product.slug,
        price=product.price,
        description=product.description,
        category=product.category.name if product.category else None,
        images=[image.image for image in valid_images],
        imageAlts=[image.alt_text or "" for image in valid_images],
        manufacturer=product.manufacturer.name if product.manufacturer else None,
        sizes=sizes,
        isFavorite=product.slug in favorite_slugs,
    )


async def get_products(
    session: AsyncSession,
    params: ProductQueryParams,
    user_id: int | None,
) -> list[ProductResponse]:
    sort = params.sort
    order = params.order
    min_price = params.minPrice
    max_price = params.maxPrice
    categories = params.category
    subcategories = params.subcategory
    manufacturer = params.manufacturer
    search_query = params.query
    page = params.page
    page_size = params.pageSize

    product_query = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.manufacturer),
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
    if subcategories:
        product_query = product_query.outerjoin(Product.subcategory).where(
            Subcategory.name.in_(subcategories)
        )
    if manufacturer:
        product_query = product_query.outerjoin(Product.manufacturer).where(
            Manufacturer.name.in_(manufacturer)
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

    favorite_slugs = await _get_favorite_slugs(session, user_id)
    return [
        _to_product_response(product, favorite_slugs) for product in paginated_products
    ]


async def get_product_facets(
    session: AsyncSession,
    params: ProductQueryParams,
) -> ProductFacetsResponse:
    min_price = params.minPrice
    max_price = params.maxPrice
    search_query = params.query
    selected_categories = params.category
    selected_subcategories = params.subcategory
    selected_manufacturers = params.manufacturer

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
    if selected_subcategories:
        base_query = base_query.join(Product.subcategory).where(
            Subcategory.name.in_(selected_subcategories)
        )
    if selected_manufacturers:
        base_query = base_query.join(Product.manufacturer).where(
            Manufacturer.name.in_(selected_manufacturers)
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
    if selected_subcategories:
        category_query = category_query.join(Product.subcategory).where(
            Subcategory.name.in_(selected_subcategories)
        )
    if selected_manufacturers:
        category_query = category_query.join(Product.manufacturer).where(
            Manufacturer.name.in_(selected_manufacturers)
        )

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
        price_query = price_query.where(Product.name.ilike(f"%{search_query}%"))
    if selected_categories:
        price_query = price_query.join(Product.category).where(
            Category.name.in_(selected_categories)
        )
    if selected_subcategories:
        price_query = price_query.join(Product.subcategory).where(
            Subcategory.name.in_(selected_subcategories)
        )
    if selected_manufacturers:
        price_query = price_query.join(Product.manufacturer).where(
            Manufacturer.name.in_(selected_manufacturers)
        )

    price_min, price_max = (await session.execute(price_query)).one()

    return ProductFacetsResponse(
        categories=categories,
        total=total_count,
        price=PriceFacetResponse(
            min=price_min or 0,
            max=price_max or 0,
        ),
    )


async def get_product(
    session: AsyncSession,
    product_slug: str,
    user_id: int | None,
) -> ProductResponse:
    product = await session.scalar(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.manufacturer),
            selectinload(Product.sizes),
        )
        .where(Product.slug == product_slug, Product.visibility_status.is_(True))
    )

    if not product:
        raise ProductNotFoundError("Product not found")

    favorite_slugs = await _get_favorite_slugs(session, user_id)
    return _to_product_response(product, favorite_slugs)


async def get_product_accessories(
    session: AsyncSession,
    product_slug: str,
    user_id: int | None,
) -> list[ProductResponse]:
    try:
        accessories = await accessory_service.get_suggested_accessories(
            session,
            product_slug,
        )
    except accessory_service.ProductNotFoundError as error:
        raise ProductNotFoundError("Product not found") from error

    favorite_slugs = await _get_favorite_slugs(session, user_id)
    return [
        _to_product_response(accessory, favorite_slugs) for accessory in accessories
    ]


async def get_product_availability(
    session: AsyncSession,
    product_slug: str,
    start_date: date,
    end_date: date,
    size: str | None = None,
) -> ProductAvailabilityResponse:
    if start_date > end_date:
        raise InvalidDateRangeError("start_date cannot be after end_date")

    product = await session.scalar(
        select(Product.id).where(
            Product.slug == product_slug,
            Product.visibility_status.is_(True),
        )
    )
    if product is None:
        raise ProductNotFoundError("Product not found")

    occupied_instance = exists(
        select(1)
        .select_from(OrderInstance)
        .join(Order, Order.id == OrderInstance.order_id)
        .where(
            OrderInstance.instance_id == Instance.id,
            Order.status != OrderStatus.CANCELLED,
            OrderInstance.start_date <= end_date,
            OrderInstance.end_date >= start_date,
        )
    )

    availability_query = select(func.count(Instance.id)).where(
        Instance.product_id == product,
        Instance.status == InstanceStatus.AVAILABLE,
        ~occupied_instance,
    )
    if size is not None:
        availability_query = availability_query.where(Instance.size == size)

    available_quantity = await session.scalar(availability_query) or 0
    return ProductAvailabilityResponse(
        available=available_quantity > 0,
        availableQuantity=available_quantity,
    )
