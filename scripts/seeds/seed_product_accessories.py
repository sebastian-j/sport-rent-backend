import asyncio
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_factory
from app.models import Product, ProductAccessory

# Initial recommendations for the example catalog. Products without a genuinely
# complementary item are intentionally omitted.
ACCESSORY_SLUGS_BY_PRODUCT = {
    "rower-szosowy": (
        "kask-rowerowy",
        "zestaw-naprawczy-do-roweru",
        "sakwy-rowerowe",
    ),
    "rower-gorski-mtb": (
        "kask-rowerowy",
        "zestaw-naprawczy-do-roweru",
        "sakwy-rowerowe",
        "jednokolowa-przyczepka-rowerowa",
    ),
    "rower-miejski": (
        "kask-rowerowy",
        "sakwy-rowerowe",
        "zestaw-naprawczy-do-roweru",
        "przyczepka-rowerowa-dla-dzieci",
        "przyczepka-rowerowa-bagazowa",
        "przyczepka-rowerowa-dla-psa",
        "skladana-przyczepka-rowerowa",
    ),
    "rower-elektryczny": (
        "kask-rowerowy",
        "sakwy-rowerowe",
        "zestaw-naprawczy-do-roweru",
        "przyczepka-rowerowa-dla-dzieci",
        "przyczepka-rowerowa-bagazowa",
        "przyczepka-rowerowa-dla-psa",
        "skladana-przyczepka-rowerowa",
    ),
    "deska-sup": (
        "kamizelka-asekuracyjna",
        "wodoodporny-worek-transportowy",
    ),
    "kajak-dwuosobowy": (
        "kamizelka-asekuracyjna",
        "wioslo-kajakowe",
        "wodoodporny-worek-transportowy",
    ),
    "kajak-dmuchany": (
        "kamizelka-asekuracyjna",
        "wioslo-kajakowe",
        "wodoodporny-worek-transportowy",
    ),
    "kanadyjka-dwuosobowa": (
        "kamizelka-asekuracyjna",
        "wioslo-kajakowe",
        "wodoodporny-worek-transportowy",
    ),
    "kamizelka-asekuracyjna": (
        "wioslo-kajakowe",
        "wodoodporny-worek-transportowy",
    ),
    "wioslo-kajakowe": (
        "kamizelka-asekuracyjna",
        "wodoodporny-worek-transportowy",
    ),
    "zestaw-via-ferrata": (
        "uprzaz-wspinaczkowa",
        "kask-wspinaczkowy",
    ),
    "uprzaz-wspinaczkowa": (
        "kask-wspinaczkowy",
        "zestaw-via-ferrata",
        "lina-wspinaczkowa-60-m",
        "zestaw-karabinkow-wspinaczkowych",
        "buty-wspinaczkowe",
    ),
    "kask-wspinaczkowy": (
        "uprzaz-wspinaczkowa",
        "zestaw-via-ferrata",
        "lina-wspinaczkowa-60-m",
        "zestaw-karabinkow-wspinaczkowych",
    ),
    "lina-wspinaczkowa-60-m": (
        "uprzaz-wspinaczkowa",
        "kask-wspinaczkowy",
        "zestaw-karabinkow-wspinaczkowych",
        "buty-wspinaczkowe",
    ),
    "zestaw-karabinkow-wspinaczkowych": (
        "uprzaz-wspinaczkowa",
        "kask-wspinaczkowy",
        "lina-wspinaczkowa-60-m",
    ),
    "buty-wspinaczkowe": (
        "uprzaz-wspinaczkowa",
        "kask-wspinaczkowy",
        "lina-wspinaczkowa-60-m",
        "zestaw-karabinkow-wspinaczkowych",
    ),
}


async def seed_product_accessories(
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> int:
    all_slugs = set(ACCESSORY_SLUGS_BY_PRODUCT)
    for accessory_slugs in ACCESSORY_SLUGS_BY_PRODUCT.values():
        all_slugs.update(accessory_slugs)

    async with session_factory.begin() as session:
        product_rows = await session.execute(
            select(Product.id, Product.slug).where(Product.slug.in_(all_slugs))
        )
        product_ids_by_slug = {
            slug: product_id for product_id, slug in product_rows if slug is not None
        }

        source_ids = [
            product_ids_by_slug[slug]
            for slug in ACCESSORY_SLUGS_BY_PRODUCT
            if slug in product_ids_by_slug
        ]
        existing_links = (
            await session.execute(
                select(
                    ProductAccessory.product_id,
                    ProductAccessory.accessory_id,
                    ProductAccessory.display_order,
                ).where(ProductAccessory.product_id.in_(source_ids))
            )
        ).all()
        existing_pairs = {
            (product_id, accessory_id) for product_id, accessory_id, _ in existing_links
        }
        used_display_orders: defaultdict[int, set[int]] = defaultdict(set)
        for product_id, _, display_order in existing_links:
            used_display_orders[product_id].add(display_order)

        links = []
        for product_slug, accessory_slugs in ACCESSORY_SLUGS_BY_PRODUCT.items():
            product_id = product_ids_by_slug.get(product_slug)
            if product_id is None:
                continue

            for display_order, accessory_slug in enumerate(accessory_slugs):
                accessory_id = product_ids_by_slug.get(accessory_slug)
                if accessory_id is None:
                    continue
                pair = (product_id, accessory_id)
                if pair in existing_pairs:
                    continue

                resolved_display_order = display_order
                while resolved_display_order in used_display_orders[product_id]:
                    resolved_display_order += 1

                links.append(
                    ProductAccessory(
                        product_id=product_id,
                        accessory_id=accessory_id,
                        display_order=resolved_display_order,
                    )
                )
                existing_pairs.add(pair)
                used_display_orders[product_id].add(resolved_display_order)

        session.add_all(links)

    print(f"Successfully seeded {len(links)} product accessory links.")
    return len(links)


if __name__ == "__main__":
    asyncio.run(seed_product_accessories())
