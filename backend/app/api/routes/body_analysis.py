from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import (
    BodyAnalysisRequest,
    BodyAnalysisResponse,
    PhotoUploadResponse,
)
from app.services.body_analysis import body_analysis_service

router = APIRouter()


@router.post("/body-analysis/upload", response_model=PhotoUploadResponse)
async def upload_body_photos(
    user_id: str = Form(...),
    photos: list[UploadFile] = File(...),
) -> PhotoUploadResponse:
    if not photos:
        raise HTTPException(status_code=400, detail="At least one photo is required.")
    if len(photos) > 2:
        raise HTTPException(status_code=400, detail="Upload up to 2 photos only.")
    saved = body_analysis_service.register_uploads(
        user_id=user_id,
        files=[(photo.filename or "uploaded.jpg", photo.content_type) for photo in photos],
    )
    return PhotoUploadResponse(user_id=user_id, photos=saved)


@router.post("/body-analysis/analyze", response_model=BodyAnalysisResponse)
def analyze_body_profile(payload: BodyAnalysisRequest) -> BodyAnalysisResponse:
    profile = body_analysis_service.analyze(payload.user_id, payload.photo_ids)
    return BodyAnalysisResponse(user_id=payload.user_id, photo_ids=payload.photo_ids, profile=profile)
