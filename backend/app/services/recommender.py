import os
import time
from typing import List
from uuid import uuid4

from app.models.schemas import Look, LookItem, RecommendRequest, WardrobeItem
from app.services.image_generator import ReplicateRateLimitError, generate_outfit_image


class RuleEngine:
    def apply(self, req: RecommendRequest) -> List[str]:
        hints: List[str] = []
        profile = req.analyzed_body_profile
        if profile and ("belly" in profile.waist_type.lower() or "full" in profile.waist_type.lower()):
            hints.append("腰腹区域优先留有余量，上衣避免贴身，腰线位置上移")
        if "腹部明显" in req.body_profile.body_tags:
            hints.append("优先选择高腰下装和垂坠上衣，弱化腹部线条")
        if profile and ("broad" in profile.shoulder_type.lower()):
            hints.append("肩部较宽时上半身简化，重心放到下装平衡比例")
        if "肩宽" in req.body_profile.body_tags:
            hints.append("避免过紧上装，优先直线条和适度宽松版型")
        if profile and ("short" in profile.leg_ratio.lower()):
            hints.append("腿部比例偏短优先短外套和高腰线，强化纵向视觉")
        if "腿粗" in req.body_profile.body_tags:
            hints.append("避免紧身裤，优先直筒或宽松锥形裤型")
        if profile and ("slim" in profile.overall_build.lower()):
            hints.append("整体偏瘦可通过叠穿与适度廓形增强量感")
        if "偏瘦" in req.body_profile.body_tags:
            hints.append("可以通过叠穿增加体积感，提升整体层次")
        if req.body_profile.height_cm <= 168:
            hints.append("优先短外套和高腰线，优化显高效果")
        if req.scene in {"面试", "通勤"}:
            hints.append("优先低饱和配色，控制正式感")
        return hints


