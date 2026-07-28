import datetime
from time import sleep
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_helpers import (
    delete_csrf_cookie,
    delete_refresh_cookie,
    generate_csrf_token,
    invalid_refresh_token,
    require_csrf,
    set_csrf_cookie,
    set_refresh_cookie,
    unauthorized,
)
from app.core.config import settings
from app.db.session import get_db_session
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    ConfirmPasswordResetRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    ValidatePasswordResetRequest,
    ValidatePasswordResetResponse,
)
from app.services.auth import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidPasswordResetTokenError,
    InvalidRefreshTokenError,
    RegistrationAddress,
    authenticate_user,
    confirm_password_reset,
    request_password_reset,
    register_user,
    revoke_auth_session,
    rotate_refresh_token,
    validate_password_reset_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
)
async def register(
    request: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    try:
        user = await register_user(
            session,
            email=str(request.email),
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            address=RegistrationAddress(
                first_line=request.address.first_line,
                second_line=request.address.second_line,
                postal_code=request.address.postal_code,
                city=request.address.city,
                country=request.address.country,
            ),
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered",
        ) from None

    return RegisterResponse(id=user.id, email=user.email)


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
    set_csrf_cookie(
        response,
        token=generate_csrf_token(),
        max_age=settings.csrf_expiration,
    )

    return AccessTokenResponse(
        access_token=tokens.access_token.token,
        token_type="bearer",
        expires_in=settings.jwt_access_expiration,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    refresh_token_cookie: Annotated[
        str | None,
        Cookie(alias="refresh_token"),
    ] = None,
):
    require_csrf(request)

    if refresh_token_cookie is None:
        raise invalid_refresh_token()

    try:
        tokens = await rotate_refresh_token(session, refresh_token_cookie)
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
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    refresh_token_cookie: Annotated[
        str | None,
        Cookie(alias="refresh_token"),
    ] = None,
):
    require_csrf(request)

    delete_refresh_cookie(response)
    delete_csrf_cookie(response)

    if refresh_token_cookie is None:
        return None

    await revoke_auth_session(session, refresh_token_cookie)

    return None


@router.post("/reset-password", status_code=204)
async def reset_password(
    request: ResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    reset_token = await request_password_reset(
        session,
        email=str(request.email),
    )

    if reset_token is not None:
        fragment = urlencode({"token": reset_token})
        print(
            "Password reset link: "
            f"{settings.frontend_url}/reset-password/confirm#{fragment}",
            flush=True,
        )

    return None


@router.post(
    "/reset-password/validate",
    response_model=ValidatePasswordResetResponse,
)
async def validate_password_reset(
    request: ValidatePasswordResetRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    try:
        email = await validate_password_reset_token(
            session,
            token=request.token,
        )
    except InvalidPasswordResetTokenError:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired password reset link",
        ) from None

    response.headers["Cache-Control"] = "no-store"
    return ValidatePasswordResetResponse(email=email)


@router.post("/reset-password/confirm", status_code=204)
async def confirm_reset_password(
    request: ConfirmPasswordResetRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    try:
        await confirm_password_reset(
            session,
            token=request.token,
            new_password=request.new_password,
        )
    except InvalidPasswordResetTokenError:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired password reset link",
        ) from None

    delete_refresh_cookie(response)
    delete_csrf_cookie(response)
    response.headers["Cache-Control"] = "no-store"

    return None


# TODO: MOCK
@router.post("/change-password", status_code=204)
def change_password(request: ChangePasswordRequest):
    sleep(1)
    return None
