import json
from time import sleep

from fastapi import APIRouter, HTTPException

from app.schemas.favorites import FavoritesResponse

router = APIRouter(prefix="/favorites", tags=["favorites"])

products_file_path = "app/api/mock_products.json"
with open(products_file_path, encoding="utf-8") as f:
    products = json.load(f)["products"]


@router.get("", response_model=list[FavoritesResponse])
async def get_favorites():
    return [
        FavoritesResponse(
            slug=product["slug"],
            name=product["name"],
            description=product["description"],
            image=product["images"][0],
            alt=product["alt"],
            price=product["price"],
        )
        for product in products[:10]
    ]


@router.post("/{product_slug}", status_code=204)
async def add_to_favorites(product_slug: str):
    sleep(0.33)
    product = next(
        (product for product in products if product["slug"] == product_slug),
        None,
    )

    if product is None or product_slug == "rower-gorski-mtb":
        raise HTTPException(status_code=404, detail="Product not found")

    return


@router.delete("/{product_slug}", status_code=204)
async def remove_from_favorites(product_slug: str):
    sleep(0.33)
    product = next(
        (product for product in products if product["slug"] == product_slug),
        None,
    )

    if product is None or product_slug == "rower-szosowy":
        raise HTTPException(status_code=404, detail="Product not found")

    return
