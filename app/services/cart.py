from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CartItem, Order, OrderInstance, OrderStatus, Product, ProductSize
from app.models.product import Instance, InstanceStatus
from app.schemas.cart import (
    AddToCartRequest,
    CartItemDate,
    CartItemResponse,
    CartProductSize,
    UpdateCartItemRequest,
)


class CartValidationError(ValueError):
    pass


class CartItemNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class ValidatedTerm:
    product: Product
    product_size: ProductSize | None
    quantity: int
    available_quantity: int
    start_date: date
    end_date: date


def merge_quantities(existing_quantity: int, added_quantity: int) -> int:
    return existing_quantity + added_quantity


def ensure_quantity_available(quantity: int, available_quantity: int) -> None:
    if quantity > available_quantity:
        raise CartValidationError(
            f"Requested quantity ({quantity}) exceeds available quantity "
            f"({available_quantity}) for selected dates"
        )


def validate_dates(start_date: date, end_date: date, today: date | None = None) -> None:
    current_date = today or date.today()
    if start_date < current_date:
        raise CartValidationError("Start date cannot be in the past")
    if start_date > end_date:
        raise CartValidationError("Start date cannot be after end date")


async def validate_term(
    session: AsyncSession,
    *,
    product_id: int | None = None,
    product_slug: str | None = None,
    quantity: int,
    size: str | None,
    start_date: date,
    end_date: date,
    today: date | None = None,
) -> ValidatedTerm:
    if quantity < 1:
        raise CartValidationError("Quantity must be at least 1")
    validate_dates(start_date, end_date, today)

    product_identifier = (
        Product.id == product_id
        if product_id is not None
        else Product.slug == product_slug
    )
    product = await session.scalar(
        select(Product)
        .options(selectinload(Product.sizes))
        .where(product_identifier, Product.visibility_status.is_(True))
    )
    if product is None:
        raise CartItemNotFoundError("Product not found")

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
        Instance.product_id == product.id,
        Instance.status == InstanceStatus.AVAILABLE,
        ~occupied_instance,
    )
    if size is not None:
        availability_query = availability_query.where(Instance.size == size)

    available_quantity = await session.scalar(availability_query) or 0
    ensure_quantity_available(quantity, available_quantity)

    product_size = None
    if product.sizes:
        if size is None:
            raise CartValidationError("Size is required for this product")
        product_size = next(
            (
                product_size
                for product_size in product.sizes
                if product_size.size == size
            ),
            None,
        )
        if product_size is None:
            raise CartValidationError("Size is not assigned to this product")
    elif size is not None:
        raise CartValidationError("Size is not assigned to this product")

    return ValidatedTerm(
        product=product,
        product_size=product_size,
        quantity=quantity,
        available_quantity=available_quantity,
        start_date=start_date,
        end_date=end_date,
    )


