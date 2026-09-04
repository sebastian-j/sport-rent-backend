import datetime
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_helpers import unauthorized
from app.core.config import settings
from app.core.tokens import decode_access_token
from app.db.session import get_db_session
from app.models import AuthSession
from app.services.email_sender import EmailSender, SmtpEmailSender
from app.services.password_reset_notifier import (
    EmailPasswordResetNotifier,
    PasswordResetNotifier,
)
from app.services.payment_provider import MockPaymentProvider, PaymentProvider

bearer_scheme = HTTPBearer(auto_error=False)
email_sender = SmtpEmailSender(
    host=settings.smtp_host,
    port=settings.smtp_port,
    username=settings.smtp_username,
    password=settings.smtp_password,
    use_tls=settings.smtp_use_tls,
    use_auth=settings.smtp_use_auth,
)
password_reset_notifier = EmailPasswordResetNotifier(
    frontend_url=settings.frontend_url,
    from_email=settings.smtp_from_email,
    email_sender=email_sender,
)
payment_provider = MockPaymentProvider()


def get_email_sender() -> EmailSender:
    return email_sender


def get_password_reset_notifier() -> PasswordResetNotifier:
    return password_reset_notifier


def get_payment_provider() -> PaymentProvider:
    return payment_provider


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> int:
    if credentials is None:
        raise unauthorized(
            "Authentication credentials were not provided",
            bearer_challenge=True,
        )
    token = credentials.credentials

    try:
        claims = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid token", bearer_challenge=True) from None

    now = datetime.datetime.now(datetime.UTC)
    auth_session = await session.scalar(
        select(AuthSession).where(
            AuthSession.id == claims.session_id,
            AuthSession.user_id == claims.user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
    )

    if auth_session is None:
        raise unauthorized("Invalid token", bearer_challenge=True)

    return claims.user_id


async def get_optional_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> int | None:
    if credentials is None:
        return None
    token = credentials.credentials

    try:
        claims = decode_access_token(token)
    except jwt.InvalidTokenError:
        return None

    now = datetime.datetime.now(datetime.UTC)
    auth_session = await session.scalar(
        select(AuthSession).where(
            AuthSession.id == claims.session_id,
            AuthSession.user_id == claims.user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
    )

    if auth_session is None:
        return None

    return claims.user_id
