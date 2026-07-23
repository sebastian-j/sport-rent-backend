from pydantic import BaseModel

MIN_PRICE = 0
MAX_PRICE = 200
DEFAULT_PAGE_SIZE = 10
DEFAULT_PAGE = 1


class ProductSize(BaseModel):
    size: str
    description: str | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    price: float | None = None
    description: str | None = None
    images: list[str] | None = None
    alt: str | None = None
    category: str | None = None
    sizes: list[ProductSize] | None = None


class ProductAvailabilityResponse(BaseModel):
    available: bool


class ProductFilter(BaseModel):
    sort: str | None = None
    order: str | None = None
    minPrice: int | None = MIN_PRICE
    maxPrice: int | None = MAX_PRICE
    category: list[str] | None = []


class ProductRequest(BaseModel):
    filter: ProductFilter | None = None
    page: int | None = DEFAULT_PAGE
    pageSize: int | None = DEFAULT_PAGE_SIZE
