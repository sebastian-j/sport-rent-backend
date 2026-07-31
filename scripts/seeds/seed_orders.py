import asyncio
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.order import Order, OrderInstance, OrderStatus
from app.models.order_address import OrderAddress
from app.models.product import Instance, Product
from app.models.user import User


async def seed_orders(session_factory=async_session_factory) -> None:
    async with session_factory() as session:
        if (await session.execute(select(Order).limit(1))).scalar_one_or_none():
            return

        users = (await session.execute(select(User).limit(1))).scalars().all()
        products = (await session.execute(select(Product).limit(2))).scalars().all()

        instances = (await session.execute(select(Instance).limit(2))).scalars().all()

        if not users or len(products) < 2 or len(instances) < 2:
            return

        user1 = users[0]
        instance1, instance2 = instances[0], instances[1]
        product1, product2 = products[0], products[1]

        orders = [
            Order(
                user_id=user1.id,
                status=OrderStatus.FINISHED,
                payment_code=uuid4(),
                address=OrderAddress(
                    first_line="Testowa 1",
                    city="Warszawa",
                    postal_code="00-001",
                    country="Polska",
                ),
                instances=[
                    OrderInstance(
                        instance_id=instance1.id,
                        start_date=date.today() - timedelta(days=10),
                        end_date=date.today() - timedelta(days=5),
                        price=product1.price,
                    )
                ],
            ),
            Order(
                user_id=user1.id,
                status=OrderStatus.PAID,
                payment_code=uuid4(),
                address=OrderAddress(
                    first_line="Długa 5",
                    city="Kraków",
                    postal_code="30-002",
                    country="Polska",
                ),
                instances=[
                    OrderInstance(
                        instance_id=instance2.id,
                        start_date=date.today() + timedelta(days=2),
                        end_date=date.today() + timedelta(days=7),
                        price=product2.price,
                    )
                ],
            ),
        ]
        session.add_all(orders)
        await session.commit()
        print(f"Successfully seeded {len(orders)} orders.")


if __name__ == "__main__":
    asyncio.run(seed_orders())
