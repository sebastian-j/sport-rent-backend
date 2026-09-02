from calendar import monthrange
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    LoyaltyTransaction,
    LoyaltyTransactionType,
    Order,
    OrderStatus,
    User,
)

MAX_LOYALTY_POINTS_AMOUNT = 2_147_483_647
MONEY_PER_EARNED_POINT = Decimal("10.00")
MONEY_PER_REDEEMED_POINT = Decimal("0.50")
MAX_POINTS_PAYMENT_SHARE = Decimal("0.30")
LOYALTY_PROGRAM_UNLOCK_SPEND = Decimal("500.00")
LOYALTY_POINTS_VALIDITY_YEARS = 1


@dataclass
class _PointLot:
    source_key: tuple[datetime, int]
    remaining: int
    expires_at: datetime | None


@dataclass(frozen=True)
class _ConsumedPointLot:
    source_key: tuple[datetime, int]
    amount: int
    expires_at: datetime | None


def _remove_expired_lots(
    lots: deque[_PointLot],
    *,
    as_of: datetime,
) -> deque[_PointLot]:
    return deque(
        lot for lot in lots if lot.expires_at is None or lot.expires_at > as_of
    )


def _consume_oldest_lots(
    lots: deque[_PointLot],
    amount: int,
) -> tuple[list[_ConsumedPointLot], int]:
    consumed_lots: list[_ConsumedPointLot] = []
    remaining_amount = amount

    while remaining_amount > 0 and lots:
        oldest_lot = lots[0]
        consumed = min(remaining_amount, oldest_lot.remaining)
        consumed_lots.append(
            _ConsumedPointLot(
                source_key=oldest_lot.source_key,
                amount=consumed,
                expires_at=oldest_lot.expires_at,
            )
        )

        oldest_lot.remaining -= consumed
        remaining_amount -= consumed

        if oldest_lot.remaining == 0:
            lots.popleft()

    return consumed_lots, remaining_amount


def _add_point_lot(
    lots: deque[_PointLot],
    transaction: LoyaltyTransaction,
    amount: int,
) -> None:
    lots.append(
        _PointLot(
            source_key=(transaction.created_at, transaction.id or 0),
            remaining=amount,
            expires_at=transaction.expires_at,
        )
    )


def _restore_refunded_lots(
    lots: deque[_PointLot],
    consumed_lots: Sequence[_ConsumedPointLot],
    refund: LoyaltyTransaction,
    amount: int,
) -> None:
    amount_to_restore = amount

    for consumed_lot in consumed_lots:
        restored = min(amount_to_restore, consumed_lot.amount)
        amount_to_restore -= restored

        if (
            consumed_lot.expires_at is not None
            and consumed_lot.expires_at <= refund.created_at
        ):
            continue

        existing_lot = next(
            (lot for lot in lots if lot.source_key == consumed_lot.source_key),
            None,
        )
        if existing_lot is None:
            lots.append(
                _PointLot(
                    source_key=consumed_lot.source_key,
                    remaining=restored,
                    expires_at=consumed_lot.expires_at,
                )
            )
        else:
            existing_lot.remaining += restored

        if amount_to_restore == 0:
            break

    if amount_to_restore > 0:
        _add_point_lot(lots, refund, amount_to_restore)

    ordered_lots = sorted(lots, key=lambda lot: lot.source_key)
    lots.clear()
    lots.extend(ordered_lots)


def calculate_balance_from_transactions(
    transactions: Sequence[LoyaltyTransaction],
    *,
    as_of: datetime,
) -> int:
    lots: deque[_PointLot] = deque()
    debt = 0
    spent_lots_by_order_id: dict[int, list[_ConsumedPointLot]] = {}

    ordered_transactions = sorted(
        transactions,
        key=lambda transaction: (
            transaction.created_at,
            transaction.id or 0,
        ),
    )

    for transaction in ordered_transactions:
        if transaction.created_at > as_of:
            break

        lots = _remove_expired_lots(
            lots,
            as_of=transaction.created_at,
        )

        if transaction.amount > 0:
            credit = transaction.amount

            if debt > 0:
                covered_debt = min(credit, debt)
                debt -= covered_debt
                credit -= covered_debt

            if credit > 0:
                consumed_lots = (
                    spent_lots_by_order_id.get(transaction.order_id)
                    if transaction.type is LoyaltyTransactionType.REFUND
                    and transaction.order_id is not None
                    else None
                )
                if consumed_lots is None:
                    _add_point_lot(lots, transaction, credit)
                else:
                    _restore_refunded_lots(
                        lots,
                        consumed_lots,
                        transaction,
                        credit,
                    )

            continue

        consumed_lots, points_to_consume = _consume_oldest_lots(
            lots,
            -transaction.amount,
        )
        if (
            transaction.type is LoyaltyTransactionType.SPEND
            and transaction.order_id is not None
        ):
            spent_lots_by_order_id[transaction.order_id] = consumed_lots

        if points_to_consume > 0:
            debt += points_to_consume

    active_lots = _remove_expired_lots(
        lots,
        as_of=as_of,
    )
    active_points = sum(lot.remaining for lot in active_lots)

    return active_points - debt


