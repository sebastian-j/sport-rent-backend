from pydantic import BaseModel


class SubcategoryResponse(BaseModel):
    name: str
    image: str | None = None
    slug: str