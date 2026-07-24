import json
import os
from time import sleep
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, HTTPException, Response

from app.core.security import (
    DUMMY_PASSWORD_HASH,
    JWT_ACCESS_EXPIRATION,
    JWT_REFRESH_EXPIRATION,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_password,
)
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

users_file_path = "app/api/mock_users.json"

with open(users_file_path, encoding="utf-8") as f:
    users = json.load(f)["users"]


AUTH_COOKIE_SECURE = (
    os.getenv("AUTH_COOKIE_SECURE", "true").strip().casefold() == "true"
)


# TODO: MOCK
@router.post("/login", response_model=AccessTokenResponse)
def login(request: LoginRequest, response: Response):
    email = str(request.email).strip().casefold()
    user = next((user for user in users if user["email"] == email), None)

    password_hash = user["password"] if user is not None else DUMMY_PASSWORD_HASH
    password_is_valid = verify_password(request.password, password_hash)

    if user is None or not password_is_valid:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(user["id"])
    refresh_token = create_refresh_token(user["id"])

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=JWT_REFRESH_EXPIRATION,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/auth",
    )

    return AccessTokenResponse(
        access_token=access_token, token_type="bearer", expires_in=JWT_ACCESS_EXPIRATION
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(refresh_token: Annotated[str | None, Cookie()] = None):
    if refresh_token is None:
        raise HTTPException(
            status_code=401,
            detail="Could not validate refresh token",
        )

    try:
        payload = decode_refresh_token(refresh_token)
        user_id = int(payload["sub"])

        user = next((user for user in users if user["id"] == user_id), None)

        if user is None:
            raise HTTPException(
                status_code=401, detail="Could not validate refresh token"
            ) from None

        access_token = create_access_token(user["id"])

        return AccessTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_ACCESS_EXPIRATION,
        )

    except jwt.InvalidTokenError, KeyError, TypeError, ValueError:
        raise HTTPException(
            status_code=401, detail="Could not validate refresh token"
        ) from None


# TODO: MOCK
@router.post("/logout")
def logout(request: LogoutRequest):
    return


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
