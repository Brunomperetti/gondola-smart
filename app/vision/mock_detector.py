"""Local detector used until an image-recognition provider is introduced."""

import json
from pathlib import Path

from app.models.product import Product

DEFAULT_PRODUCTS_PATH = Path(__file__).resolve().parents[2] / "examples" / "products.json"


class MockProductDetector:
    """Return structured fixture data behind a replaceable detector interface."""

    def __init__(self, products_path: Path = DEFAULT_PRODUCTS_PATH) -> None:
        self.products_path = products_path

    def detect(self) -> list[Product]:
        data = json.loads(self.products_path.read_text(encoding="utf-8"))
        return [Product.model_validate(item) for item in data]
