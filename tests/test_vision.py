import asyncio
from io import BytesIO
import inspect
import os

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.config import Settings, get_settings
from app.main import app
from app.models.detection import (
    BoundingBox,
    DetectedProductCandidate,
    DetectionIssue,
    VisionDetectionResult,
)
from app.services.analysis import classify_candidate
from app.vision.base import ImageInput, VisionHints, VisionProviderError
from app.vision.deduplication import deduplicate_candidates
from app.vision.mock_detector import MockVisionProvider
from app.vision.openai_provider import OpenAIVisionProvider
from app.vision.provider_factory import get_vision_provider


def image_bytes(image_format: str = "JPEG", size: tuple[int, int] = (40, 40)) -> bytes:
    stream = BytesIO()
    Image.new("RGB", size, "white").save(stream, format=image_format)
    return stream.getvalue()


def candidate(**changes: object) -> DetectedProductCandidate:
    values: dict[str, object] = {
        "detection_id": "one",
        "source_image_index": 0,
        "name": "Total",
        "brand": "Colgate",
        "variant": None,
        "category": "toothpaste",
        "price": 3200,
        "price_text": "$3.200",
        "quantity": 140,
        "quantity_text": "140 g",
        "unit": "g",
        "confidence": 0.95,
        "product_confidence": 0.95,
        "price_confidence": 0.95,
        "association_confidence": 0.95,
        "product_bbox": None,
        "price_bbox": None,
        "price_type": "regular",
        "price_condition": None,
        "package_count": None,
        "unit_length": None,
        "issues": [],
        "requires_confirmation": False,
    }
    values.update(changes)
    return DetectedProductCandidate.model_validate(values)


