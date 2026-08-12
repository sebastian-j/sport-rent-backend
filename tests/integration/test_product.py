import pytest
from httpx import AsyncClient


@pytest.mark.parametrize("page_size", [0, 101])
async def test_products_reject_invalid_page_size(
    client: AsyncClient,
    page_size: int,
) -> None:
    response = await client.get(
        "/product",
        params={"pageSize": page_size},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "pageSize"


@pytest.mark.parametrize("page_size", [1, 100])
async def test_products_accept_page_size_boundaries(
    client: AsyncClient,
    page_size: int,
) -> None:
    response = await client.get(
        "/product",
        params={"pageSize": page_size},
    )

    assert response.status_code == 200