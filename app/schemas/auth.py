from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
AddressLine = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
OptionalAddressLine = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=255),
]
PostalCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=32),
]


class RegisterAddressRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_line: AddressLine
    second_line: OptionalAddressLine | None = None
    postal_code: PostalCode
    city: ShortText
    country: ShortText


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: Password
    first_name: ShortText
    last_name: ShortText
    address: RegisterAddressRequest


class RegisterResponse(BaseModel):
    id: int
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
