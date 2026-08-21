from datetime import datetime

from pydantic import BaseModel

from app.models.loyalty_transaction import LoyaltyTransactionType


class LoyaltyResponse(BaseModel):
    balance: int


class LoyaltyHistoryItemResponse(BaseModel):
    id: int
    created_at: datetime
    amount: int
    order_id: int | None
    type: LoyaltyTransactionType
    description: str | None


class LoyaltyHistoryResponse(BaseModel):
    items: list[LoyaltyHistoryItemResponse]
    balance: int
    page: int
    pageSize: int
    total: int
    totalPages: int
