from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.promo_codes import DiscountType, PromoCode
from app.schemas.promo_code import PromoCodeCreate
from app.services.promo_code import (
    PromoCodeAlreadyExistsError,
    create_promo_code,
    get_valid_promo_code,
)


async def test_create_percentage_promo_code_persists_it(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_promo_codes: None,
) -> None:
    request = PromoCodeCreate(
        code="  sport10  ",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("0.10"),
        minimum_order_value=Decimal("100.00"),
        max_uses=50,
    )

    async with test_session_factory() as session:
        created = await create_promo_code(session, request)
        created_id = created.id

    async with test_session_factory() as session:
        persisted = await session.get(PromoCode, created_id)

    assert persisted is not None
    assert persisted.code == "SPORT10"
    assert persisted.discount_type == DiscountType.PERCENTAGE
    assert persisted.discount_value == Decimal("0.1000")
    assert persisted.minimum_order_value == Decimal("100.00")
    assert persisted.is_active is True
    assert persisted.usage_count == 0
    assert persisted.max_uses == 50
    assert persisted.created_at is not None


async def test_create_fixed_amount_promo_code_persists_it(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_promo_codes: None,
) -> None:
    request = PromoCodeCreate(
        code="MINUS20",
        discount_type=DiscountType.FIXED_AMOUNT,
        discount_value=Decimal("20.00"),
    )

    async with test_session_factory() as session:
        created = await create_promo_code(session, request)

    assert created.id is not None
    assert created.discount_type == DiscountType.FIXED_AMOUNT
    assert created.discount_value == Decimal("20.0000")


async def test_create_promo_code_rejects_duplicate_code(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_promo_codes: None,
) -> None:
    first_request = PromoCodeCreate(
        code="SPORT10",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("0.10"),
    )
    duplicate_request = PromoCodeCreate(
        code=" sport10 ",
        discount_type=DiscountType.FIXED_AMOUNT,
        discount_value=Decimal("10.00"),
    )

    async with test_session_factory() as session:
        await create_promo_code(session, first_request)

    async with test_session_factory() as session:
        with pytest.raises(
            PromoCodeAlreadyExistsError,
            match="Promo code SPORT10 already exists",
        ):
            await create_promo_code(session, duplicate_request)


async def test_get_valid_promo_code_returns_normalized_match(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_promo_codes: None,
) -> None:
    now = datetime(2026, 8, 19, 12, tzinfo=UTC)
    request = PromoCodeCreate(
        code="SPORT10",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("0.10"),
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
        max_uses=1,
    )

    async with test_session_factory() as session:
        created = await create_promo_code(session, request)
        found = await get_valid_promo_code(session, " sport10 ", now=now)

    assert found is not None
    assert found.id == created.id


@pytest.mark.parametrize(
    ("request_overrides", "usage_count"),
    [
        ({"is_active": False}, 0),
        ({"valid_from": datetime(2026, 8, 20, tzinfo=UTC)}, 0),
        ({"valid_until": datetime(2026, 8, 18, tzinfo=UTC)}, 0),
        ({"max_uses": 1}, 1),
    ],
)
async def test_get_valid_promo_code_rejects_unavailable_code(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_promo_codes: None,
    request_overrides: dict[str, object],
    usage_count: int,
) -> None:
    now = datetime(2026, 8, 19, 12, tzinfo=UTC)
    request = PromoCodeCreate(
        code="UNAVAILABLE",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("0.10"),
        **request_overrides,
    )

    async with test_session_factory() as session:
        created = await create_promo_code(session, request)
        created.usage_count = usage_count
        await session.commit()

        found = await get_valid_promo_code(session, created.code, now=now)

    assert found is None
