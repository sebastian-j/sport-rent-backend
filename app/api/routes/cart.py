from time import sleep

from fastapi import APIRouter, HTTPException
import json

from app.api.routes.product import products_file_path
from app.schemas.cart import (
    AddToCartRequest,
    CartItemResponse,
    CartItemDate,
    PromoCodeValidationRequest,
    PromoCodeValidationResponse,
    SubmitCartRequest,
    SubmitCartResponse,
    UpdateCartItemRequest,
)

router = APIRouter(prefix="/cart", tags=["cart"])

with open(products_file_path, encoding="utf-8") as f:
    products = json.load(f)["products"]


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
            price=product["price"],
            dates=[
                CartItemDate(
                    id=101,
                    start_date="2026-08-01", 
                    end_date="2026-08-05",
                    quantity=1,
                    size="L" if product.get("sizes") else None
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


@router.delete("/{product_id}", status_code=204, summary="Całkowite usunięcie produktu z koszyka")
async def remove_product_from_cart(product_id: int):
    sleep(0.2)
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    return


@router.delete("/{product_id}/{cart_item_id}", status_code=204, summary="Usunięcie terminu z koszyka")
async def remove_cart_item_date(product_id: int, cart_item_id: int):
    sleep(0.2)
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    return


@router.patch("/{product_id}/{cart_item_id}", status_code=204, summary="Zmiana szczegółów terminu w koszyku")
async def update_cart_item(product_id: int, cart_item_id: int, request: UpdateCartItemRequest):
    sleep(0.2)
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    return


@router.post("/submit", response_model=SubmitCartResponse, summary="Potwierdzenie rezerwacji")
async def submit_cart(request: SubmitCartRequest):
    sleep(0.5)
    return SubmitCartResponse(order_id=101, status="confirmed")


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
