#!/usr/bin/env python3
"""Run one real OpenAI vision extraction without starting FastAPI."""

import argparse
import asyncio
from io import BytesIO
import os
from pathlib import Path
import sys

from PIL import Image, UnidentifiedImageError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings  # noqa: E402
from app.vision.base import ImageInput, VisionHints  # noqa: E402
from app.vision.openai_provider import OpenAIVisionProvider  # noqa: E402

SUPPORTED_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a real shelf-vision smoke test.")
    parser.add_argument("image", type=Path, help="JPEG, PNG, or WebP shelf photograph")
    parser.add_argument("--category", dest="category_hint")
    parser.add_argument("--query")
    return parser.parse_args()


def load_image(path: Path) -> ImageInput:
    content = path.read_bytes()
    try:
        with Image.open(BytesIO(content)) as opened:
            image_format = opened.format
            opened.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as error:
        raise ValueError(f"'{path}' is not a valid image") from error
    if image_format not in SUPPORTED_FORMATS:
        raise ValueError("only JPEG, PNG, and WebP images are supported")
    return ImageInput(
        content=content,
        media_type=SUPPORTED_FORMATS[image_format],
        filename=path.name,
    )


async def run() -> None:
    args = parse_args()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    settings = get_settings()
    provider = OpenAIVisionProvider(
        api_key=api_key,
        model=settings.openai_vision_model,
        timeout=settings.openai_timeout_seconds,
    )
    result = await provider.analyze_images(
        [load_image(args.image)],
        VisionHints(category_hint=args.category_hint, query=args.query),
    )
    print(result.model_dump_json(indent=2))


def main() -> int:
    try:
        asyncio.run(run())
    except Exception as error:
        print(f"Live vision smoke test failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
