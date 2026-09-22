"""Environment-backed application configuration."""

from functools import lru_cache
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    vision_provider: str = "mock"
    openai_api_key: str | None = None
    openai_vision_model: str = "gpt-5.6-luna"
    openai_timeout_seconds: float = Field(default=45, gt=0)
    max_images_per_analysis: int = Field(default=3, ge=1)
    max_image_size_mb: int = Field(default=10, ge=1)


@lru_cache
def get_settings() -> Settings:
    """Read settings once without ever logging secrets."""

    return Settings(
        vision_provider=os.getenv("VISION_PROVIDER", "mock").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_vision_model=os.getenv("OPENAI_VISION_MODEL", "gpt-5.6-luna"),
        openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "45")),
        max_images_per_analysis=int(os.getenv("MAX_IMAGES_PER_ANALYSIS", "3")),
        max_image_size_mb=int(os.getenv("MAX_IMAGE_SIZE_MB", "10")),
    )
