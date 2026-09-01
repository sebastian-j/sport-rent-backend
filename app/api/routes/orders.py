from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.schemas.order import (
    CreateOrderRequest,
    OrderResponse,
    PaginatedOrdersResponse,
)
from app.services import order as order_service
from app.services.order_addresses import (
    InvalidOrderAddressError,
    MissingDefaultAddressError,
)

router = APIRouter(prefix="/orders", tags=["orders"])

CurrentUser = Annotated[int, Depends(get_current_user_id)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def bad_request(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def not_found(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


def invalid_request(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
    )


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dodanie zamówienia",
)
async def create_order(
    request: CreateOrderRequest, user_id: CurrentUser, session: DatabaseSession
) -> OrderResponse:
    try:
        return await order_service.create_order(session, user_id, request)
    except order_service.EmptyCartError as error:
        raise bad_request(error) from error
    except order_service.PromoCodeInvalidError as error:
        raise invalid_request(error) from error
    except (InvalidOrderAddressError, MissingDefaultAddressError) as error:
        raise invalid_request(error) from error
    except order_service.OrderValidationError as error:
        raise invalid_request(error) from error


@router.get(
    "",
    response_model=PaginatedOrdersResponse,
    summary="Lista zamówień użytkownika",
)
async def get_orders(
    user_id: CurrentUser,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
) -> PaginatedOrdersResponse:
    items, total = await order_service.list_orders(
        session,
        user_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedOrdersResponse(
        items=items,
        page=page,
        pageSize=page_size,
        total=total,
        totalPages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Szczegóły zamówienia",
)
async def get_order(
    order_id: int, user_id: CurrentUser, session: DatabaseSession
) -> OrderResponse:
    try:
        return await order_service.get_order(session, user_id, order_id)
    except order_service.OrderNotFoundError as error:
        raise not_found(error) from error
