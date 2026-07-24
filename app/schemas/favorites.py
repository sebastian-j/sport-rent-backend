from pydantic import BaseModel


class FavoritesResponse(BaseModel):
    slug: str
    name: str
    description: str
    image: str
    alt: str
    price: float