async def add_item(
    session: AsyncSession, user_id: int, request: AddToCartRequest
) -> CartItem:
    term = await validate_term(
        session,
        product_slug=request.product_slug,
        quantity=request.quantity,
        size=request.size,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    existing_quantity = await _locked_term_quantity(
        session,
        user_id=user_id,
        product_id=term.product.id,
        product_size_id=term.product_size.id if term.product_size else None,
        start_date=term.start_date,
        end_date=term.end_date,
    )
    ensure_quantity_available(
        merge_quantities(existing_quantity, term.quantity),
        term.available_quantity,
    )
    statement = (
        insert(CartItem)
        .values(
            user_id=user_id,
            product_id=term.product.id,
            product_size_id=term.product_size.id if term.product_size else None,
            quantity=term.quantity,
            start_date=term.start_date,
            end_date=term.end_date,
        )
        .on_conflict_do_update(
            constraint="uq_cart_item_term",
            set_={"quantity": CartItem.quantity + term.quantity},
            where=(CartItem.quantity + term.quantity) <= term.available_quantity,
        )
        .returning(CartItem.id)
    )
    item_id = (await session.execute(statement)).scalar_one_or_none()
    if item_id is None:
        current_quantity = await _locked_term_quantity(
            session,
            user_id=user_id,
            product_id=term.product.id,
            product_size_id=term.product_size.id if term.product_size else None,
            start_date=term.start_date,
            end_date=term.end_date,
        )
        ensure_quantity_available(
            merge_quantities(current_quantity, term.quantity),
            term.available_quantity,
        )
        raise CartValidationError("Cart item could not be added")
    await session.commit()
    return await get_item(session, user_id, item_id)


async def _locked_term_quantity(
    session: AsyncSession,
    *,
    user_id: int,
    product_id: int,
    product_size_id: int | None,
    start_date: date,
    end_date: date,
) -> int:
    return (
        await session.scalar(
            select(CartItem.quantity)
            .where(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id,
                CartItem.product_size_id == product_size_id,
                CartItem.start_date == start_date,
                CartItem.end_date == end_date,
            )
            .with_for_update()
        )
        or 0
    )


async def get_item(session: AsyncSession, user_id: int, item_id: int) -> CartItem:
    item = await session.scalar(
        select(CartItem)
        .options(selectinload(CartItem.product_size))
        .where(CartItem.id == item_id, CartItem.user_id == user_id)
    )
    if item is None:
        raise CartItemNotFoundError("Cart item not found")
    return item


async def update_item(
    session: AsyncSession,
    user_id: int,
    item_id: int,
    request: UpdateCartItemRequest,
) -> CartItem:
    item = await session.scalar(
        select(CartItem)
        .options(selectinload(CartItem.product_size))
        .where(CartItem.id == item_id, CartItem.user_id == user_id)
        .with_for_update()
    )
    if item is None:
        raise CartItemNotFoundError("Cart item not found")

    values = request.model_dump(exclude_unset=True)
    size = values.get(
        "size", item.product_size.size if item.product_size is not None else None
    )
    term = await validate_term(
        session,
        product_id=item.product_id,
        quantity=values.get("quantity", item.quantity),
        size=size,
        start_date=values.get("start_date", item.start_date),
        end_date=values.get("end_date", item.end_date),
    )

    collision = await session.scalar(
        select(CartItem)
        .where(
            CartItem.user_id == user_id,
            CartItem.product_id == item.product_id,
            CartItem.product_size_id
            == (term.product_size.id if term.product_size else None),
            CartItem.start_date == term.start_date,
            CartItem.end_date == term.end_date,
            CartItem.id != item.id,
        )
        .with_for_update()
    )
    if collision is not None:
        merged_quantity = merge_quantities(collision.quantity, term.quantity)
        ensure_quantity_available(merged_quantity, term.available_quantity)
        collision.quantity = merged_quantity
        result_id = collision.id
        await session.delete(item)
    else:
        item.product_size_id = term.product_size.id if term.product_size else None
        item.product_size = term.product_size
        item.quantity = term.quantity
        item.start_date = term.start_date
        item.end_date = term.end_date
        result_id = item.id

    await session.commit()
    return await get_item(session, user_id, result_id)


async def remove_item(session: AsyncSession, user_id: int, item_id: int) -> None:
    result = await session.execute(
        delete(CartItem).where(CartItem.id == item_id, CartItem.user_id == user_id)
    )
    if result.rowcount == 0:
        raise CartItemNotFoundError("Cart item not found")
    await session.commit()


async def remove_product(
    session: AsyncSession, user_id: int, product_slug: str
) -> None:
    result = await session.execute(
        delete(CartItem).where(
            CartItem.product_id.in_(
                select(Product.id).where(Product.slug == product_slug)
            ),
            CartItem.user_id == user_id,
        )
    )
    if result.rowcount == 0:
        raise CartItemNotFoundError("Product not found in cart")
    await session.commit()


def group_cart_items(items: Sequence[CartItem]) -> list[CartItemResponse]:
    products: dict[int, CartItemResponse] = {}
    for item in items:
        product = item.product
        response = products.get(product.id)
        if response is None:
            first_image = min(
                product.images,
                key=lambda image: image.display_order,
                default=None,
            )
            response = CartItemResponse(
                slug=product.slug,
                product_name=product.name,
                image=(first_image.image if first_image else ""),
                alt=first_image.alt_text if first_image else None,
                price=product.price,
                sizes=[
                    CartProductSize(size=size.size, description=size.description)
                    for size in sorted(product.sizes, key=lambda size: size.id)
                ],
                dates=[],
            )
            products[product.id] = response
        response.dates.append(
            CartItemDate(
                id=item.id,
                quantity=item.quantity,
                size=item.product_size.size if item.product_size else None,
                start_date=item.start_date,
                end_date=item.end_date,
            )
        )
    return list(products.values())


async def get_cart(session: AsyncSession, user_id: int) -> list[CartItemResponse]:
    items = (
        await session.scalars(
            select(CartItem)
            .options(
                selectinload(CartItem.product).selectinload(Product.images),
                selectinload(CartItem.product).selectinload(Product.sizes),
                selectinload(CartItem.product_size),
            )
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at, CartItem.id)
        )
    ).all()
    return group_cart_items(items)


async def has_cart_items(session: AsyncSession, user_id: int) -> bool:
    item_id = await session.scalar(
        select(CartItem.id).where(CartItem.user_id == user_id).limit(1)
    )
    return item_id is not None


def item_response(item: CartItem) -> CartItemDate:
    return CartItemDate(
        id=item.id,
        quantity=item.quantity,
        size=item.product_size.size if item.product_size else None,
        start_date=item.start_date,
        end_date=item.end_date,
    )
