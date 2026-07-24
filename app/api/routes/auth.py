import datetime
import os
import uuid
from time import sleep
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.security import (
    DUMMY_PASSWORD_HASH,
    JWT_ACCESS_EXPIRATION,
    JWT_REFRESH_EXPIRATION,
    REFRESH_TOKEN_GRACE_PERIOD,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    encode_refresh_token,
    verify_password,
)
from app.db.session import get_db_session
from app.models import AuthSession, User
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

AUTH_COOKIE_SECURE = (
    os.getenv("AUTH_COOKIE_SECURE", "true").strip().casefold() == "true"
)


@router.post("/login", response_model=AccessTokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    email = str(request.email).strip().casefold()

    user = await session.scalar(select(User).where(User.email == email))

    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH

    password_is_valid = await run_in_threadpool(
        verify_password, request.password, password_hash
    )

    if user is None or not password_is_valid:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    session_id = uuid.uuid4()
    access_token = create_access_token(user.id, session_id)
    refresh_token = create_refresh_token(user.id, session_id)

    session.add(
        AuthSession(
            id=session_id,
            user_id=user.id,
            current_jti=refresh_token.jti,
            current_issued_at=refresh_token.issued_at,
            expires_at=refresh_token.expires_at,
        )
    )

    user.last_login_at = refresh_token.issued_at

    await session.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token.token,
        max_age=JWT_REFRESH_EXPIRATION,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/auth",
    )

    return AccessTokenResponse(
        access_token=access_token.token,
        token_type="bearer",
        expires_in=JWT_ACCESS_EXPIRATION,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    if refresh_token is None:
        raise HTTPException(
            status_code=401,
            detail="Could not validate refresh token",
        )

    try:
        payload = decode_refresh_token(refresh_token)
        session_id = uuid.UUID(payload["sid"])
        token_jti = uuid.UUID(payload["jti"])
        user_id = int(payload["sub"])
    except jwt.InvalidTokenError, KeyError, TypeError, ValueError:
        raise HTTPException(
            status_code=401, detail="Could not validate refresh token"
        ) from None

    auth_session = await session.scalar(
        select(AuthSession).where(AuthSession.id == session_id).with_for_update()
    )
    now = datetime.datetime.now(datetime.UTC)

    if (
        auth_session is None
        or auth_session.user_id != user_id
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= now
    ):
        raise HTTPException(
            status_code=401,
            detail="Could not validate refresh token",
        )

    if token_jti == auth_session.current_jti:
        refresh_token_to_return = create_refresh_token(user_id, auth_session.id)

        auth_session.previous_jti = auth_session.current_jti
        auth_session.previous_valid_until = now + REFRESH_TOKEN_GRACE_PERIOD
        auth_session.current_jti = refresh_token_to_return.jti
        auth_session.current_issued_at = refresh_token_to_return.issued_at
        auth_session.expires_at = refresh_token_to_return.expires_at
    elif (
        token_jti == auth_session.previous_jti
        and auth_session.previous_valid_until is not None
        and now <= auth_session.previous_valid_until
    ):
        refresh_token_to_return = encode_refresh_token(
            user_id=user_id,
            session_id=session_id,
            jti=auth_session.current_jti,
            issued_at=auth_session.current_issued_at,
            expires_at=auth_session.expires_at,
        )
    else:
        auth_session.revoked_at = now
        await session.commit()

        raise HTTPException(
            status_code=401,
            detail="Could not validate refresh token",
        )

    access_token = create_access_token(user_id, auth_session.id)

    await session.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token_to_return.token,
        max_age=max(0, int((refresh_token_to_return.expires_at - now).total_seconds())),
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/auth",
    )

    return AccessTokenResponse(
        access_token=access_token.token,
        token_type="bearer",
        expires_in=JWT_ACCESS_EXPIRATION,
    )


# TODO: MOCK
@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/auth",
        secure=AUTH_COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
    return None


# TODO: MOCK
@router.post("/reset-password", status_code=204)
def reset_password(request: ResetPasswordRequest):
    sleep(1)
    return None


# TODO: MOCK
@router.post("/change-password", status_code=204)
def change_password(request: ChangePasswordRequest):
    sleep(1)
    return None
