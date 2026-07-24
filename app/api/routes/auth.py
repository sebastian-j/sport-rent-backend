import datetime
from time import sleep
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_helpers import (
    delete_refresh_cookie,
    invalid_refresh_token,
    set_refresh_cookie,
    unauthorized,
)
from app.core.config import settings
from app.db.session import get_db_session
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
)
from app.services.auth import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    authenticate_user,
    revoke_auth_session,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AccessTokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    try:
        tokens = await authenticate_user(
            session,
            email=str(request.email),
            password=request.password,
        )
    except InvalidCredentialsError:
        raise unauthorized("Incorrect email or password") from None

    set_refresh_cookie(
        response,
        token=tokens.refresh_token.token,
        max_age=settings.jwt_refresh_expiration,
    )

    return AccessTokenResponse(
        access_token=tokens.access_token.token,
        token_type="bearer",
        expires_in=settings.jwt_access_expiration,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    if refresh_token is None:
        raise invalid_refresh_token()

    try:
        tokens = await rotate_refresh_token(session, refresh_token)
    except InvalidRefreshTokenError:
        raise invalid_refresh_token() from None

    now = datetime.datetime.now(datetime.UTC)

    set_refresh_cookie(
        response,
        token=tokens.refresh_token.token,
        max_age=max(
            0,
            int((tokens.refresh_token.expires_at - now).total_seconds()),
        ),
    )

    return AccessTokenResponse(
        access_token=tokens.access_token.token,
        token_type="bearer",
        expires_in=settings.jwt_access_expiration,
    )


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    delete_refresh_cookie(response)

    if refresh_token is None:
        return None

    await revoke_auth_session(session, refresh_token)

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
