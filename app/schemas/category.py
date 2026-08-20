from pydantic import BaseModel

from app.schemas.subcategory import SubcategoryResponse


class CategoryResponse(BaseModel):
    name: str
    image: str | None = None
    slug: str
    subcategories: list[SubcategoryResponse]
