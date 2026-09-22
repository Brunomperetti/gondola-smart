from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "gondola-smart",
        "version": "0.1.0",
    }


def test_compare() -> None:
    response = client.post(
        "/compare",
        json={
            "products": [
                {
                    "id": "one",
                    "name": "Arroz",
                    "brand": "Marca",
                    "category": "rice",
                    "price": 1800,
                    "quantity": 1,
                    "unit": "kg",
                }
            ]
        },
    )
    assert response.status_code == 200
    item = response.json()["rankings"]["rice"][0]
    assert item["normalized_price"] == 1800
    assert item["position"] == 1


def test_compare_accepts_empty_product_list() -> None:
    response = client.post("/compare", json={"products": []})

    assert response.status_code == 200
    assert response.json() == {"rankings": {}}


def test_demo_loads_fixture_and_groups_products() -> None:
    response = client.get("/demo")
    assert response.status_code == 200
    rankings = response.json()["rankings"]
    assert set(rankings) == {"toothpaste", "cookies", "detergent", "toilet_paper"}
    assert all(len(group) == 3 for group in rankings.values())


def test_mock_analysis_runs_full_flow() -> None:
    response = client.post("/analyze/mock")
    assert response.status_code == 200
    assert response.json()["rankings"]["toothpaste"][0]["position"] == 1


def test_api_returns_clear_validation_errors() -> None:
    response = client.post(
        "/compare",
        json={
            "products": [
                {
                    "id": "bad",
                    "name": "Inválido",
                    "brand": "Marca",
                    "category": "unknown",
                    "price": 0,
                    "quantity": 1,
                    "unit": "kg",
                }
            ]
        },
    )
    assert response.status_code == 422
    assert "unknown category" in response.text
