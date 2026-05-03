import os
import time
from typing import List
from uuid import uuid4

from app.models.schemas import Look, LookExplanation, LookItem, LookScores, RecommendRequest
from app.services.catalog_service import (
    filter_by_body_profile,
    filter_by_budget,
    filter_by_category,
    filter_by_scene,
    filter_by_style,
    load_catalog,
    score_item_for_user,
)
from app.services.image_generator import ReplicateRateLimitError, generate_outfit_image


class OutfitComposer:
    @staticmethod
    def _normalize_scene(scene: str) -> str:
        s = (scene or "").strip().lower()
        if scene in {"面试"} or s == "interview":
            return "interview"
        if scene in {"约会"} or s == "date":
            return "date"
        if s == "travel" or scene in {"旅行"}:
            return "travel"
        if s == "school" or scene in {"校园"}:
            return "school"
        if s == "work" or scene in {"通勤", "工作"}:
            return "work"
        if s == "daily" or scene in {"日常"}:
            return "daily"
        return "daily"

    @staticmethod
    def _normalize_style(styles: List[str]) -> str:
        blob = " ".join(styles).lower()
        if any("极简" in x for x in styles) or "minimal" in blob:
            return "minimal"
        if any("商务" in x for x in styles) or "business" in blob:
            return "business"
        if any("韩系" in x for x in styles) or "korean" in blob:
            return "korean"
        if "street" in blob:
            return "street"
        if "vintage" in blob:
            return "vintage"
        return "casual"

    @staticmethod
    def _budget_tier(total_budget: int, single_item_budget: int) -> str:
        if total_budget <= 600 or single_item_budget <= 180:
            return "low"
        if total_budget >= 1600 or single_item_budget >= 500:
            return "high"
        return "mid"

    @staticmethod
    def _extract_body_features(req: RecommendRequest) -> dict[str, str | bool]:
        profile = req.analyzed_body_profile
        tags = set(req.body_profile.body_tags)
        height = req.body_profile.height_cm
        broad_shoulders = False
        narrow_shoulders = False
        belly_visible = False
        thick_thighs = False
        slim_build = False
        profile_primary = profile is not None

        if profile:
            shoulder_lower = profile.shoulder_type.lower()
            waist_lower = profile.waist_type.lower()
            build_lower = profile.overall_build.lower()
            shape_lower = profile.body_subtype.lower()
            broad_shoulders = "broad" in shoulder_lower
            narrow_shoulders = "narrow" in shoulder_lower
            belly_visible = "belly" in waist_lower or "full" in waist_lower
            slim_build = "slim" in build_lower or "lean" in build_lower
            thick_thighs = "thick" in shape_lower
        else:
            broad_shoulders = "肩宽" in tags
            belly_visible = "腹部明显" in tags
            thick_thighs = "腿粗" in tags
            slim_build = "偏瘦" in tags

        # Height impression + leg-ratio cues are currently rule-based placeholders.
        short_height = height <= 168
        tall_height = height >= 180
        if profile and "short" in profile.leg_ratio.lower():
            leg_ratio = "short"
        elif "腿短" in tags:
            leg_ratio = "short"
        elif tall_height:
            leg_ratio = "long"
        else:
            leg_ratio = "balanced"

        if slim_build:
            overall_build = "slim"
        elif profile and "muscular" in profile.overall_build.lower():
            overall_build = "muscular"
        elif broad_shoulders and not belly_visible:
            overall_build = "athletic"
        elif belly_visible:
            overall_build = "stocky"
        else:
            overall_build = "balanced"

        return {
            "profile_primary": profile_primary,
            "broad_shoulders": broad_shoulders,
            "narrow_shoulders": narrow_shoulders,
            "belly_visible": belly_visible,
            "thick_thighs": thick_thighs,
            "short_height": short_height,
            "tall_height": tall_height,
            "leg_ratio": leg_ratio,
            "overall_build": overall_build,
        }

    @staticmethod
    def _gender_cue(body_tags: List[str]) -> str:
        if "female" in body_tags:
            return "female"
        if "other" in body_tags:
            return "androgynous"
        return "male"

    @staticmethod
    def _body_prompt_fields(req: RecommendRequest, features: dict[str, str | bool]) -> dict[str, str]:
        profile = req.analyzed_body_profile
        shape_lower = profile.body_subtype.lower() if profile else ""
        shoulder_lower = profile.shoulder_type.lower() if profile else ""
        waist_lower = profile.waist_type.lower() if profile else ""
        build_lower = profile.overall_build.lower() if profile else ""

        if "round" in shape_lower or features["overall_build"] in {"stocky", "chubby"}:
            face_shape = "rounder face"
        elif "sharp" in shape_lower:
            face_shape = "natural face shape"
        else:
            face_shape = "natural face shape"

        if features["broad_shoulders"] or "broad" in shoulder_lower:
            shoulder_width = "broader shoulders"
        elif features["narrow_shoulders"] or "narrow" in shoulder_lower:
            shoulder_width = "narrower shoulders"
        else:
            shoulder_width = "balanced shoulder width"

        if features["belly_visible"] or "belly" in waist_lower or "full" in waist_lower:
            waist_visibility = "slightly visible belly"
        else:
            waist_visibility = "natural waist visibility"

        if features["thick_thighs"] or "thick" in shape_lower:
            thigh_thickness = "thicker thighs"
        else:
            thigh_thickness = "balanced thighs"

        if "stocky" in build_lower or features["overall_build"] == "stocky":
            overall_build = "stocky balanced build"
        elif "muscular" in build_lower:
            overall_build = "balanced stocky build"
        elif "slim" in build_lower:
            overall_build = "casual body type"
        else:
            overall_build = "everyday male body"

        if features["leg_ratio"] == "short":
            body_proportion = "casual proportions, realistic body proportions"
        elif features["leg_ratio"] == "long":
            body_proportion = "natural proportions, realistic body proportions"
        else:
            body_proportion = "realistic body proportions, natural proportions"

        return {
            "face_shape": face_shape,
            "shoulder_width": shoulder_width,
            "waist_visibility": waist_visibility,
            "thigh_thickness": thigh_thickness,
            "overall_build": overall_build,
            "body_proportion": body_proportion,
        }

    @staticmethod
    def _look_variation(look_index: int) -> tuple[str, str, str]:
        if look_index == 1:
            return (
                "relaxed standing pose, hands by sides",
                "front-facing camera angle",
                "clean neutral styling tone",
            )
        if look_index == 2:
            return (
                "natural walking pose, one step forward",
                "three-quarter camera angle",
                "warm casual styling tone",
            )
        return (
            "easy natural pose, slight torso turn",
            "slight side camera angle",
            "soft daily styling tone",
        )

    @staticmethod
    def _style_cue(style_key: str) -> str:
        if style_key == "minimal":
            return "minimal casual style"
        if style_key == "business":
            return "smart business casual style"
        if style_key == "korean":
            return "korean street style"
        return "casual everyday style"

    @staticmethod
    def _scene_cue(scene_key: str) -> str:
        if scene_key == "interview":
            return "clean indoor office background"
        if scene_key == "date":
            return "soft-lit cafe background"
        return "neutral indoor background"

    def _build_image_prompt(
        self,
        req: RecommendRequest,
        scene_key: str,
        style_key: str,
        features: dict[str, str | bool],
        top: str,
        bottom: str,
        shoes: str,
        outerwear: str | None,
        look_index: int,
    ) -> str:
        gender = self._gender_cue(req.body_profile.body_tags)
        body_fields = self._body_prompt_fields(req, features)
        style_cue = self._style_cue(style_key)
        scene_cue = self._scene_cue(scene_key)
        pose_cue, angle_cue, tone_cue = self._look_variation(look_index)
        # Catalog `name_key` is turned into English-ish tokens via underscores → spaces before this call.
        outerwear_en = outerwear if outerwear else "light jacket"
        outfit_parts = [
            f"wearing a fully covered {outerwear_en} over {top}",
            bottom,
            shoes,
        ]
        outfit_desc = ", ".join(outfit_parts)
        # look_index keeps prompts distinct per option (avoids accidental cache collisions)
        return (
            f"realistic korean {gender} casual outfit photo, fully clothed, "
            f"wearing top and outerwear, {outfit_desc}, "
            f"similar body type reference, realistic everyday proportions, "
            f"{body_fields['face_shape']}, slightly broad shoulders, "
            f"slightly visible belly, thicker thighs, "
            f"natural average body proportions, relaxed casual fit, "
            f"full body, head-to-toe visible, {pose_cue}, {angle_cue}, {tone_cue}, "
            f"casual outfit photo, {style_cue}, {scene_cue}, "
            f"outfit {look_index} of 3, clear fit details, high quality"
        )

    @staticmethod
    def _score_clamp(value: int) -> int:
        return max(0, min(100, value))

    def _body_fit_score(
        self,
        *,
        features: dict[str, str | bool],
        top: str,
        bottom: str,
        outerwear: str | None,
    ) -> tuple[int, list[str], list[str], str]:
        score = 80
        why: list[str] = []
        avoid: list[str] = []
        tip = "Keep silhouette balanced with one clear vertical line."

        if features["broad_shoulders"]:
            if "padded_shoulder" in top or "heavy_shoulder" in top or ("padded_shoulder" in (outerwear or "")):
                score -= 10
                avoid.append("Skip heavy shoulder details for broad shoulders.")
            else:
                score += 6
                why.append("Upper-body details are controlled, which helps broad shoulders look balanced.")

        if features["belly_visible"]:
            if "tight" in top:
                score -= 12
                avoid.append("Avoid tight tops when waistline is visible.")
            if any(token in top for token in ("relaxed", "oversized", "knit", "shirt")):
                score += 7
                why.append("Relaxed drape on top softens the waistline.")
                tip = "Use draped tops and avoid clingy fabric around the midsection."

        if features["thick_thighs"]:
            if "skinny" in bottom:
                score -= 12
                avoid.append("Skinny bottoms can over-emphasize thicker thighs.")
            if any(token in bottom for token in ("straight", "wide", "cargo", "relaxed", "tapered")):
                score += 7
                why.append("Straight/relaxed bottom shape improves leg balance.")

        if features["leg_ratio"] == "short":
            if "high_waist" in bottom:
                score += 8
                why.append("High-waist bottoms visually lengthen shorter leg ratios.")
            if outerwear and any(token in outerwear for token in ("cropped", "short")):
                score += 6
                why.append("Short outerwear helps raise the visual waistline.")
            tip = "Prioritize high-waist bottoms with shorter outerwear."

        if features["overall_build"] == "stocky":
            if any(token in top for token in ("shirt", "polo", "knit", "minimal")):
                score += 8
                why.append("Clean vertical emphasis works well for stockier builds.")
            if "tight" in top or "skinny" in bottom:
                score -= 8
                avoid.append("Avoid overly tight fits; keep room for cleaner proportions.")
            tip = "Prefer clean vertical lines with relaxed fits."

        return self._score_clamp(score), why, avoid, tip

    def _scene_fit_score(self, *, scene_key: str, top: str, bottom: str, shoes: str, outerwear: str | None) -> tuple[int, list[str]]:
        score = 78
        why: list[str] = []
        if scene_key == "interview":
            if any(token in top for token in ("shirt", "polo")):
                score += 8
                why.append("Shirt-based upper fits interview formality.")
            if any(token in bottom for token in ("trousers", "straight")):
                score += 6
            if any(token in shoes for token in ("derby", "loafers", "boots")):
                score += 5
        elif scene_key == "date":
            if any(token in top for token in ("knit", "shirt", "polo")):
                score += 6
                why.append("Softer texture reads approachable for date settings.")
            if outerwear and any(token in outerwear for token in ("light", "cropped", "cardigan")):
                score += 4
        elif scene_key == "travel":
            if any(token in shoes for token in ("sneakers", "running", "trainer")):
                score += 8
                why.append("Comfort-focused footwear supports travel movement.")
            if outerwear:
                score += 4
        else:  # daily/work/school
            if any(token in shoes for token in ("sneakers", "trainer", "loafers")):
                score += 5
            if outerwear:
                score += 3
                why.append("Layered outerwear improves day-to-day versatility.")

        return self._score_clamp(score), why

    @staticmethod
    def _style_fit_score(style_key: str, top: str, bottom: str, shoes: str) -> int:
        score = 76
        if style_key == "minimal":
            if any(token in top + bottom + shoes for token in ("shirt", "trousers", "loafers", "derby")):
                score += 10
        elif style_key == "business":
            if any(token in top + bottom + shoes for token in ("shirt", "trousers", "derby", "loafers", "blazer")):
                score += 10
        else:  # casual/street/vintage/korean
            if any(token in top + bottom + shoes for token in ("sneakers", "jeans", "hoodie", "cargo", "trainer")):
                score += 10
        return max(0, min(100, score))

    def _budget_fit_score(self, *, est_price: int, req: RecommendRequest) -> int:
        # Compare estimated look price vs total/single budgets.
        score = 82
        if est_price > req.total_budget:
            over = est_price - req.total_budget
            score -= min(25, over // 20)
        else:
            score += 10
        if req.single_item_budget > 0 and est_price / 3 > req.single_item_budget:
            score -= 8
        return self._score_clamp(score)

    @staticmethod
    def _primary_reason_key(features: dict[str, str | bool]) -> str:
        if features["short_height"]:
            return "short_height"
        if features["leg_ratio"] == "short":
            return "leg_short"
        if features["belly_visible"]:
            return "belly"
        if features["broad_shoulders"]:
            return "broad_shoulders"
        if features["thick_thighs"]:
            return "thick_thighs"
        if features["narrow_shoulders"]:
            return "narrow_shoulders"
        ob = str(features["overall_build"])
        if ob == "slim":
            return "slim"
        if ob == "muscular":
            return "muscular"
        if ob == "athletic":
            return "athletic"
        if ob == "stocky":
            return "stocky"
        return "balanced"

    @staticmethod
    def _style_color_cat(style_key: str) -> str:
        if style_key == "minimal":
            return "minimal"
        if style_key == "business":
            return "business"
        return "casual"

    @staticmethod
    def _color_key(scene_key: str, style_key: str) -> str:
        cat = OutfitComposer._style_color_cat(style_key)
        return f"{scene_key}_{cat}"

    @staticmethod
    def _fit_key(features: dict[str, str | bool]) -> str:
        if features["short_height"] or features["leg_ratio"] == "short":
            return "vertical_emphasis"
        if features["broad_shoulders"]:
            return "upper_simple_lower_volume"
        if features["belly_visible"]:
            return "waist_definition_drape"
        ob = str(features["overall_build"])
        if ob in {"muscular", "athletic"}:
            return "athletic_trim"
        return "balanced_silhouette"

    def _estimate_size(self, req: RecommendRequest, features: dict[str, str | bool]) -> str:
        h = req.body_profile.height_cm
        w = req.body_profile.weight_kg
        if h <= 170 and w >= 75:
            return "L" if w < 90 else "XL"
        if h >= 180 and w >= 80:
            return "XL"
        if h >= 175:
            return "L"
        if w <= 60:
            return "M"
        if features["overall_build"] == "stocky":
            return "L"
        return "M"

    def _get_catalog_pool(
        self,
        *,
        scene_key: str,
        style_key: str,
        req: RecommendRequest,
        body_features: dict[str, str | bool],
    ) -> dict[str, list[dict]]:
        catalog = load_catalog()
        body_tags = {
            "balanced",
            str(body_features["overall_build"]),
            "short_leg_ratio" if body_features["leg_ratio"] == "short" else "balanced",
            "broad_shoulders" if body_features["broad_shoulders"] else "",
            "visible_belly" if body_features["belly_visible"] else "",
            "thick_thighs" if body_features["thick_thighs"] else "",
            "short_height" if body_features["short_height"] else "",
        }
        body_tags = {t for t in body_tags if t}

        preferred_size = self._estimate_size(req, body_features)
        max_item = max(req.single_item_budget, int(req.total_budget * 0.45))

        def ranked(category: str) -> list[dict]:
            items = filter_by_category(catalog, category)
            scene_items = filter_by_scene(items, scene_key)
            items = scene_items or items
            style_items = filter_by_style(items, style_key)
            items = style_items or items
            items = filter_by_body_profile(items, body_tags)
            budget_items = filter_by_budget(items, max_item)
            items = budget_items or items
            return sorted(
                items,
                key=lambda item: score_item_for_user(
                    item=item,
                    scene_key=scene_key,
                    style_key=style_key,
                    body_tags=body_tags,
                    max_price_krw=max_item,
                    preferred_size=preferred_size,
                ),
                reverse=True,
            )[:7]

        return {
            "top": ranked("top"),
            "bottom": ranked("bottom"),
            "shoes": ranked("shoes"),
            "outerwear": ranked("outerwear"),
            "accessory": ranked("accessory"),
        }

    def compose(self, req: RecommendRequest) -> List[Look]:
        scene_key = self._normalize_scene(req.scene)
        style_key = self._normalize_style(req.style_preferences)
        image_generation_enabled = bool(os.getenv("REPLICATE_API_TOKEN"))
        body_features = self._extract_body_features(req)
        budget_tier = self._budget_tier(req.total_budget, req.single_item_budget)
        preferred_size = self._estimate_size(req, body_features)
        pool = self._get_catalog_pool(
            scene_key=scene_key,
            style_key=style_key,
            req=req,
            body_features=body_features,
        )

        tops = pool["top"][:4]
        bottoms = pool["bottom"][:4]
        shoes_list = pool["shoes"][:4]
        outers = [None, *pool["outerwear"][:3]]
        accessories_pool = pool["accessory"][:3]
        scored_candidates: list[dict] = []
        combo_index = 0
        for top_item in tops:
            for bottom_item in bottoms:
                for shoes_item in shoes_list:
                    for outer_item in outers:
                        accessory_items = accessories_pool[:1]
                        combo_index += 1
                        top_key = top_item["name_key"]
                        bottom_key = bottom_item["name_key"]
                        shoes_key = shoes_item["name_key"]
                        outer_key = outer_item["name_key"] if outer_item else None
                        accessory_keys = [a["name_key"] for a in accessory_items]

                        top_prompt = top_key.replace("_", " ")
                        bottom_prompt = bottom_key.replace("_", " ")
                        shoes_prompt = shoes_key.replace("_", " ")
                        outer_prompt = outer_key.replace("_", " ") if outer_key else None
                        image_prompt = self._build_image_prompt(
                            req=req,
                            scene_key=scene_key,
                            style_key=style_key,
                            features=body_features,
                            top=top_prompt,
                            bottom=bottom_prompt,
                            shoes=shoes_prompt,
                            outerwear=outer_prompt,
                            look_index=combo_index,
                        )

                        est_price = (
                            int(top_item["price_krw"])
                            + int(bottom_item["price_krw"])
                            + int(shoes_item["price_krw"])
                            + (int(outer_item["price_krw"]) if outer_item else 0)
                            + sum(int(a["price_krw"]) for a in accessory_items)
                        )

                        body_score, why_body, avoid, tip = self._body_fit_score(
                            features=body_features,
                            top=top_key,
                            bottom=bottom_key,
                            outerwear=outer_key,
                        )
                        scene_score, why_scene = self._scene_fit_score(
                            scene_key=scene_key,
                            top=top_key,
                            bottom=bottom_key,
                            shoes=shoes_key,
                            outerwear=outer_key,
                        )
                        style_score = self._style_fit_score(style_key, top_key, bottom_key, shoes_key)
                        budget_score = self._budget_fit_score(est_price=est_price // 100, req=req)
                        size_score = 88 if preferred_size in top_item.get("size_range", []) else 72
                        overall = self._score_clamp(
                            int(
                                body_score * 0.3
                                + scene_score * 0.22
                                + style_score * 0.16
                                + budget_score * 0.16
                                + size_score * 0.16
                            )
                        )
                        scores = LookScores(
                            body_fit_score=body_score,
                            scene_fit_score=scene_score,
                            style_fit_score=style_score,
                            budget_fit_score=budget_score,
                            overall_score=overall,
                        )
                        fit_reasons = [
                            "top_fit_and_size_match" if preferred_size in top_item.get("size_range", []) else "top_fit_size_fallback",
                            f"bottom_scene_ready_{scene_key}",
                            "budget_within_target" if est_price <= req.total_budget else "budget_over_target",
                        ]
                        explanation = LookExplanation(
                            scores=scores,
                            why_this_works=(why_body + why_scene)[:3] or ["Balanced item mix from the catalog."],
                            what_to_avoid=avoid[:3] or ["Avoid over-tight fits and high visual noise."],
                            improvement_tip=tip,
                        )
                        reason_key = f"{self._primary_reason_key(body_features)}_{budget_tier}"
                        color_key = self._color_key(scene_key, style_key)
                        fit_key = self._fit_key(body_features)
                        look = Look(
                            look_id=str(uuid4()),
                            items=LookItem(
                                top=top_key,
                                bottom=bottom_key,
                                shoes=shoes_key,
                                outerwear=outer_key,
                                accessories=accessory_keys,
                            ),
                            reason_key=reason_key,
                            color_key=color_key,
                            fit_key=fit_key,
                            scene_note_key=scene_key,
                            recommended_size=preferred_size,
                            estimated_price_krw=est_price,
                            item_fit_reasons=fit_reasons,
                            scores=scores,
                            explanation=explanation,
                            alternatives=["TODO: future connect real brand product crawler for live alternatives."],
                            image_prompt=image_prompt,
                            image_url=None,
                            image_error_code=None,
                        )
                        scored_candidates.append({"overall": overall, "look": look})
                        if len(scored_candidates) >= 24:
                            break
                    if len(scored_candidates) >= 24:
                        break
                if len(scored_candidates) >= 24:
                    break
            if len(scored_candidates) >= 24:
                break

        top_candidates = sorted(scored_candidates, key=lambda x: x["overall"], reverse=True)[:3]
        for idx, entry in enumerate(top_candidates):
            look = entry["look"]
            image_url = None
            image_error_code = None
            try:
                image_url = generate_outfit_image(look.image_prompt)
            except ReplicateRateLimitError:
                image_error_code = "RATE_LIMIT"
                if idx == 1:
                    time.sleep(8)
                    try:
                        image_url = generate_outfit_image(look.image_prompt)
                        image_error_code = None if image_url else "RATE_LIMIT"
                    except ReplicateRateLimitError:
                        image_error_code = "RATE_LIMIT"
            except Exception:
                image_url = None
            look.image_url = image_url
            look.image_error_code = image_error_code
            if image_generation_enabled and idx < len(top_candidates) - 1:
                time.sleep(8)
        # TODO: future update catalog from Musinsa / brand APIs / scraped data.
        return [c["look"] for c in top_candidates]


class RecommenderService:
    def __init__(self) -> None:
        self.composer = OutfitComposer()

    def generate(self, req: RecommendRequest) -> List[Look]:
        return self.composer.compose(req)
