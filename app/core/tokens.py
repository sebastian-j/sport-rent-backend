import datetime
import uuid
from dataclasses import dataclass
from typing import Literal

import jwt

from app.core.config import settings

TokenType = Literal["access", "refresh"]

_REQUIRED_CLAIMS = [
    "sub",
    "sid",
    "type",
    "jti",
    "iat",
    "exp",
    "iss",
    "aud",
]


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    jti: uuid.UUID
    issued_at: datetime.datetime
    expires_at: datetime.datetime


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: int
    session_id: uuid.UUID
    token_id: uuid.UUID
    token_type: TokenType
    issued_at: datetime.datetime
    expires_at: datetime.datetime


def _decode_token(
    token: str,
    *,
    secret: str,
    expected_type: TokenType,
) -> TokenClaims:
    payload = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": _REQUIRED_CLAIMS},
    )

    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError("Invalid token type")

    try:
        subject = payload["sub"]
        session_id = payload["sid"]
        token_id = payload["jti"]
        issued_at_timestamp = payload["iat"]
        expires_at_timestamp = payload["exp"]

        if not all(isinstance(value, str) for value in (subject, session_id, token_id)):
            raise ValueError

        if (
            type(issued_at_timestamp) is not int
            or type(expires_at_timestamp) is not int
        ):
            raise ValueError

        user_id = int(subject)

        if user_id <= 0 or str(user_id) != subject:
            raise ValueError

        issued_at = datetime.datetime.fromtimestamp(
            issued_at_timestamp,
            datetime.UTC,
        )
        expires_at = datetime.datetime.fromtimestamp(
            expires_at_timestamp,
            datetime.UTC,
        )

        if expires_at <= issued_at:
            raise ValueError

        return TokenClaims(
            user_id=user_id,
            session_id=uuid.UUID(session_id),
            token_id=uuid.UUID(token_id),
            token_type=expected_type,
            issued_at=issued_at,
            expires_at=expires_at,
        )
    except KeyError, OSError, OverflowError, TypeError, ValueError:
        raise jwt.InvalidTokenError("Invalid token claims") from None


def create_access_token(
    user_id: int,
    session_id: uuid.UUID,
) -> IssuedToken:
    issued_at = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
    expires_at = issued_at + datetime.timedelta(seconds=settings.jwt_access_expiration)
    jti = uuid.uuid4()

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": "access",
        "jti": str(jti),
        "iat": issued_at,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }

    token = jwt.encode(
        payload,
        settings.jwt_access_secret,
        algorithm="HS256",
    )

    return IssuedToken(
        token=token,
        jti=jti,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def decode_access_token(token: str) -> TokenClaims:
    return _decode_token(
        token,
        secret=settings.jwt_access_secret,
        expected_type="access",
    )


def encode_refresh_token(
    user_id: int,
    session_id: uuid.UUID,
    jti: uuid.UUID,
    issued_at: datetime.datetime,
    expires_at: datetime.datetime,
) -> IssuedToken:
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": "refresh",
        "jti": str(jti),
        "iat": issued_at,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }

    token = jwt.encode(
        payload,
        settings.jwt_refresh_secret,
        algorithm="HS256",
    )

    return IssuedToken(
        token=token,
        jti=jti,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def create_refresh_token(
    user_id: int,
    session_id: uuid.UUID,
) -> IssuedToken:
    issued_at = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
    expires_at = issued_at + datetime.timedelta(seconds=settings.jwt_refresh_expiration)

    return encode_refresh_token(
        user_id=user_id,
        session_id=session_id,
        jti=uuid.uuid4(),
        issued_at=issued_at,
        expires_at=expires_at,
    )


def decode_refresh_token(token: str) -> TokenClaims:
    return _decode_token(
        token,
        secret=settings.jwt_refresh_secret,
        expected_type="refresh",
    )
