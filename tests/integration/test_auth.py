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
from app.core.passwords import verify_password
from app.core.tokens import decode_access_token, decode_refresh_token
from app.models import Address, AuthSession, User
from tests.support import SeededUser

REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def refresh_token_from(response: Response) -> str:
    token = response.cookies.get(REFRESH_COOKIE_NAME)
    assert token
    return token


def cookie_from(response: Response, name: str):
    cookie = SimpleCookie()
    for value in response.headers.get_list("set-cookie"):
        cookie.load(value)
    return cookie[name]


def refresh_cookie_from(response: Response):
    return cookie_from(response, REFRESH_COOKIE_NAME)


def csrf_token_from(response: Response) -> str:
    token = response.cookies.get(CSRF_COOKIE_NAME)
    assert token
    return token


def csrf_headers(
    csrf_token: str,
    *,
    refresh_token: str | None = None,
) -> dict[str, str]:
    cookies = [f"{CSRF_COOKIE_NAME}={csrf_token}"]
    if refresh_token is not None:
        cookies.append(f"{REFRESH_COOKIE_NAME}={refresh_token}")

    return {
        "Cookie": "; ".join(cookies),
        CSRF_HEADER_NAME: csrf_token,
    }


def assert_refresh_cookie_deleted(response: Response) -> None:
    cookie = refresh_cookie_from(response)

    assert cookie.value == ""
    assert cookie["max-age"] == "0"
    assert cookie["expires"]
    assert cookie["path"] == "/auth"
    assert cookie["httponly"]
    assert cookie["samesite"].casefold() == "lax"
    assert bool(cookie["secure"]) is settings.auth_cookie_secure


def assert_csrf_cookie_deleted(response: Response) -> None:
    cookie = cookie_from(response, CSRF_COOKIE_NAME)

    assert cookie.value == ""
    assert cookie["max-age"] == "0"
    assert cookie["expires"]
    assert cookie["path"] == "/"
    assert not cookie["httponly"]
    assert cookie["samesite"].casefold() == "lax"
    assert bool(cookie["secure"]) is settings.auth_cookie_secure


async def login(client: AsyncClient, user: SeededUser) -> Response:
    return await client.post(
        "/auth/login",
        json={"email": user.email, "password": user.password},
    )


def registration_payload(
    *,
    email: str = "new.user@example.com",
    password: str = "Secure-password-123!",
) -> dict[str, object]:
    return {
        "email": email,
        "password": password,
        "first_name": "Jan",
        "last_name": "Nowak",
        "address": {
            "first_line": "ul. Testowa 10",
            "second_line": "lok. 2",
            "postal_code": "00-001",
            "city": "Warszawa",
            "country": "Polska",
        },
    }


