from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CartItem, Order, OrderInstance, OrderStatus, User
from app.models.product import Instance, InstanceStatus
from app.models.promo_codes import DiscountType, PromoCode
from app.schemas.order import (
    CreateOrderRequest,
    OrderAddressRequest,
    OrderInstanceResponse,
    OrderResponse,
)
from app.services import cart as cart_service
from app.services import loyalty as loyalty_service
from app.services import promo_code as promo_code_service
from app.services.order_addresses import (
    create_order_address_snapshot,
    snapshot_default_address,
)

# TODO - TEMPORARY
POINTS_TO_CURRENCY = Decimal("1")


class OrderValidationError(ValueError):
    pass


class EmptyCartError(OrderValidationError):
    pass


class PromoCodeInvalidError(OrderValidationError):
    pass


def rental_days(start_date: date, end_date: date) -> int:
    days = (end_date - start_date).days
    if days < 0:
        raise OrderValidationError("End date cannot be before start date")
    return 1 if days == 0 else days


def line_total(unit_price: Decimal, start_date: date, end_date: date) -> Decimal:
    return unit_price * rental_days(start_date, end_date)


def apply_promo_discount(subtotal: Decimal, promo: PromoCode) -> Decimal:
    if promo.minimum_order_value is not None and subtotal < promo.minimum_order_value:
        raise PromoCodeInvalidError(
            "Order total does not meet the promo code minimum value"
        )

    if promo.discount_type is DiscountType.PERCENTAGE:
        discount = subtotal * promo.discount_value
    else:
        discount = promo.discount_value

    return max(subtotal - discount, Decimal("0.00"))


def address_response(address) -> OrderAddressRequest:
    return OrderAddressRequest(
        first_name=address.first_name,
        last_name=address.last_name,
        first_line=address.first_line,
        second_line=address.second_line,
        postal_code=address.postal_code,
        city=address.city,
        country=address.country,
        company=address.company,
        nip=address.nip,
    )


def order_response(order: Order, total_price: Decimal) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total_price=float(total_price),
        used_points=order.used_points,
        address=address_response(order.address),
        instances=[
            OrderInstanceResponse(
                product_name=order_instance.instance.product.name,
                size=order_instance.instance.size,
                start_date=order_instance.start_date,
                end_date=order_instance.end_date,
                price=float(order_instance.price),
            )
            for order_instance in order.instances
        ],
    )


async def _load_cart_items(session: AsyncSession, user_id: int) -> list[CartItem]:
    items = (
        await session.scalars(
            select(CartItem)
            .options(
                selectinload(CartItem.product),
                selectinload(CartItem.product_size),
            )
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.id)
            .with_for_update()
        )
    ).all()
    return list(items)


async def _allocate_instances(
    session: AsyncSession,
    *,
    product_id: int,
    size: str | None,
    start_date: date,
    end_date: date,
    quantity: int,
) -> list[Instance]:
    occupied = exists(
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

    query = (
        select(Instance)
        .where(
            Instance.product_id == product_id,
            Instance.status == InstanceStatus.AVAILABLE,
            ~occupied,
        )
        .order_by(Instance.id)
        .with_for_update()
        .limit(quantity)
    )
    if size is not None:
        query = query.where(Instance.size == size)

    instances = list(await session.scalars(query))
    if len(instances) < quantity:
        raise OrderValidationError(
            "Not enough available instances for selected product and dates"
        )
    return instances


async def _resolve_address(
    session: AsyncSession,
    user_id: int,
    request: CreateOrderRequest,
):
    if request.address is not None:
        return create_order_address_snapshot(**request.address.model_dump())

    user = await session.scalar(
        select(User)
        .options(selectinload(User.default_address))
        .where(User.id == user_id)
    )
    if user is None:
        raise OrderValidationError("User not found")
    return snapshot_default_address(user)


async def _resolve_promo(
    session: AsyncSession,
    code: str | None,
) -> PromoCode | None:
    if code is None or not code.strip():
        return None

    promo = await promo_code_service.get_valid_promo_code(session, code)
    if promo is None:
        raise PromoCodeInvalidError("Promo code is invalid or expired")
    return promo


async def create_order(
    session: AsyncSession,
    user_id: int,
    request: CreateOrderRequest,
) -> OrderResponse:
    cart_items = await _load_cart_items(session, user_id)
    if not cart_items:
        raise EmptyCartError("Cart is empty")

    address = await _resolve_address(session, user_id, request)
    promo = await _resolve_promo(session, request.promo_code)

    order_instances: list[OrderInstance] = []
    subtotal = Decimal("0.00")

    for cart_item in cart_items:
        size = cart_item.product_size.size if cart_item.product_size else None
        try:
            term = await cart_service.validate_term(
                session,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                size=size,
                start_date=cart_item.start_date,
                end_date=cart_item.end_date,
            )
        except cart_service.CartValidationError as error:
            raise OrderValidationError(str(error)) from error
        except cart_service.CartItemNotFoundError as error:
            raise OrderValidationError(str(error)) from error

        instances = await _allocate_instances(
            session,
            product_id=term.product.id,
            size=size,
            start_date=term.start_date,
            end_date=term.end_date,
            quantity=term.quantity,
        )

        unit_price = Decimal(str(term.product.price))
        for instance in instances:
            order_instances.append(
                OrderInstance(
                    instance_id=instance.id,
                    start_date=term.start_date,
                    end_date=term.end_date,
                    price=unit_price,
                )
            )
            subtotal += line_total(unit_price, term.start_date, term.end_date)

    total_price = apply_promo_discount(subtotal, promo) if promo else subtotal

    order = Order(
        user_id=user_id,
        status=OrderStatus.UNPAID,
        payment_code=uuid4(),
        used_points=False,
        promo_code_id=promo.id if promo else None,
        address=address,
        instances=order_instances,
    )
    session.add(order)
    await session.flush()

    if promo is not None:
        promo.usage_count += 1

    if request.used_points:
        balance = await loyalty_service.get_balance(session, user_id)
        if balance <= 0:
            raise OrderValidationError("No loyalty points available to spend")

        max_points_for_total = int(total_price // POINTS_TO_CURRENCY)
        points_to_spend = min(balance, max_points_for_total)
        if points_to_spend <= 0:
            raise OrderValidationError("Order total is too low to spend loyalty points")

        await loyalty_service.spend_points(
            session,
            user_id,
            order.id,
            points_to_spend,
            description=f"Points spent on order #{order.id}",
        )
        order.used_points = True
        total_price = max(
            total_price - (Decimal(points_to_spend) * POINTS_TO_CURRENCY),
            Decimal("0.00"),
        )

    await session.execute(delete(CartItem).where(CartItem.user_id == user_id))
    await session.commit()

    order = await session.scalar(
        select(Order)
        .options(
            selectinload(Order.address),
            selectinload(Order.instances)
            .selectinload(OrderInstance.instance)
            .selectinload(Instance.product),
        )
        .where(Order.id == order.id)
    )
    if order is None:
        raise OrderValidationError("Order could not be loaded after creation")

    return order_response(order, total_price)
