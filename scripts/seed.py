import asyncio
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.passwords import hash_password
from app.db.session import async_session_factory, engine
from app.models import Address, User


@dataclass(frozen=True, slots=True)
class SeedAddress:
    first_name: str
    last_name: str
    first_line: str
    second_line: str | None
    postal_code: str
    city: str
    country: str


@dataclass(frozen=True, slots=True)
class SeedUser:
    email: str
    address: SeedAddress


SEED_USERS = (
    SeedUser(
        email="jan.kowalski@poczta.pl",
        address=SeedAddress(
            first_name="Jan",
            last_name="Kowalski",
            first_line="ul. Przykładowa 123",
            second_line=None,
            postal_code="00-001",
            city="Warszawa",
            country="Polska",
        ),
    ),
    SeedUser(
        email="anna.nowak@poczta.pl",
        address=SeedAddress(
            first_name="Anna",
            last_name="Nowak",
            first_line="ul. Testowa 456",
            second_line="Mieszkanie 12",
            postal_code="30-002",
            city="Kraków",
            country="Polska",
        ),
    ),
    SeedUser(
        email="piotr.wisniewski@poczta.pl",
        address=SeedAddress(
            first_name="Piotr",
            last_name="Wiśniewski",
            first_line="ul. Przykładowa 789",
            second_line=None,
            postal_code="80-003",
            city="Gdańsk",
            country="Polska",
        ),
    ),
)


async def seed_users(
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> tuple[int, int]:
    seed_password = settings.require_seed_user_password()
    seed_emails = [seed_user.email for seed_user in SEED_USERS]

    async with session_factory.begin() as session:
        existing_users = await session.scalars(
            select(User)
            .options(selectinload(User.address))
            .where(User.email.in_(seed_emails))
        )
        users_by_email = {user.email: user for user in existing_users}
        added_users = 0
        added_addresses = 0

        for seed_user in SEED_USERS:
            user = users_by_email.get(seed_user.email)

            if user is None:
                user = User(
                    email=seed_user.email,
                    password_hash=hash_password(seed_password),
                )
                session.add(user)
                added_users += 1

            if user.address is None:
                user.address = Address(
                    first_name=seed_user.address.first_name,
                    second_name=seed_user.address.last_name,
                    first_line=seed_user.address.first_line,
                    second_line=seed_user.address.second_line,
                    postal_code=seed_user.address.postal_code,
                    city=seed_user.address.city,
                    country=seed_user.address.country,
                )
                added_addresses += 1

    print(f"Added {added_users} users and {added_addresses} addresses")

    return added_users, added_addresses


async def main() -> None:
    try:
        await seed_users()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
