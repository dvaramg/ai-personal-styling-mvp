from typing import List, Optional

from pydantic import BaseModel, Field


class BodyProfile(BaseModel):
    height_cm: int = Field(..., ge=120, le=230)
    weight_kg: int = Field(..., ge=30, le=200)
    body_tags: List[str] = Field(default_factory=list)
    skin_tone: Optional[str] = None
    hair_length: Optional[str] = None


class WardrobeItem(BaseModel):
    category: str
    color: str
    season: str
    style: str
    fit: str
    frequently_worn: bool = False
    wear_count: int = 0


class RecommendRequest(BaseModel):
    user_id: str
    body_profile: BodyProfile
    analyzed_body_profile: Optional["BodyAnalysisProfile"] = None
    style_preferences: List[str]
    scene: str
    total_budget: int
    single_item_budget: int
    wardrobe_items: List[WardrobeItem] = Field(default_factory=list)


class LookItem(BaseModel):
    top: str
    bottom: str
    shoes: str
    outerwear: Optional[str] = None
    accessories: List[str] = Field(default_factory=list)


class Look(BaseModel):
    look_id: str
    items: LookItem
    reason_key: str
    color_key: str
    fit_key: str
    scene_note_key: str
    recommended_size: str
    estimated_price_krw: int
    item_fit_reasons: List[str] = Field(default_factory=list)
    scores: "LookScores"
    explanation: "LookExplanation"
    alternatives: List[str] = Field(default_factory=list)
    image_prompt: str
    image_url: Optional[str] = None
    image_error_code: Optional[str] = None


class LookScores(BaseModel):
    body_fit_score: int = Field(..., ge=0, le=100)
    scene_fit_score: int = Field(..., ge=0, le=100)
    style_fit_score: int = Field(..., ge=0, le=100)
    budget_fit_score: int = Field(..., ge=0, le=100)
    overall_score: int = Field(..., ge=0, le=100)


class LookExplanation(BaseModel):
    scores: LookScores
    why_this_works: List[str] = Field(default_factory=list)
    what_to_avoid: List[str] = Field(default_factory=list)
    improvement_tip: str


class RecommendResponse(BaseModel):
    user_id: str
    looks: List[Look]


class GeneratePreviewRequest(BaseModel):
    look_id: str
    image_prompt: str


class GeneratePreviewResponse(BaseModel):
    look_id: str
    image_url: Optional[str] = None
    error_code: Optional[str] = None
    retry_after_sec: Optional[int] = None


class UploadedPhoto(BaseModel):
    photo_id: str
    filename: str
    content_type: Optional[str] = None


class PhotoUploadResponse(BaseModel):
    user_id: str
    photos: List[UploadedPhoto]


class BodyAnalysisRequest(BaseModel):
    user_id: str
    photo_ids: List[str] = Field(default_factory=list, min_length=1, max_length=2)


class BodyAnalysisProfile(BaseModel):
    estimated_height_range: str
    estimated_weight_range: str
    shoulder_type: str
    waist_type: str
    thigh_type: str
    leg_ratio: str
    overall_build: str
    body_subtype: str
    styling_direction: str


class BodyAnalysisResponse(BaseModel):
    user_id: str
    photo_ids: List[str]
    profile: BodyAnalysisProfile


class WardrobeUpsertRequest(BaseModel):
    user_id: str
    items: List[WardrobeItem]


class WardrobeInsightsResponse(BaseModel):
    user_id: str
    most_frequently_worn: List[WardrobeItem]
    underused_items: List[WardrobeItem]


class MissingEssentialsResponse(BaseModel):
    user_id: str
    missing_essentials: List[str]


class HatRecommendRequest(BaseModel):
    user_id: str
    photo_ids: List[str] = Field(default_factory=list, min_length=1, max_length=2)
    style_preference: str = ""


class HatRecommendationItem(BaseModel):
    """UI copy from i18n `hat.types.{hat_type}`; `score` is a lightweight match hint (0–100)."""

    hat_type: str
    score: int = Field(default=88, ge=0, le=100)
    image_prompt: str
    image_url: Optional[str] = None
    image_error_code: Optional[str] = None


class HatRecommendResponse(BaseModel):
    user_id: str
    recommendations: List[HatRecommendationItem]


class HatGeneratePreviewRequest(BaseModel):
    image_prompt: str
    hat_type: Optional[str] = None


class HatGeneratePreviewResponse(BaseModel):
    hat_type: Optional[str] = None
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    error_code: Optional[str] = None
    retry_after_sec: Optional[int] = None
    message: Optional[str] = None
