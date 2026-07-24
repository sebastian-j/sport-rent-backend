import asyncio
import datetime
import uuid
from dataclasses import dataclass

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.passwords import DUMMY_PASSWORD_HASH, verify_password
from app.core.tokens import (
    IssuedToken,
    TokenClaims,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    encode_refresh_token,
)
from app.models import AuthSession, User


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AuthTokens:
    access_token: IssuedToken
    refresh_token: IssuedToken


async def authenticate_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
) -> AuthTokens:
    normalized_email = email.strip().casefold()
    user = await session.scalar(select(User).where(User.email == normalized_email))

    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_is_valid = await asyncio.to_thread(
        verify_password,
        password,
        password_hash,
    )

    if user is None or not password_is_valid:
        raise InvalidCredentialsError

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

    return AuthTokens(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def rotate_refresh_token(
    session: AsyncSession,
    token: str,
) -> AuthTokens:
    try:
        claims = decode_refresh_token(token)
    except jwt.InvalidTokenError:
        raise InvalidRefreshTokenError from None

    auth_session = await _get_auth_session_for_update(
        session,
        claims.session_id,
    )
    now = datetime.datetime.now(datetime.UTC)

    if (
        auth_session is None
        or auth_session.user_id != claims.user_id
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= now
    ):
        raise InvalidRefreshTokenError

    if claims.token_id == auth_session.current_jti:
        refresh_token = _rotate_current_token(
            auth_session,
            claims,
            now,
        )
    elif (
        claims.token_id == auth_session.previous_jti
        and auth_session.previous_valid_until is not None
        and now <= auth_session.previous_valid_until
    ):
        refresh_token = _recreate_current_token(auth_session, claims)
    else:
        auth_session.revoked_at = now
        await session.commit()
        raise InvalidRefreshTokenError

    access_token = create_access_token(claims.user_id, auth_session.id)

    await session.commit()

    return AuthTokens(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def revoke_auth_session(
    session: AsyncSession,
    token: str,
) -> None:
    try:
        claims = decode_refresh_token(token)
    except jwt.InvalidTokenError:
        return

    auth_session = await _get_auth_session_for_update(
        session,
        claims.session_id,
    )

    if (
        auth_session is not None
        and auth_session.user_id == claims.user_id
        and auth_session.revoked_at is None
    ):
        auth_session.revoked_at = datetime.datetime.now(datetime.UTC)

    await session.commit()


async def _get_auth_session_for_update(
    session: AsyncSession,
    session_id: uuid.UUID,
) -> AuthSession | None:
    return await session.scalar(
        select(AuthSession).where(AuthSession.id == session_id).with_for_update()
    )


def _rotate_current_token(
    auth_session: AuthSession,
    claims: TokenClaims,
    now: datetime.datetime,
) -> IssuedToken:
    refresh_token = create_refresh_token(
        claims.user_id,
        auth_session.id,
    )

    auth_session.previous_jti = auth_session.current_jti
    auth_session.previous_valid_until = now + settings.refresh_token_grace_period
    auth_session.current_jti = refresh_token.jti
    auth_session.current_issued_at = refresh_token.issued_at
    auth_session.expires_at = refresh_token.expires_at

    return refresh_token


def _recreate_current_token(
    auth_session: AuthSession,
    claims: TokenClaims,
) -> IssuedToken:
    return encode_refresh_token(
        user_id=claims.user_id,
        session_id=claims.session_id,
        jti=auth_session.current_jti,
        issued_at=auth_session.current_issued_at,
        expires_at=auth_session.expires_at,
    )
