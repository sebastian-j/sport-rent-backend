from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.hsqldb_sync import HsqldbReservationSyncRequest
from app.services.hsqldb_sync import synchronize_hsqldb_reservations

router = APIRouter(prefix="/sync", tags=["HSQLDB synchronization"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "/reservations",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def synchronize_reservations(
    request: HsqldbReservationSyncRequest,
    session: DatabaseSession,
) -> None:
    await synchronize_hsqldb_reservations(session, request)
