import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.schemas.product import (
    ProductAvailabilityResponse,
    ProductRequest,
    ProductResponse,
)

router = APIRouter(prefix="/product", tags=["product"])

products_file_path = "app/api/mock_products.json"

with open(products_file_path, encoding="utf-8") as f:
    products = json.load(f)["products"]


@router.get("", response_model=list[ProductResponse])
async def get_products(request: Annotated[ProductRequest, Query()]):
    sort = request.filter.sort if request.filter else None
    order = request.filter.order if request.filter else None
    min_price = request.filter.minPrice if request.filter else None
    max_price = request.filter.maxPrice if request.filter else None
    categories = request.filter.category if request.filter else None

    filtered_products = [
        product
        for product in products
        if (min_price is None or product.get("price", 0) >= min_price)
        and (max_price is None or product.get("price", 0) <= max_price)
        and (not categories or product.get("category") in categories)
    ]

    if sort and order:
        if sort == "price":
            filtered_products.sort(
                key=lambda x: x.get("price", 0), reverse=(order == "desc")
            )
        elif sort == "name":
            filtered_products.sort(
                key=lambda x: x.get("name", "").lower(), reverse=(order == "desc")
            )

    page = request.page or 1
    page_size = request.pageSize or 10

    start_index = (page - 1) * page_size
    end_index = start_index + page_size

    paginated_products = filtered_products[start_index:end_index]

    return paginated_products


@router.get("/{product_slug}", response_model=ProductResponse)
async def get_product(product_slug: str):
    product = next(
        (product for product in products if product.get("slug") == product_slug), None
    )

    if product:
        return product

    raise HTTPException(status_code=404, detail="Product not found")


@router.get("/{product_slug}/availability", response_model=ProductAvailabilityResponse)
async def get_product_availability(product_slug: str, start_date: str, end_date: str):
    return ProductAvailabilityResponse(available=True)
