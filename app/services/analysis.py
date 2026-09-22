"""Deterministic orchestration from uploads to safe rankings."""

from io import BytesIO

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from app.comparison.categories import CATEGORY_CONFIG
from app.comparison.normalize import UNIT_DIMENSIONS
from app.comparison.ranking import RankedProduct, rank_products
from app.config import Settings
from app.models.detection import DetectedProductCandidate, DetectionIssue
from app.models.product import Product
from app.vision.base import ImageInput, VisionHints, VisionProvider
from app.vision.deduplication import deduplicate_candidates

ALLOWED_MEDIA_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
CRITICAL_ISSUES = set(DetectionIssue) - {DetectionIssue.DUPLICATE_CANDIDATE}


class AnalysisRequestError(ValueError):
    status_code = 400


class UnsupportedImageError(AnalysisRequestError):
    status_code = 415


class ImageTooLargeError(AnalysisRequestError):
    status_code = 413


class HintValidationError(AnalysisRequestError):
    status_code = 422


class AnalysisSummary(BaseModel):
    images_received: int
    detections_total: int
    duplicates_removed: int
    rankable_count: int
    needs_confirmation_count: int
    unsupported_count: int


class AnalysisResponse(BaseModel):
    analysis: AnalysisSummary
    rankings: dict[str, list[RankedProduct]]
    rankable_products: list[Product]
    needs_confirmation: list[DetectedProductCandidate]
    unsupported_products: list[DetectedProductCandidate]
    warnings: list[str]


async def validate_images(
    uploads: list[UploadFile], settings: Settings
) -> list[ImageInput]:
    if not uploads:
        raise AnalysisRequestError("at least one image is required")
    if len(uploads) > settings.max_images_per_analysis:
        raise AnalysisRequestError(
            f"at most {settings.max_images_per_analysis} images are allowed"
        )

    maximum = settings.max_image_size_mb * 1024 * 1024
    images: list[ImageInput] = []
    for upload in uploads:
        media_type = (upload.content_type or "").lower()
        if media_type not in ALLOWED_MEDIA_TYPES:
            raise UnsupportedImageError(
                "supported image types are image/jpeg, image/png, and image/webp"
            )
        content = await upload.read(maximum + 1)
        if len(content) > maximum:
            raise ImageTooLargeError(
                f"each image must be at most {settings.max_image_size_mb} MB"
            )
        try:
            with Image.open(BytesIO(content)) as opened:
                detected_format = opened.format
                opened.verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as error:
            raise AnalysisRequestError("uploaded content is not a valid image") from error
        if detected_format != ALLOWED_MEDIA_TYPES[media_type]:
            raise UnsupportedImageError(
                "image content does not match its declared media type"
            )
        images.append(ImageInput(content, media_type, upload.filename))
    return images


def _add_issue(
    candidate: DetectedProductCandidate, issue: DetectionIssue
) -> DetectedProductCandidate:
    issues = list(dict.fromkeys([*candidate.issues, issue]))
    return candidate.model_copy(update={"issues": issues})


