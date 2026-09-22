"""OpenAI Responses API vision provider."""

import base64

from openai import APITimeoutError, OpenAI
from pydantic import ValidationError

from app.models.detection import VisionDetectionResult
from app.vision.base import (
    ImageInput,
    VisionHints,
    VisionProviderError,
    VisionProviderResponseError,
    VisionProviderTimeoutError,
)
from app.vision.prompts import VISION_EXTRACTION_PROMPT


class OpenAIVisionProvider:
    """Extract shelf observations with structured output, without ranking them."""

    def __init__(self, api_key: str, model: str, timeout: float = 45) -> None:
        self.model = model
        self.client = OpenAI(api_key=api_key, timeout=timeout, max_retries=1)

    def analyze_images(
        self, images: list[ImageInput], hints: VisionHints
    ) -> VisionDetectionResult:
        hint_text = (
            f"Optional category hint: {hints.category_hint or 'none'}. "
            f"Optional search query: {hints.query or 'none'}. "
            "Hints narrow attention but must never cause invented detections. "
            "source_image_index is the zero-based position of the source image."
        )
        content: list[dict[str, str]] = [{"type": "input_text", "text": hint_text}]
        for index, image in enumerate(images):
            encoded = base64.b64encode(image.content).decode("ascii")
            content.append(
                {"type": "input_text", "text": f"Source image index: {index}"}
            )
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{image.media_type};base64,{encoded}",
                    "detail": "high",
                }
            )
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": VISION_EXTRACTION_PROMPT},
                    {"role": "user", "content": content},
                ],
                text_format=VisionDetectionResult,
            )
        except APITimeoutError as error:
            raise VisionProviderTimeoutError("vision provider timed out") from error
        except ValidationError as error:
            raise VisionProviderResponseError("vision provider returned invalid data") from error
        except Exception as error:
            raise VisionProviderError("vision provider request failed") from error

        parsed = response.output_parsed
        if parsed is None:
            raise VisionProviderResponseError("vision provider returned no structured data")
        return parsed
