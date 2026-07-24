import datetime
import os
import uuid
from dataclasses import dataclass

import jwt
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

JWT_ACCESS_SECRET = os.environ["JWT_ACCESS_SECRET"]
JWT_ACCESS_EXPIRATION = int(os.environ["JWT_ACCESS_EXPIRATION"])
JWT_REFRESH_SECRET = os.environ["JWT_REFRESH_SECRET"]
JWT_REFRESH_EXPIRATION = int(os.environ["JWT_REFRESH_EXPIRATION"])
DUMMY_PASSWORD_HASH = password_hash.hash("dummy-password")
REFRESH_TOKEN_GRACE_PERIOD = datetime.timedelta(seconds=5)


if len(JWT_ACCESS_SECRET) < 32:
    raise ValueError("JWT_ACCESS_SECRET must be at least 32 characters long")
if len(JWT_REFRESH_SECRET) < 32:
    raise ValueError("JWT_REFRESH_SECRET must be at least 32 characters long")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


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
    expires_at = issued_at + datetime.timedelta(seconds=JWT_ACCESS_EXPIRATION)
    jti = uuid.uuid4()

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": "access",
        "jti": str(jti),
        "iat": issued_at,
        "exp": expires_at,
        "iss": "sport-rent-backend",
        "aud": "sport-rent-backend",
    }

    token = jwt.encode(
        payload,
        JWT_ACCESS_SECRET,
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
        JWT_ACCESS_SECRET,
        algorithms=["HS256"],
        audience="sport-rent-backend",
        issuer="sport-rent-backend",
        options={"require": ["sub", "sid", "type", "jti", "iat", "exp", "iss", "aud"]},
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
        "iss": "sport-rent-backend",
        "aud": "sport-rent-backend",
    }

    token = jwt.encode(
        payload,
        JWT_REFRESH_SECRET,
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
    expires_at = issued_at + datetime.timedelta(seconds=JWT_REFRESH_EXPIRATION)

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
        JWT_REFRESH_SECRET,
        algorithms=["HS256"],
        audience="sport-rent-backend",
        issuer="sport-rent-backend",
        options={"require": ["sub", "sid", "type", "jti", "iat", "exp", "iss", "aud"]},
    )
    if payload["type"] != "refresh":
        raise jwt.InvalidTokenError("Invalid token type")

    return payload
