import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "clothing_catalog.json"
# TODO: future connect real brand product crawler to replace local mock catalog.
# TODO: future update catalog from Musinsa / brand APIs / scraped feeds.


@lru_cache(maxsize=1)
def load_catalog() -> list[dict[str, Any]]:
    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def filter_by_category(items: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    return [item for item in items if item.get("category") == category]


def filter_by_budget(items: list[dict[str, Any]], max_price_krw: int) -> list[dict[str, Any]]:
    if max_price_krw <= 0:
        return items
    return [item for item in items if int(item.get("price_krw", 0)) <= max_price_krw]


def filter_by_scene(items: list[dict[str, Any]], scene_key: str) -> list[dict[str, Any]]:
    return [item for item in items if scene_key in item.get("scene_tags", [])]


def filter_by_style(items: list[dict[str, Any]], style_key: str) -> list[dict[str, Any]]:
    if not style_key:
        return items
    if style_key == "korean":
        style_key = "korean_basic"
    return [item for item in items if style_key in item.get("style_tags", [])]


def filter_by_body_profile(items: list[dict[str, Any]], body_tags: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        avoid = set(item.get("avoid_body_tags", []))
        if avoid & body_tags:
            continue
        out.append(item)
    return out


def score_item_for_user(
    *,
    item: dict[str, Any],
    scene_key: str,
    style_key: str,
    body_tags: set[str],
    max_price_krw: int,
    preferred_size: str,
) -> int:
    score = 70
    if scene_key in item.get("scene_tags", []):
        score += 10
    if style_key in item.get("style_tags", []) or (style_key == "korean" and "korean_basic" in item.get("style_tags", [])):
        score += 9
    rec = set(item.get("recommended_body_tags", []))
    if rec & body_tags:
        score += 8
    if preferred_size in item.get("size_range", []):
        score += 8
    if max_price_krw > 0:
        price = int(item.get("price_krw", 0))
        if price <= max_price_krw:
            score += 8
        else:
            score -= min(20, (price - max_price_krw) // 5000)
    return max(0, min(100, score))
