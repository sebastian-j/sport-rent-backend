from pydantic import BaseModel


class RandomCategoryResponse(BaseModel):
    name: str
    image: str
    slug: str
