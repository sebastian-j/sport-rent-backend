from fastapi import APIRouter, HTTPException

from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


# TODO: Add logic
@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    if request.email == "error":
        raise HTTPException(status_code=401, detail="Email or password is wrong")
    
    user_email = request.email
    user_password = request.password
    access_token = f"{user_email}_access_token"
    refresh_token = f"{user_password}_refresh_token"

    return LoginResponse(access_token=access_token, refresh_token=refresh_token)
