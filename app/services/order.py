from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CartItem,
    Order,
    OrderInstance,
    OrderStatus,
    User,
)
from app.models.product import Instance, InstanceStatus, Product
from app.models.promo_codes import DiscountType, PromoCode
from app.schemas.order import (
    CreateOrderRequest,
    OrderAddressRequest,
    OrderInstanceResponse,
    OrderRecipient,
    OrderResponse,
)
from app.services import cart as cart_service
from app.services import loyalty as loyalty_service
from app.services import promo_code as promo_code_service
from app.services.order_addresses import (
    create_order_address_snapshot,
    snapshot_default_address,
)


class OrderValidationError(ValueError):
    pass


class EmptyCartError(OrderValidationError):
    pass


class PromoCodeInvalidError(OrderValidationError):
    pass


class OrderNotFoundError(ValueError):
    pass


def rental_days(start_date: date, end_date: date) -> int:
    days = (end_date - start_date).days
    if days < 0:
        raise OrderValidationError("End date cannot be before start date")
    return 1 if days == 0 else days


def line_total(unit_price: Decimal, start_date: date, end_date: date) -> Decimal:
    return unit_price * rental_days(start_date, end_date)


def _apply_promo_amount(subtotal: Decimal, promo: PromoCode) -> Decimal:
    if promo.discount_type is DiscountType.PERCENTAGE:
        discount = subtotal * promo.discount_value
    else:
        discount = promo.discount_value
    return max(subtotal - discount, Decimal("0.00"))


def apply_promo_discount(subtotal: Decimal, promo: PromoCode) -> Decimal:
    if promo.minimum_order_value is not None and subtotal < promo.minimum_order_value:
        raise PromoCodeInvalidError(
            "Order total does not meet the promo code minimum value"
        )
    return _apply_promo_amount(subtotal, promo)


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


def order_subtotal(order: Order) -> Decimal:
    subtotal = Decimal("0.00")
    for order_instance in order.instances:
        subtotal += line_total(
            Decimal(str(order_instance.price)),
            order_instance.start_date,
            order_instance.end_date,
        )
    return subtotal


def _primary_product_image(product: Product) -> str | None:
    if not product.images:
        return None

    primary_image = min(product.images, key=lambda i: i.display_order)
    return primary_image.image


def order_response(order: Order, total_price: Decimal | None = None) -> OrderResponse:
    if total_price is None:
        total_price = order.total_price

    discount = max(order_subtotal(order) - total_price, Decimal("0.00"))

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        created_at=order.created_at,
        status=order.status,
        payment_code=str(order.payment_code) if order.payment_code else None,
        total_price=float(total_price),
        discount=float(discount),
        used_points=order.used_points,
        recipient=OrderRecipient(
            first_name=order.recipient_first_name,
            last_name=order.recipient_last_name,
        ),
        address=address_response(order.address),
        instances=[
            OrderInstanceResponse(
                product_id=order_instance.instance.product.id,
                product_name=order_instance.instance.product.name,
                image=_primary_product_image(order_instance.instance.product),
                size=order_instance.instance.size,
                quantity=1,
                start_date=order_instance.start_date,
                end_date=order_instance.end_date,
                price=float(order_instance.price),
            )
            for order_instance in order.instances
        ],
    )


def _order_load_options():
    return (
        selectinload(Order.address),
        selectinload(Order.instances)
        .selectinload(OrderInstance.instance)
        .selectinload(Instance.product)
        .selectinload(Product.images),
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
        points_to_spend=0,
        promo_code_id=promo.id if promo else None,
        total_price=total_price,
        recipient_first_name=request.recipient.first_name,
        recipient_last_name=request.recipient.last_name,
        address=address,
        instances=order_instances,
    )
    session.add(order)
    await session.flush()

    if promo is not None:
        promo.usage_count += 1

    points_to_spend = request.points_to_spend

    if points_to_spend > 0:
        lifetime_qualifying_spend = await loyalty_service.get_lifetime_qualifying_spend(
            session,
            user_id,
        )

        try:
            loyalty_service.validate_points_redemption(
                points_to_spend,
                total_price,
                lifetime_qualifying_spend,
            )
            balance = await loyalty_service.get_balance(session, user_id)
            if balance < points_to_spend:
                raise loyalty_service.InsufficientLoyaltyPointsError(
                    available=balance,
                    requested=points_to_spend,
                )
            await loyalty_service.spend_points(
                session,
                user_id,
                order.id,
                points_to_spend,
                description=f"Points reserved for order #{order.id}",
            )
        except (
            loyalty_service.InvalidLoyaltyPointsAmountError,
            loyalty_service.LoyaltyProgramLockedError,
            loyalty_service.LoyaltyPointsRedemptionLimitError,
            loyalty_service.InsufficientLoyaltyPointsError,
        ) as error:
            raise OrderValidationError(str(error)) from error

        order.points_to_spend = points_to_spend
        order.used_points = True
        total_price -= loyalty_service.calculate_points_discount(points_to_spend)
    order.total_price = total_price

    await session.execute(delete(CartItem).where(CartItem.user_id == user_id))
    await session.commit()

    order = await session.scalar(
        select(Order).options(*_order_load_options()).where(Order.id == order.id)
    )
    if order is None:
        raise OrderValidationError("Order could not be loaded after creation")

    return order_response(order, total_price)


async def list_orders(
    session: AsyncSession,
    user_id: int,
    *,
    page: int,
    page_size: int,
) -> tuple[list[OrderResponse], int]:
    total = (
        await session.scalar(
            select(func.count(Order.id)).where(Order.user_id == user_id)
        )
        or 0
    )
    orders = (
        await session.scalars(
            select(Order)
            .options(*_order_load_options())
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return [order_response(order) for order in orders], total


async def get_order(
    session: AsyncSession,
    user_id: int,
    order_id: int,
) -> OrderResponse:
    order = await session.scalar(
        select(Order)
        .options(*_order_load_options())
        .where(Order.id == order_id, Order.user_id == user_id)
    )
    if order is None:
        raise OrderNotFoundError("Order not found")
    return order_response(order)
