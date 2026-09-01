import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path


def slugify(text: str) -> str:
    text = text.translate(
        str.maketrans(
            {
                "ł": "l",
                "Ł": "L",
                "'": "-",
            }
        )
    )
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text).strip("-")


def unique_slug(base_slug: str, taken: Iterable[str]) -> str:
    taken_set = taken if isinstance(taken, set) else set(taken)
    slug = base_slug or "product"
    if slug not in taken_set:
        return slug

    suffix = 2
    while True:
        candidate = f"{slug}-{suffix}"
        if candidate not in taken_set:
            return candidate
        suffix += 1


def find_image(name: str, directory: Path, storage_path: Path) -> str | None:
    if not directory.is_dir():
        return None

    target_slug = slugify(name)
    matching_images = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and slugify(path.stem) == target_slug
    )

    if not matching_images:
        return None

    return (storage_path / matching_images[0].name).as_posix()
