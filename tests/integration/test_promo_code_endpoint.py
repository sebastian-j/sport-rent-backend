from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.promo_codes import DiscountType
from app.schemas.promo_code import PromoCodeCreate
from app.services.promo_code import create_promo_code
from tests.support import SeededUser


async def authorization_headers(
    client: AsyncClient,
    user: SeededUser,
) -> dict[str, str]:
    response = await client.post(
        "/auth/login",
        json={"email": user.email, "password": user.password},
    )
    assert response.status_code == 200

    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_validate_promo_code_returns_discount_details(
    client: AsyncClient,
    test_user: SeededUser,
    test_session_factory: async_sessionmaker[AsyncSession],
    empty_promo_codes: None,
) -> None:
    request = PromoCodeCreate(
        code="MINUS20",
        discount_type=DiscountType.FIXED_AMOUNT,
        discount_value=Decimal("20.00"),
        minimum_order_value=Decimal("100.00"),
    )
    async with test_session_factory() as session:
        await create_promo_code(session, request)

    headers = await authorization_headers(client, test_user)
    response = await client.post(
        "/cart/promo-code/validate",
        json={"promo_code": " minus20 "},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "discount_type": "FIXED_AMOUNT",
        "discount_value": "20.0000",
        "minimum_order_value": "100.00",
    }


async def test_validate_promo_code_returns_invalid_for_unknown_code(
    client: AsyncClient,
    test_user: SeededUser,
    empty_promo_codes: None,
) -> None:
    headers = await authorization_headers(client, test_user)
    response = await client.post(
        "/cart/promo-code/validate",
        json={"promo_code": "UNKNOWN"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "discount_type": None,
        "discount_value": None,
        "minimum_order_value": None,
    }
