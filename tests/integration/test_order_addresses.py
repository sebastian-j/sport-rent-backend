from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.models import Address, Order, OrderStatus, User
from app.services.order_addresses import (
    create_order_address_snapshot,
    snapshot_default_address,
)


async def test_order_address_is_independent_from_user_default_address(
    empty_auth_database: None,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory.begin() as session:
        user = User(
            email="order-address@example.com",
            password_hash="password-hash",
            first_name="Jan",
            last_name="Kowalski",
            default_address=Address(
                first_line="ul. Domowa 1",
                second_line=None,
                postal_code="00-001",
                city="Warszawa",
                country="Polska",
            ),
        )
        session.add(user)

    async with test_session_factory.begin() as session:
        user = await session.scalar(
            select(User)
            .options(selectinload(User.default_address))
            .where(User.email == "order-address@example.com")
        )
        assert user is not None
        assert user.default_address is not None

        order = Order(
            user_id=user.id,
            status=OrderStatus.PENDING,
            total_price=Decimal("0.00"),
            recipient_first_name="Jan",
            recipient_last_name="Kowalski",
            address=snapshot_default_address(user),
        )
        session.add(order)

    async with test_session_factory.begin() as session:
        user = await session.scalar(
            select(User)
            .options(selectinload(User.default_address))
            .where(User.email == "order-address@example.com")
        )
        assert user is not None
        assert user.default_address is not None
        user.default_address.city = "Kraków"
        user.default_address.first_line = "ul. Nowa 2"

    async with test_session_factory() as session:
        order = await session.scalar(select(Order).options(selectinload(Order.address)))

    assert order is not None
    assert order.address.city == "Warszawa"
    assert order.address.first_line == "ul. Domowa 1"
    assert order.address.first_name is None
    assert order.address.last_name is None
    assert order.recipient_first_name == "Jan"
    assert order.recipient_last_name == "Kowalski"


def test_order_address_supports_another_person_or_company() -> None:
    another_person = create_order_address_snapshot(
        first_name="Anna",
        last_name="Nowak",
        first_line="ul. Inna 3",
        second_line=None,
        postal_code="30-001",
        city="Kraków",
        country="Polska",
        company=None,
        nip=None,
    )
    company = create_order_address_snapshot(
        first_name=None,
        last_name=None,
        first_line="ul. Firmowa 4",
        second_line=None,
        postal_code="80-001",
        city="Gdańsk",
        country="Polska",
        company="Sport Rent sp. z o.o.",
        nip="1234567890",
    )

    assert another_person.first_name == "Anna"
    assert another_person.last_name == "Nowak"
    assert another_person.company is None
    assert company.first_name is None
    assert company.last_name is None
    assert company.company == "Sport Rent sp. z o.o."
    assert company.nip == "1234567890"


def test_order_address_allows_address_without_person_or_company() -> None:
    address = create_order_address_snapshot(
        first_name=None,
        last_name=None,
        first_line="ul. Niekompletna 5",
        second_line=None,
        postal_code="00-001",
        city="Warszawa",
        country="Polska",
        company=None,
        nip=None,
    )

    assert address.first_name is None
    assert address.last_name is None
    assert address.company is None
