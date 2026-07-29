from datetime import date

from pydantic import BaseModel, Field, model_validator


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
    product_id: int
    product_name: str
    image: str
    alt: str | None = None
    price: float
    sizes: list[CartProductSize]
    dates: list[CartItemDate]


class CartStatusResponse(BaseModel):
    has_items: bool


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

    @model_validator(mode="after")
    def ensure_not_empty(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class PromoCodeValidationRequest(BaseModel):
    promo_code: str


class PromoCodeValidationResponse(BaseModel):
    discount_rate: float | None = Field(default=None, ge=0, le=1)
