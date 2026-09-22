"""Central provider selection."""

from app.config import Settings, get_settings
from app.vision.base import VisionProvider, VisionProviderConfigurationError
from app.vision.mock_detector import MockVisionProvider
from app.vision.openai_provider import OpenAIVisionProvider


def get_vision_provider(settings: Settings | None = None) -> VisionProvider:
    settings = settings or get_settings()
    if settings.vision_provider == "mock":
        return MockVisionProvider()
    if settings.vision_provider == "openai":
        if not settings.openai_api_key:
            raise VisionProviderConfigurationError(
                "OPENAI_API_KEY is required when VISION_PROVIDER=openai"
            )
        return OpenAIVisionProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_vision_model,
            timeout=settings.openai_timeout_seconds,
        )
    raise VisionProviderConfigurationError(
        f"unsupported VISION_PROVIDER '{settings.vision_provider}'"
    )
