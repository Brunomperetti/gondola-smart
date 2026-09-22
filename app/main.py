"""FastAPI application entry point."""

from fastapi import FastAPI

from app import __version__
from app.api.routes import router

app = FastAPI(
    title="Gondola Smart",
    description="Visión de góndolas, validación y ranking seguro de productos.",
    version=__version__,
)
app.include_router(router)
