from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_optional_current_user_id
from app.db.session import get_db_session
from app.schemas.product import (
    ProductAvailabilityCalendarResponse,
    ProductAvailabilityResponse,
    ProductFacetsResponse,
    ProductQueryParams,
    ProductResponse,
)
from app.services import product as product_service

router = APIRouter(prefix="/product", tags=["product"])

OptionalUser = Annotated[int | None, Depends(get_optional_current_user_id)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def not_found(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


def invalid_request(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
    )


@router.get("", response_model=list[ProductResponse])
async def get_products(
    params: Annotated[ProductQueryParams, Query()],
    user_id: OptionalUser,
    session: DatabaseSession,
):
    return await product_service.get_products(session, params, user_id)


@router.get("/count", response_model=ProductFacetsResponse)
async def get_categories_count(
    params: Annotated[ProductQueryParams, Query()],
    session: DatabaseSession,
):
    return await product_service.get_product_facets(session, params)


@router.get("/{product_slug}", response_model=ProductResponse)
async def get_product(
    product_slug: str,
    user_id: OptionalUser,
    session: DatabaseSession,
):
    try:
        return await product_service.get_product(session, product_slug, user_id)
    except product_service.ProductNotFoundError as error:
        raise not_found(error) from error


@router.get("/{product_slug}/accessories", response_model=list[ProductResponse])
async def get_product_accessories(
    product_slug: str,
    user_id: OptionalUser,
    session: DatabaseSession,
) -> list[ProductResponse]:
    try:
        return await product_service.get_product_accessories(
            session, product_slug, user_id
        )
    except product_service.ProductNotFoundError as error:
        raise not_found(error) from error


@router.get("/{product_slug}/availability", response_model=ProductAvailabilityResponse)
async def get_product_availability(
    product_slug: str,
    start_date: date,
    end_date: date,
    session: DatabaseSession,
    size: str | None = None,
):
    try:
        return await product_service.get_product_availability(
            session,
            product_slug,
            start_date,
            end_date,
            size,
        )
    except product_service.InvalidDateRangeError as error:
        raise invalid_request(error) from error
    except product_service.ProductNotFoundError as error:
        raise not_found(error) from error


@router.get(
    "/{product_slug}/availability-calendar",
    response_model=ProductAvailabilityCalendarResponse,
)
async def get_product_availability_calendar(
    product_slug: str,
    session: DatabaseSession,
    quantity: Annotated[int, Query(ge=1, le=100)] = 1,
    size: str | None = None,
) -> ProductAvailabilityCalendarResponse:
    try:
        return await product_service.get_product_availability_calendar(
            session,
            product_slug,
            quantity,
            size,
        )
    except product_service.ProductNotFoundError as error:
        raise not_found(error) from error
