import json

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

PAGE_SIZE = 10

router = APIRouter(prefix="/product", tags=["product"])

products_file_path = "app/api/mock_products.json"

with open(products_file_path, encoding="utf-8") as f:
    products = json.load(f)["products"]


@router.get("/")
async def get_products(filter: str = None, page: int = 1):
    if filter:
        products_list = jsonable_encoder(
            [
                product
                for product in products
                if filter.lower() in product["name"].lower()
            ]
        )
    if page:
        start_index = (page - 1) * PAGE_SIZE
        end_index = start_index + PAGE_SIZE
        products_list = jsonable_encoder(products[start_index:end_index])
    return products_list


@router.get("/{product_slug}")
async def get_product(product_slug: str):
    product = next(
        (product for product in products if product["slug"] == product_slug), None
    )
    if product:
        return jsonable_encoder(product)
    raise HTTPException(status_code=404, detail="Product not found")


@router.get("/{product_slug}/availability")
async def get_product_availability(product_slug: str, start_date: str, end_date: str):
    # TODO: Implement logic to check product availability
    return {"available": True}
