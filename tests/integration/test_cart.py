import asyncio
import datetime
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.tokens import create_access_token
from app.models import Product, ProductImage, ProductSize, User
from tests.conftest import TEST_PASSWORD
from tests.support import SeededUser

SIZED_PRODUCT_ID = 9101
PLAIN_PRODUCT_ID = 9102
HIDDEN_PRODUCT_ID = 9103


def future_date(days: int) -> str:
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


def authorization(user_id: int) -> dict[str, str]:
    token = create_access_token(user_id, uuid.uuid4()).token
    return {"Authorization": f"Bearer {token}"}


def item_payload(
    *,
    product_id: int = SIZED_PRODUCT_ID,
    quantity: int = 1,
    size: str | None = "M",
    start_days: int = 2,
    end_days: int = 4,
) -> dict[str, object]:
    return {
        "product_id": product_id,
        "quantity": quantity,
        "size": size,
        "start_date": future_date(start_days),
        "end_date": future_date(end_days),
    }


@pytest_asyncio.fixture
async def cart_products(
    empty_auth_database: None,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[None]:
    async with test_session_factory.begin() as session:
        sized = Product(
            id=SIZED_PRODUCT_ID,
            name="Rower testowy",
            description="",
            price=50,
            slug="rower-testowy-cart",
            visibility_status=True,
            images=[
                ProductImage(image="second.jpg", alt_text="Drugi", display_order=2),
                ProductImage(image="first.jpg", alt_text="Pierwszy", display_order=1),
            ],
            sizes=[
                ProductSize(size="M", description="Medium"),
                ProductSize(size="L", description="Large"),
            ],
        )
        plain = Product(
            id=PLAIN_PRODUCT_ID,
            name="Kajak testowy",
            description="",
            price=80,
            slug="kajak-testowy-cart",
            visibility_status=True,
        )
        hidden = Product(
            id=HIDDEN_PRODUCT_ID,
            name="Ukryty",
            description="",
            price=100,
            slug="ukryty-testowy-cart",
            visibility_status=False,
        )
        session.add_all([sized, plain, hidden])

    try:
        yield
    finally:
        async with test_session_factory.begin() as session:
            await session.execute(
                delete(Product).where(
                    Product.id.in_(
                        [SIZED_PRODUCT_ID, PLAIN_PRODUCT_ID, HIDDEN_PRODUCT_ID]
                    )
                )
            )


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/cart", None),
        ("GET", "/cart/status", None),
        ("POST", "/cart/items", item_payload()),
        ("PATCH", "/cart/items/1", {"quantity": 2}),
        ("DELETE", "/cart/items/1", None),
        ("DELETE", f"/cart/products/{SIZED_PRODUCT_ID}", None),
    ],
)
async def test_cart_requires_authentication(
    client: AsyncClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    response = await client.request(method, path, json=payload)
    assert response.status_code == 401


async def test_empty_cart(
    client: AsyncClient, test_user: SeededUser, cart_products: None
) -> None:
    response = await client.get("/cart", headers=authorization(test_user.id))
    assert response.status_code == 200
    assert response.json() == []


async def test_cart_status_tracks_if_user_has_items(
    client: AsyncClient, test_user: SeededUser, cart_products: None
) -> None:
    headers = authorization(test_user.id)

    empty_status = await client.get("/cart/status", headers=headers)
    assert empty_status.status_code == 200
    assert empty_status.json() == {"has_items": False}

    item = (
        await client.post("/cart/items", headers=headers, json=item_payload())
    ).json()

    filled_status = await client.get("/cart/status", headers=headers)
    assert filled_status.status_code == 200
    assert filled_status.json() == {"has_items": True}

    await client.delete(f"/cart/items/{item['id']}", headers=headers)

    cleared_status = await client.get("/cart/status", headers=headers)
    assert cleared_status.status_code == 200
    assert cleared_status.json() == {"has_items": False}


async def test_adds_groups_and_orders_terms(
    client: AsyncClient, test_user: SeededUser, cart_products: None
) -> None:
    headers = authorization(test_user.id)
    first = await client.post(
        "/cart/items",
        headers=headers,
        json=item_payload(quantity=2),
    )
    second = await client.post(
        "/cart/items",
        headers=headers,
        json=item_payload(size="L", start_days=8, end_days=9),
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = await client.get("/cart", headers=headers)
    assert response.status_code == 200
    assert response.json() == [
        {
            "product_id": SIZED_PRODUCT_ID,
            "product_name": "Rower testowy",
            "image": "first.jpg",
            "alt": "Pierwszy",
            "price": 50.0,
            "sizes": [
                {"size": "M", "description": "Medium"},
                {"size": "L", "description": "Large"},
            ],
            "dates": [first.json(), second.json()],
        }
    ]


async def test_identical_addition_merges_quantity(
    client: AsyncClient, test_user: SeededUser, cart_products: None
) -> None:
    headers = authorization(test_user.id)
    first = await client.post(
        "/cart/items", headers=headers, json=item_payload(quantity=2)
    )
    second = await client.post(
        "/cart/items", headers=headers, json=item_payload(quantity=3)
    )

    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["quantity"] == 5


async def test_patch_fully_edits_and_merges_collision(
    client: AsyncClient, test_user: SeededUser, cart_products: None
) -> None:
    headers = authorization(test_user.id)
    first = (
        await client.post("/cart/items", headers=headers, json=item_payload(quantity=2))
    ).json()
    second = (
        await client.post(
            "/cart/items",
            headers=headers,
            json=item_payload(quantity=3, size="L", start_days=8, end_days=10),
        )
    ).json()

    edited = await client.patch(
        f"/cart/items/{second['id']}",
        headers=headers,
        json={
            "quantity": 4,
            "size": "M",
            "start_date": future_date(3),
            "end_date": future_date(5),
        },
    )
    assert edited.status_code == 200
    assert edited.json()["quantity"] == 4
    assert edited.json()["size"] == "M"

    merged = await client.patch(
        f"/cart/items/{edited.json()['id']}",
        headers=headers,
        json={
            "start_date": first["start_date"],
            "end_date": first["end_date"],
        },
    )
    assert merged.status_code == 200
    assert merged.json()["id"] == first["id"]
    assert merged.json()["quantity"] == 6

    cart = (await client.get("/cart", headers=headers)).json()
    assert len(cart[0]["dates"]) == 1


async def test_removes_term_then_product_disappears(
    client: AsyncClient, test_user: SeededUser, cart_products: None
) -> None:
    headers = authorization(test_user.id)
    item = (
        await client.post("/cart/items", headers=headers, json=item_payload())
    ).json()

    response = await client.delete(f"/cart/items/{item['id']}", headers=headers)
    assert response.status_code == 204
    assert (await client.get("/cart", headers=headers)).json() == []


async def test_removes_all_product_terms(
    client: AsyncClient, test_user: SeededUser, cart_products: None
) -> None:
    headers = authorization(test_user.id)
    await client.post("/cart/items", headers=headers, json=item_payload())
    await client.post(
        "/cart/items",
        headers=headers,
        json=item_payload(start_days=7, end_days=8),
    )

    response = await client.delete(
        f"/cart/products/{SIZED_PRODUCT_ID}", headers=headers
    )
    assert response.status_code == 204
    assert (await client.get("/cart", headers=headers)).json() == []


async def test_users_are_isolated(
    client: AsyncClient,
    test_user: SeededUser,
    cart_products: None,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    second_user_id = 9199
    async with test_session_factory.begin() as session:
        session.add(
            User(
                id=second_user_id,
                email="cart-second@example.com",
                password_hash=TEST_PASSWORD,
            )
        )
    item = (
        await client.post(
            "/cart/items",
            headers=authorization(test_user.id),
            json=item_payload(),
        )
    ).json()

    other_headers = authorization(second_user_id)
    assert (await client.get("/cart", headers=other_headers)).json() == []
    assert (await client.get("/cart/status", headers=other_headers)).json() == {
        "has_items": False
    }
    assert (
        await client.get("/cart/status", headers=authorization(test_user.id))
    ).json() == {"has_items": True}
    assert (
        await client.patch(
            f"/cart/items/{item['id']}",
            headers=other_headers,
            json={"quantity": 5},
        )
    ).status_code == 404
    assert (
        await client.delete(f"/cart/items/{item['id']}", headers=other_headers)
    ).status_code == 404


@pytest.mark.parametrize(
    ("payload", "status_code"),
    [
        (item_payload(product_id=999999), 404),
        (item_payload(product_id=HIDDEN_PRODUCT_ID), 404),
        (item_payload(size=None), 422),
        (item_payload(size="XL"), 422),
        (item_payload(product_id=PLAIN_PRODUCT_ID, size="M"), 422),
        (item_payload(quantity=0), 422),
        (
            {
                **item_payload(),
                "start_date": future_date(-1),
                "end_date": future_date(2),
            },
            422,
        ),
        (
            {
                **item_payload(),
                "start_date": future_date(4),
                "end_date": future_date(2),
            },
            422,
        ),
    ],
)
async def test_rejects_invalid_additions(
    client: AsyncClient,
    test_user: SeededUser,
    cart_products: None,
    payload: dict[str, object],
    status_code: int,
) -> None:
    response = await client.post(
        "/cart/items", headers=authorization(test_user.id), json=payload
    )
    assert response.status_code == status_code


async def test_rejects_empty_patch_and_invalid_duplicate_without_mutation(
    client: AsyncClient, test_user: SeededUser, cart_products: None
) -> None:
    headers = authorization(test_user.id)
    item = (
        await client.post("/cart/items", headers=headers, json=item_payload(quantity=2))
    ).json()

    assert (
        await client.patch(f"/cart/items/{item['id']}", headers=headers, json={})
    ).status_code == 422
    assert (
        await client.post("/cart/items", headers=headers, json=item_payload(quantity=0))
    ).status_code == 422

    cart = (await client.get("/cart", headers=headers)).json()
    assert cart[0]["dates"][0]["quantity"] == 2


async def test_parallel_identical_addition_is_atomic(
    client: AsyncClient, test_user: SeededUser, cart_products: None
) -> None:
    headers = authorization(test_user.id)
    responses = await asyncio.gather(
        *[
            client.post("/cart/items", headers=headers, json=item_payload(quantity=1))
            for _ in range(5)
        ]
    )

    assert all(response.status_code == 201 for response in responses)
    assert {response.json()["id"] for response in responses} == {
        responses[0].json()["id"]
    }

    cart = (await client.get("/cart", headers=headers)).json()
    assert cart[0]["dates"][0]["quantity"] == 5


async def test_missing_item_and_product_return_not_found(
    client: AsyncClient, test_user: SeededUser, cart_products: None
) -> None:
    headers = authorization(test_user.id)
    assert (
        await client.patch("/cart/items/999999", headers=headers, json={"quantity": 2})
    ).status_code == 404
    assert (
        await client.delete("/cart/items/999999", headers=headers)
    ).status_code == 404
    assert (
        await client.delete(f"/cart/products/{SIZED_PRODUCT_ID}", headers=headers)
    ).status_code == 404
