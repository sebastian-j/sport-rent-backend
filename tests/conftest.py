import os
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from app.api.dependencies import get_password_reset_notifier
from app.api.routes.auth import password_reset_rate_limiter
from app.core.config import settings
from app.core.passwords import hash_password
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app as fastapi_app
from app.models import (
    Address,
    AuthSession,
    Order,
    PasswordResetToken,
    PromoCode,
    User,
)
from tests.support import SeededUser

TEST_EMAIL = "jan.kowalski@poczta.pl"
TEST_PASSWORD = "Correct-test-password-123!"


class TestPasswordResetNotifier:
    async def send_password_reset_link(
        self,
        *,
        email: str,
        token: str,
    ) -> None:
        print(
            f"Password reset link for {email}: "
            f"{settings.frontend_url}/reset-password/confirm#token={token}",
            flush=True,
        )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    database_url = os.getenv("TEST_DATABASE_URL", settings.database_url)
    schema_name = f"test_auth_{uuid.uuid4().hex}"
    admin_engine = create_async_engine(database_url, poolclass=NullPool)
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,
        execution_options={"schema_translate_map": {None: schema_name}},
    )
    schema_created = False

    try:
        async with admin_engine.begin() as connection:
            await connection.execute(CreateSchema(schema_name))
        schema_created = True

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        yield engine
    finally:
        await engine.dispose()

        try:
            if schema_created:
                async with admin_engine.begin() as connection:
                    await connection.execute(DropSchema(schema_name, cascade=True))
        finally:
            await admin_engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def application(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[FastAPI]:
    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with test_session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db_session] = override_db_session
    fastapi_app.dependency_overrides[get_password_reset_notifier] = (
        TestPasswordResetNotifier
    )

    try:
        yield fastapi_app
    finally:
        fastapi_app.dependency_overrides.pop(get_db_session, None)
        fastapi_app.dependency_overrides.pop(get_password_reset_notifier, None)


@pytest_asyncio.fixture
async def client(application: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=application)

    async with AsyncClient(
        transport=transport,
        base_url="https://testserver",
    ) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_password_reset_rate_limiter() -> Iterator[None]:
    password_reset_rate_limiter.clear()
    yield
    password_reset_rate_limiter.clear()


@pytest.fixture(scope="session")
def test_password_hash() -> str:
    return hash_password(TEST_PASSWORD)


async def clear_auth_database(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory.begin() as session:
        await session.execute(delete(Order))
        await session.execute(delete(User))
        await session.execute(delete(Address))


@pytest_asyncio.fixture
async def empty_auth_database(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[None]:
    await clear_auth_database(test_session_factory)

    try:
        yield
    finally:
        await clear_auth_database(test_session_factory)


@pytest_asyncio.fixture
async def empty_promo_codes(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[None]:
    async with test_session_factory.begin() as session:
        await session.execute(delete(PromoCode))

    try:
        yield
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(delete(PromoCode))


@pytest_asyncio.fixture
async def test_user(
    empty_auth_database: None,
    test_session_factory: async_sessionmaker[AsyncSession],
    test_password_hash: str,
) -> SeededUser:
    async with test_session_factory.begin() as session:
        await session.execute(delete(AuthSession))
        await session.execute(delete(PasswordResetToken))
        await session.execute(delete(User))
        session.add(
            User(
                id=1,
                email=TEST_EMAIL,
                password_hash=test_password_hash,
            )
        )

    try:
        yield SeededUser(
            id=1,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(delete(AuthSession))
            await session.execute(delete(PasswordResetToken))
            await session.execute(delete(User))
