from datetime import datetime

from pydantic import BaseModel


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
    payment_code: str
    total: float


class OrderItemDetailResponse(BaseModel):
    product_id: int
    product_name: str | None
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
    discount: float
    items: list[OrderItemDetailResponse]
