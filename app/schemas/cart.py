from pydantic import BaseModel, Field


class PromoCodeValidationRequest(BaseModel):
    promo_code: str


class PromoCodeValidationResponse(BaseModel):
    discount_rate: float | None = Field(default=None, ge=0, le=1)
