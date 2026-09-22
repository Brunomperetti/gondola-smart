"""Models for incomplete and potentially uncertain visual detections."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

from app.models.product import SupportedUnit


class DetectionIssue(StrEnum):
    MISSING_NAME = "MISSING_NAME"
    MISSING_BRAND = "MISSING_BRAND"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MISSING_PRICE = "MISSING_PRICE"
    MISSING_QUANTITY = "MISSING_QUANTITY"
    MISSING_UNIT = "MISSING_UNIT"
    MISSING_PACKAGE_COUNT = "MISSING_PACKAGE_COUNT"
    MISSING_UNIT_LENGTH = "MISSING_UNIT_LENGTH"
    AMBIGUOUS_PRICE = "AMBIGUOUS_PRICE"
    AMBIGUOUS_PRICE_ASSOCIATION = "AMBIGUOUS_PRICE_ASSOCIATION"
    CONDITIONAL_PRICE = "CONDITIONAL_PRICE"
    UNSUPPORTED_CATEGORY = "UNSUPPORTED_CATEGORY"
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"


PriceType = Literal["regular", "promotion", "loyalty", "unknown"]


class BoundingBox(RootModel[tuple[float, float, float, float]]):
    """Normalized image coordinates."""

    @model_validator(mode="after")
    def validate_coordinates(self) -> "BoundingBox":
        x_min, y_min, x_max, y_max = self.root
        if not all(0 <= coordinate <= 1 for coordinate in self.root):
            raise ValueError("bounding box coordinates must be between 0 and 1")
        if x_max < x_min or y_max < y_min:
            raise ValueError("bounding box maximums must follow minimums")
        return self


class DetectedProductCandidate(BaseModel):
    """A visual observation; missing data is deliberately allowed."""

    model_config = ConfigDict(str_strip_whitespace=True)

    detection_id: str = Field(min_length=1)
    source_image_index: int = Field(ge=0)
    name: str | None = None
    brand: str | None = None
    variant: str | None = None
    category: str | None = None
    price: float | None = None
    price_text: str | None = None
    quantity: float | None = None
    quantity_text: str | None = None
    unit: SupportedUnit | None = None
    package_count: int | None = None
    unit_length: float | None = None
    confidence: float = Field(ge=0, le=1)
    product_confidence: float | None = Field(default=None, ge=0, le=1)
    price_confidence: float | None = Field(default=None, ge=0, le=1)
    association_confidence: float | None = Field(default=None, ge=0, le=1)
    product_bbox: BoundingBox | None = None
    price_bbox: BoundingBox | None = None
    price_type: PriceType = "unknown"
    price_condition: str | None = None
    issues: list[DetectionIssue] = Field(default_factory=list)
    requires_confirmation: bool = False


class VisionDetectionResult(BaseModel):
    candidates: list[DetectedProductCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
