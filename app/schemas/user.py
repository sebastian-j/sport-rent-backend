from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

StrippedString = Annotated[str, Field(strip_whitespace=True, min_length=1)]


class UpdateAddressRequest(BaseModel):
    first_name: StrippedString
    last_name: StrippedString
    city: StrippedString
    first_line: StrippedString
    second_line: Annotated[str, Field(strip_whitespace=True)] | None = None
    postal_code: StrippedString
    country: StrippedString


class UserResponse(BaseModel):
    email: str
    first_name: str
    last_name: str
    city: str
    first_line: str
    second_line: str | None
    postal_code: str
    country: str
    privacy_policy_accepted: bool


class UserHistoryItemResponse(BaseModel):
    id: int
    created_at: datetime
    status: str
    payment_code: str | None
    total: float


class OrderItemDetailsResponse(BaseModel):
    product_id: int
    product_name: str
    image: str | None
    size: str | None
    quantity: int
    start_date: datetime
    end_date: datetime
    unit_price: float


class OrderDetailResponse(BaseModel):
    id: int
    created_at: datetime
    status: str
    total: float
    discount: float | None
    items: list[OrderItemDetailsResponse]
