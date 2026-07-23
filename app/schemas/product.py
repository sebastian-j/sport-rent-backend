from pydantic import BaseModel


class ProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    price: float | None = None
    description: str | None = None
    images: list[str] | None = None
    alt: str | None = None
    category: str | None = None
    sizes: list[dict[str, str]] | None = None


class ProductAvailabilityResponse(BaseModel):
    available: bool
