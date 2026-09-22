"""Conservative identity-based deduplication for overlapping photographs."""

import re

from app.models.detection import DetectedProductCandidate, DetectionIssue


def _text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def _identity(candidate: DetectedProductCandidate) -> tuple[object, ...] | None:
    # Name and brand prevent same-brand variants from being collapsed.
    if not candidate.name or not candidate.brand:
        return None
    return (
        _text(candidate.brand),
        _text(candidate.name),
        _text(candidate.variant),
        candidate.quantity,
        candidate.unit,
        candidate.price,
    )


def deduplicate_candidates(
    candidates: list[DetectedProductCandidate],
) -> tuple[list[DetectedProductCandidate], list[DetectedProductCandidate]]:
    """Keep the most confident exact identity and return discarded duplicates."""

    unique: list[DetectedProductCandidate] = []
    positions: dict[tuple[object, ...], int] = {}
    duplicates: list[DetectedProductCandidate] = []
    for candidate in candidates:
        key = _identity(candidate)
        if key is None or key not in positions:
            if key is not None:
                positions[key] = len(unique)
            unique.append(candidate)
            continue
        current_index = positions[key]
        current = unique[current_index]
        discarded = candidate
        if candidate.confidence > current.confidence:
            unique[current_index] = candidate
            discarded = current
        issues = list(dict.fromkeys([*discarded.issues, DetectionIssue.DUPLICATE_CANDIDATE]))
        duplicates.append(
            discarded.model_copy(update={"issues": issues, "requires_confirmation": True})
        )
    return unique, duplicates
