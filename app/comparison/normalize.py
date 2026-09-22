"""Unit conversion and normalized price calculation."""

from pydantic import BaseModel

from app.comparison.categories import CATEGORY_CONFIG, CategoryRule
from app.models.product import Product

UNIT_DIMENSIONS = {
    "g": "mass",
    "kg": "mass",
    "ml": "volume",
    "l": "volume",
    "unit": "count",
    "units": "count",
    "m": "length",
}

TO_BASE_UNIT = {
    "g": 1.0,
    "kg": 1000.0,
    "ml": 1.0,
    "l": 1000.0,
    "unit": 1.0,
    "units": 1.0,
    "m": 1.0,
}


class NormalizedPrice(BaseModel):
    normalized_price: float
    comparison_quantity: float
    comparison_unit: str
    display_unit: str


def convert_quantity(quantity: float, from_unit: str, to_unit: str) -> float:
    """Convert between supported units of the same physical dimension."""

    if from_unit not in UNIT_DIMENSIONS or to_unit not in UNIT_DIMENSIONS:
        raise ValueError(f"unknown unit conversion: {from_unit} to {to_unit}")
    if UNIT_DIMENSIONS[from_unit] != UNIT_DIMENSIONS[to_unit]:
        raise ValueError(f"incompatible units: {from_unit} and {to_unit}")
    base_quantity = quantity * TO_BASE_UNIT[from_unit]
    return base_quantity / TO_BASE_UNIT[to_unit]


def _total_quantity(product: Product, rule: CategoryRule) -> float:
    if rule.uses_package_length:
        if UNIT_DIMENSIONS[product.unit] != "count":
            raise ValueError(
                f"unit '{product.unit}' is incompatible with category '{product.category}'"
            )
        if product.package_count is None or product.unit_length is None:
            raise ValueError(
                f"category '{product.category}' requires package_count and unit_length"
            )
        return product.package_count * product.unit_length

    product_dimension = UNIT_DIMENSIONS[product.unit]
    if product_dimension != rule.dimension:
        raise ValueError(
            f"unit '{product.unit}' is incompatible with category '{product.category}'"
        )
    return convert_quantity(product.quantity, product.unit, rule.comparison_unit)


def normalize_product(product: Product) -> NormalizedPrice:
    """Calculate a product price at its category's comparison quantity."""

    rule = CATEGORY_CONFIG[product.category]
    total = _total_quantity(product, rule)
    normalized_price = product.price * rule.comparison_quantity / total
    return NormalizedPrice(
        normalized_price=round(normalized_price, 2),
        comparison_quantity=rule.comparison_quantity,
        comparison_unit=rule.comparison_unit,
        display_unit=rule.display_unit,
    )
