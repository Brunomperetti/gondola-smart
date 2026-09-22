"""Provider-neutral vision contracts and controlled errors."""

from dataclasses import dataclass
from typing import Protocol

from app.models.detection import VisionDetectionResult


@dataclass(frozen=True)
class ImageInput:
    content: bytes
    media_type: str
    filename: str | None = None


@dataclass(frozen=True)
class VisionHints:
    category_hint: str | None = None
    query: str | None = None


class VisionProvider(Protocol):
    async def analyze_images(
        self, images: list[ImageInput], hints: VisionHints
    ) -> VisionDetectionResult: ...


class VisionProviderError(RuntimeError):
    """A provider failed without exposing implementation details."""


class VisionProviderConfigurationError(VisionProviderError):
    pass


class VisionProviderResponseError(VisionProviderError):
    pass


class VisionProviderTimeoutError(VisionProviderError):
    pass
