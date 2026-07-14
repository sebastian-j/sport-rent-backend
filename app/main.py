from fastapi import FastAPI

from app.api.routes import health, products

app = FastAPI()

app.include_router(health.router)
app.include_router(products.router)
