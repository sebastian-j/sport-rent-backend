from datetime import date

from pydantic import BaseModel, Field


# konkretny termin wypożyczenia dla produktu (RentalDate)
class CartItemDate(BaseModel):
    id: int
    quantity: int = Field(ge=1)
    size: str | None = None
    start_date: date
    end_date: date


# zgrupowany produkt w koszyku - CartProduct
class CartItemResponse(BaseModel):
    product_id: int
    product_name: str
    image: str
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


class SubmitCartRequest(BaseModel):
    promo_code: str | None = None


class SubmitCartResponse(BaseModel):
    order_id: int
    status: str = "confirmed"


class PromoCodeValidationRequest(BaseModel):
    promo_code: str


class PromoCodeValidationResponse(BaseModel):
    discount_rate: float | None = Field(default=None, ge=0, le=1)
