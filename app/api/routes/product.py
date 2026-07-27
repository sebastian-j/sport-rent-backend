import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.product import (
    CategoryResponse,
    ProductAvailabilityResponse,
    ProductQueryParams,
    ProductResponse,
)
from app.services.image import convert_images_to_base64

router = APIRouter(prefix="/product", tags=["product"])

products_file_path = "app/assets/mock_products.json"

with open(products_file_path, encoding="utf-8") as f:
    products = json.load(f)["products"]


@router.get("", response_model=list[ProductResponse])
async def get_products(params: Annotated[ProductQueryParams, Depends()]):
    sort = params.sort
    order = params.order
    min_price = params.minPrice
    max_price = params.maxPrice
    categories = params.category
    query = params.query

    filtered_products = [
        product
        for product in products
        if (min_price is None or product.get("price", 0) >= min_price)
        and (max_price is None or product.get("price", 0) <= max_price)
        and (not categories or product.get("category") in categories)
        and (not query or query.lower() in product.get("name", "").lower())
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

    page = params.page or 1
    page_size = params.pageSize or 10

    start_index = (page - 1) * page_size
    end_index = start_index + page_size

    paginated_products = filtered_products[start_index:end_index]

    results = []
    for p in paginated_products:
        p_copy = dict(p)
        p_copy["images"] = convert_images_to_base64(p_copy.get("images"))
        results.append(p_copy)

    return results


@router.get("/count", response_model=tuple[list[CategoryResponse], int])
async def get_categories_count(params: Annotated[ProductQueryParams, Depends()]):
    min_price = params.minPrice
    max_price = params.maxPrice
    search_query = params.query

    filtered_products = [
        product
        for product in products
        if (min_price is None or product.get("price", 0) >= min_price)
        and (max_price is None or product.get("price", 0) <= max_price)
        and (
            not search_query or search_query.lower() in product.get("name", "").lower()
        )
    ]

    category_count = {}
    for product in filtered_products:
        category = product.get("category")
        if category:
            category_count[category] = category_count.get(category, 0) + 1

    return (
        [{"name": cat, "count": count} for cat, count in category_count.items()],
        len(filtered_products),
    )


@router.get("/{product_slug}", response_model=ProductResponse)
async def get_product(product_slug: str):
    product = next(
        (product for product in products if product.get("slug") == product_slug), None
    )

    if product:
        p_copy = dict(product)
        p_copy["images"] = convert_images_to_base64(p_copy.get("images"))
        return p_copy

    raise HTTPException(status_code=404, detail="Product not found")


@router.get("/{product_slug}/availability", response_model=ProductAvailabilityResponse)
async def get_product_availability(product_slug: str, start_date: str, end_date: str):
    return ProductAvailabilityResponse(available=True)
