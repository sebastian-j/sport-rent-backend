from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
import json

PAGE_SIZE = 10

router = APIRouter(prefix="/product", tags=["products"])

products_file_path = "app/api/mock_products.json"

with open(products_file_path, "r", encoding="utf-8") as f:
    products = json.load(f)["products"]

@router.get("/")
async def get_products(filter: str = None, page: int = 1):
    if filter:
        products_list = jsonable_encoder([product for product in products if filter.lower() in product['name'].lower()])
    if page:
        start_index = (page - 1) * PAGE_SIZE
        end_index = start_index + PAGE_SIZE
        products_list = jsonable_encoder(products[start_index:end_index])
    else:
        products_list = jsonable_encoder(products)
    return products_list

@router.get("/{product_id}")
async def get_product(product_id: int):
    product = next((product for product in products if product["id"] == product_id), None)
    if product:
        return jsonable_encoder(product)
    return {"error": "Product not found"}

@router.get("/{product_id}/availability")
async def get_product_availability(product_id: int, start_date: str, end_date: str):
    # TODO: Implement logic to check product availability
    return {"available": True}