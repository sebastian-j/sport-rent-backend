import hmac
import secrets
from typing import Literal

from fastapi import HTTPException, Request, Response, status

from app.core.config import settings

_REFRESH_COOKIE_NAME = "refresh_token"
_REFRESH_COOKIE_PATH = "/auth"
_REFRESH_COOKIE_SAMESITE: Literal["lax"] = "lax"
_CSRF_COOKIE_NAME = "csrf_token"
_CSRF_HEADER_NAME = "X-CSRF-Token"
_CSRF_COOKIE_PATH = "/"
_CSRF_COOKIE_SAMESITE: Literal["lax"] = "lax"


def unauthorized(
    detail: str,
    *,
    bearer_challenge: bool = False,
) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if bearer_challenge else None

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=headers,
    )


def invalid_refresh_token() -> HTTPException:
    response = Response()
    delete_refresh_cookie(response)

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"Set-Cookie": response.headers["set-cookie"]},
    )


def set_refresh_cookie(
    response: Response,
    *,
    token: str,
    max_age: int,
) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        max_age=max(0, max_age),
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=_REFRESH_COOKIE_SAMESITE,
        path=_REFRESH_COOKIE_PATH,
    )


def delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_REFRESH_COOKIE_NAME,
        path=_REFRESH_COOKIE_PATH,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=_REFRESH_COOKIE_SAMESITE,
    )


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(
    response: Response,
    *,
    token: str,
    max_age: int,
) -> None:
    response.set_cookie(
        key=_CSRF_COOKIE_NAME,
        value=token,
        max_age=max(0, max_age),
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite=_CSRF_COOKIE_SAMESITE,
        path=_CSRF_COOKIE_PATH,
    )


def delete_csrf_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_CSRF_COOKIE_NAME,
        path=_CSRF_COOKIE_PATH,
        secure=settings.auth_cookie_secure,
        httponly=False,
        samesite=_CSRF_COOKIE_SAMESITE,
    )


def require_csrf(request: Request) -> None:
    csrf_cookie = request.cookies.get(_CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(_CSRF_HEADER_NAME)

    if (
        not csrf_cookie
        or not csrf_header
        or not hmac.compare_digest(csrf_cookie, csrf_header)
    ):
        raise HTTPException(
            status_code=403,
            detail="Could not validate credentials",
        )
