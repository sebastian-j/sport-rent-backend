from datetime import datetime

from pydantic import BaseModel


class LoyaltyResponse(BaseModel):
    balance: int


class LoyaltyHistoryItemResponse(BaseModel):
    id: int
    created_at: datetime
    amount: int
    order_id: int


class LoyaltyHistoryResponse(BaseModel):
    items: list[LoyaltyHistoryItemResponse]
    balance: int