def calculate_points_expiration(earned_at: datetime) -> datetime:
    expiration_year = earned_at.year + LOYALTY_POINTS_VALIDITY_YEARS
    expiration_day = min(
        earned_at.day,
        monthrange(expiration_year, earned_at.month)[1],
    )
    return earned_at.replace(
        year=expiration_year,
        day=expiration_day,
    )


class LoyaltyProgramLockedError(ValueError):
    def __init__(self, *, current_spend: Decimal) -> None:
        self.current_spend = current_spend
        self.required_spend = LOYALTY_PROGRAM_UNLOCK_SPEND
        super().__init__(
            f"Loyalty program requires {self.required_spend} in qualifying spend; "
            f"current spend: {current_spend}"
        )


class InvalidLoyaltyPointsAmountError(ValueError):
    pass


class LoyaltyPointsRedemptionLimitError(ValueError):
    def __init__(self, *, maximum: int, requested: int) -> None:
        self.maximum = maximum
        self.requested = requested
        super().__init__(
            f"Maximum redeemable points: {maximum}, requested: {requested}"
        )


class InsufficientLoyaltyPointsError(ValueError):
    def __init__(self, *, available: int, requested: int) -> None:
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient loyalty points: available {available}, requested {requested}"
        )


class LoyaltyUserNotFoundError(ValueError):
    pass


def calculate_points_discount(points: int) -> Decimal:
    if isinstance(points, bool) or not isinstance(points, int):
        raise ValueError("Points must be an integer")

    if points < 0:
        raise ValueError("Points cannot be negative")

    return Decimal(points) * MONEY_PER_REDEEMED_POINT


