from datetime import date, datetime

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
    points_to_spend: int = Field(default=0, ge=0)


class OrderInstanceResponse(BaseModel):
    product_id: int
    product_name: str
    image: str | None
    size: str | None
    quantity: int
    start_date: date
    end_date: date
    price: float


class OrderResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    status: OrderStatus
    payment_code: str | None
    total_price: float
    discount: float
    used_points: bool
    address: OrderAddressRequest
    instances: list[OrderInstanceResponse]


class PaginatedOrdersResponse(BaseModel):
    items: list[OrderResponse]
    page: int
    pageSize: int
    total: int
    totalPages: int
