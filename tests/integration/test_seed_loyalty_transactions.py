from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import LoyaltyTransaction, User
from scripts.seeds.seed_loyalty_transactions import (
    JAN_KOWALSKI_EMAIL,
    SEED_LOYALTY_AMOUNTS,
    SEED_LOYALTY_DESCRIPTION_PREFIX,
    seed_loyalty_transactions,
)
from scripts.seeds.seed_users import seed_users


async def test_seed_loyalty_transactions_adds_history_and_is_idempotent(
    empty_auth_database: None,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await seed_users(test_session_factory)

    first_result = await seed_loyalty_transactions(test_session_factory)
    second_result = await seed_loyalty_transactions(test_session_factory)

    assert first_result == len(SEED_LOYALTY_AMOUNTS)
    assert second_result == 0

    async with test_session_factory() as session:
        user_id = await session.scalar(
            select(User.id).where(User.email == JAN_KOWALSKI_EMAIL)
        )
        transaction_count = await session.scalar(
            select(func.count(LoyaltyTransaction.id)).where(
                LoyaltyTransaction.user_id == user_id,
                LoyaltyTransaction.description.startswith(
                    SEED_LOYALTY_DESCRIPTION_PREFIX
                ),
            )
        )
        balance = await session.scalar(
            select(func.sum(LoyaltyTransaction.amount)).where(
                LoyaltyTransaction.user_id == user_id
            )
        )

    assert transaction_count == len(SEED_LOYALTY_AMOUNTS)
    assert balance == sum(SEED_LOYALTY_AMOUNTS)
