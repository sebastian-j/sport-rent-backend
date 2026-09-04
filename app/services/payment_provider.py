from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from app.models.payment import PaymentStatus


@dataclass(frozen=True, slots=True)
class PaymentProviderResult:
    provider_payment_id: str
    status: PaymentStatus
    redirect_url: str | None = None


class PaymentProvider(Protocol):
    name: str

    async def create_payment(
        self,
        *,
        reference: str,
        amount: Decimal,
        currency: str,
    ) -> PaymentProviderResult: ...


class MockPaymentProvider:
    name = "mock"

    async def create_payment(
        self,
        *,
        reference: str,
        amount: Decimal,
        currency: str,
    ) -> PaymentProviderResult:
        return PaymentProviderResult(
            provider_payment_id=f"mock-{uuid4()}",
            status=PaymentStatus.SUCCEEDED,
        )
