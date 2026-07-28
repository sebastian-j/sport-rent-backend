from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.models import Address, User
from scripts.seed import SEED_USERS, seed_users


async def test_seed_users_adds_addresses_and_is_idempotent(
    empty_auth_database: None,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_result = await seed_users(test_session_factory)
    second_result = await seed_users(test_session_factory)

    assert first_result == (len(SEED_USERS), len(SEED_USERS))
    assert second_result == (0, 0)

    async with test_session_factory() as session:
        users = list(
            await session.scalars(
                select(User).options(selectinload(User.address)).order_by(User.email)
            )
        )
        address_count = await session.scalar(select(func.count()).select_from(Address))

    assert len(users) == len(SEED_USERS)
    assert address_count == len(SEED_USERS)

    seed_users_by_email = {seed_user.email: seed_user for seed_user in SEED_USERS}
    for user in users:
        seed_user = seed_users_by_email[user.email]

        assert user.address is not None
        assert user.address.first_name == seed_user.address.first_name
        assert user.address.last_name == seed_user.address.last_name
        assert user.address.first_line == seed_user.address.first_line
        assert user.address.second_line == seed_user.address.second_line
        assert user.address.postal_code == seed_user.address.postal_code
        assert user.address.city == seed_user.address.city
        assert user.address.country == seed_user.address.country
        assert user.address.company is None
        assert user.address.nip is None
