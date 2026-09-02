from datetime import date, datetime, time

from sqlalchemy import exists, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.hsqldb_reservation import HsqldbReservation
from app.models.order import Order, OrderInstance, OrderStatus
from app.models.product import Instance, InstanceStatus


def available_instance_conditions(
    *,
    product_id: int,
    size: str | None,
    start_date: date,
    end_date: date,
) -> tuple[ColumnElement[bool], ...]:
    requested_start_at = datetime.combine(start_date, time.min)
    requested_end_at = datetime.combine(end_date, time.max)

    occupied_by_order = exists(
        select(1)
        .select_from(OrderInstance)
        .join(Order, Order.id == OrderInstance.order_id)
        .where(
            OrderInstance.instance_id == Instance.id,
            Order.status != OrderStatus.CANCELLED,
            OrderInstance.start_date <= end_date,
            OrderInstance.end_date >= start_date,
        )
    )

    occupied_by_hsqldb = exists(
        select(1)
        .select_from(HsqldbReservation)
        .where(
            HsqldbReservation.instance_id == Instance.id,
            HsqldbReservation.begin_at <= requested_end_at,
            HsqldbReservation.end_at >= requested_start_at,
            # TODO: Filter by active source_status values once their meaning is known.
        )
    )

    conditions = [
        Instance.product_id == product_id,
        Instance.status == InstanceStatus.AVAILABLE,
        ~occupied_by_order,
        ~occupied_by_hsqldb,
    ]
    if size is not None:
        conditions.append(Instance.size == size)

    return tuple(conditions)
