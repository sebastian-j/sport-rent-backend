import json
from time import sleep

from fastapi import APIRouter, HTTPException

from app.core.security import (
    JWT_ACCESS_EXPIRATION,
    create_access_token,
    verify_password,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

users_file_path = "app/api/mock_users.json"

with open(users_file_path, encoding="utf-8") as f:
    users = json.load(f)["users"]


# TODO: MOCK
@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    email = str(request.email).strip().casefold()
    user = next((user for user in users if user["email"] == email), None)

    if user is None or not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(user["id"])

    return LoginResponse(
        access_token=access_token, token_type="bearer", expires_in=JWT_ACCESS_EXPIRATION
    )


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
