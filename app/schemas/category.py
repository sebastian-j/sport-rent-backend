from pydantic import BaseModel


class CategoryResponse(BaseModel):
    name: str
    image: str | None = None
    slug: str
