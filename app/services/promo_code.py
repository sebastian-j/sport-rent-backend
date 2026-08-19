from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.promo_codes import PromoCode
from app.schemas.promo_code import PromoCodeCreate


class PromoCodeAlreadyExistsError(ValueError):
    pass


async def create_promo_code(
    session: AsyncSession,
    request: PromoCodeCreate,
) -> PromoCode:
    promo_code = PromoCode(**request.model_dump())

    session.add(promo_code)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise PromoCodeAlreadyExistsError(
            f"Promo code {request.code} already exists"
        ) from error

    await session.refresh(promo_code)
    return promo_code


async def get_valid_promo_code(
    session: AsyncSession,
    code: str,
    *,
    now: datetime | None = None,
) -> PromoCode | None:
    current_time = now or datetime.now(UTC)
    normalized_code = code.strip().upper()

    return await session.scalar(
        select(PromoCode).where(
            PromoCode.code == normalized_code,
            PromoCode.is_active.is_(True),
            or_(
                PromoCode.valid_from.is_(None),
                PromoCode.valid_from <= current_time,
            ),
            or_(
                PromoCode.valid_until.is_(None),
                PromoCode.valid_until >= current_time,
            ),
            or_(
                PromoCode.max_uses.is_(None),
                PromoCode.usage_count < PromoCode.max_uses,
            ),
        )
    )
