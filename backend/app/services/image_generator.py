import os
import logging
from pathlib import Path
from typing import Optional

import replicate
from dotenv import load_dotenv


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=_BACKEND_ROOT / ".env")
_IMAGE_CACHE: dict[str, str] = {}
logger = logging.getLogger(__name__)
_CN_TO_EN = {
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
}


class ReplicateRateLimitError(Exception):
    def __init__(self, retry_after_sec: int = 8) -> None:
        self.retry_after_sec = retry_after_sec
        super().__init__("Replicate rate limit reached")


def generate_outfit_image(prompt: str) -> Optional[str]:
    if not prompt.strip():
        return None

    if prompt in _IMAGE_CACHE:
        return _IMAGE_CACHE[prompt]

    if not os.getenv("REPLICATE_API_TOKEN"):
        logger.warning("REPLICATE_API_TOKEN is missing, skip image generation.")
        return None

    normalized_prompt = prompt
    for zh, en in _CN_TO_EN.items():
        normalized_prompt = normalized_prompt.replace(zh, en)

    model_ref = "bytedance/sdxl-lightning-4step:6f7a773af6fc3e8de9d5a3c00be77c17308914bf67772726aff83496ba1e3bbe"

    try:
        output = replicate.run(
            model_ref,
            input={
                "prompt": normalized_prompt,
                "negative_prompt": (
                    "low quality, worst quality, blurry, "
                    "shirtless, bare chest, abs, six pack, bodybuilding, gym body, "
                    "underwear, nude, muscular torso, exaggerated muscles"
                ),
                "width": 512,
                "height": 768,
                "num_outputs": 1,
                "num_inference_steps": 4,
                "guidance_scale": 0,
            },
        )

    except Exception as e:
        logger.warning("Replicate image generation failed: %s", e)
        msg = str(e).lower()
        if "429" in msg or "rate limit" in msg or "too many requests" in msg:
            raise ReplicateRateLimitError(retry_after_sec=8)
        return None

    if isinstance(output, list) and output:
        url = output[0].url
        if url:
            _IMAGE_CACHE[prompt] = url
            return url

    if output:
        url = getattr(output, "url", None)
        if url:
            _IMAGE_CACHE[prompt] = url
            return url
    return None
