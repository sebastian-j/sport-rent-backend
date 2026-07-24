import json
import os
import uuid
from time import sleep
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.security import (
    DUMMY_PASSWORD_HASH,
    JWT_ACCESS_EXPIRATION,
    JWT_REFRESH_EXPIRATION,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_password,
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

users_file_path = "app/api/mock_users.json"

with open(users_file_path, encoding="utf-8") as f:
    users = json.load(f)["users"]


AUTH_COOKIE_SECURE = (
    os.getenv("AUTH_COOKIE_SECURE", "true").strip().casefold() == "true"
)


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
        raise HTTPException(status_code=401, detail="Incorrect email or password")

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

    response.set_cookie(
        key="refresh_token",
        value=refresh_token.token,
        max_age=JWT_REFRESH_EXPIRATION,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/auth",
    )

    return AccessTokenResponse(
        access_token=access_token.token,
        token_type="bearer",
        expires_in=JWT_ACCESS_EXPIRATION,
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

        session_id = uuid.UUID(payload["sid"])
        user_id = int(payload["sub"])

        user = next((user for user in users if user["id"] == user_id), None)

        if user is None:
            raise HTTPException(
                status_code=401, detail="Could not validate refresh token"
            ) from None

        access_token = create_access_token(user["id"], session_id)

        return AccessTokenResponse(
            access_token=access_token.token,
            token_type="bearer",
            expires_in=JWT_ACCESS_EXPIRATION,
        )

    except jwt.InvalidTokenError, KeyError, TypeError, ValueError:
        raise HTTPException(
            status_code=401, detail="Could not validate refresh token"
        ) from None


# TODO: MOCK
@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/auth",
        secure=AUTH_COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
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
