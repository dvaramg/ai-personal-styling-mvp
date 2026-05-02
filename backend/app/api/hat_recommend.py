from fastapi import APIRouter, File, Form, UploadFile

from app.models.schemas import (
    HatRecommendRequest,
    HatRecommendResponse,
    PhotoUploadResponse,
)
from app.services.hat_recommender import hat_recommender_service

router = APIRouter()


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
    recommendations = hat_recommender_service.recommend(
        user_id=payload.user_id,
        photo_ids=payload.photo_ids,
        style_preference=payload.style_preference,
    )
    return HatRecommendResponse(user_id=payload.user_id, recommendations=recommendations)
