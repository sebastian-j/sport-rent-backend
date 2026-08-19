from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.promo_codes import DiscountType


class CartProductSize(BaseModel):
    size: str
    description: str | None = None


class CartItemDate(BaseModel):
    id: int
    quantity: int = Field(ge=1)
    size: str | None = None
    start_date: date
    end_date: date


class CartItemResponse(BaseModel):
    slug: str
    product_name: str
    image: str
    alt: str | None = None
    price: float
    sizes: list[CartProductSize]
    dates: list[CartItemDate]


class CartStatusResponse(BaseModel):
    has_items: bool


class AddToCartRequest(BaseModel):
    product_slug: str
    start_date: date
    end_date: date
    quantity: int = Field(default=1, ge=1)
    size: str | None = None


class UpdateCartItemRequest(BaseModel):
    quantity: int | None = Field(default=None, ge=1)
    size: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def ensure_not_empty(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class PromoCodeValidationRequest(BaseModel):
    promo_code: str


class PromoCodeValidationResponse(BaseModel):
    valid: bool
    discount_type: DiscountType | None = None
    discount_value: Decimal | None = None
    minimum_order_value: Decimal | None = None
