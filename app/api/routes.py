"""Gondola Smart API routes."""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app import __version__
from app.comparison.ranking import RankedProduct, rank_products
from app.config import get_settings
from app.models.product import Product
from app.services.analysis import AnalysisRequestError, AnalysisResponse, AnalysisService
from app.vision.base import (
    VisionProviderConfigurationError,
    VisionProviderError,
    VisionProviderResponseError,
    VisionProviderTimeoutError,
)
from app.vision.mock_detector import MockProductDetector
from app.vision.provider_factory import get_vision_provider

router = APIRouter()
detector = MockProductDetector()


class CompareRequest(BaseModel):
    products: list[Product]


class RankingResponse(BaseModel):
    rankings: dict[str, list[RankedProduct]]


def _rank(products: list[Product]) -> RankingResponse:
    try:
        return RankingResponse(rankings=rank_products(products))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "gondola-smart", "version": __version__}


@router.post("/compare", response_model=RankingResponse)
def compare(request: CompareRequest) -> RankingResponse:
    return _rank(request.products)


@router.get("/demo", response_model=RankingResponse)
def demo() -> RankingResponse:
    return _rank(detector.detect())


@router.post("/analyze/mock", response_model=RankingResponse)
def analyze_mock() -> RankingResponse:
    return _rank(detector.detect())


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    files: Annotated[list[UploadFile], File(description="One to three shelf images")] = [],
    category_hint: Annotated[str | None, Form()] = None,
    query: Annotated[str | None, Form()] = None,
) -> AnalysisResponse:
    """Extract, validate, deduplicate, and deterministically rank shelf products."""

    try:
        provider = get_vision_provider()
        return await AnalysisService(provider, get_settings()).analyze(
            files, category_hint, query
        )
    except AnalysisRequestError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    except VisionProviderConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VisionProviderTimeoutError as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except VisionProviderResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except VisionProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
