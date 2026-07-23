from time import sleep

from fastapi import APIRouter, HTTPException

from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# TODO: MOCK
@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    if request.email.startswith("error"):
        raise HTTPException(status_code=401, detail="Email or password is wrong")

    user_email = request.email
    user_password = request.password
    access_token = f"{user_email}_access_token"
    refresh_token = f"{user_password}_refresh_token"

    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


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
