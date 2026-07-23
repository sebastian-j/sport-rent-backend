import json

from fastapi import APIRouter, HTTPException

from app.schemas.product import ProductAvailabilityResponse, ProductResponse

router = APIRouter(prefix="/product", tags=["product"])

products_file_path = "app/api/mock_products.json"

with open(products_file_path, encoding="utf-8") as f:
    products = json.load(f)["products"]


@router.get("", response_model=list[ProductResponse])
async def get_products(filter: str = None, page: int = 1, page_size: int = 10):
    filtered_products = products

    if filter:
        filtered_products = [
            product
            for product in filtered_products
            if filter.lower() in product.get("name", "").lower()
        ]

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
