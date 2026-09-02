from collections.abc import AsyncIterator
from datetime import date, datetime, time, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.hsqldb_reservation import HsqldbReservation
from app.models.product import Instance, Product
from app.services.cart import CartValidationError, validate_term
from app.services.order import OrderValidationError, _allocate_instances


@pytest_asyncio.fixture
async def hsqldb_blocked_product(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[tuple[Product, date]]:
    reserved_date = date.today() + timedelta(days=30)
    product = Product(
        name="HSQLDB availability product",
        description=None,
        price=10,
        slug=f"hsqldb-availability-{uuid4().hex}",
        meta_description=None,
        visibility_status=True,
        instances=[Instance(), Instance()],
    )

    async with test_session_factory.begin() as session:
        session.add(product)
        await session.flush()
        session.add(
            HsqldbReservation(
                source_position_id=900_001,
                instance_id=product.instances[0].id,
                begin_at=datetime.combine(reserved_date, time(10)),
                end_at=datetime.combine(reserved_date, time(18)),
                source_status=0,
            )
        )

    try:
        yield product, reserved_date
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(
                delete(HsqldbReservation).where(
                    HsqldbReservation.source_position_id == 900_001
                )
            )
            await session.execute(delete(Product).where(Product.id == product.id))


async def test_product_availability_excludes_hsqldb_reservation(
    client: AsyncClient,
    hsqldb_blocked_product: tuple[Product, date],
) -> None:
    product, reserved_date = hsqldb_blocked_product

    response = await client.get(
        f"/product/{product.slug}/availability",
        params={"start_date": reserved_date, "end_date": reserved_date},
    )

    assert response.status_code == 200
    assert response.json() == {"available": True, "availableQuantity": 1}

    response_after_reservation = await client.get(
        f"/product/{product.slug}/availability",
        params={
            "start_date": reserved_date + timedelta(days=1),
            "end_date": reserved_date + timedelta(days=1),
        },
    )

    assert response_after_reservation.status_code == 200
    assert response_after_reservation.json() == {
        "available": True,
        "availableQuantity": 2,
    }


async def test_cart_validation_excludes_hsqldb_reservation(
    test_session_factory: async_sessionmaker[AsyncSession],
    hsqldb_blocked_product: tuple[Product, date],
) -> None:
    product, reserved_date = hsqldb_blocked_product

    async with test_session_factory() as session:
        with pytest.raises(CartValidationError, match="exceeds available"):
            await validate_term(
                session,
                product_id=product.id,
                quantity=2,
                size=None,
                start_date=reserved_date,
                end_date=reserved_date,
            )


async def test_order_allocation_excludes_hsqldb_reservation(
    test_session_factory: async_sessionmaker[AsyncSession],
    hsqldb_blocked_product: tuple[Product, date],
) -> None:
    product, reserved_date = hsqldb_blocked_product

    async with test_session_factory() as session:
        with pytest.raises(OrderValidationError, match="Not enough available"):
            await _allocate_instances(
                session,
                product_id=product.id,
                size=None,
                start_date=reserved_date,
                end_date=reserved_date,
                quantity=2,
            )
