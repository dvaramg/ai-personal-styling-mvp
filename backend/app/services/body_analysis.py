from typing import Dict, List
from uuid import uuid4

from app.models.schemas import (
    BodyAnalysisProfile,
    UploadedPhoto,
)


class BodyAnalysisService:
    """
    Mock body-analysis workflow for Phase 2.
    Designed to be replaced by real CV/vision inference later.
    """

    def __init__(self) -> None:
        self._photo_store: Dict[str, List[UploadedPhoto]] = {}

    def register_uploads(self, user_id: str, files: list[tuple[str, str | None]]) -> List[UploadedPhoto]:
        saved: List[UploadedPhoto] = []
        for filename, content_type in files[:2]:
            saved.append(
                UploadedPhoto(
                    photo_id=str(uuid4()),
                    filename=filename,
                    content_type=content_type,
                )
            )
        self._photo_store.setdefault(user_id, [])
        self._photo_store[user_id].extend(saved)
        return saved

    def analyze(self, user_id: str, photo_ids: list[str]) -> BodyAnalysisProfile:
        all_photos = self._photo_store.get(user_id, [])
        selected = [photo for photo in all_photos if photo.photo_id in set(photo_ids)]
        signal = len(selected)
        filename_text = " ".join([photo.filename.lower() for photo in selected])

        estimated_height_range = "168-174 cm"
        estimated_weight_range = "68-78 kg"
        shoulder_type = "balanced"
        waist_type = "natural_waist"
        thigh_type = "balanced"
        leg_ratio = "balanced"
        overall_build = "balanced"
        body_subtype = "balanced_everyday"
        styling_direction = "clean casual, straight fit pants, light outerwear, avoid skinny pants"

        if signal >= 2:
            leg_ratio = "slightly_long"
            estimated_height_range = "170-176 cm"
        if "gym" in filename_text or "fit" in filename_text:
            shoulder_type = "slightly_broad"
            thigh_type = "thick"
            overall_build = "balanced_stocky"
            body_subtype = "broad_shoulders_with_thicker_thighs"
            estimated_weight_range = "75-85 kg"
        if "office" in filename_text or "daily" in filename_text:
            waist_type = "slightly_visible_belly"
            styling_direction = "clean casual, straight fit pants, short outerwear, avoid skinny pants"

        return BodyAnalysisProfile(
            estimated_height_range=estimated_height_range,
            estimated_weight_range=estimated_weight_range,
            shoulder_type=shoulder_type,
            waist_type=waist_type,
            thigh_type=thigh_type,
            leg_ratio=leg_ratio,
            overall_build=overall_build,
            body_subtype=body_subtype,
            styling_direction=styling_direction,
        )


body_analysis_service = BodyAnalysisService()
