"""Gondola Smart API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import __version__
from app.comparison.ranking import RankedProduct, rank_products
from app.models.product import Product
from app.vision.mock_detector import MockProductDetector

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
