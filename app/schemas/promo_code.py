from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.promo_codes import DiscountType


class PromoCodeCreate(BaseModel):
    code: str = Field(max_length=100)
    discount_type: DiscountType
    discount_value: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    minimum_order_value: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    is_active: bool = True
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_uses: int | None = Field(default=None, gt=0)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        code = value.strip().upper()

        if not code:
            raise ValueError("Code cannot be empty")

        return code

    @model_validator(mode="after")
    def validate_values(self) -> PromoCodeCreate:
        if self.discount_type == DiscountType.PERCENTAGE and self.discount_value > 1:
            raise ValueError("Percentage discount cannot be greater than 1")

        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from > self.valid_until
        ):
            raise ValueError("valid_until must be after valid_from")

        return self


class PromoCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    minimum_order_value: Decimal | None
    is_active: bool
    valid_from: datetime | None
    valid_until: datetime | None
    created_at: datetime
    usage_count: int
    max_uses: int | None
