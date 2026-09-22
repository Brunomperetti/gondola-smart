"""Models for incomplete and potentially uncertain visual detections."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class BoundingBox(BaseModel):
    """Structured normalized image coordinates."""

    model_config = ConfigDict(extra="forbid")

    x_min: float = Field(ge=0, le=1)
    y_min: float = Field(ge=0, le=1)
    x_max: float = Field(ge=0, le=1)
    y_max: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_coordinates(self) -> "BoundingBox":
        if self.x_max < self.x_min or self.y_max < self.y_min:
            raise ValueError("bounding box maximums must follow minimums")
        return self


class DetectedProductCandidate(BaseModel):
    """A visual observation; missing data is deliberately allowed."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    detection_id: str = Field(min_length=1)
    source_image_index: int = Field(ge=0)
    name: str | None
    brand: str | None
    variant: str | None
    category: str | None
    price: float | None
    price_text: str | None
    quantity: float | None
    quantity_text: str | None
    unit: SupportedUnit | None
    package_count: int | None
    unit_length: float | None
    confidence: float = Field(ge=0, le=1)
    product_confidence: float | None = Field(ge=0, le=1)
    price_confidence: float | None = Field(ge=0, le=1)
    association_confidence: float | None = Field(ge=0, le=1)
    product_bbox: BoundingBox | None
    price_bbox: BoundingBox | None
    price_type: PriceType
    price_condition: str | None
    issues: list[DetectionIssue]
    requires_confirmation: bool


class VisionDetectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[DetectedProductCandidate]
    warnings: list[str]
