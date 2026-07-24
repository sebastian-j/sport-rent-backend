import datetime
import uuid
from dataclasses import dataclass

import jwt

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    jti: uuid.UUID
    issued_at: datetime.datetime
    expires_at: datetime.datetime


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


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.jwt_access_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={
            "require": [
                "sub",
                "sid",
                "type",
                "jti",
                "iat",
                "exp",
                "iss",
                "aud",
            ]
        },
    )
    if payload["type"] != "access":
        raise jwt.InvalidTokenError("Invalid token type")

    return payload


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


def decode_refresh_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.jwt_refresh_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={
            "require": [
                "sub",
                "sid",
                "type",
                "jti",
                "iat",
                "exp",
                "iss",
                "aud",
            ]
        },
    )
    if payload["type"] != "refresh":
        raise jwt.InvalidTokenError("Invalid token type")

    return payload