class OutfitComposer:
    _ITEM_EN_MAP = {
        "纯色针织上衣": "solid knit sweater",
        "锥形西裤": "tapered trousers",
        "德比鞋": "derby shoes",
        "短款外套": "cropped jacket",
        "廓形衬衫": "oversized shirt",
        "直筒牛仔裤": "straight jeans",
        "小白鞋": "white sneakers",
        "短款卫衣": "cropped hoodie",
        "高腰工装裤": "high-waisted cargo pants",
        "复古跑鞋": "retro running shoes",
        "轻薄夹克": "light jacket",
        "挺括衬衫": "crisp shirt",
        "短款西装外套": "cropped blazer",
        "细针织Polo": "fine-knit polo",
        "直筒西裤": "straight-leg trousers",
        "乐福鞋": "loafers",
        "轻薄风衣": "light trench coat",
        "高支衬衫": "high-thread-count shirt",
        "高腰西裤": "high-waisted trousers",
        "切尔西靴": "chelsea boots",
        "结构化夹克": "structured jacket",
        "质感针织上衣": "textured knit top",
        "垂坠休闲西裤": "draped relaxed trousers",
        "短夹克": "short jacket",
        "宽松衬衫": "relaxed shirt",
        "直筒长裤": "straight-leg pants",
        "轻薄针织开衫": "light knit cardigan",
        "短款针织开衫": "cropped knit cardigan",
        "高腰阔腿裤": "high-waisted wide-leg pants",
        "皮质板鞋": "leather sneakers",
        "廓形外套": "oversized coat",
        "宽松卫衣": "relaxed sweatshirt",
        "工装长裤": "cargo pants",
        "基础T恤": "basic t-shirt",
        "锥形休闲裤": "tapered casual pants",
        "德训鞋": "german trainer sneakers",
        "牛仔外套": "denim jacket",
    }
    @staticmethod
    def _normalize_scene(scene: str) -> str:
        if scene in {"面试"}:
            return "interview"
        if scene in {"约会"}:
            return "date"
        return "daily"

    @staticmethod
    def _normalize_style(styles: List[str]) -> str:
        if "极简" in styles:
            return "minimal"
        if "韩系" in styles:
            return "korean"
        if "商务风" in styles:
            return "business"
        return "casual"

    @staticmethod
    def _budget_tier(total_budget: int, single_item_budget: int) -> str:
        if total_budget <= 600 or single_item_budget <= 180:
            return "low"
        if total_budget >= 1600 or single_item_budget >= 500:
            return "high"
        return "mid"

    @staticmethod
    def _body_mode(req: RecommendRequest, features: dict[str, str | bool]) -> str:
        profile = req.analyzed_body_profile
        tags = set(req.body_profile.body_tags)

        muscular_tag_hit = any(tag in tags for tag in {"健身", "肌肉明显", "胸肩明显"})
        profile_build = profile.overall_build.lower() if profile else ""

        # muscular: explicit muscular signal only
        if "muscular" in profile_build or muscular_tag_hit:
            return "muscular"

        # slim: low body volume / narrow shoulder cues
        if features["narrow_shoulders"] or features["overall_build"] == "slim":
            return "slim"

        # stocky: broader frame + belly + thicker thighs
        if features["broad_shoulders"] and features["belly_visible"] and features["thick_thighs"]:
            return "stocky"

        # chubby: belly-visible with soft overall impression
        if features["belly_visible"]:
            if profile and any(token in profile.body_subtype.lower() for token in {"soft", "round"}):
                return "chubby"
            if features["overall_build"] == "stocky":
                return "chubby"
            return "chubby"

        # athletic: broad shoulder without belly, sporty lower body
        if features["broad_shoulders"] and (not features["belly_visible"]):
            if features["thick_thighs"] or (profile and "athletic" in profile_build):
                return "athletic"
            return "athletic"

        return "balanced"

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

    def _to_english_item(self, item: str) -> str:
        normalized = (
            item.replace("韩系", "")
            .replace("简洁", "")
            .replace("商务感", "")
            .replace("纯色", "")
            .replace("低调", "")
            .replace("微宽松", "")
            .replace("可叠穿", "")
            .replace("宽松版", "")
            .replace("垂坠", "")
            .replace("高腰", "")
            .replace("结构化", "")
            .replace("皮质", "")
            .replace("九分", "")
            .strip()
        )
        return self._ITEM_EN_MAP.get(normalized, normalized)

    @staticmethod
    def _gender_cue(body_tags: List[str]) -> str:
        if "female" in body_tags:
            return "female"
        if "other" in body_tags:
            return "androgynous"
        return "male"

    @staticmethod
    def _body_cue(body_mode: str) -> str:
        if body_mode == "muscular":
            return "solid everyday body"
        if body_mode == "athletic":
            return "realistic everyday body"
        if body_mode == "stocky":
            return "stocky balanced build"
        if body_mode == "chubby":
            return "soft rounded build"
        if body_mode == "slim":
            return "natural everyday body"
        return "realistic everyday body"

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
        body_mode: str,
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
        top_en = self._to_english_item(top)
        bottom_en = self._to_english_item(bottom)
        shoes_en = self._to_english_item(shoes)
        outerwear_en = self._to_english_item(outerwear) if outerwear else "light jacket"
        outfit_parts = [
            f"wearing a fully covered {outerwear_en} over {top_en}",
            bottom_en,
            shoes_en,
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

    def _scene_candidates(
        self, scene_key: str, features: dict[str, str | bool]
    ) -> list[tuple[str, str, str, str | None]]:
        if features["broad_shoulders"]:
            if scene_key == "interview":
                return [
                    ("简洁领口衬衫", "宽松直筒西裤", "德比鞋", "短款利落外套"),
                    ("纯色针织Polo", "阔腿西裤", "乐福鞋", "轻薄短风衣"),
                    ("极简衬衫", "高腰宽直筒裤", "切尔西靴", "无垫肩夹克"),
                ]
            if scene_key == "date":
                return [
                    ("简洁针织上衣", "垂坠阔腿裤", "乐福鞋", "短夹克"),
                    ("基础衬衫", "直筒宽松裤", "复古跑鞋", "轻薄开衫"),
                    ("纯色上衣", "高腰直筒裤", "皮质板鞋", "短款廓形外套"),
                ]
            return [
                ("基础T恤", "宽松直筒牛仔裤", "小白鞋", "短夹克"),
                ("简洁卫衣", "阔腿工装裤", "复古跑鞋", None),
                ("纯色针织上衣", "高腰宽锥形裤", "德训鞋", "轻薄外套"),
            ]

        if features["narrow_shoulders"]:
            if scene_key == "interview":
                return [
                    ("宽领衬衫", "直筒西裤", "德比鞋", "结构化短西装"),
                    ("层次针织上衣", "高腰西裤", "乐福鞋", "有肩线外套"),
                    ("叠穿衬衫马甲", "直筒西裤", "切尔西靴", "廓形夹克"),
                ]
            if scene_key == "date":
                return [
                    ("宽领针织上衣", "垂坠休闲裤", "乐福鞋", "短款外套"),
                    ("叠穿衬衫开衫", "直筒长裤", "复古跑鞋", "结构感开衫"),
                    ("层次卫衣", "高腰阔腿裤", "皮质板鞋", "廓形外套"),
                ]
            return [
                ("宽领T恤", "直筒牛仔裤", "小白鞋", "结构夹克"),
                ("叠穿卫衣", "工装长裤", "复古跑鞋", "短款外套"),
                ("针织马甲衬衫", "锥形休闲裤", "德训鞋", "轻薄外套"),
            ]

        if scene_key == "interview":
            return [
                ("挺括衬衫", "锥形西裤", "德比鞋", "短款西装外套"),
                ("细针织Polo", "直筒西裤", "乐福鞋", "轻薄风衣"),
                ("高支衬衫", "高腰西裤", "切尔西靴", "结构化夹克"),
            ]
        if scene_key == "date":
            return [
                ("质感针织上衣", "垂坠休闲西裤", "乐福鞋", "短夹克"),
                ("宽松衬衫", "直筒长裤", "复古跑鞋", "轻薄针织开衫"),
                ("短款针织开衫", "高腰阔腿裤", "皮质板鞋", "廓形外套"),
            ]
        return [
            ("纯色针织上衣", "直筒牛仔裤", "小白鞋", "轻薄夹克"),
            ("宽松卫衣", "工装长裤", "复古跑鞋", None),
            ("基础T恤", "锥形休闲裤", "德训鞋", "牛仔外套"),
        ]

    def _apply_style(self, top: str, bottom: str, shoes: str, style_key: str) -> tuple[str, str, str]:
        if style_key == "minimal":
            return (f"简洁{top}", f"纯色{bottom}", f"低调{shoes}")
        if style_key == "korean":
            return (f"韩系{top}", f"九分{bottom}", f"干净{shoes}")
        if style_key == "business":
            return (f"商务感{top}", f"结构化{bottom}", f"皮质{shoes}")
        return (top, bottom, shoes)

    def _apply_body_rules(
        self,
        top: str,
        bottom: str,
        shoes: str,
        outerwear: str | None,
        features: dict[str, str | bool],
        look_index: int,
    ) -> tuple[str, str, str, str | None, str]:
        reasons: list[str] = []
        next_top = top
        next_bottom = bottom
        next_shoes = shoes
        next_outerwear = outerwear

        if features["broad_shoulders"]:
            # Shoulder宽 -> upper更简洁，视觉重心下移
            next_top = f"简洁线条{next_top}"
            if look_index == 0 and next_outerwear:
                next_outerwear = "轻薄短款外套"
            next_bottom = f"平衡感{next_bottom}"
            reasons.append("肩宽体型优先简化上半身细节，并用更有量感的下装平衡比例")

        if features["narrow_shoulders"]:
            next_top = f"层次感{next_top}"
            next_outerwear = next_outerwear or "结构化短外套"
            reasons.append("肩窄体型通过叠穿、宽领口和有肩线外套提升上半身存在感")

        if features["belly_visible"]:
            next_top = f"宽松垂坠{next_top}"
            next_bottom = f"高腰直筒{next_bottom}"
            reasons.append("腹部线条明显时避免贴身上衣，改用垂坠上装与高腰下装")

        if features["thick_thighs"]:
            next_bottom = f"直筒宽松{next_bottom}".replace("紧身", "直筒")
            reasons.append("大腿偏粗时避免紧身裤型，使用直筒或宽松锥形裤更修饰")

        if features["short_height"]:
            next_outerwear = "短款利落外套" if next_outerwear else "短款叠穿马甲"
            next_bottom = f"高腰{next_bottom}"
            next_shoes = f"轻量厚底{next_shoes}"
            reasons.append("身高显矮时通过短外套+高腰线提升下半身占比")

        if features["leg_ratio"] == "short":
            next_bottom = f"九分高腰{next_bottom}"
            reasons.append("腿部比例偏短时通过九分高腰裤型拉长视觉腿长")

        if features["overall_build"] == "slim":
            next_top = f"可叠穿{next_top}"
            next_outerwear = next_outerwear or "轻薄叠穿马甲"
            reasons.append("整体偏瘦可加入叠穿和宽松轮廓，增加体积感")
        elif features["overall_build"] == "muscular":
            next_top = f"克制廓形{next_top}"
            next_bottom = f"直筒平衡{next_bottom}"
            reasons.append("肌肉量较明显时，上装控制膨胀感，下装保持直筒平衡整体轮廓")
        elif features["overall_build"] == "athletic":
            next_top = f"微宽松{next_top}"
            reasons.append("骨架偏运动型，使用微宽松版型避免上半身过度膨胀")
        elif features["overall_build"] == "stocky":
            next_top = f"纵向线条{next_top}"
            reasons.append("整体厚实型优先纵向线条与低对比搭配，减少横向扩张")

        if not reasons:
            reasons.append("体型均衡，保持合身剪裁与清晰腰线即可")

        return (next_top, next_bottom, next_shoes, next_outerwear, "；".join(reasons))

    def _budget_details(self, budget_tier: str) -> tuple[list[str], list[str], str]:
        if budget_tier == "low":
            return ([], ["同版型平价替代，优先基础款"], "预算较紧，优先核心三件套并控制单品复杂度")
        if budget_tier == "high":
            return (
                ["质感腕表", "皮带"],
                ["可升级为设计师品牌或高质面料版本"],
                "预算充足，可增加层次与配饰提升完整度",
            )
        return (["简约腕表"], ["可替换为更正式鞋款或更平价外套"], "预算适中，平衡实用性与完整度")

    @staticmethod
    def _match_wardrobe_item(
        items: list[WardrobeItem],
        category_candidates: list[str],
        style_key: str,
    ) -> WardrobeItem | None:
        normalized_candidates = {c.lower() for c in category_candidates}
        filtered = [
            item
            for item in items
            if item.category.lower() in normalized_candidates
        ]
        if not filtered:
            return None
        style_hits = [item for item in filtered if style_key in item.style.lower()]
        pool = style_hits or filtered
        return max(pool, key=lambda item: (item.wear_count, item.frequently_worn))

    def compose(self, req: RecommendRequest, hints: List[str]) -> List[Look]:
        scene_key = self._normalize_scene(req.scene)
        style_key = self._normalize_style(req.style_preferences)
        image_generation_enabled = bool(os.getenv("REPLICATE_API_TOKEN"))
        body_features = self._extract_body_features(req)
        body_mode = self._body_mode(req, body_features)
        budget_tier = self._budget_tier(req.total_budget, req.single_item_budget)
        candidates = self._scene_candidates(scene_key, body_features)
        wardrobe_items = req.wardrobe_items

        looks: List[Look] = []
        for idx, (top, bottom, shoes, outerwear) in enumerate(candidates):
            top, bottom, shoes = self._apply_style(top, bottom, shoes, style_key)
            top, bottom, shoes, outerwear, body_reason = self._apply_body_rules(
                top=top,
                bottom=bottom,
                shoes=shoes,
                outerwear=outerwear,
                features=body_features,
                look_index=idx,
            )
            accessories, alternatives, budget_note = self._budget_details(budget_tier)
            if idx == 0 and budget_tier != "low" and "简约腕表" not in accessories:
                accessories = ["简约腕表", *accessories]

            # Prioritize wardrobe items before suggesting new purchases.
            top_item = self._match_wardrobe_item(wardrobe_items, ["top", "上衣"], style_key)
            bottom_item = self._match_wardrobe_item(wardrobe_items, ["bottom", "下装"], style_key)
            shoes_item = self._match_wardrobe_item(wardrobe_items, ["shoes", "鞋子"], style_key)
            outerwear_item = self._match_wardrobe_item(wardrobe_items, ["outerwear", "外套"], style_key)

            if top_item:
                top = f"衣橱复用-{top_item.color}{top_item.style}{top_item.category}"
            if bottom_item:
                bottom = f"衣橱复用-{bottom_item.color}{bottom_item.fit}{bottom_item.category}"
            if shoes_item:
                shoes = f"衣橱复用-{shoes_item.color}{shoes_item.style}{shoes_item.category}"
            if outerwear_item:
                outerwear = f"衣橱复用-{outerwear_item.color}{outerwear_item.style}{outerwear_item.category}"

            reused_count = sum(1 for item in [top_item, bottom_item, shoes_item, outerwear_item] if item)
            if reused_count:
                alternatives = [
                    f"已优先复用衣橱单品 {reused_count} 件，仅在缺失位置建议新增购买",
                    *alternatives,
                ]

            image_prompt = self._build_image_prompt(
                req=req,
                scene_key=scene_key,
                style_key=style_key,
                body_mode=body_mode,
                features=body_features,
                top=top,
                bottom=bottom,
                shoes=shoes,
                outerwear=outerwear,
                look_index=idx + 1,
            )
            image_url = None
            image_error_code = None
            try:
                image_url = generate_outfit_image(image_prompt)
            except ReplicateRateLimitError:
                image_error_code = "RATE_LIMIT"
                # If look2 hits rate-limit, wait and retry once.
                if idx == 1:
                    time.sleep(8)
                    try:
                        image_url = generate_outfit_image(image_prompt)
                        image_error_code = None if image_url else "RATE_LIMIT"
                    except ReplicateRateLimitError:
                        image_error_code = "RATE_LIMIT"
            except Exception:
                image_url = None

            reason_parts = [body_reason, budget_note]
            if hints:
                reason_parts.append("；".join(hints[:2]))
            reason = "；".join(reason_parts)

            look = Look(
                look_id=str(uuid4()),
                items=LookItem(
                    top=top,
                    bottom=bottom,
                    shoes=shoes,
                    outerwear=outerwear,
                    accessories=accessories,
                ),
                reason=reason,
                color_logic="使用低饱和中性色打底，按场景加入一处重点色",
                proportion_tip=(
                    "短外套+高腰线+同色系鞋裤，优先修正身高与腿部比例"
                    if body_features["short_height"] or body_features["leg_ratio"] == "short"
                    else "通过上简下稳和纵向线条优化全身比例"
                ),
                scene_note=f"适用于{req.scene}场景",
                alternatives=alternatives,
                image_prompt=image_prompt,
                image_url=image_url,
                image_error_code=image_error_code,
            )
            looks.append(look)
            if image_generation_enabled and idx < len(candidates) - 1:
                time.sleep(8)
        return looks


class RecommenderService:
    def __init__(self) -> None:
        self.rule_engine = RuleEngine()
        self.composer = OutfitComposer()

    def generate(self, req: RecommendRequest) -> List[Look]:
        hints = self.rule_engine.apply(req)
        return self.composer.compose(req, hints)
