from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import hsqldb_sync as hsqldb_sync_route
from app.schemas.hsqldb_sync import HsqldbReservationSyncRequest


async def test_synchronizes_reservation_snapshot(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_synchronize(
        session: AsyncSession,
        request: HsqldbReservationSyncRequest,
    ) -> None:
        captured["session"] = session
        captured["request"] = request

    monkeypatch.setattr(
        hsqldb_sync_route,
        "synchronize_hsqldb_reservations",
        fake_synchronize,
    )

    response = await client.post(
        "/sync/reservations",
        json={
            "reservations": [
                {
                    "source_position_id": 1001,
                    "begin_at": "2026-09-01T10:00:00",
                    "end_at": "2026-09-05T18:00:00",
                    "source_status": 1,
                    "source_name": "Kije Dynafit/004",
                    "product_name": "Kije Dynafit",
                    "inventory_code": "004",
                }
            ]
        },
    )

    assert response.status_code == 204
    assert response.content == b""
    assert isinstance(captured["session"], AsyncSession)

    request = captured["request"]
    assert isinstance(request, HsqldbReservationSyncRequest)
    assert len(request.reservations) == 1
    assert request.reservations[0].source_position_id == 1001
    assert request.reservations[0].inventory_code == "004"
