from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    LoyaltyTransaction,
    LoyaltyTransactionType,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
)
from app.schemas.payment import PaymentResponse
from app.services import loyalty as loyalty_service
from app.services.payment_provider import PaymentProvider, PaymentProviderResult


class PaymentNotFoundError(ValueError):
    pass


class PaymentValidationError(ValueError):
    pass


def payment_response(payment: Payment) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        order_id=payment.order_id,
        status=payment.status,
        amount=float(payment.amount),
        currency=payment.currency,
        redirect_url=payment.redirect_url,
        created_at=payment.created_at,
        completed_at=payment.completed_at,
    )


async def apply_payment_result(
    session: AsyncSession,
    payment_id: int,
    result: PaymentProviderResult,
) -> PaymentResponse:
    payment = await session.scalar(
        select(Payment).where(Payment.id == payment_id).with_for_update()
    )
    if payment is None:
        raise PaymentNotFoundError("Payment not found")

    order = await session.scalar(
        select(Order).where(Order.id == payment.order_id).with_for_update()
    )
    if order is None:
        raise PaymentNotFoundError("Order not found")

    payment.provider_payment_id = result.provider_payment_id
    payment.redirect_url = result.redirect_url
    payment.status = result.status

    if result.status is PaymentStatus.SUCCEEDED:
        if order.status not in (OrderStatus.UNPAID, OrderStatus.PAID):
            raise PaymentValidationError(
                f"Order with status {order.status.value} cannot be paid"
            )

        if order.status is OrderStatus.UNPAID:
            if order.points_to_spend > 0:
                existing_spend = await session.scalar(
                    select(LoyaltyTransaction).where(
                        LoyaltyTransaction.order_id == order.id,
                        LoyaltyTransaction.type == LoyaltyTransactionType.SPEND,
                    )
                )
                if existing_spend is None:
                    await loyalty_service.spend_points(
                        session,
                        order.user_id,
                        order.id,
                        order.points_to_spend,
                        description=f"Points spent on order #{order.id}",
                    )
                order.used_points = True

            order.status = OrderStatus.PAID
            await loyalty_service.apply_loyalty_for_paid_order(session, order)

        payment.completed_at = await session.scalar(select(func.clock_timestamp()))

    await session.commit()
    return payment_response(payment)


async def start_order_payment(
    session: AsyncSession,
    user_id: int,
    order_id: int,
    provider: PaymentProvider,
) -> PaymentResponse:
    order = await session.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .with_for_update()
    )
    if order is None:
        raise PaymentNotFoundError("Order not found")

    payment = await session.scalar(
        select(Payment).where(Payment.order_id == order.id).with_for_update()
    )
    if payment is not None and payment.status is PaymentStatus.SUCCEEDED:
        return payment_response(payment)
    if (
        payment is not None
        and payment.status is PaymentStatus.PENDING
        and payment.provider_payment_id is not None
    ):
        return payment_response(payment)

    if order.status is OrderStatus.PAID:
        raise PaymentValidationError("Paid order has no successful payment record")
    if order.status is not OrderStatus.UNPAID:
        raise PaymentValidationError(
            f"Order with status {order.status.value} cannot be paid"
        )

    if payment is None:
        payment = Payment(
            order_id=order.id,
            provider=provider.name,
            status=PaymentStatus.PENDING,
            amount=Decimal(order.total_price),
            currency="PLN",
        )
        session.add(payment)
    else:
        payment.provider = provider.name
        payment.provider_payment_id = None
        payment.status = PaymentStatus.PENDING
        payment.redirect_url = None
        payment.completed_at = None

    await session.flush()
    payment_id = payment.id
    reference = str(order.payment_code or order.id)
    amount = Decimal(payment.amount)
    currency = payment.currency
    await session.commit()

    result = await provider.create_payment(
        reference=reference,
        amount=amount,
        currency=currency,
    )
    return await apply_payment_result(session, payment_id, result)
