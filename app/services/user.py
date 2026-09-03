from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.address import Address
from app.models.order import Order, OrderInstance
from app.models.product import Instance, Product
from app.models.user import User
from app.schemas.user import (
    OrderDetailResponse,
    OrderItemDetailsResponse,
    PaginatedUserHistoryResponse,
    UpdateAddressRequest,
    UserHistoryItemResponse,
    UserResponse,
)
from app.services import order as order_service


class UserNotFoundError(LookupError):
    pass


class OrderNotFoundError(LookupError):
    pass


async def get_user(session: AsyncSession, user_id: int) -> UserResponse:
    user = await session.scalar(
        select(User)
        .options(selectinload(User.default_address))
        .where(User.id == user_id)
    )

    if not user:
        raise UserNotFoundError("Could not validate credentials")

    addr = user.default_address

    return UserResponse(
        email=user.email,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        city=addr.city if addr else "",
        first_line=addr.first_line if addr else "",
        second_line=addr.second_line if addr else "",
        postal_code=addr.postal_code if addr else "",
        country=addr.country if addr else "",
        privacy_policy_accepted=True,
    )


async def update_personal_address(
    session: AsyncSession,
    user_id: int,
    request: UpdateAddressRequest,
) -> None:
    user = await session.scalar(
        select(User)
        .options(selectinload(User.default_address))
        .where(User.id == user_id)
    )
    if not user:
        raise UserNotFoundError("User not found")
    user.first_name = request.first_name
    user.last_name = request.last_name

    addr = user.default_address
    if not addr:
        user.default_address = Address(
            first_line=request.first_line,
            second_line=request.second_line,
            postal_code=request.postal_code,
            city=request.city,
            country=request.country,
        )
    else:
        addr.first_line = request.first_line
        addr.second_line = request.second_line
        addr.postal_code = request.postal_code
        addr.city = request.city
        addr.country = request.country

    await session.commit()


async def get_user_history(
    session: AsyncSession,
    user_id: int,
    *,
    page: int,
    page_size: int,
) -> PaginatedUserHistoryResponse:
    total_orders = (
        await session.scalar(
            select(func.count(Order.id)).where(Order.user_id == user_id)
        )
        or 0
    )

    offset = (page - 1) * page_size
    orders = (
        (
            await session.scalars(
                select(Order)
                .options(
                    selectinload(Order.instances),
                    selectinload(Order.promo_code),
                    selectinload(Order.loyalty_transactions),
                )
                .where(Order.user_id == user_id)
                .order_by(Order.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        .unique()
        .all()
    )

    items = [
        UserHistoryItemResponse(
            id=order.id,
            created_at=order.created_at,
            status=order.status.value,
            payment_code=str(order.payment_code) if order.payment_code else None,
            total=float(order_service.order_total(order)),
        )
        for order in orders
    ]
    total_pages = (total_orders + page_size - 1) // page_size
    return PaginatedUserHistoryResponse(
        items=items,
        page=page,
        pageSize=page_size,
        total=total_orders,
        totalPages=total_pages,
    )


async def get_order_details(
    session: AsyncSession,
    user_id: int,
    order_id: int,
) -> OrderDetailResponse:
    order = (
        (
            await session.scalars(
                select(Order)
                .options(
                    selectinload(Order.promo_code),
                    selectinload(Order.loyalty_transactions),
                    selectinload(Order.instances)
                    .selectinload(OrderInstance.instance)
                    .selectinload(Instance.product)
                    .selectinload(Product.images),
                )
                .where(Order.id == order_id)
            )
        )
        .unique()
        .first()
    )

    if not order or order.user_id != user_id:
        raise OrderNotFoundError("Order not found")

    total = order_service.order_total(order)
    subtotal = order_service.order_subtotal(order)
    discount = max(subtotal - total, Decimal("0.00"))

    items_response = []
    for order_instance in order.instances:
        product_obj = order_instance.instance.product

        image = None
        if product_obj.images:
            primary_img = min(product_obj.images, key=lambda img: img.display_order)
            image = primary_img.image

        item_total = order_service.line_total(
            Decimal(str(order_instance.price)),
            order_instance.start_date,
            order_instance.end_date,
        )

        items_response.append(
            OrderItemDetailsResponse(
                product_id=product_obj.id,
                product_name=product_obj.name,
                image=image,
                size=order_instance.instance.size,
                quantity=1,
                start_date=datetime.combine(
                    order_instance.start_date, datetime.min.time()
                ),
                end_date=datetime.combine(order_instance.end_date, datetime.min.time()),
                unit_price=float(item_total),
            )
        )

    return OrderDetailResponse(
        id=order.id,
        created_at=order.created_at,
        status=order.status.value,
        total=float(total),
        discount=float(discount),
        items=items_response,
    )
