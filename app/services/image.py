import base64
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=128)
def get_image_as_base64(image_path: str) -> str | None:
    if not image_path:
        return None

    if image_path.startswith("data:image"):
        return image_path

    path = Path(image_path)
    if not path.exists():
        path = Path("app") / image_path

    if path.exists() and path.is_file():
        ext = path.suffix.lower().lstrip(".")
        mime_type = "jpeg" if ext in ("jpg", "jpeg") else ext
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:image/{mime_type};base64,{encoded}"

    return None


def convert_images_to_base64(images: list[str] | None) -> list[str] | None:
    if not images:
        return images
    encoded_images = []
    for img in images:
        b64 = get_image_as_base64(img)
        if b64:
            encoded_images.append(b64)
        else:
            encoded_images.append(img)
    return encoded_images
