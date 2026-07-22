import json

from fastapi import APIRouter, HTTPException

from app.api.routes.products import products_file_path
from app.schemas.user import (
    OrderDetailResponse,
    OrderItemDetailResponse,
    UserHistoryItemResponse,
    UserResponse,
)

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


@router.get("/", response_model=list[UserResponse])
async def get_users():
    users_list = [
        UserResponse(
            email=user["email"],
            first_name=user["address"]["first_name"],
            last_name=user["address"]["last_name"],
            city=user["address"]["city"],
            first_line=user["address"]["first_line"],
            second_line=user["address"].get("second_line"),
            postal_code=user["address"]["postal_code"],
            country=user["address"]["country"],
            privacy_policy_accepted=user["privacy_policy_accepted"],
        )
        for user in users
    ]
    return users_list


@router.get("/history", response_model=list[UserHistoryItemResponse])
async def get_user_history():
    MOCK_USER_ID = 1
    user_history = [
        UserHistoryItemResponse(
            id=order["id"],
            created_at=order["created_at"],
            status=order["status"],
            payment_code=order["payment_code"],
            total=sum(item["price"] for item in order["items"]),
        )
        for order in history
        if order["user_id"] == MOCK_USER_ID
    ]
    return user_history


@router.get("/history/{order_id}", response_model=OrderDetailResponse)
async def get_order_details(order_id: int):
    order = next(
        (order for order in history if order["id"] == order_id),
        None,
    )

    if order:
        order_total = sum(i["price"] for i in order["items"])

        order_details = OrderDetailResponse(
            id=order["id"],
            created_at=order["created_at"],
            status=order["status"],
            total=order_total,
            discount=0.0,
            items=[
                OrderItemDetailResponse(
                    product_id=item["product_id"],
                    product_name=next(
                        (p["name"] for p in products if p["id"] == item["product_id"]),
                        None,
                    ),
                    image=next(
                        (
                            p["images"][0]
                            for p in products
                            if p["id"] == item["product_id"] and p.get("images")
                        ),
                        None,
                    ),
                    size=item.get("size"),
                    quantity=sum(
                        1
                        for x in order["items"]
                        if x["product_id"] == item["product_id"]
                    ),
                    start_date=item["startDate"],
                    end_date=item["endDate"],
                    unit_price=item["price"],
                )
                for item in order["items"]
            ],
        )
        return order_details

    raise HTTPException(status_code=404, detail="Order not found")
