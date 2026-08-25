from pydantic import BaseModel


class ManufacturerResponse(BaseModel):
    name: str
    slug: str