def calculate_earned_points(cash_paid: Decimal) -> int:
    if cash_paid < 0:
        raise ValueError("Cash paid cannot be negative")

    return int(cash_paid // MONEY_PER_EARNED_POINT)


def calculate_max_redeemable_points(order_value: Decimal) -> int:
    if order_value < 0:
        raise ValueError("Order value cannot be negative")

    maximum_discount = order_value * MAX_POINTS_PAYMENT_SHARE
    return int(maximum_discount // MONEY_PER_REDEEMED_POINT)


async def get_lifetime_qualifying_spend(
    session: AsyncSession,
    user_id: int,
) -> Decimal:
    total = await session.scalar(
        select(func.sum(Order.total_price)).where(
            Order.user_id == user_id,
            Order.status.in_(
                (
                    OrderStatus.PAID,
                    OrderStatus.GIVEN_OUT,
                    OrderStatus.FINISHED,
                )
            ),
        )
    )
    return total or Decimal("0.00")


async def get_balance(session: AsyncSession, user_id: int) -> int:
    as_of = await _get_database_time(session)

    transactions = list(
        await session.scalars(
            select(LoyaltyTransaction)
            .where(LoyaltyTransaction.user_id == user_id)
            .order_by(
                LoyaltyTransaction.created_at,
                LoyaltyTransaction.id,
            )
        )
    )
    return calculate_balance_from_transactions(
        transactions,
        as_of=as_of,
    )


async def get_history(
    session: AsyncSession,
    user_id: int,
    *,
    page: int,
    page_size: int,
) -> tuple[list[LoyaltyTransaction], int]:
    total = (
        await session.scalar(
            select(func.count(LoyaltyTransaction.id)).where(
                LoyaltyTransaction.user_id == user_id
            )
        )
        or 0
    )
    transactions = (
        await session.scalars(
            select(LoyaltyTransaction)
            .where(LoyaltyTransaction.user_id == user_id)
            .order_by(
                LoyaltyTransaction.created_at.desc(),
                LoyaltyTransaction.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return list(transactions), total


async def _lock_user(session: AsyncSession, user_id: int) -> None:
    existing_user_id = await session.scalar(
        select(User.id).where(User.id == user_id).with_for_update()
    )
    if existing_user_id is None:
        raise LoyaltyUserNotFoundError(f"User {user_id} not found")


async def _get_database_time(session: AsyncSession) -> datetime:
    current_time = await session.scalar(select(func.now()))
    if current_time is None:
        raise RuntimeError("Could not read the current database time")
    return current_time


def _require_valid_amount(amount: object) -> None:
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise InvalidLoyaltyPointsAmountError(
            "Loyalty points amount must be an integer"
        )
    if amount <= 0:
        raise InvalidLoyaltyPointsAmountError("Loyalty points amount must be positive")
    if amount > MAX_LOYALTY_POINTS_AMOUNT:
        raise InvalidLoyaltyPointsAmountError(
            f"Loyalty points amount must not exceed {MAX_LOYALTY_POINTS_AMOUNT}"
        )


def validate_points_redemption(
    points: int,
    order_value: Decimal,
    lifetime_qualifying_spend: Decimal,
) -> None:
    if isinstance(points, bool) or not isinstance(points, int):
        raise InvalidLoyaltyPointsAmountError(
            "Loyalty points amount must be an integer"
        )

    if points == 0:
        return

    _require_valid_amount(points)

    if lifetime_qualifying_spend < LOYALTY_PROGRAM_UNLOCK_SPEND:
        raise LoyaltyProgramLockedError(
            current_spend=lifetime_qualifying_spend,
        )

    maximum = calculate_max_redeemable_points(order_value)
    if points > maximum:
        raise LoyaltyPointsRedemptionLimitError(
            maximum=maximum,
            requested=points,
        )


async def earn_points(
    session: AsyncSession,
    user_id: int,
    order_id: int,
    amount: int,
    *,
    description: str | None = None,
) -> LoyaltyTransaction:
    _require_valid_amount(amount)
    await _lock_user(session, user_id)
    earned_at = await _get_database_time(session)

    transaction = LoyaltyTransaction(
        user_id=user_id,
        order_id=order_id,
        type=LoyaltyTransactionType.EARN,
        amount=amount,
        description=description,
        created_at=earned_at,
        expires_at=calculate_points_expiration(earned_at),
    )
    session.add(transaction)
    await session.flush()
    return transaction


async def spend_points(
    session: AsyncSession,
    user_id: int,
    order_id: int,
    amount: int,
    *,
    description: str | None = None,
) -> LoyaltyTransaction:
    _require_valid_amount(amount)
    await _lock_user(session, user_id)

    balance = await get_balance(session, user_id)
    if balance < amount:
        raise InsufficientLoyaltyPointsError(
            available=balance,
            requested=amount,
        )

    transaction = LoyaltyTransaction(
        user_id=user_id,
        order_id=order_id,
        type=LoyaltyTransactionType.SPEND,
        amount=-amount,
        description=description,
    )
    session.add(transaction)
    await session.flush()
    return transaction


async def apply_loyalty_for_paid_order(
    session: AsyncSession,
    order: Order,
) -> LoyaltyTransaction | None:
    if order.status is not OrderStatus.PAID:
        raise ValueError("Loyalty can only be applied to a paid order")

    existing_transaction = await session.scalar(
        select(LoyaltyTransaction).where(
            LoyaltyTransaction.order_id == order.id,
            LoyaltyTransaction.type == LoyaltyTransactionType.EARN,
        )
    )
    if existing_transaction is not None:
        return existing_transaction

    earned_points = calculate_earned_points(order.total_price)
    if earned_points == 0:
        return None

    return await earn_points(
        session,
        order.user_id,
        order.id,
        earned_points,
        description=f"Points earned for order #{order.id}",
    )


async def apply_loyalty_for_cancelled_order(
    session: AsyncSession,
    order: Order,
) -> list[LoyaltyTransaction]:
    if order.status is not OrderStatus.CANCELLED:
        raise ValueError("Loyalty can only be reversed for a cancelled order")

    await _lock_user(session, order.user_id)

    order_transactions = list(
        await session.scalars(
            select(LoyaltyTransaction).where(
                LoyaltyTransaction.order_id == order.id,
            )
        )
    )
    transactions_by_type = {
        transaction.type: transaction for transaction in order_transactions
    }
    applied_transactions: list[LoyaltyTransaction] = []
    new_transactions: list[LoyaltyTransaction] = []

    spent_transaction = transactions_by_type.get(LoyaltyTransactionType.SPEND)
    if spent_transaction is not None:
        refund_transaction = transactions_by_type.get(LoyaltyTransactionType.REFUND)
        if refund_transaction is None:
            refund_transaction = LoyaltyTransaction(
                user_id=order.user_id,
                order_id=order.id,
                type=LoyaltyTransactionType.REFUND,
                amount=-spent_transaction.amount,
                description=f"Points refunded for cancelled order #{order.id}",
            )
            new_transactions.append(refund_transaction)
        applied_transactions.append(refund_transaction)

    earned_transaction = transactions_by_type.get(LoyaltyTransactionType.EARN)
    if earned_transaction is not None:
        reversal_transaction = transactions_by_type.get(LoyaltyTransactionType.REVERSAL)
        if reversal_transaction is None:
            reversal_transaction = LoyaltyTransaction(
                user_id=order.user_id,
                order_id=order.id,
                type=LoyaltyTransactionType.REVERSAL,
                amount=-earned_transaction.amount,
                description=f"Points reversed for cancelled order #{order.id}",
            )
            new_transactions.append(reversal_transaction)
        applied_transactions.append(reversal_transaction)

    if new_transactions:
        session.add_all(new_transactions)
        await session.flush()

    return applied_transactions
