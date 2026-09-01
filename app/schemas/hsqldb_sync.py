from datetime import datetime

from pydantic import BaseModel


class HsqldbReservationSyncItem(BaseModel):
    source_position_id: int
    begin_at: datetime | None
    end_at: datetime | None
    source_status: int | None
    source_name: str | None
    product_name: str | None
    inventory_code: str | None


class HsqldbReservationSyncRequest(BaseModel):
    reservations: list[HsqldbReservationSyncItem]
