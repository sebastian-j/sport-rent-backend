from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.schemas.loyalty import (
    LoyaltyHistoryItemResponse,
    LoyaltyHistoryResponse,
    LoyaltyResponse,
)
from app.services import loyalty as loyalty_service

router = APIRouter(prefix="/loyalty", tags=["loyalty"])

CurrentUser = Annotated[int, Depends(get_current_user_id)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=LoyaltyResponse)
async def get_points(
    user_id: CurrentUser,
    session: DatabaseSession,
) -> LoyaltyResponse:
    lifetime_spend = await loyalty_service.get_lifetime_qualifying_spend(
        session,
        user_id,
    )
    return LoyaltyResponse(
        balance=await loyalty_service.get_balance(session, user_id),
        lifetime_qualifying_spend=float(lifetime_spend),
        redemption_unlocked=(
            lifetime_spend >= loyalty_service.LOYALTY_PROGRAM_UNLOCK_SPEND
        ),
        unlock_spend_required=float(loyalty_service.LOYALTY_PROGRAM_UNLOCK_SPEND),
    )


@router.get("/history", response_model=LoyaltyHistoryResponse)
async def get_points_history(
    user_id: CurrentUser,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
) -> LoyaltyHistoryResponse:
    transactions, total = await loyalty_service.get_history(
        session,
        user_id,
        page=page,
        page_size=page_size,
    )

    return LoyaltyHistoryResponse(
        items=[
            LoyaltyHistoryItemResponse(
                id=transaction.id,
                created_at=transaction.created_at,
                expires_at=transaction.expires_at,
                amount=transaction.amount,
                order_id=transaction.order_id,
                type=transaction.type,
                description=transaction.description,
            )
            for transaction in transactions
        ],
        balance=await loyalty_service.get_balance(session, user_id),
        page=page,
        pageSize=page_size,
        total=total,
        totalPages=(total + page_size - 1) // page_size,
    )
