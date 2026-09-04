from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class ReservedInstancePeriod:
    instance_id: int
    start_date: date
    end_date: date


def calculate_unavailable_dates(
    *,
    instance_count: int,
    requested_quantity: int,
    reservations: list[ReservedInstancePeriod],
    today: date,
) -> tuple[list[date], bool]:
    if requested_quantity > instance_count:
        return [], True
    if not reservations:
        return [], False

    first_date = max(today, min(item.start_date for item in reservations))
    last_date = max(item.end_date for item in reservations)
    if last_date < first_date:
        return [], False

    unavailable_dates: list[date] = []
    current_date = first_date
    while current_date <= last_date:
        occupied_instances = {
            item.instance_id
            for item in reservations
            if item.start_date <= current_date <= item.end_date
        }
        if instance_count - len(occupied_instances) < requested_quantity:
            unavailable_dates.append(current_date)
        current_date += timedelta(days=1)

    return unavailable_dates, False
