"""Local detector used until an image-recognition provider is introduced."""

import json
from pathlib import Path

from app.models.detection import DetectedProductCandidate, VisionDetectionResult
from app.models.product import Product
from app.vision.base import ImageInput, VisionHints

DEFAULT_PRODUCTS_PATH = Path(__file__).resolve().parents[2] / "examples" / "products.json"


class MockProductDetector:
    """Return structured fixture data behind a replaceable detector interface."""

    def __init__(self, products_path: Path = DEFAULT_PRODUCTS_PATH) -> None:
        self.products_path = products_path

    def detect(self) -> list[Product]:
        data = json.loads(self.products_path.read_text(encoding="utf-8"))
        return [Product.model_validate(item) for item in data]


class MockVisionProvider:
    """Deterministic image provider for local development and CI."""

    async def analyze_images(
        self, images: list[ImageInput], hints: VisionHints
    ) -> VisionDetectionResult:
        products = MockProductDetector().detect()
        candidates = [
            DetectedProductCandidate(
                detection_id=f"mock-{index}",
                source_image_index=index % len(images),
                name=product.name,
                brand=product.brand,
                variant=product.variant,
                category=product.category,
                price=product.price,
                price_text=f"${product.price:g}",
                quantity=product.quantity,
                quantity_text=f"{product.quantity:g} {product.unit}",
                unit=product.unit,
                package_count=product.package_count,
                unit_length=product.unit_length,
                confidence=product.confidence or 0.99,
                product_confidence=product.confidence or 0.99,
                price_confidence=0.99,
                association_confidence=0.99,
                product_bbox=None,
                price_bbox=None,
                price_type="regular",
                price_condition=None,
                issues=[],
                requires_confirmation=False,
            )
            for index, product in enumerate(products)
        ]
        return VisionDetectionResult(candidates=candidates, warnings=[])
