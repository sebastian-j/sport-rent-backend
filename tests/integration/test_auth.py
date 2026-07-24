import asyncio
import datetime
from http.cookies import SimpleCookie

import jwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.tokens import decode_access_token, decode_refresh_token
from app.models import AuthSession, User
from tests.support import SeededUser

REFRESH_COOKIE_NAME = "refresh_token"


def refresh_token_from(response: Response) -> str:
    token = response.cookies.get(REFRESH_COOKIE_NAME)
    assert token
    return token


def refresh_cookie_from(response: Response):
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    return cookie[REFRESH_COOKIE_NAME]


def assert_refresh_cookie_deleted(response: Response) -> None:
    cookie = refresh_cookie_from(response)

    assert cookie.value == ""
    assert cookie["max-age"] == "0"
    assert cookie["expires"]
    assert cookie["path"] == "/auth"
    assert cookie["httponly"]
    assert cookie["samesite"].casefold() == "lax"
    assert bool(cookie["secure"]) is settings.auth_cookie_secure


async def login(client: AsyncClient, user: SeededUser) -> Response:
    return await client.post(
        "/auth/login",
        json={"email": user.email, "password": user.password},
    )


async def test_login_returns_access_token_and_creates_session(
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    response = await login(client, test_user)

    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "token_type", "expires_in"}
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == settings.jwt_access_expiration
    assert "refresh_token" not in response.json()

    cookie = refresh_cookie_from(response)
    assert cookie.value
    assert cookie["max-age"] == str(settings.jwt_refresh_expiration)
    assert cookie["path"] == "/auth"
    assert cookie["httponly"]
    assert cookie["samesite"].casefold() == "lax"
    assert bool(cookie["secure"]) is settings.auth_cookie_secure

    access_claims = decode_access_token(response.json()["access_token"])
    refresh_claims = decode_refresh_token(cookie.value)

    assert access_claims.user_id == test_user.id
    assert refresh_claims.user_id == test_user.id
    assert access_claims.session_id == refresh_claims.session_id
    assert access_claims.token_type == "access"
    assert refresh_claims.token_type == "refresh"
    assert access_claims.expires_at - access_claims.issued_at == datetime.timedelta(
        seconds=settings.jwt_access_expiration
    )
    assert refresh_claims.expires_at - refresh_claims.issued_at == datetime.timedelta(
        seconds=settings.jwt_refresh_expiration
    )

    async with test_session_factory() as session:
        user = await session.get(User, test_user.id)
        auth_session = await session.get(AuthSession, refresh_claims.session_id)

    assert user is not None
    assert user.last_login_at == refresh_claims.issued_at
    assert auth_session is not None
    assert auth_session.user_id == test_user.id
    assert auth_session.current_jti == refresh_claims.token_id
    assert auth_session.revoked_at is None


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("jan.kowalski@poczta.pl", "incorrect-password"),
        ("unknown@example.com", "incorrect-password"),
    ],
)
async def test_login_rejects_invalid_credentials_without_creating_session(
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    email: str,
    password: str,
) -> None:
    response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}
    assert "set-cookie" not in response.headers

    async with test_session_factory() as session:
        session_count = await session.scalar(
            select(func.count()).select_from(AuthSession)
        )
        user = await session.get(User, test_user.id)

    assert session_count == 0
    assert user is not None
    assert user.last_login_at is None


