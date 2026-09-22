from app.comparison.ranking import rank_products
from app.models.product import Product


def make_product(identifier: str, category: str, price: float, quantity: float) -> Product:
    return Product(
        id=identifier,
        name=identifier,
        brand="Marca",
        category=category,
        price=price,
        quantity=quantity,
        unit="g",
    )


def test_ranking_orders_by_normalized_price_and_calculates_savings() -> None:
    products = [
        make_product("expensive", "cookies", 900, 100),
        make_product("best", "cookies", 1200, 300),
        make_product("middle", "cookies", 1000, 200),
    ]

    ranked = rank_products(products)["cookies"]

    assert [item.product.id for item in ranked] == ["best", "middle", "expensive"]
    assert [item.position for item in ranked] == [1, 2, 3]
    assert ranked[0].savings_vs_next == 100
    assert ranked[-1].savings_vs_next is None


def test_ranking_groups_different_categories() -> None:
    cookie = make_product("cookie", "cookies", 1000, 200)
    pasta = make_product("pasta", "pasta", 1000, 500)

    result = rank_products([cookie, pasta])

    assert set(result) == {"cookies", "pasta"}
    assert result["cookies"][0].product.id == "cookie"
    assert result["pasta"][0].product.id == "pasta"


def test_equal_normalized_prices_preserve_input_order() -> None:
    first = make_product("first", "cookies", 1000, 200)
    second = make_product("second", "cookies", 500, 100)

    ranked = rank_products([second, first])["cookies"]

    assert [item.product.id for item in ranked] == ["second", "first"]
    assert ranked[0].savings_vs_next == 0


def test_low_confidence_requires_confirmation() -> None:
    uncertain = make_product("uncertain", "cookies", 1000, 200).model_copy(
        update={"confidence": 0.74}
    )
    certain = make_product("certain", "cookies", 1000, 200).model_copy(
        update={"confidence": 0.75}
    )

    assert uncertain.requires_confirmation is True
    assert certain.requires_confirmation is False
