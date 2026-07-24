import asyncio
import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import async_session_factory, engine
from app.models import User

SEED_USER_PASSWORD = os.environ["SEED_USER_PASSWORD"]

SEED_USERS = [
    "jan.kowalski@poczta.pl",
    "anna.nowak@poczta.pl",
    "piotr.wisniewski@poczta.pl",
]


async def seed_users() -> None:
    seed_password = SEED_USER_PASSWORD

    async with async_session_factory.begin() as session:
        result = await session.scalars(
            select(User.email).where(User.email.in_(SEED_USERS))
        )
        existing_emails = set(result.all())

        missing_users = [
            User(
                email=email,
                password_hash=hash_password(seed_password),
            )
            for email in SEED_USERS
            if email not in existing_emails
        ]

        session.add_all(missing_users)

    print(f"Added {len(missing_users)} users")


async def main() -> None:
    try:
        await seed_users()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
