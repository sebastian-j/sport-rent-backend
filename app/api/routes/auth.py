import datetime
import uuid
from time import sleep
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.auth_helpers import (
    delete_refresh_cookie,
    invalid_refresh_token,
    set_refresh_cookie,
    unauthorized,
)
from app.core.config import settings
from app.core.passwords import DUMMY_PASSWORD_HASH, verify_password
from app.core.tokens import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    encode_refresh_token,
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
        raise unauthorized("Incorrect email or password")

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

    set_refresh_cookie(
        response,
        token=refresh_token.token,
        max_age=settings.jwt_refresh_expiration,
    )

    return AccessTokenResponse(
        access_token=access_token.token,
        token_type="bearer",
        expires_in=settings.jwt_access_expiration,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    if refresh_token is None:
        raise invalid_refresh_token()

    try:
        claims = decode_refresh_token(refresh_token)
    except jwt.InvalidTokenError:
        raise invalid_refresh_token() from None

    auth_session = await session.scalar(
        select(AuthSession).where(AuthSession.id == claims.session_id).with_for_update()
    )
    now = datetime.datetime.now(datetime.UTC)

    if (
        auth_session is None
        or auth_session.user_id != claims.user_id
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= now
    ):
        raise invalid_refresh_token()

    if claims.token_id == auth_session.current_jti:
        refresh_token_to_return = create_refresh_token(
            claims.user_id,
            auth_session.id,
        )

        auth_session.previous_jti = auth_session.current_jti
        auth_session.previous_valid_until = now + settings.refresh_token_grace_period
        auth_session.current_jti = refresh_token_to_return.jti
        auth_session.current_issued_at = refresh_token_to_return.issued_at
        auth_session.expires_at = refresh_token_to_return.expires_at
    elif (
        claims.token_id == auth_session.previous_jti
        and auth_session.previous_valid_until is not None
        and now <= auth_session.previous_valid_until
    ):
        refresh_token_to_return = encode_refresh_token(
            user_id=claims.user_id,
            session_id=claims.session_id,
            jti=auth_session.current_jti,
            issued_at=auth_session.current_issued_at,
            expires_at=auth_session.expires_at,
        )
    else:
        auth_session.revoked_at = now
        await session.commit()

        raise invalid_refresh_token()

    access_token = create_access_token(claims.user_id, auth_session.id)

    await session.commit()

    set_refresh_cookie(
        response,
        token=refresh_token_to_return.token,
        max_age=max(0, int((refresh_token_to_return.expires_at - now).total_seconds())),
    )

    return AccessTokenResponse(
        access_token=access_token.token,
        token_type="bearer",
        expires_in=settings.jwt_access_expiration,
    )


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    delete_refresh_cookie(response)

    if refresh_token is None:
        return None

    try:
        claims = decode_refresh_token(refresh_token)
    except jwt.InvalidTokenError:
        return None

    auth_session = await session.scalar(
        select(AuthSession).where(AuthSession.id == claims.session_id).with_for_update()
    )

    if (
        auth_session is not None
        and auth_session.user_id == claims.user_id
        and auth_session.revoked_at is None
    ):
        auth_session.revoked_at = datetime.datetime.now(datetime.UTC)

    await session.commit()

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
