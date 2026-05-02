from typing import Dict, List
from uuid import uuid4

from app.models.schemas import HatRecommendationItem, UploadedPhoto


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
            base = [
                ("Structured Baseball Cap", "Clean silhouette matches minimal style lines."),
                ("Wool 6-Panel Cap", "Soft texture adds detail without visual noise."),
                ("Short-Brim Cap", "Compact brim keeps the look sharp and tidy."),
            ]
        elif "business" in style or "商务" in style:
            base = [
                ("Flat Cap", "Refined shape works with smart-casual layering."),
                ("Wool Newsboy Cap", "Adds mature texture while keeping a polished tone."),
                ("Dark Minimal Baseball Cap", "Low-profile option for relaxed business days."),
            ]
        else:
            base = [
                ("Classic Baseball Cap", "Easy daily match with tees, shirts, and jackets."),
                ("Bucket Hat", "Soft brim balances upper-body volume and face outline."),
                ("Beanie (Light Rib)", "Adds casual warmth and works with street styling."),
            ]

        if "round" in filename_hint or "face" in filename_hint:
            base[1] = ("Mid-Brim Bucket Hat", "Mid brim helps balance a rounder face shape.")
        if "broad" in filename_hint or "shoulder" in filename_hint:
            base[0] = ("Medium-Crown Baseball Cap", "Balanced crown avoids over-emphasizing broad shoulders.")

        return [
            HatRecommendationItem(
                hat_type=hat,
                reason=reason,
                avoid="Avoid oversized logos and very tall crowns that overpower face balance.",
                styling_tips=f"Use neutral colors first, then add one accent tone. Pair with {hat.lower()} for everyday layering.",
            )
            for hat, reason in base[:3]
        ]


hat_recommender_service = HatRecommenderService()
