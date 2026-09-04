from datetime import date

from app.services.availability import (
    ReservedInstancePeriod,
    calculate_unavailable_dates,
)


def test_marks_dates_without_requested_quantity_as_unavailable() -> None:
    unavailable, fully_unavailable = calculate_unavailable_dates(
        instance_count=2,
        requested_quantity=2,
        reservations=[
            ReservedInstancePeriod(1, date(2026, 9, 10), date(2026, 9, 12)),
        ],
        today=date(2026, 9, 1),
    )

    assert unavailable == [
        date(2026, 9, 10),
        date(2026, 9, 11),
        date(2026, 9, 12),
    ]
    assert fully_unavailable is False


def test_counts_each_reserved_instance_only_once_per_day() -> None:
    unavailable, fully_unavailable = calculate_unavailable_dates(
        instance_count=2,
        requested_quantity=1,
        reservations=[
            ReservedInstancePeriod(1, date(2026, 9, 10), date(2026, 9, 12)),
            ReservedInstancePeriod(1, date(2026, 9, 11), date(2026, 9, 13)),
            ReservedInstancePeriod(2, date(2026, 9, 12), date(2026, 9, 12)),
        ],
        today=date(2026, 9, 1),
    )

    assert unavailable == [date(2026, 9, 12)]
    assert fully_unavailable is False


def test_reports_product_as_fully_unavailable_when_quantity_exceeds_stock() -> None:
    unavailable, fully_unavailable = calculate_unavailable_dates(
        instance_count=1,
        requested_quantity=2,
        reservations=[],
        today=date(2026, 9, 1),
    )

    assert unavailable == []
    assert fully_unavailable is True
