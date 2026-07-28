import asyncio
import datetime
import uuid
from dataclasses import dataclass

import jwt
from sqlalchemy import select, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.email import normalize_email
from app.core.password_reset import (
    generate_password_reset_token,
    hash_password_reset_token,
)
from app.core.passwords import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.core.tokens import (
    IssuedToken,
    TokenClaims,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    encode_refresh_token,
)
from app.models import Address, AuthSession, PasswordResetToken, User


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class InvalidPasswordResetTokenError(Exception):
    pass


class EmailAlreadyRegisteredError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class RegistrationAddress:
    first_line: str
    second_line: str | None
    postal_code: str
    city: str
    country: str


@dataclass(frozen=True, slots=True)
class AuthTokens:
    access_token: IssuedToken
    refresh_token: IssuedToken


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    address: RegistrationAddress,
) -> User:
    normalized_email = normalize_email(email)
    existing_user_id = await session.scalar(
        select(User.id).where(User.email == normalized_email)
    )

    if existing_user_id is not None:
        raise EmailAlreadyRegisteredError

    password_hash = await asyncio.to_thread(hash_password, password)
    user = User(
        email=normalized_email,
        password_hash=password_hash,
        first_name=first_name,
        last_name=last_name,
        default_address=Address(
            first_line=address.first_line,
            second_line=address.second_line or None,
            postal_code=address.postal_code,
            city=address.city,
            country=address.country,
        ),
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing_user_id = await session.scalar(
            select(User.id).where(User.email == normalized_email)
        )
        if existing_user_id is not None:
            raise EmailAlreadyRegisteredError from None
        raise

    return user


async def authenticate_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
) -> AuthTokens:
    normalized_email = normalize_email(email)
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


async def request_password_reset(
    session: AsyncSession,
    *,
    email: str,
) -> str | None:
    reset_token = generate_password_reset_token()
    token_hash = hash_password_reset_token(reset_token)
    normalized_email = email.strip().casefold()
    user = await session.scalar(
        select(User).where(User.email == normalized_email).with_for_update()
    )

    if user is None:
        await session.rollback()
        return None

    await session.execute(
        delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(seconds=settings.password_reset_expiration),
        )
    )
    await session.commit()

    return reset_token


async def validate_password_reset_token(
    session: AsyncSession,
    *,
    token: str,
) -> str:
    now = datetime.datetime.now(datetime.UTC)
    email = await session.scalar(
        select(User.email)
        .join(
            PasswordResetToken,
            PasswordResetToken.user_id == User.id,
        )
        .where(
            PasswordResetToken.token_hash == hash_password_reset_token(token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )

    if email is None:
        raise InvalidPasswordResetTokenError

    return email


async def confirm_password_reset(
    session: AsyncSession,
    *,
    token: str,
    new_password: str,
) -> None:
    token_hash = hash_password_reset_token(token)
    user_id = await session.scalar(
        select(PasswordResetToken.user_id).where(
            PasswordResetToken.token_hash == token_hash
        )
    )

    if user_id is None:
        raise InvalidPasswordResetTokenError

    user = await session.get(User, user_id, with_for_update=True)
    reset_token = await session.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .with_for_update()
    )
    now = datetime.datetime.now(datetime.UTC)

    if (
        user is None
        or reset_token is None
        or reset_token.used_at is not None
        or reset_token.expires_at <= now
    ):
        raise InvalidPasswordResetTokenError

    user.password_hash = await asyncio.to_thread(hash_password, new_password)

    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    await session.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    await session.commit()


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
