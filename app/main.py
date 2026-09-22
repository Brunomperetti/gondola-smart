"""FastAPI application entry point."""

from fastapi import FastAPI

from app import __version__
from app.api.routes import router

app = FastAPI(
    title="Gondola Smart",
    description="Normalización y ranking de precios de productos.",
    version=__version__,
)
app.include_router(router)
