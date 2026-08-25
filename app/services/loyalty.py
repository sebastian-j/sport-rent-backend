from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LoyaltyTransaction, LoyaltyTransactionType, User

MAX_LOYALTY_POINTS_AMOUNT = 2_147_483_647


class InvalidLoyaltyPointsAmountError(ValueError):
    pass


class InsufficientLoyaltyPointsError(ValueError):
    def __init__(self, *, available: int, requested: int) -> None:
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient loyalty points: available {available}, requested {requested}"
        )


class LoyaltyUserNotFoundError(ValueError):
    pass


async def get_balance(session: AsyncSession, user_id: int) -> int:
    balance = await session.scalar(
        select(func.coalesce(func.sum(LoyaltyTransaction.amount), 0)).where(
            LoyaltyTransaction.user_id == user_id
        )
    )
    return int(balance or 0)


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

    transaction = LoyaltyTransaction(
        user_id=user_id,
        order_id=order_id,
        type=LoyaltyTransactionType.EARN,
        amount=amount,
        description=description,
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
