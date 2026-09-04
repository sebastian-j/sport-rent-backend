from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_helpers import unauthorized
from app.api.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.schemas.user import (
    OrderDetailResponse,
    PaginatedUserHistoryResponse,
    UpdateAddressRequest,
    UserResponse,
)
from app.services import user as user_service

router = APIRouter(prefix="/user", tags=["user"])

CurrentUser = Annotated[int, Depends(get_current_user_id)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def not_found(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.get("", response_model=UserResponse)
async def get_user(
    user_id: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await user_service.get_user(session, user_id)
    except user_service.UserNotFoundError as error:
        raise unauthorized(str(error), bearer_challenge=True) from error


@router.patch("/address", status_code=status.HTTP_204_NO_CONTENT)
async def update_personal_address(
    request: UpdateAddressRequest,
    user_id: CurrentUser,
    session: DatabaseSession,
):
    try:
        await user_service.update_personal_address(session, user_id, request)
    except user_service.UserNotFoundError as error:
        raise unauthorized(str(error)) from error


@router.get("/history", response_model=PaginatedUserHistoryResponse)
async def get_user_history(
    user_id: CurrentUser,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
):
    return await user_service.get_user_history(
        session,
        user_id,
        page=page,
        page_size=page_size,
    )


@router.get("/history/{order_id}", response_model=OrderDetailResponse)
async def get_order_details(
    order_id: int,
    user_id: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await user_service.get_order_details(session, user_id, order_id)
    except user_service.OrderNotFoundError as error:
        raise not_found(error) from error
