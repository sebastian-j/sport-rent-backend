from pydantic import BaseModel, Field

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
    imageAlts: list[str]
    category: str | None = None
    sizes: list[ProductSize] | None = None
    isFavorite: bool = False


class ProductAvailabilityResponse(BaseModel):
    available: bool


class ProductQueryParams(BaseModel):
    sort: str | None = None
    order: str | None = None
    minPrice: int | None = Field(default=MIN_PRICE, ge=0)
    maxPrice: int | None = Field(default=MAX_PRICE, ge=0)
    category: list[str] | None = None
    query: str | None = None
    page: int = Field(default=DEFAULT_PAGE, ge=1)
    pageSize: int = Field(default=DEFAULT_PAGE_SIZE, ge=1)


class CategoryResponse(BaseModel):
    name: str
    count: int


class PriceFacetResponse(BaseModel):
    min: float
    max: float


class ProductFacetsResponse(BaseModel):
    categories: list[CategoryResponse]
    total: int
    price: PriceFacetResponse