async def test_access_token_protects_endpoint_and_expired_token_is_rejected(
    client: AsyncClient,
    test_user: SeededUser,
) -> None:
    login_response = await login(client, test_user)
    access_token = login_response.json()["access_token"]

    response = await client.get(
        "/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == test_user.email

    payload = jwt.decode(
        access_token,
        options={"verify_signature": False},
    )
    now = datetime.datetime.now(datetime.UTC)
    payload["iat"] = int((now - datetime.timedelta(minutes=2)).timestamp())
    payload["exp"] = int((now - datetime.timedelta(minutes=1)).timestamp())
    expired_token = jwt.encode(
        payload,
        settings.jwt_access_secret,
        algorithm="HS256",
    )

    expired_response = await client.get(
        "/user",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert expired_response.status_code == 401
    assert expired_response.headers["www-authenticate"] == "Bearer"
    assert expired_response.json() == {"detail": "Invalid token"}


@pytest.mark.parametrize("refresh_token", [None, "not-a-jwt"])
async def test_refresh_rejects_invalid_cookie_and_deletes_it(
    client: AsyncClient,
    refresh_token: str | None,
) -> None:
    headers = {}
    if refresh_token is not None:
        headers["Cookie"] = f"{REFRESH_COOKIE_NAME}={refresh_token}"

    response = await client.post("/auth/refresh", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate refresh token"}
    assert_refresh_cookie_deleted(response)


async def test_refresh_rotates_token_and_updates_session(
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    login_response = await login(client, test_user)
    original_refresh_token = refresh_token_from(login_response)
    original_claims = decode_refresh_token(original_refresh_token)

    response = await client.post("/auth/refresh")

    assert response.status_code == 200
    rotated_refresh_token = refresh_token_from(response)
    rotated_claims = decode_refresh_token(rotated_refresh_token)
    access_claims = decode_access_token(response.json()["access_token"])

    assert rotated_refresh_token != original_refresh_token
    assert rotated_claims.session_id == original_claims.session_id
    assert rotated_claims.token_id != original_claims.token_id
    assert access_claims.session_id == original_claims.session_id

    async with test_session_factory() as session:
        auth_session = await session.get(AuthSession, original_claims.session_id)

    assert auth_session is not None
    assert auth_session.current_jti == rotated_claims.token_id
    assert auth_session.previous_jti == original_claims.token_id
    assert auth_session.previous_valid_until is not None
    assert auth_session.revoked_at is None


async def test_parallel_refresh_returns_same_rotated_token(
    application: FastAPI,
    client: AsyncClient,
    test_user: SeededUser,
) -> None:
    login_response = await login(client, test_user)
    original_refresh_token = refresh_token_from(login_response)

    async def refresh() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as refresh_client:
            return await refresh_client.post(
                "/auth/refresh",
                headers={"Cookie": (f"{REFRESH_COOKIE_NAME}={original_refresh_token}")},
            )

    first_response, second_response = await asyncio.gather(refresh(), refresh())

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert refresh_token_from(first_response) == refresh_token_from(second_response)


async def test_reusing_old_refresh_token_revokes_session(
    application: FastAPI,
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    login_response = await login(client, test_user)
    original_refresh_token = refresh_token_from(login_response)
    original_claims = decode_refresh_token(original_refresh_token)

    refresh_response = await client.post("/auth/refresh")
    current_refresh_token = refresh_token_from(refresh_response)

    async with test_session_factory.begin() as session:
        auth_session = await session.get(AuthSession, original_claims.session_id)
        assert auth_session is not None
        auth_session.previous_valid_until = datetime.datetime.now(
            datetime.UTC
        ) - datetime.timedelta(seconds=1)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as reuse_client:
        reuse_response = await reuse_client.post(
            "/auth/refresh",
            headers={"Cookie": f"{REFRESH_COOKIE_NAME}={original_refresh_token}"},
        )
        current_response = await reuse_client.post(
            "/auth/refresh",
            headers={"Cookie": f"{REFRESH_COOKIE_NAME}={current_refresh_token}"},
        )

    assert reuse_response.status_code == 401
    assert_refresh_cookie_deleted(reuse_response)
    assert current_response.status_code == 401
    assert_refresh_cookie_deleted(current_response)

    async with test_session_factory() as session:
        auth_session = await session.get(AuthSession, original_claims.session_id)

    assert auth_session is not None
    assert auth_session.revoked_at is not None


@pytest.mark.parametrize("refresh_token", [None, "not-a-jwt"])
async def test_logout_is_idempotent_without_valid_cookie(
    client: AsyncClient,
    refresh_token: str | None,
) -> None:
    headers = {}
    if refresh_token is not None:
        headers["Cookie"] = f"{REFRESH_COOKIE_NAME}={refresh_token}"

    response = await client.post("/auth/logout", headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert_refresh_cookie_deleted(response)


async def test_logout_revokes_only_current_device_session(
    application: FastAPI,
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_login = await login(client, test_user)
    first_refresh_token = refresh_token_from(first_login)
    first_claims = decode_refresh_token(first_refresh_token)

    second_login = await login(client, test_user)
    second_refresh_token = refresh_token_from(second_login)
    second_claims = decode_refresh_token(second_refresh_token)

    logout_response = await client.post(
        "/auth/logout",
        headers={"Cookie": f"{REFRESH_COOKIE_NAME}={first_refresh_token}"},
    )

    assert logout_response.status_code == 204
    assert_refresh_cookie_deleted(logout_response)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as refresh_client:
        first_refresh_response = await refresh_client.post(
            "/auth/refresh",
            headers={"Cookie": f"{REFRESH_COOKIE_NAME}={first_refresh_token}"},
        )
        second_refresh_response = await refresh_client.post(
            "/auth/refresh",
            headers={"Cookie": f"{REFRESH_COOKIE_NAME}={second_refresh_token}"},
        )

    assert first_refresh_response.status_code == 401
    assert second_refresh_response.status_code == 200

    async with test_session_factory() as session:
        first_session = await session.get(AuthSession, first_claims.session_id)
        second_session = await session.get(AuthSession, second_claims.session_id)

    assert first_session is not None
    assert first_session.revoked_at is not None
    assert second_session is not None
    assert second_session.revoked_at is None
