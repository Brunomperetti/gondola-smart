"""Central configuration for all comparable product categories."""

from dataclasses import dataclass
from typing import Literal

Dimension = Literal["mass", "volume", "count", "length"]


@dataclass(frozen=True)
class CategoryRule:
    dimension: Dimension
    comparison_quantity: float
    comparison_unit: str
    display_unit: str
    uses_package_length: bool = False


CATEGORY_CONFIG: dict[str, CategoryRule] = {
    "cookies": CategoryRule("mass", 100, "g", "100 g"),
    "toothpaste": CategoryRule("mass", 100, "g", "100 g"),
    "pasta": CategoryRule("mass", 1, "kg", "kg"),
    "rice": CategoryRule("mass", 1, "kg", "kg"),
    "shampoo": CategoryRule("volume", 1, "l", "litro"),
    "detergent": CategoryRule("volume", 1, "l", "litro"),
    "soda": CategoryRule("volume", 1, "l", "litro"),
    "toilet_paper": CategoryRule("length", 1, "m", "metro", True),
    "paper_towel": CategoryRule("length", 1, "m", "metro", True),
    "diapers": CategoryRule("count", 1, "unit", "unidad"),
    "eggs": CategoryRule("count", 1, "unit", "unidad"),
}
