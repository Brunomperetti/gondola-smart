"""Product domain model."""

from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.comparison.categories import CATEGORY_CONFIG

SupportedUnit = Literal["g", "kg", "ml", "l", "unit", "units", "m"]


class Product(BaseModel):
    """A product and the structured data needed to compare its value."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    variant: str | None = None
    category: str
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    unit: SupportedUnit
    package_count: int | None = Field(default=None, gt=0)
    unit_length: float | None = Field(default=None, gt=0)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("category")
    @classmethod
    def category_must_be_supported(cls, value: str) -> str:
        if value not in CATEGORY_CONFIG:
            supported = ", ".join(sorted(CATEGORY_CONFIG))
            raise ValueError(f"unknown category '{value}'; supported: {supported}")
        return value

    @model_validator(mode="after")
    def validate_package_data(self) -> Self:
        """Ensure package metadata represents a coherent physical package."""

        paper_categories = {"toilet_paper", "paper_towel"}
        if self.category in paper_categories:
            if self.package_count is None:
                raise ValueError(f"category '{self.category}' requires package_count")
            if self.unit_length is None:
                raise ValueError(f"category '{self.category}' requires unit_length")

        if (
            self.unit in {"unit", "units"}
            and self.package_count is not None
            and self.quantity != self.package_count
        ):
            raise ValueError("quantity must match package_count for unit-based products")
        return self

    @computed_field
    @property
    def requires_confirmation(self) -> bool:
        """Flag uncertain detections without discarding them."""

        return self.confidence is not None and self.confidence < 0.75
