from time import sleep
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.schemas.cart import (
    AddToCartRequest,
    CartItemDate,
    CartItemResponse,
    CartStatusResponse,
    PromoCodeValidationRequest,
    PromoCodeValidationResponse,
    UpdateCartItemRequest,
)
from app.services import cart as cart_service

router = APIRouter(prefix="/cart", tags=["cart"])

CurrentUser = Annotated[int, Depends(get_current_user_id)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=list[CartItemResponse], summary="Szczegóły koszyka")
async def get_cart():
    if not products:
        return []

    product = products[0]
    return [
        CartItemResponse(
            product_id=product["id"],
            product_name=product["name"],
            image=product["images"][0] if product.get("images") else "",
            alt=product["imageAlts"][0],
            price=product["price"],
            dates=[
                CartItemDate(
                    id=101,
                    start_date="2026-08-01",
                    end_date="2026-08-05",
                    quantity=1,
                    size=product["sizes"][0] if product.get("sizes") else None,
                )
            ],
        )
    ]


@router.post("", status_code=204, summary="Dodanie produktu do koszyka")
async def add_to_cart(request: AddToCartRequest):
    sleep(0.2)
    product = next((p for p in products if p["id"] == request.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return
  
  
def not_found(error: cart_service.CartItemNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


def invalid_request(error: cart_service.CartValidationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
    )


@router.get("", response_model=list[CartItemResponse], summary="Szczegóły koszyka")
async def get_cart(user_id: CurrentUser, session: DatabaseSession):
    return await cart_service.get_cart(session, user_id)


@router.get(
    "/status",
    response_model=CartStatusResponse,
    summary="Informacja, czy koszyk zawiera produkty",
)
async def get_cart_status(user_id: CurrentUser, session: DatabaseSession):
    return CartStatusResponse(
        has_items=await cart_service.has_cart_items(session, user_id)
    )


@router.post(
    "/items",
    response_model=CartItemDate,
    status_code=status.HTTP_201_CREATED,
    summary="Dodanie terminu do koszyka",
)
async def add_to_cart(
    request: AddToCartRequest, user_id: CurrentUser, session: DatabaseSession
):
    try:
        item = await cart_service.add_item(session, user_id, request)
    except cart_service.CartItemNotFoundError as error:
        raise not_found(error) from error
    except cart_service.CartValidationError as error:
        raise invalid_request(error) from error
    return cart_service.item_response(item)


@router.patch(
    "/items/{item_id}",
    response_model=CartItemDate,
    summary="Zmiana szczegółów terminu w koszyku",
)
async def update_cart_item(
    item_id: int,
    request: UpdateCartItemRequest,
    user_id: CurrentUser,
    session: DatabaseSession,
):
    try:
        item = await cart_service.update_item(session, user_id, item_id, request)
    except cart_service.CartItemNotFoundError as error:
        raise not_found(error) from error
    except cart_service.CartValidationError as error:
        raise invalid_request(error) from error
    return cart_service.item_response(item)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Usunięcie terminu z koszyka",
)
async def remove_cart_item(
    item_id: int, user_id: CurrentUser, session: DatabaseSession
):
    try:
        await cart_service.remove_item(session, user_id, item_id)
    except cart_service.CartItemNotFoundError as error:
        raise not_found(error) from error


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Całkowite usunięcie produktu z koszyka",
)
async def remove_product_from_cart(
    product_id: int, user_id: CurrentUser, session: DatabaseSession
):
    try:
        await cart_service.remove_product(session, user_id, product_id)
    except cart_service.CartItemNotFoundError as error:
        raise not_found(error) from error


# TODO: MOCK
@router.post(
    "/promo-code/validate",
    response_model=PromoCodeValidationResponse,
    summary="Sprawdź kod promocyjny",
    response_description="Wartość rabatu przypisana do kodu promocyjnego",
)
def validate_promo_code(request: PromoCodeValidationRequest):
    if request.promo_code.upper().startswith("D"):
        sleep(1)
    if request.promo_code.upper().endswith("SPORT10"):
        return PromoCodeValidationResponse(discount_rate=0.1)
    return PromoCodeValidationResponse()
