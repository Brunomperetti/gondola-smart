import pytest
from pydantic import ValidationError

from app.comparison.normalize import convert_quantity, normalize_product
from app.models.product import Product


def product(**changes: object) -> Product:
    values = {
        "id": "test_1",
        "name": "Producto",
        "brand": "Marca",
        "category": "cookies",
        "price": 1000,
        "quantity": 200,
        "unit": "g",
    }
    values.update(changes)
    return Product.model_validate(values)


def test_converts_grams_to_kilos() -> None:
    assert convert_quantity(500, "g", "kg") == 0.5


def test_converts_kilos_to_grams() -> None:
    assert convert_quantity(1.5, "kg", "g") == 1500


def test_converts_milliliters_to_liters() -> None:
    assert convert_quantity(1500, "ml", "l") == 1.5


def test_converts_liters_to_milliliters() -> None:
    assert convert_quantity(2, "l", "ml") == 2000


def test_price_per_100_grams() -> None:
    result = normalize_product(product(price=3200, quantity=140, category="toothpaste"))
    assert result.normalized_price == 2285.71
    assert result.display_unit == "100 g"


def test_price_per_kilo() -> None:
    result = normalize_product(product(price=1500, quantity=500, category="pasta"))
    assert result.normalized_price == 3000
    assert result.comparison_unit == "kg"


def test_price_per_liter() -> None:
    result = normalize_product(
        product(price=1800, quantity=750, unit="ml", category="detergent")
    )
    assert result.normalized_price == 2400


def test_price_per_unit() -> None:
    result = normalize_product(
        product(price=3600, quantity=12, unit="units", category="eggs")
    )
    assert result.normalized_price == 300


def test_price_per_total_meter_of_toilet_paper() -> None:
    result = normalize_product(
        product(
            price=4800,
            quantity=4,
            unit="units",
            category="toilet_paper",
            package_count=4,
            unit_length=30,
        )
    )
    assert result.normalized_price == 40
    assert result.display_unit == "metro"


def test_toilet_paper_requires_package_count() -> None:
    with pytest.raises(ValidationError, match="requires package_count"):
        product(
            category="toilet_paper",
            quantity=4,
            unit="units",
            unit_length=30,
        )


def test_toilet_paper_requires_unit_length() -> None:
    with pytest.raises(ValidationError, match="requires unit_length"):
        product(
            category="toilet_paper",
            quantity=4,
            unit="units",
            package_count=4,
        )


def test_unit_quantity_must_match_package_count() -> None:
    with pytest.raises(ValidationError, match="quantity must match package_count"):
        product(
            category="toilet_paper",
            quantity=4,
            unit="units",
            package_count=6,
            unit_length=30,
        )


@pytest.mark.parametrize(
    ("field", "value"), [("package_count", 0), ("unit_length", 0)]
)
def test_toilet_paper_requires_positive_package_values(
    field: str, value: float
) -> None:
    package_data: dict[str, object] = {"package_count": 4, "unit_length": 30}
    package_data[field] = value

    with pytest.raises(ValidationError, match="greater than 0"):
        product(
            category="toilet_paper",
            quantity=4,
            unit="units",
            **package_data,
        )


@pytest.mark.parametrize("field,value", [("price", 0), ("quantity", -1)])
def test_rejects_non_positive_values(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        product(**{field: value})


def test_rejects_unknown_category_and_unit() -> None:
    with pytest.raises(ValidationError, match="unknown category"):
        product(category="unknown")
    with pytest.raises(ValidationError):
        product(unit="oz")


def test_rejects_unit_incompatible_with_category() -> None:
    with pytest.raises(ValueError, match="incompatible"):
        normalize_product(product(category="soda", unit="g"))
