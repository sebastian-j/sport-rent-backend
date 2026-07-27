from http.cookies import SimpleCookie

import pytest
from fastapi import HTTPException, Request, Response

from app.api.auth_helpers import (
    delete_csrf_cookie,
    generate_csrf_token,
    require_csrf,
    set_csrf_cookie,
)
from app.core.config import settings

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = b"x-csrf-token"


def csrf_cookie_from(response: Response):
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    return cookie[CSRF_COOKIE_NAME]


def request_with_csrf(
    *,
    cookie_token: str | None,
    header_token: str | None,
) -> Request:
    headers: list[tuple[bytes, bytes]] = []

    if cookie_token is not None:
        headers.append(
            (
                b"cookie",
                f"{CSRF_COOKIE_NAME}={cookie_token}".encode(),
            )
        )

    if header_token is not None:
        headers.append((CSRF_HEADER_NAME, header_token.encode()))

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/auth/refresh",
            "headers": headers,
        }
    )


def test_generate_csrf_token_returns_unique_random_tokens() -> None:
    first_token = generate_csrf_token()
    second_token = generate_csrf_token()

    assert first_token
    assert second_token
    assert first_token != second_token


def test_set_csrf_cookie_sets_expected_attributes() -> None:
    response = Response()

    set_csrf_cookie(
        response,
        token="csrf-token",
        max_age=settings.csrf_expiration,
    )

    cookie = csrf_cookie_from(response)
    assert cookie.value == "csrf-token"
    assert cookie["max-age"] == str(settings.csrf_expiration)
    assert cookie["path"] == "/"
    assert not cookie["httponly"]
    assert cookie["samesite"].casefold() == "lax"
    assert bool(cookie["secure"]) is settings.auth_cookie_secure


def test_delete_csrf_cookie_expires_cookie() -> None:
    response = Response()

    delete_csrf_cookie(response)

    cookie = csrf_cookie_from(response)
    assert cookie.value == ""
    assert cookie["max-age"] == "0"
    assert cookie["expires"]
    assert cookie["path"] == "/"
    assert not cookie["httponly"]
    assert cookie["samesite"].casefold() == "lax"
    assert bool(cookie["secure"]) is settings.auth_cookie_secure


def test_require_csrf_accepts_matching_cookie_and_header() -> None:
    request = request_with_csrf(
        cookie_token="csrf-token",
        header_token="csrf-token",
    )

    require_csrf(request)


@pytest.mark.parametrize(
    ("cookie_token", "header_token"),
    [
        (None, "csrf-token"),
        ("csrf-token", None),
        ("csrf-token", "different-token"),
        ("", "csrf-token"),
        ("csrf-token", ""),
    ],
)
def test_require_csrf_rejects_missing_or_mismatched_token(
    cookie_token: str | None,
    header_token: str | None,
) -> None:
    request = request_with_csrf(
        cookie_token=cookie_token,
        header_token=header_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        require_csrf(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Could not validate credentials"
