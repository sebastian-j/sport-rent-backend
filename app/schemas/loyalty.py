from datetime import datetime

from pydantic import BaseModel

from app.models.loyalty_transaction import LoyaltyTransactionType


class LoyaltyResponse(BaseModel):
    balance: int
    lifetime_qualifying_spend: float
    redemption_unlocked: bool
    unlock_spend_required: float


class LoyaltyHistoryItemResponse(BaseModel):
    id: int
    created_at: datetime
    expires_at: datetime | None
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
