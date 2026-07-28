from datetime import date

from pydantic import BaseModel, Field


class CartItemDate(BaseModel):
    id: int
    quantity: int = Field(ge=1)
    size: str | None = None
    start_date: date
    end_date: date


class CartItemResponse(BaseModel):
    product_id: int
    product_name: str
    image: str
    alt: str | None = None
    price: float
    dates: list[CartItemDate]


class AddToCartRequest(BaseModel):
    product_id: int
    start_date: date
    end_date: date
    quantity: int = Field(default=1, ge=1)
    size: str | None = None


class UpdateCartItemRequest(BaseModel):
    quantity: int | None = Field(default=None, ge=1)
    size: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class PromoCodeValidationRequest(BaseModel):
    promo_code: str


class PromoCodeValidationResponse(BaseModel):
    discount_rate: float | None = Field(default=None, ge=0, le=1)
