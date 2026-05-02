from typing import Dict, List

from fastapi import APIRouter

from app.models.schemas import (
    BodyProfile,
    Look,
    RecommendRequest,
    MissingEssentialsResponse,
    WardrobeInsightsResponse,
    WardrobeItem,
    WardrobeUpsertRequest,
)
from app.services.recommender import RecommenderService

router = APIRouter()
wardrobe_by_user: Dict[str, List[WardrobeItem]] = {}
recommender = RecommenderService()


@router.post("/wardrobe/items")
def upsert_wardrobe(payload: WardrobeUpsertRequest) -> dict:
    wardrobe_by_user[payload.user_id] = payload.items
    return {"ok": True, "count": len(payload.items)}


@router.get("/wardrobe/items/{user_id}", response_model=list[WardrobeItem])
def get_wardrobe(user_id: str) -> list[WardrobeItem]:
    return wardrobe_by_user.get(user_id, [])


@router.get("/wardrobe/insights/{user_id}", response_model=WardrobeInsightsResponse)
def wardrobe_insights(user_id: str) -> WardrobeInsightsResponse:
    items = wardrobe_by_user.get(user_id, [])
    sorted_items = sorted(items, key=lambda item: item.wear_count, reverse=True)
    most = sorted_items[:5]
    underused = [item for item in items if item.wear_count <= 1][:5]
    return WardrobeInsightsResponse(
        user_id=user_id,
        most_frequently_worn=most,
        underused_items=underused,
    )


@router.get("/wardrobe/essentials/{user_id}", response_model=MissingEssentialsResponse)
def missing_essentials(user_id: str) -> MissingEssentialsResponse:
    items = wardrobe_by_user.get(user_id, [])
    categories = {item.category.lower() for item in items}
    required = {"top", "bottom", "shoes", "outerwear"}
    missing = [category for category in required if category not in categories]
    return MissingEssentialsResponse(user_id=user_id, missing_essentials=missing)


@router.get("/wardrobe/today-outfit/{user_id}", response_model=Look | None)
def today_outfit_from_wardrobe(user_id: str, scene: str = "日常") -> Look | None:
    items = wardrobe_by_user.get(user_id, [])
    if not items:
        return None
    req = RecommendRequest(
        user_id=user_id,
        body_profile=BodyProfile(height_cm=175, weight_kg=70, body_tags=[]),
        style_preferences=["日常休闲"],
        scene=scene,
        total_budget=1000,
        single_item_budget=400,
        wardrobe_items=items,
    )
    looks = recommender.generate(req)
    return looks[0] if looks else None
