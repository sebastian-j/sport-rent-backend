from datetime import date

from pydantic import BaseModel, Field

from app.models.order import OrderStatus


class OrderAddressRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    first_line: str = Field(min_length=1)
    second_line: str | None = None
    postal_code: str = Field(min_length=1)
    city: str = Field(min_length=1)
    country: str = Field(min_length=1)
    company: str | None = None
    nip: str | None = None


class CreateOrderRequest(BaseModel):
    address: OrderAddressRequest | None = None
    promo_code: str | None = None
    used_points: bool = False


class OrderInstanceResponse(BaseModel):
    product_name: str
    size: str | None
    start_date: date
    end_date: date
    price: float


class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    total_price: float
    used_points: bool
    address: OrderAddressRequest
    instances: list[OrderInstanceResponse]
