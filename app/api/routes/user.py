from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth_helpers import unauthorized
from app.api.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.models.address import Address
from app.models.order import Order, OrderInstance
from app.models.product import Instance, Product
from app.models.user import User
from app.schemas.user import (
    OrderDetailResponse,
    OrderItemDetailsResponse,
    UpdateAddressRequest,
    UserHistoryItemResponse,
    UserResponse,
    PaginatedUserHistoryResponse
)
from app.services.image import get_image_as_base64

router = APIRouter(prefix="/user", tags=["user"])


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
async def update_personal_address(
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
    user.first_name = request.first_name
    user.last_name = request.last_name

    addr = user.default_address
    if not addr:
        addr = Address(
            first_line=request.first_line,
            second_line=request.second_line,
            postal_code=request.postal_code,
            city=request.city,
            country=request.country,
        )
        user.default_address = addr
    else:
        addr.first_line = request.first_line
        addr.second_line = request.second_line
        addr.postal_code = request.postal_code
        addr.city = request.city
        addr.country = request.country

    await session.commit()
    return None


@router.get("/history", response_model=PaginatedUserHistoryResponse)
async def get_user_history(
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
):
    total_orders = (
        await session.scalar(
            select(func.count(Order.id)).where(Order.user_id == user_id)
        )
    or 0
    )

    offset = (page - 1) * page_size
    orders = (
        (
            await session.scalars(
                select(Order)
                .options(selectinload(Order.instances))
                .where(Order.user_id == user_id)
                .order_by(Order.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        .unique()
        .all()
    )

    items = []
    for order in orders:
        order_total = 0
        for order_instance in order.instances:
            days = (order_instance.end_date - order_instance.start_date).days
            if days < 0:
                raise ValueError(
                    f"Rental #{order_instance.id}: end_date before start_date"
                )
            if days == 0:
                days = 1
            order_total += order_instance.price * days

        items.append(
            UserHistoryItemResponse(
                id=order.id,
                created_at=order.created_at,
                status=order.status.value,
                payment_code=str(order.payment_code) if order.payment_code else None,
                total=order_total,
            )
        )
    total_pages = (total_orders + page_size - 1) // page_size
    return PaginatedUserHistoryResponse(
        items=items,
        page=page,
        pageSize=page_size,
        total=total_orders,
        totalPages=total_pages,
    )


@router.get("/history/{order_id}", response_model=OrderDetailResponse)
async def get_order_details(
    order_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    order = (
        (
            await session.scalars(
                select(Order)
                .options(
                    selectinload(Order.instances)
                    .selectinload(OrderInstance.instance)
                    .selectinload(Instance.product)
                    .selectinload(Product.images)
                )
                .where(Order.id == order_id)
            )
        )
        .unique()
        .first()
    )

    if not order or order.user_id != user_id:
        raise HTTPException(status_code=404, detail="Order not found")

    total = 0
    items_response = []
    for order_instance in order.instances:
        product_obj = order_instance.instance.product

        image_b64 = None
        if product_obj.images:
            primary_img = next(
                (img for img in product_obj.images if img.display_order == 1),
                product_obj.images[0],
            )
            image_b64 = get_image_as_base64(primary_img.image)

        days = (order_instance.end_date - order_instance.start_date).days
        if days < 0:
            raise ValueError(f"Rental #{order_instance.id}: end_date before start_date")
        if days == 0:
            days = 1

        item_total = order_instance.price * days
        total += item_total

        items_response.append(
            OrderItemDetailsResponse(
                product_id=product_obj.id,
                product_name=product_obj.name,
                image=image_b64,
                size=order_instance.instance.size,
                quantity=1,
                start_date=datetime.combine(
                    order_instance.start_date, datetime.min.time()
                ),
                end_date=datetime.combine(order_instance.end_date, datetime.min.time()),
                unit_price=item_total,
            )
        )

    return OrderDetailResponse(
        id=order.id,
        created_at=order.created_at,
        status=order.status.value,
        total=total,
        discount=0.0,
        items=items_response,
    )
