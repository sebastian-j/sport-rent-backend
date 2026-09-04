from datetime import datetime

from pydantic import BaseModel

from app.models.payment import PaymentStatus


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    status: PaymentStatus
    amount: float
    currency: str
    redirect_url: str | None
    created_at: datetime
    completed_at: datetime | None
