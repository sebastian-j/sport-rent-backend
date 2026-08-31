from app.models import OrderAddress, User


class InvalidOrderAddressError(ValueError):
    pass


class MissingDefaultAddressError(ValueError):
    pass


def create_order_address_snapshot(
    *,
    first_name: str | None,
    last_name: str | None,
    first_line: str,
    second_line: str | None,
    postal_code: str,
    city: str,
    country: str,
    company: str | None,
    nip: str | None,
) -> OrderAddress:
    has_first_name = bool(first_name)
    has_last_name = bool(last_name)

    if has_first_name != has_last_name:
        raise InvalidOrderAddressError(
            "First name and last name must be provided together"
        )

    return OrderAddress(
        first_name=first_name,
        last_name=last_name,
        first_line=first_line,
        second_line=second_line,
        postal_code=postal_code,
        city=city,
        country=country,
        company=company,
        nip=nip,
    )


def snapshot_default_address(user: User) -> OrderAddress:
    address = user.default_address
    if address is None:
        raise MissingDefaultAddressError

    return create_order_address_snapshot(
        first_name=address.first_name,
        last_name=address.last_name,
        first_line=address.first_line,
        second_line=address.second_line,
        postal_code=address.postal_code,
        city=address.city,
        country=address.country,
        company=address.company,
        nip=address.nip,
    )