@pytest.mark.parametrize(
    ("fmt", "content_type"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")],
)
def test_analyze_accepts_real_image_formats(fmt: str, content_type: str) -> None:
    response = TestClient(app).post(
        "/analyze", files={"files": (f"shelf.{fmt.lower()}", image_bytes(fmt), content_type)}
    )
    assert response.status_code == 200
    assert response.json()["analysis"]["images_received"] == 1


def test_analyze_mock_runs_detection_classification_and_ranking() -> None:
    response = TestClient(app).post(
        "/analyze",
        files={"files": ("shelf.jpg", image_bytes("JPEG"), "image/jpeg")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["rankable_count"] > 0
    assert payload["rankings"]["toothpaste"][0]["product"]["name"] == "Total Clean Mint"
    assert payload["rankings"]["toothpaste"][0]["position"] == 1


def test_rejects_fake_jpeg() -> None:
    response = TestClient(app).post(
        "/analyze", files={"files": ("fake.jpg", b"not an image", "image/jpeg")}
    )
    assert response.status_code == 400


def test_rejects_unsupported_media_type() -> None:
    response = TestClient(app).post(
        "/analyze", files={"files": ("shelf.gif", b"GIF89a", "image/gif")}
    )
    assert response.status_code == 415


def test_rejects_too_large_image(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_IMAGE_SIZE_MB", "1")
    get_settings.cache_clear()
    try:
        response = TestClient(app).post(
            "/analyze",
            files={"files": ("huge.jpg", b"x" * (1024 * 1024 + 1), "image/jpeg")},
        )
        assert response.status_code == 413
    finally:
        get_settings.cache_clear()


def test_rejects_zero_and_more_than_three_images() -> None:
    client = TestClient(app)
    assert client.post("/analyze").status_code == 400
    files = [("files", (f"{i}.png", image_bytes("PNG"), "image/png")) for i in range(4)]
    assert client.post("/analyze", files=files).status_code == 400


def test_candidate_transforms_to_product() -> None:
    checked, product = classify_candidate(candidate())
    assert checked.requires_confirmation is False
    assert product is not None
    assert product.id == "one"


@pytest.mark.parametrize(
    ("changes", "issue"),
    [
        ({"price": None}, DetectionIssue.MISSING_PRICE),
        ({"quantity": None}, DetectionIssue.MISSING_QUANTITY),
        ({"category": "cereal"}, DetectionIssue.UNSUPPORTED_CATEGORY),
        ({"confidence": 0.74}, DetectionIssue.LOW_CONFIDENCE),
        ({"association_confidence": 0.5}, DetectionIssue.AMBIGUOUS_PRICE_ASSOCIATION),
        ({"price_type": "loyalty", "price_condition": "Club X"}, DetectionIssue.CONDITIONAL_PRICE),
        ({"price_type": "unknown"}, DetectionIssue.CONDITIONAL_PRICE),
    ],
)
def test_unsafe_candidates_are_not_products(
    changes: dict[str, object], issue: DetectionIssue
) -> None:
    checked, product = classify_candidate(candidate(**changes))
    assert product is None
    assert checked.requires_confirmation is True
    assert issue in checked.issues


def test_complete_paper_is_rankable_but_missing_metres_is_not() -> None:
    complete = candidate(
        category="toilet_paper", quantity=4, unit="units", package_count=4, unit_length=30
    )
    assert classify_candidate(complete)[1] is not None
    checked, product = classify_candidate(complete.model_copy(update={"unit_length": None}))
    assert product is None
    assert DetectionIssue.MISSING_UNIT_LENGTH in checked.issues


def test_deduplicates_overlap_and_keeps_highest_confidence() -> None:
    first = candidate(confidence=0.8)
    second = candidate(detection_id="two", source_image_index=1, confidence=0.98)
    unique, duplicates = deduplicate_candidates([first, second])
    assert [item.detection_id for item in unique] == ["two"]
    assert DetectionIssue.DUPLICATE_CANDIDATE in duplicates[0].issues


def test_does_not_deduplicate_distinct_variants() -> None:
    unique, duplicates = deduplicate_candidates(
        [candidate(variant="Mint"), candidate(detection_id="two", variant="Whitening")]
    )
    assert len(unique) == 2
    assert duplicates == []


def test_mock_provider_and_factory() -> None:
    provider = get_vision_provider(Settings(vision_provider="mock"))
    result = asyncio.run(
        provider.analyze_images(
            [ImageInput(image_bytes(), "image/jpeg")], VisionHints()
        )
    )
    assert isinstance(provider, MockVisionProvider)
    assert result.candidates


def test_openai_provider_contract_is_async() -> None:
    assert inspect.iscoroutinefunction(OpenAIVisionProvider.analyze_images)


def test_openai_factory_requires_key() -> None:
    with pytest.raises(VisionProviderError, match="OPENAI_API_KEY"):
        get_vision_provider(Settings(vision_provider="openai", openai_api_key=None))


def test_analyze_returns_503_when_openai_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VISION_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        response = TestClient(app).post(
            "/analyze",
            files={"files": ("shelf.png", image_bytes("PNG"), "image/png")},
        )
        assert response.status_code == 503
        assert "OPENAI_API_KEY" in response.text
    finally:
        get_settings.cache_clear()


def test_analyze_returns_controlled_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenProvider:
        async def analyze_images(
            self, images: list[ImageInput], hints: VisionHints
        ) -> VisionDetectionResult:
            raise VisionProviderError("vision provider request failed")

    monkeypatch.setattr("app.api.routes.get_vision_provider", lambda: BrokenProvider())
    response = TestClient(app).post(
        "/analyze", files={"files": ("shelf.png", image_bytes("PNG"), "image/png")}
    )
    assert response.status_code == 502
    assert response.json() == {"detail": "vision provider request failed"}


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_VISION_TESTS") != "1" or not os.getenv("OPENAI_API_KEY"),
    reason="set RUN_LIVE_VISION_TESTS=1 and OPENAI_API_KEY to run",
)
def test_live_openai_provider_opt_in() -> None:
    provider = get_vision_provider(
        Settings(vision_provider="openai", openai_api_key=os.environ["OPENAI_API_KEY"])
    )
    result = asyncio.run(
        provider.analyze_images(
            [ImageInput(image_bytes("PNG"), "image/png")], VisionHints()
        )
    )
    assert isinstance(result, VisionDetectionResult)


def test_structured_output_schema_uses_explicit_bounding_box_object() -> None:
    schema = VisionDetectionResult.model_json_schema()
    assert set(schema["required"]) == {"candidates", "warnings"}
    bbox = schema["$defs"]["BoundingBox"]
    assert bbox["type"] == "object"
    assert set(bbox["required"]) == {"x_min", "y_min", "x_max", "y_max"}
    assert bbox["additionalProperties"] is False
    for coordinate in bbox["properties"].values():
        assert coordinate["minimum"] == 0
        assert coordinate["maximum"] == 1
    candidate_schema = schema["$defs"]["DetectedProductCandidate"]
    assert set(candidate_schema["required"]) == set(candidate_schema["properties"])
    assert candidate_schema["additionalProperties"] is False


def test_bounding_box_validates_coordinate_order() -> None:
    valid = BoundingBox(x_min=0.1, y_min=0.2, x_max=0.8, y_max=0.9)
    assert valid.x_max == 0.8
    with pytest.raises(ValueError, match="maximums"):
        BoundingBox(x_min=0.8, y_min=0.2, x_max=0.1, y_max=0.9)
