import re
import unicodedata
from pathlib import Path


def slugify(text: str) -> str:
    text = text.translate(str.maketrans({"ł": "l", "Ł": "L"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


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
