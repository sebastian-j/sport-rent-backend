import datetime

import pytest

from app.models import CartItem, Product, ProductImage, ProductSize
from app.services.cart import (
    CartValidationError,
    ensure_quantity_available,
    group_cart_items,
    merge_quantities,
    validate_dates,
)


def test_validate_dates_accepts_today_and_rejects_invalid_ranges() -> None:
    today = datetime.date(2026, 7, 29)
    validate_dates(today, today, today)

    with pytest.raises(CartValidationError, match="past"):
        validate_dates(today - datetime.timedelta(days=1), today, today)
    with pytest.raises(CartValidationError, match="after"):
        validate_dates(today + datetime.timedelta(days=2), today, today)


def test_group_cart_items_groups_products_and_uses_first_image() -> None:
    product = Product(
        id=1,
        name="Rower",
        price=25,
        slug="rower",
        visibility_status=True,
        images=[
            ProductImage(image="two.jpg", alt_text="Two", display_order=2),
            ProductImage(image="one.jpg", alt_text="One", display_order=1),
        ],
        sizes=[ProductSize(id=10, size="M", description="Medium")],
    )
    first = CartItem(
        id=100,
        user_id=1,
        product_id=1,
        product_size_id=10,
        quantity=2,
        start_date=datetime.date(2026, 8, 1),
        end_date=datetime.date(2026, 8, 2),
        product=product,
        product_size=product.sizes[0],
    )
    second = CartItem(
        id=101,
        user_id=1,
        product_id=1,
        product_size_id=10,
        quantity=1,
        start_date=datetime.date(2026, 8, 3),
        end_date=datetime.date(2026, 8, 4),
        product=product,
        product_size=product.sizes[0],
    )

    result = group_cart_items([first, second])

    assert len(result) == 1
    assert result[0].slug == "rower"
    assert result[0].image == "one.jpg"
    assert [item.id for item in result[0].dates] == [100, 101]


def test_merge_quantities_adds_the_updated_term_to_existing_term() -> None:
    assert merge_quantities(2, 4) == 6


def test_ensure_quantity_available_rejects_overflow() -> None:
    ensure_quantity_available(2, 2)
    with pytest.raises(CartValidationError, match="exceeds available"):
        ensure_quantity_available(3, 2)
