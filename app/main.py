from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    auth,
    cart,
    category,
    favorites,
    health,
    hsqldb_sync,
    loyalty,
    manufacturer,
    orders,
    product,
    user,
)
from app.core.config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory="app/assets"), name="assets")

app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(category.router)
app.include_router(favorites.router)
app.include_router(health.router)
app.include_router(hsqldb_sync.router)
app.include_router(loyalty.router)
app.include_router(manufacturer.router)
app.include_router(orders.router)
app.include_router(product.router)
app.include_router(user.router)
