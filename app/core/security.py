import datetime
import os
import uuid

import jwt
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

JWT_ACCESS_SECRET = os.environ["JWT_ACCESS_SECRET"]
JWT_ACCESS_EXPIRATION = int(os.environ["JWT_ACCESS_EXPIRATION"])
JWT_REFRESH_SECRET = os.environ["JWT_REFRESH_SECRET"]
JWT_REFRESH_EXPIRATION = int(os.environ["JWT_REFRESH_EXPIRATION"])
DUMMY_PASSWORD_HASH = password_hash.hash("dummy-password")


if len(JWT_ACCESS_SECRET) < 32:
    raise ValueError("JWT_ACCESS_SECRET must be at least 32 characters long")
if len(JWT_REFRESH_SECRET) < 32:
    raise ValueError("JWT_REFRESH_SECRET must be at least 32 characters long")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    iat = datetime.datetime.now(datetime.UTC)
    exp = iat + datetime.timedelta(seconds=JWT_ACCESS_EXPIRATION)
    data = {
        "sub": str(user_id),
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": iat,
        "exp": exp,
        "iss": "sport-rent-backend",
        "aud": "sport-rent-backend",
    }
    return jwt.encode(data, JWT_ACCESS_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        JWT_ACCESS_SECRET,
        algorithms=["HS256"],
        audience="sport-rent-backend",
        issuer="sport-rent-backend",
        options={"require": ["sub", "type", "jti", "iat", "exp", "iss", "aud"]},
    )
    if payload["type"] != "access":
        raise jwt.InvalidTokenError("Invalid token type")

    return payload


def create_refresh_token(user_id: int) -> str:
    iat = datetime.datetime.now(datetime.UTC)
    exp = iat + datetime.timedelta(seconds=JWT_REFRESH_EXPIRATION)
    data = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": iat,
        "exp": exp,
        "iss": "sport-rent-backend",
        "aud": "sport-rent-backend",
    }
    return jwt.encode(data, JWT_REFRESH_SECRET, algorithm="HS256")


def decode_refresh_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        JWT_REFRESH_SECRET,
        algorithms=["HS256"],
        audience="sport-rent-backend",
        issuer="sport-rent-backend",
        options={"require": ["sub", "type", "jti", "iat", "exp", "iss", "aud"]},
    )
    if payload["type"] != "refresh":
        raise jwt.InvalidTokenError("Invalid token type")

    return payload
