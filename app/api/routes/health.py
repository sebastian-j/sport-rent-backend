from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])

class HealthResponse(BaseModel):
    status: str

@router.get("", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")