async def test_register_creates_user_with_normalized_email_and_hashed_password(
    client: AsyncClient,
    empty_auth_database: None,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    response = await client.post(
        "/auth/register",
        json=registration_payload(email="  NEW.User@Example.COM  "),
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new.user@example.com"
    assert set(response.json()) == {"id", "email"}

    async with test_session_factory() as session:
        result = await session.execute(
            select(User, Address)
            .join(Address, User.address_id == Address.id)
            .where(User.email == "new.user@example.com")
        )
        row = result.one_or_none()

    assert row is not None
    user, address = row
    assert user.id == response.json()["id"]
    assert user.password_hash != "Secure-password-123!"
    assert verify_password("Secure-password-123!", user.password_hash)
    assert address.first_name == "Jan"
    assert address.second_name == "Nowak"
    assert address.first_line == "ul. Testowa 10"
    assert address.second_line == "lok. 2"
    assert address.postal_code == "00-001"
    assert address.city == "Warszawa"
    assert address.country == "Polska"
    assert address.company is None
    assert address.nip is None


async def test_register_rejects_existing_normalized_email(
    client: AsyncClient,
    empty_auth_database: None,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    email = "existing.user@example.com"
    first_response = await client.post(
        "/auth/register",
        json=registration_payload(email=email),
    )
    assert first_response.status_code == 201

    response = await client.post(
        "/auth/register",
        json=registration_payload(email=f"  {email.upper()}  "),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Email is already registered"}

    async with test_session_factory() as session:
        user_count = await session.scalar(select(func.count()).select_from(User))

    assert user_count == 1


async def test_register_rejects_too_short_password(
    client: AsyncClient,
    empty_auth_database: None,
) -> None:
    response = await client.post(
        "/auth/register",
        json=registration_payload(password="short"),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["first_name", "last_name"])
async def test_register_requires_first_and_last_name(
    client: AsyncClient,
    empty_auth_database: None,
    field: str,
) -> None:
    payload = registration_payload()
    del payload[field]

    response = await client.post("/auth/register", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["company", "nip"])
async def test_register_rejects_company_and_nip(
    client: AsyncClient,
    empty_auth_database: None,
    field: str,
) -> None:
    payload = registration_payload()
    address = payload["address"]
    assert isinstance(address, dict)
    address[field] = "not-allowed"

    response = await client.post("/auth/register", json=payload)

    assert response.status_code == 422


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

    csrf_cookie = cookie_from(response, CSRF_COOKIE_NAME)
    assert csrf_cookie.value
    assert csrf_cookie["max-age"] == str(settings.csrf_expiration)
    assert csrf_cookie["path"] == "/"
    assert not csrf_cookie["httponly"]
    assert csrf_cookie["samesite"].casefold() == "lax"
    assert bool(csrf_cookie["secure"]) is settings.auth_cookie_secure

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
    headers = csrf_headers("csrf-token", refresh_token=refresh_token)

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
    csrf_token = csrf_token_from(login_response)

    response = await client.post(
        "/auth/refresh",
        headers={CSRF_HEADER_NAME: csrf_token},
    )

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
    csrf_token = csrf_token_from(login_response)

    async def refresh() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as refresh_client:
            return await refresh_client.post(
                "/auth/refresh",
                headers=csrf_headers(
                    csrf_token,
                    refresh_token=original_refresh_token,
                ),
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
    csrf_token = csrf_token_from(login_response)

    refresh_response = await client.post(
        "/auth/refresh",
        headers={CSRF_HEADER_NAME: csrf_token},
    )
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
            headers=csrf_headers(
                csrf_token,
                refresh_token=original_refresh_token,
            ),
        )
        current_response = await reuse_client.post(
            "/auth/refresh",
            headers=csrf_headers(
                csrf_token,
                refresh_token=current_refresh_token,
            ),
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
    headers = csrf_headers("csrf-token", refresh_token=refresh_token)

    response = await client.post("/auth/logout", headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert_refresh_cookie_deleted(response)
    assert_csrf_cookie_deleted(response)


@pytest.mark.parametrize("endpoint", ["/auth/refresh", "/auth/logout"])
async def test_cookie_authenticated_endpoints_require_matching_csrf_token(
    client: AsyncClient,
    endpoint: str,
) -> None:
    response = await client.post(
        endpoint,
        headers={
            "Cookie": f"{CSRF_COOKIE_NAME}=csrf-token",
            CSRF_HEADER_NAME: "different-token",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Could not validate credentials"}


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
    csrf_token = csrf_token_from(second_login)

    logout_response = await client.post(
        "/auth/logout",
        headers=csrf_headers(
            csrf_token,
            refresh_token=first_refresh_token,
        ),
    )

    assert logout_response.status_code == 204
    assert_refresh_cookie_deleted(logout_response)
    assert_csrf_cookie_deleted(logout_response)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as refresh_client:
        first_refresh_response = await refresh_client.post(
            "/auth/refresh",
            headers=csrf_headers(
                csrf_token,
                refresh_token=first_refresh_token,
            ),
        )
        second_refresh_response = await refresh_client.post(
            "/auth/refresh",
            headers=csrf_headers(
                csrf_token,
                refresh_token=second_refresh_token,
            ),
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
