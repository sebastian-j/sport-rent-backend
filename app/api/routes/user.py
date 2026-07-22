import json

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from app.api.routes.product import products_file_path

router = APIRouter(prefix="/user", tags=["user"])

users_file_path = "app/api/mock_users.json"
address_file_path = "app/api/mock_addresses.json"
history_file_path = "app/api/mock_history.json"

with open(users_file_path, encoding="utf-8") as f:
    users = json.load(f)["users"]

with open(address_file_path, encoding="utf-8") as f:
    addresses = json.load(f)["addresses"]

with open(history_file_path, encoding="utf-8") as f:
    history = json.load(f)["orders"]

with open(products_file_path, encoding="utf-8") as f:
    products = json.load(f)["products"]

for user in users:
    address_id = user.get("address_id")
    if address_id:
        address = next(
            (address for address in addresses if address["id"] == address_id), None
        )
        user["address"] = address


@router.get("/")
async def get_users():
    users_list = [
        [
            user["email"],
            user["address"]["first_name"],
            user["address"]["last_name"],
            user["address"]["city"],
            user["address"]["first_line"],
            user["address"]["second_line"],
            user["address"]["postal_code"],
            user["address"]["country"],
            user["privacy_policy_accepted"],
        ]
        for user in users
    ]
    return jsonable_encoder(users_list)


@router.get("/history")
async def get_user_history():
    MOCK_USER_ID = 1
    user_history = [
        [
            order["id"],
            order["created_at"],
            order["status"],
            order["payment_code"],
            sum(item["price"] for item in order["items"]),
        ]
        for order in history
        if order["user_id"] == MOCK_USER_ID
    ]
    return jsonable_encoder(user_history)


@router.get("/history/{order_id}")
async def get_order_details(order_id: int):
    order = next(
        (order for order in history if order["id"] == order_id),
        None,
    )

    if order:
        order_total = sum(i["price"] for i in order["items"])

        order_details = {
            "id": order["id"],
            "created_at": order["created_at"],
            "status": order["status"],
            "total": order_total,
            "discount": 0,
            "items": [
                {
                    "product_id": item["product_id"],
                    "product_name": next(
                        (p["name"] for p in products if p["id"] == item["product_id"]),
                        None,
                    ),
                    "image": next(
                        (
                            p["images"][0]
                            for p in products
                            if p["id"] == item["product_id"] and p.get("images")
                        ),
                        None,
                    ),
                    "size": item.get("size"),
                    "quantity": sum(
                        1
                        for x in order["items"]
                        if x["product_id"] == item["product_id"]
                    ),
                    "start_date": item["startDate"],
                    "end_date": item["endDate"],
                    "unit_price": item["price"],
                }
                for item in order["items"]
            ],
        }

        return jsonable_encoder(order_details)

    return {"error": "Order not found"}
