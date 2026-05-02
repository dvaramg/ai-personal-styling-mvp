import logging

from fastapi import APIRouter

from app.models.schemas import (
    GeneratePreviewRequest,
    GeneratePreviewResponse,
    RecommendRequest,
    RecommendResponse,
)
from app.services.history_store import history_store
from app.services.image_generator import ReplicateRateLimitError, generate_outfit_image
from app.services.recommender import RecommenderService

router = APIRouter()
recommender = RecommenderService()
logger = logging.getLogger(__name__)


@router.post("/recommend", response_model=RecommendResponse)
def recommend(payload: RecommendRequest) -> RecommendResponse:
    looks = recommender.generate(payload)
    history_store.save(payload.user_id, looks)
    return RecommendResponse(user_id=payload.user_id, looks=looks)


@router.post("/looks/generate-preview", response_model=GeneratePreviewResponse)
def generate_preview(payload: GeneratePreviewRequest) -> GeneratePreviewResponse:
    try:
        image_url = generate_outfit_image(payload.image_prompt)
    except ReplicateRateLimitError as exc:
        logger.warning("Preview rate limited for look_id=%s", payload.look_id)
        return GeneratePreviewResponse(
            look_id=payload.look_id,
            image_url=None,
            error_code="RATE_LIMIT",
            retry_after_sec=exc.retry_after_sec,
        )
    return GeneratePreviewResponse(look_id=payload.look_id, image_url=image_url)