def classify_candidate(
    candidate: DetectedProductCandidate,
) -> tuple[DetectedProductCandidate, Product | None]:
    """Validate an observation and convert it only when ranking is safe."""

    checked = candidate
    required = (("name", DetectionIssue.MISSING_NAME), ("brand", DetectionIssue.MISSING_BRAND))
    for field, issue in required:
        if not getattr(checked, field):
            checked = _add_issue(checked, issue)
    if checked.category not in CATEGORY_CONFIG:
        checked = _add_issue(checked, DetectionIssue.UNSUPPORTED_CATEGORY)
    if checked.price is None or checked.price <= 0:
        checked = _add_issue(checked, DetectionIssue.MISSING_PRICE)
    if checked.quantity is None or checked.quantity <= 0:
        checked = _add_issue(checked, DetectionIssue.MISSING_QUANTITY)
    if checked.unit is None:
        checked = _add_issue(checked, DetectionIssue.MISSING_UNIT)
    if checked.confidence < 0.75:
        checked = _add_issue(checked, DetectionIssue.LOW_CONFIDENCE)
    if checked.product_confidence is not None and checked.product_confidence < 0.75:
        checked = _add_issue(checked, DetectionIssue.LOW_CONFIDENCE)
    if checked.price_confidence is not None and checked.price_confidence < 0.75:
        checked = _add_issue(checked, DetectionIssue.AMBIGUOUS_PRICE)
    if checked.association_confidence is not None and checked.association_confidence < 0.75:
        checked = _add_issue(checked, DetectionIssue.AMBIGUOUS_PRICE_ASSOCIATION)
    # Unknown means the provider could not establish that the visible price is
    # unconditional. For v0.2 only an explicit regular price can be ranked.
    if (
        checked.price_type in {"promotion", "loyalty", "unknown"}
        or checked.price_condition
    ):
        checked = _add_issue(checked, DetectionIssue.CONDITIONAL_PRICE)
    if checked.category in {"toilet_paper", "paper_towel"}:
        if checked.package_count is None or checked.package_count <= 0:
            checked = _add_issue(checked, DetectionIssue.MISSING_PACKAGE_COUNT)
        if checked.unit_length is None or checked.unit_length <= 0:
            checked = _add_issue(checked, DetectionIssue.MISSING_UNIT_LENGTH)

    # Reject dimension mismatches before they can reach the stable v0.1 engine.
    if checked.category in CATEGORY_CONFIG and checked.unit:
        rule = CATEGORY_CONFIG[checked.category]
        expected = "count" if rule.uses_package_length else rule.dimension
        if UNIT_DIMENSIONS[checked.unit] != expected:
            checked = _add_issue(checked, DetectionIssue.MISSING_UNIT)

    must_confirm = checked.requires_confirmation or bool(
        set(checked.issues) & CRITICAL_ISSUES
    )
    checked = checked.model_copy(update={"requires_confirmation": must_confirm})
    if must_confirm:
        return checked, None

    try:
        product = Product(
            id=checked.detection_id,
            name=checked.name or "",
            brand=checked.brand or "",
            variant=checked.variant,
            category=checked.category or "",
            price=checked.price or 0,
            quantity=checked.quantity or 0,
            unit=checked.unit,  # type: ignore[arg-type]
            package_count=checked.package_count,
            unit_length=checked.unit_length,
            confidence=checked.confidence,
        )
    except ValueError:
        checked = _add_issue(checked, DetectionIssue.MISSING_UNIT)
        return checked.model_copy(update={"requires_confirmation": True}), None
    return checked, product


class AnalysisService:
    def __init__(self, provider: VisionProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    async def analyze(
        self,
        uploads: list[UploadFile],
        category_hint: str | None = None,
        query: str | None = None,
    ) -> AnalysisResponse:
        if category_hint and category_hint not in CATEGORY_CONFIG:
            raise HintValidationError("category_hint is not a supported category")
        images = await validate_images(uploads, self.settings)
        detected = await self.provider.analyze_images(
            images, VisionHints(category_hint=category_hint, query=query)
        )
        unique, duplicates = deduplicate_candidates(detected.candidates)
        rankable: list[Product] = []
        confirmation: list[DetectedProductCandidate] = list(duplicates)
        unsupported: list[DetectedProductCandidate] = []
        for candidate in unique:
            checked, product = classify_candidate(candidate)
            if DetectionIssue.UNSUPPORTED_CATEGORY in checked.issues:
                unsupported.append(checked)
            elif product is None:
                confirmation.append(checked)
            else:
                rankable.append(product)
        warnings = list(detected.warnings)
        if duplicates:
            warnings.append(f"Removed {len(duplicates)} probable duplicate detection(s).")
        return AnalysisResponse(
            analysis=AnalysisSummary(
                images_received=len(images),
                detections_total=len(detected.candidates),
                duplicates_removed=len(duplicates),
                rankable_count=len(rankable),
                needs_confirmation_count=len(confirmation),
                unsupported_count=len(unsupported),
            ),
            rankings=rank_products(rankable),
            rankable_products=rankable,
            needs_confirmation=confirmation,
            unsupported_products=unsupported,
            warnings=warnings,
        )
