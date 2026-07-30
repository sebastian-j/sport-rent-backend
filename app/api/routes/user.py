import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth_helpers import unauthorized
from app.api.dependencies import get_current_user_id
from app.api.routes.product import products_file_path
from app.db.session import get_db_session
from app.models.address import Address
from app.models.user import User
from app.schemas.user import (
    OrderDetailResponse,
    OrderItemDetailsResponse,
    UpdateAddressRequest,
    UserHistoryItemResponse,
    UserResponse,
)
from app.services.image import get_image_as_base64

router = APIRouter(prefix="/user", tags=["user"])

users_file_path = "app/assets/mock_users.json"
address_file_path = "app/assets/mock_addresses.json"
history_file_path = "app/assets/mock_history.json"

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


@router.get("", response_model=UserResponse)
async def get_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    user = await session.scalar(
        select(User)
        .options(selectinload(User.default_address))
        .where(User.id == user_id)
    )

    if not user:
        raise unauthorized(
            "Could not validate credentials",
            bearer_challenge=True,
        )

    addr = user.default_address

    user_response = UserResponse(
        email=user.email,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        city=addr.city if addr else "",
        first_line=addr.first_line if addr else "",
        second_line=addr.second_line if addr else "",
        postal_code=addr.postal_code if addr else "",
        country=addr.country if addr else "",
        privacy_policy_accepted=True,
    )
    return user_response


@router.patch("/address", status_code=status.HTTP_204_NO_CONTENT)
async def update_address(
    request: UpdateAddressRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    user = await session.scalar(
        select(User)
        .options(selectinload(User.default_address))
        .where(User.id == user_id)
    )
    if not user:
        raise unauthorized("User not found")
    if request.first_name is not None:
        user.first_name = request.first_name
    if request.last_name is not None:
        user.last_name = request.last_name

    addr = user.default_address
    if not addr:
        addr = Address(
            first_line="",
            postal_code="",
            city="",
            country="",
        )
        user.default_address = addr
    if request.first_line is not None:
        addr.first_line = request.first_line
    if request.second_line is not None:
        addr.second_line = request.second_line
    if request.postal_code is not None:
        addr.postal_code = request.postal_code
    if request.city is not None:
        addr.city = request.city
    if request.country is not None:
        addr.country = request.country

    await session.commit()
    return None


@router.get("/history", response_model=list[UserHistoryItemResponse])
async def get_user_history(user_id: Annotated[int, Depends(get_current_user_id)]):
    user_history = [
        UserHistoryItemResponse(
            id=order["id"],
            created_at=order["created_at"],
            status=order["status"],
            payment_code=order["payment_code"],
            total=sum(item["price"] for item in order["items"]),
        )
        for order in history
        if order["user_id"] == user_id
    ]
    return user_history


@router.get("/history/{order_id}", response_model=OrderDetailResponse)
async def get_order_details(
    order_id: int, user_id: Annotated[int, Depends(get_current_user_id)]
):
    order = next(
        (order for order in history if order["id"] == order_id),
        None,
    )

    if not order or order["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Order not found")

    order_total = sum(i["price"] for i in order["items"])

    order_details = OrderDetailResponse(
        id=order["id"],
        created_at=order["created_at"],
        status=order["status"],
        total=order_total,
        discount=0.0,
        items=[
            OrderItemDetailsResponse(
                product_id=item["product_id"],
                product_name=next(
                    (p["name"] for p in products if p["id"] == item["product_id"]),
                    "Nieznany produkt",
                ),
                image=get_image_as_base64(
                    next(
                        (
                            p["images"][0]
                            for p in products
                            if p["id"] == item["product_id"] and p.get("images")
                        ),
                        None,
                    )
                ),
                size=item.get("size"),
                quantity=item.get("quantity", 1),
                start_date=item["startDate"],
                end_date=item["endDate"],
                unit_price=item["price"],
            )
            for item in order["items"]
        ],
    )
    return order_details
