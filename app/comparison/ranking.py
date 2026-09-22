"""Ranking engine, independent from the HTTP API."""

from collections import defaultdict

from pydantic import BaseModel

from app.comparison.normalize import normalize_product
from app.models.product import Product


class RankedProduct(BaseModel):
    position: int
    product: Product
    normalized_price: float
    comparison_quantity: float
    comparison_unit: str
    display_unit: str
    savings_vs_next: float | None = None


def rank_products(products: list[Product]) -> dict[str, list[RankedProduct]]:
    """Group products by category and rank each group by normalized price."""

    grouped: dict[str, list[Product]] = defaultdict(list)
    for product in products:
        grouped[product.category].append(product)

    rankings: dict[str, list[RankedProduct]] = {}
    for category, category_products in grouped.items():
        normalized = [(product, normalize_product(product)) for product in category_products]
        normalized.sort(key=lambda item: item[1].normalized_price)
        results: list[RankedProduct] = []
        for index, (product, value) in enumerate(normalized):
            savings = None
            if index + 1 < len(normalized):
                savings = round(
                    normalized[index + 1][1].normalized_price - value.normalized_price, 2
                )
            results.append(
                RankedProduct(
                    position=index + 1,
                    product=product,
                    savings_vs_next=savings,
                    **value.model_dump(),
                )
            )
        rankings[category] = results
    return rankings
