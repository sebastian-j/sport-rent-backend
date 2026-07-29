from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.models import Address, User
from scripts.seeds.seed_users import SEED_USERS, seed_users


async def test_seed_users_adds_addresses_and_is_idempotent(
    empty_auth_database: None,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory.begin() as session:
        session.add(
            User(
                email=SEED_USERS[0].email,
                password_hash="existing-password-hash",
            )
        )

    first_result = await seed_users(test_session_factory)
    second_result = await seed_users(test_session_factory)

    assert first_result == (len(SEED_USERS) - 1, len(SEED_USERS))
    assert second_result == (0, 0)

    async with test_session_factory() as session:
        users = list(
            await session.scalars(
                select(User)
                .options(selectinload(User.default_address))
                .order_by(User.email)
            )
        )
        address_count = await session.scalar(select(func.count()).select_from(Address))

    assert len(users) == len(SEED_USERS)
    assert address_count == len(SEED_USERS)

    seed_users_by_email = {seed_user.email: seed_user for seed_user in SEED_USERS}
    for user in users:
        seed_user = seed_users_by_email[user.email]

        assert user.first_name == seed_user.first_name
        assert user.last_name == seed_user.last_name
        assert user.default_address is not None
        assert user.default_address.first_name is None
        assert user.default_address.last_name is None
        assert user.default_address.first_line == seed_user.address.first_line
        assert user.default_address.second_line == seed_user.address.second_line
        assert user.default_address.postal_code == seed_user.address.postal_code
        assert user.default_address.city == seed_user.address.city
        assert user.default_address.country == seed_user.address.country
        assert user.default_address.company is None
        assert user.default_address.nip is None
