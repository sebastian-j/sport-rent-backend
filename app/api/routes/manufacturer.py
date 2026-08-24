from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models import Manufacturer
from app.schemas.manufacturer import ManufacturerResponse

router = APIRouter(prefix="/manufacturers", tags=["manufacturers"])


@router.get("", response_model=list[ManufacturerResponse])
async def get_manufacturers(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ManufacturerResponse]:
    manufacturers = (
        await session.scalars(select(Manufacturer).order_by(Manufacturer.id))
    ).all()
    return [
        ManufacturerResponse(
            name=manufacturer.name,
            slug=manufacturer.slug,
        )
        for manufacturer in manufacturers
    ]
