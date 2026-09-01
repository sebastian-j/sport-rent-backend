from datetime import datetime

import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.hsqldb_reservation import HsqldbReservation
from app.models.product import Instance, Product
from app.schemas.hsqldb_sync import (
    HsqldbReservationSyncItem,
    HsqldbReservationSyncRequest,
)
from app.services.hsqldb_sync import synchronize_hsqldb_reservations


@pytest_asyncio.fixture
async def empty_hsqldb_reservations(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory.begin() as session:
        await session.execute(delete(HsqldbReservation))


async def add_product(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    name: str,
    hsqldb_name: str,
    inventory_codes: list[str | None],
) -> tuple[int, list[int]]:
    product = Product(
        name=name,
        hsqldb_name=hsqldb_name,
        description=None,
        price=10,
        slug=f"hsqldb-{name.lower().replace(' ', '-')}",
        meta_description=None,
        visibility_status=True,
        instances=[
            Instance(hsqldb_inventory_code=inventory_code)
            for inventory_code in inventory_codes
        ],
    )

    async with session_factory.begin() as session:
        session.add(product)
        await session.flush()
        return product.id, [instance.id for instance in product.instances]


def sync_item(
    source_position_id: int,
    *,
    product_name: str,
    inventory_code: str | None,
    source_status: int | None = 1,
    end_at: datetime | None = datetime(2026, 9, 5, 18),
) -> HsqldbReservationSyncItem:
    return HsqldbReservationSyncItem(
        source_position_id=source_position_id,
        begin_at=datetime(2026, 9, 1, 10),
        end_at=end_at,
        source_status=source_status,
        source_name=(
            f"{product_name} {inventory_code}"
            if inventory_code is not None
            else product_name
        ),
        product_name=product_name,
        inventory_code=inventory_code,
    )


async def test_matches_instance_by_product_name_and_inventory_code(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_hsqldb_reservations: None,
) -> None:
    _, instance_ids = await add_product(
        test_session_factory,
        name="Sync skis coded",
        hsqldb_name="Narty testowe",
        inventory_codes=["10001", "10002"],
    )
    request = HsqldbReservationSyncRequest(
        reservations=[
            sync_item(
                1001,
                product_name="Narty testowe",
                inventory_code="10002",
            )
        ]
    )

    async with test_session_factory() as session:
        await synchronize_hsqldb_reservations(session, request)

    async with test_session_factory() as session:
        reservation = await session.get(HsqldbReservation, 1001)

    assert reservation is not None
    assert reservation.instance_id == instance_ids[1]
    assert reservation.source_status == 1


async def test_matches_only_instance_when_inventory_code_is_missing(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_hsqldb_reservations: None,
) -> None:
    _, instance_ids = await add_product(
        test_session_factory,
        name="Sync bike single",
        hsqldb_name="Rower bez numeru",
        inventory_codes=[None],
    )
    request = HsqldbReservationSyncRequest(
        reservations=[
            sync_item(
                1002,
                product_name="Rower bez numeru",
                inventory_code=None,
            )
        ]
    )

    async with test_session_factory() as session:
        await synchronize_hsqldb_reservations(session, request)

    async with test_session_factory() as session:
        reservation = await session.get(HsqldbReservation, 1002)

    assert reservation is not None
    assert reservation.instance_id == instance_ids[0]


async def test_skips_product_without_code_when_instance_is_ambiguous(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_hsqldb_reservations: None,
) -> None:
    await add_product(
        test_session_factory,
        name="Sync bike ambiguous",
        hsqldb_name="Rower niejednoznaczny",
        inventory_codes=[None, None],
    )
    request = HsqldbReservationSyncRequest(
        reservations=[
            sync_item(
                1003,
                product_name="Rower niejednoznaczny",
                inventory_code=None,
            )
        ]
    )

    async with test_session_factory() as session:
        await synchronize_hsqldb_reservations(session, request)

    async with test_session_factory() as session:
        reservation = await session.get(HsqldbReservation, 1003)

    assert reservation is None


async def test_updates_existing_reservation_idempotently(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_hsqldb_reservations: None,
) -> None:
    await add_product(
        test_session_factory,
        name="Sync kayak update",
        hsqldb_name="Kajak aktualizowany",
        inventory_codes=["20001"],
    )
    first_request = HsqldbReservationSyncRequest(
        reservations=[
            sync_item(
                1004,
                product_name="Kajak aktualizowany",
                inventory_code="20001",
            )
        ]
    )
    updated_end_at = datetime(2026, 9, 8, 18)
    second_request = HsqldbReservationSyncRequest(
        reservations=[
            sync_item(
                1004,
                product_name="Kajak aktualizowany",
                inventory_code="20001",
                source_status=0,
                end_at=updated_end_at,
            )
        ]
    )

    async with test_session_factory() as session:
        await synchronize_hsqldb_reservations(session, first_request)
        await synchronize_hsqldb_reservations(session, second_request)

    async with test_session_factory() as session:
        reservations = list(await session.scalars(select(HsqldbReservation)))

    assert len(reservations) == 1
    assert reservations[0].source_position_id == 1004
    assert reservations[0].end_at == updated_end_at
    assert reservations[0].source_status == 0


async def test_removes_reservation_missing_from_next_snapshot(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_hsqldb_reservations: None,
) -> None:
    await add_product(
        test_session_factory,
        name="Sync tent stale",
        hsqldb_name="Namiot usuwany",
        inventory_codes=["30001"],
    )
    first_request = HsqldbReservationSyncRequest(
        reservations=[
            sync_item(
                1005,
                product_name="Namiot usuwany",
                inventory_code="30001",
            )
        ]
    )

    async with test_session_factory() as session:
        await synchronize_hsqldb_reservations(session, first_request)
        await synchronize_hsqldb_reservations(
            session,
            HsqldbReservationSyncRequest(reservations=[]),
        )

    async with test_session_factory() as session:
        reservation = await session.get(HsqldbReservation, 1005)

    assert reservation is None


async def test_keeps_existing_instance_when_item_identity_is_temporarily_missing(
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_hsqldb_reservations: None,
) -> None:
    _, instance_ids = await add_product(
        test_session_factory,
        name="Sync carrier incomplete",
        hsqldb_name="Nosidełko z brakującą nazwą",
        inventory_codes=[None],
    )
    first_request = HsqldbReservationSyncRequest(
        reservations=[
            sync_item(
                1006,
                product_name="Nosidełko z brakującą nazwą",
                inventory_code=None,
            )
        ]
    )
    updated_end_at = datetime(2026, 9, 9, 18)
    incomplete_request = HsqldbReservationSyncRequest(
        reservations=[
            HsqldbReservationSyncItem(
                source_position_id=1006,
                begin_at=datetime(2026, 9, 1, 10),
                end_at=updated_end_at,
                source_status=0,
                source_name=None,
                product_name=None,
                inventory_code=None,
            )
        ]
    )

    async with test_session_factory() as session:
        await synchronize_hsqldb_reservations(session, first_request)
        await synchronize_hsqldb_reservations(session, incomplete_request)

    async with test_session_factory() as session:
        reservation = await session.get(HsqldbReservation, 1006)

    assert reservation is not None
    assert reservation.instance_id == instance_ids[0]
    assert reservation.end_at == updated_end_at
    assert reservation.source_status == 0
