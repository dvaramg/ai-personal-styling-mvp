import logging
import random
import time

from fastapi import APIRouter, File, Form, UploadFile

from app.models.schemas import (
    HatGeneratePreviewRequest,
    HatGeneratePreviewResponse,
    HatRecommendRequest,
    HatRecommendResponse,
    PhotoUploadResponse,
)
from app.services.hat_recommender import hat_recommender_service
from app.services.image_generator import ReplicateRateLimitError, generate_outfit_image

router = APIRouter()
logger = logging.getLogger(__name__)

HAT_IMAGE_NEGATIVE_EXTRA = (
    "fashion model, runway model, magazine cover glam, exaggerated face, plastic skin, "
    "wide-angle distortion, unrealistic hat shape, fantasy helmet, cartoon hat, giant brim, "
    "deformed headwear, beauty retouch overload, celebrity lookalike, "
    "bodybuilder, muscular body, gym physique, fitness model, ripped abs, huge muscles, "
    "oversized shoulders, heroic proportions"
)


def _pre_delay_hat_generation() -> None:
    """Space out Replicate calls to reduce 429 collisions with other flows."""
    time.sleep(random.uniform(5.0, 8.0))


def _generate_hat_image_with_retry(image_prompt: str) -> tuple[str | None, str | None]:
    """
    Returns (image_url, error_code). error_code is None on success.
    One 5–8s delay before the first attempt; on 429, wait 8s and retry once.
    """
    _pre_delay_hat_generation()
    try:
        url = generate_outfit_image(image_prompt, negative_prompt_extra=HAT_IMAGE_NEGATIVE_EXTRA)
        if url:
            return url, None
        return None, "GENERATION_FAILED"
    except ReplicateRateLimitError:
        logger.warning("Hat preview rate limited; waiting 8s then retrying once")
        time.sleep(8)
        try:
            url = generate_outfit_image(image_prompt, negative_prompt_extra=HAT_IMAGE_NEGATIVE_EXTRA)
            if url:
                return url, None
            return None, "RATE_LIMIT"
        except ReplicateRateLimitError:
            logger.warning("Hat preview still rate limited after retry")
            return None, "RATE_LIMIT"
    except Exception:
        logger.exception("Hat preview generation failed")
        return None, "GENERATION_FAILED"


def _preview_response_base(payload: HatGeneratePreviewRequest) -> dict:
    return {
        "hat_type": payload.hat_type,
        "image_prompt": payload.image_prompt.strip() or None,
    }


@router.post("/hat-recommend/upload", response_model=PhotoUploadResponse)
async def upload_hat_photos(
    user_id: str = Form(...),
    photos: list[UploadFile] = File(...),
) -> PhotoUploadResponse:
    files = [(photo.filename, photo.content_type) for photo in photos[:2]]
    uploaded = hat_recommender_service.register_uploads(user_id=user_id, files=files)
    return PhotoUploadResponse(user_id=user_id, photos=uploaded)


@router.post("/hat-recommend", response_model=HatRecommendResponse)
def recommend_hat(payload: HatRecommendRequest) -> HatRecommendResponse:
    """
    Text recommendations only. Clients should call POST /hat-recommend/preview for images
    (one automatic call for the first hat after a client-side delay is recommended).
    """
    recommendations = hat_recommender_service.recommend(
        user_id=payload.user_id,
        photo_ids=payload.photo_ids,
        style_preference=payload.style_preference,
    )
    return HatRecommendResponse(user_id=payload.user_id, recommendations=recommendations)


@router.post("/hat-recommend/preview", response_model=HatGeneratePreviewResponse)
def generate_hat_preview(payload: HatGeneratePreviewRequest) -> HatGeneratePreviewResponse:
    """
    Returns JSON: hat_type, image_prompt, image_url (null on failure),
    plus error_code / message / retry_after_sec when applicable.
    """
    base = _preview_response_base(payload)
    if not payload.image_prompt.strip():
        return HatGeneratePreviewResponse(
            **base,
            image_url=None,
            error_code="INVALID",
            message="image_prompt is required",
        )

    image_url, err = _generate_hat_image_with_retry(payload.image_prompt)

    if err == "RATE_LIMIT":
        return HatGeneratePreviewResponse(
            **base,
            image_url=None,
            error_code="RATE_LIMIT",
            retry_after_sec=8,
            message="Rate limited. Please wait and try again.",
        )

    if not image_url:
        return HatGeneratePreviewResponse(
            **base,
            image_url=None,
            error_code=err or "GENERATION_FAILED",
            message="Image was not generated. Check REPLICATE_API_TOKEN and try again.",
        )

    return HatGeneratePreviewResponse(**base, image_url=image_url, error_code=None, message=None)
