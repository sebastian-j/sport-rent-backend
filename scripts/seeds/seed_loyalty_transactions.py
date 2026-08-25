import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_factory
from app.models import LoyaltyTransaction, LoyaltyTransactionType, User

JAN_KOWALSKI_EMAIL = "jan.kowalski@poczta.pl"
SEED_LOYALTY_AMOUNTS = (
    120,
    80,
    -30,
    150,
    50,
    200,
    -75,
    90,
    110,
    -40,
    160,
    70,
    130,
    100,
)
SEED_LOYALTY_DESCRIPTION_PREFIX = "Przykładowa transakcja lojalnościowa"


async def seed_loyalty_transactions(
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> int:
    async with session_factory.begin() as session:
        user = await session.scalar(
            select(User).where(User.email == JAN_KOWALSKI_EMAIL)
        )
        if user is None:
            print(f"Skipped loyalty transactions: user {JAN_KOWALSKI_EMAIL} not found")
            return 0

        descriptions = [
            f"{SEED_LOYALTY_DESCRIPTION_PREFIX} {index:02d}"
            for index in range(1, len(SEED_LOYALTY_AMOUNTS) + 1)
        ]
        existing_descriptions = set(
            await session.scalars(
                select(LoyaltyTransaction.description).where(
                    LoyaltyTransaction.user_id == user.id,
                    LoyaltyTransaction.description.in_(descriptions),
                )
            )
        )
        now = datetime.now(UTC)
        transactions = [
            LoyaltyTransaction(
                user_id=user.id,
                type=LoyaltyTransactionType.ADJUSTMENT,
                amount=amount,
                description=description,
                created_at=now - timedelta(days=index - 1),
            )
            for index, (amount, description) in enumerate(
                zip(SEED_LOYALTY_AMOUNTS, descriptions, strict=True),
                start=1,
            )
            if description not in existing_descriptions
        ]
        session.add_all(transactions)

    print(f"Successfully seeded {len(transactions)} loyalty transactions.")
    return len(transactions)


if __name__ == "__main__":
    asyncio.run(seed_loyalty_transactions())
