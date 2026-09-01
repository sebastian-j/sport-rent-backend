from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hsqldb_reservation import HsqldbReservation
from app.models.product import Instance, Product
from app.schemas.hsqldb_sync import (
    HsqldbReservationSyncItem,
    HsqldbReservationSyncRequest,
)


def _resolve_instance(
    products_by_name: dict[str, Product],
    item: HsqldbReservationSyncItem,
) -> Instance | None:
    if item.product_name is None:
        return None

    product = products_by_name.get(item.product_name)
    if product is None:
        return None

    if item.inventory_code is None:
        if len(product.instances) == 1:
            return product.instances[0]
        return None

    for instance in product.instances:
        if instance.hsqldb_inventory_code == item.inventory_code:
            return instance

    return None


async def _load_products_by_name(
    session: AsyncSession,
) -> dict[str, Product]:
    result = await session.scalars(
        select(Product)
        .where(Product.hsqldb_name.is_not(None))
        .options(selectinload(Product.instances))
    )

    products_by_name: dict[str, Product] = {}

    for product in result.unique():
        if product.hsqldb_name is not None:
            products_by_name[product.hsqldb_name] = product

    return products_by_name


async def synchronize_hsqldb_reservations(
    session: AsyncSession,
    request: HsqldbReservationSyncRequest,
) -> None:
    products_by_name = await _load_products_by_name(session)

    items_by_id = {item.source_position_id: item for item in request.reservations}

    existing_result = await session.scalars(select(HsqldbReservation))
    existing_by_id = {
        reservation.source_position_id: reservation for reservation in existing_result
    }

    for source_position_id, item in items_by_id.items():
        instance = _resolve_instance(products_by_name, item)
        reservation = existing_by_id.get(source_position_id)

        if instance is None and reservation is None:
            continue

        if reservation is None:
            reservation = HsqldbReservation(
                source_position_id=source_position_id,
                instance_id=instance.id,
            )
            session.add(reservation)
        elif instance is not None:
            reservation.instance_id = instance.id

        reservation.begin_at = item.begin_at
        reservation.end_at = item.end_at
        reservation.source_status = item.source_status

    current_source_ids = set(items_by_id)

    if current_source_ids:
        await session.execute(
            delete(HsqldbReservation).where(
                HsqldbReservation.source_position_id.not_in(current_source_ids)
            )
        )
    else:
        await session.execute(delete(HsqldbReservation))

    await session.commit()
