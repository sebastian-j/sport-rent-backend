import datetime
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_helpers import unauthorized
from app.core.tokens import decode_access_token
from app.db.session import get_db_session
from app.models import AuthSession

bearer_scheme = HTTPBearer(auto_error=False)


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


def get_optional_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> int | None:
    if credentials is None:
        return None
    token = credentials.credentials
    try:
        claims = decode_access_token(token)
        return claims.user_id
    except jwt.InvalidTokenError:
        return None
