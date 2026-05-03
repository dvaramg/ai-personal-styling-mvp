from typing import Dict, List
from uuid import uuid4

from app.models.schemas import HatRecommendationItem, UploadedPhoto

# Stable IDs for i18n keys on the client: t(`hat.${hat_type}.reason`), etc.
HAT_TYPE_IMAGE_LABEL: dict[str, str] = {
    "structured_baseball_cap": "a structured baseball cap",
    "wool_6_panel_cap": "a wool six-panel cap",
    "short_brim_cap": "a short-brim cap",
    "flat_cap": "a flat cap",
    "wool_newsboy_cap": "a wool newsboy cap",
    "dark_minimal_baseball_cap": "a dark minimal baseball cap",
    "classic_baseball_cap": "a classic baseball cap",
    "bucket_hat": "a bucket hat",
    "beanie_light_rib": "a light rib knit beanie",
    "mid_brim_bucket_hat": "a mid-brim bucket hat",
    "medium_crown_baseball_cap": "a medium-crown baseball cap",
}


def _build_hat_image_prompt(
    hat_type: str,
    style_preference: str,
    *,
    has_user_photo_reference: bool,
) -> str:
    """Portrait prompt tuned for hat focus, everyday body types, and no runway / gym look."""
    style = (style_preference or "casual everyday clothing").strip()
    hat_worn = HAT_TYPE_IMAGE_LABEL.get(hat_type, "a casual everyday hat")
    ref = "natural face, normal human body proportions, ordinary adult, not muscular"
    if has_user_photo_reference:
        ref = (
            "natural face, normal human body proportions, relatable everyday adult like a casual photo upload, "
            "not muscular, not a model"
        )
    return (
        f"realistic Korean male portrait, wearing {hat_worn}, fully clothed in casual everyday clothing, "
        f"{ref}, upper body visible, strong focus on the hat and fit on head, {style}, neutral background, "
        "soft natural daylight, avoid fashion model or runway look"
    )


class HatRecommenderService:
    """
    Independent MVP module for hat recommendations.
    Kept separate from outfit recommender so it can evolve as a standalone product.
    """

    def __init__(self) -> None:
        self._photo_store: Dict[str, List[UploadedPhoto]] = {}

    def register_uploads(self, user_id: str, files: list[tuple[str, str | None]]) -> List[UploadedPhoto]:
        uploaded: List[UploadedPhoto] = []
        for filename, content_type in files[:2]:
            uploaded.append(
                UploadedPhoto(
                    photo_id=str(uuid4()),
                    filename=filename,
                    content_type=content_type,
                )
            )
        self._photo_store.setdefault(user_id, [])
        self._photo_store[user_id].extend(uploaded)
        return uploaded

    def recommend(self, user_id: str, photo_ids: list[str], style_preference: str) -> List[HatRecommendationItem]:
        source = self._photo_store.get(user_id, [])
        selected = [p for p in source if p.photo_id in set(photo_ids)]
        filename_hint = " ".join(p.filename.lower() for p in selected)
        style = (style_preference or "casual").lower()

        if "minimal" in style or "极简" in style:
            base = ["structured_baseball_cap", "wool_6_panel_cap", "short_brim_cap"]
        elif "business" in style or "商务" in style:
            base = ["flat_cap", "wool_newsboy_cap", "dark_minimal_baseball_cap"]
        else:
            base = ["classic_baseball_cap", "bucket_hat", "beanie_light_rib"]

        if "round" in filename_hint or "face" in filename_hint:
            base[1] = "mid_brim_bucket_hat"
        if "broad" in filename_hint or "shoulder" in filename_hint:
            base[0] = "medium_crown_baseball_cap"

        has_ref = bool(selected)
        out: List[HatRecommendationItem] = []
        for idx, hat_type in enumerate(base[:3]):
            score = max(72, min(96, 92 - idx * 5))
            out.append(
                HatRecommendationItem(
                    hat_type=hat_type,
                    score=score,
                    image_prompt=_build_hat_image_prompt(
                        hat_type,
                        style_preference,
                        has_user_photo_reference=has_ref,
                    ),
                )
            )
        return out


hat_recommender_service = HatRecommenderService()
