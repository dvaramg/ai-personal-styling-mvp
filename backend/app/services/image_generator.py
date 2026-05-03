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


def _extract_replicate_output_url(output: object) -> Optional[str]:
    if output is None:
        return None
    if isinstance(output, str) and output.startswith("http"):
        return output
    if isinstance(output, list) and output:
        return _extract_replicate_output_url(output[0])
    url = getattr(output, "url", None)
    if url:
        return str(url)
    if isinstance(output, dict):
        u = output.get("url")
        if u:
            return str(u)
    return None


class ReplicateRateLimitError(Exception):
    def __init__(self, retry_after_sec: int = 8) -> None:
        self.retry_after_sec = retry_after_sec
        super().__init__("Replicate rate limit reached")


def generate_outfit_image(
    prompt: str,
    *,
    negative_prompt_extra: Optional[str] = None,
) -> Optional[str]:
    # Prompts are expected to be English (catalog / hat label keys resolved upstream).
    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        return None

    cache_key = (
        normalized_prompt if not negative_prompt_extra else f"{normalized_prompt}\nneg:{negative_prompt_extra}"
    )
    if cache_key in _IMAGE_CACHE:
        return _IMAGE_CACHE[cache_key]

    if not os.getenv("REPLICATE_API_TOKEN"):
        logger.warning("REPLICATE_API_TOKEN is missing, skip image generation.")
        return None

    model_ref = "bytedance/sdxl-lightning-4step:6f7a773af6fc3e8de9d5a3c00be77c17308914bf67772726aff83496ba1e3bbe"

    base_negative = (
        "low quality, worst quality, blurry, "
        "shirtless, bare chest, abs, six pack, bodybuilding, gym body, "
        "underwear, nude, muscular torso, exaggerated muscles"
    )
    negative = (
        f"{base_negative}, {negative_prompt_extra}" if negative_prompt_extra else base_negative
    )

    try:
        output = replicate.run(
            model_ref,
            input={
                "prompt": normalized_prompt,
                "negative_prompt": negative,
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
        status = getattr(e, "status", None) or getattr(e, "status_code", None)
        if status == 429:
            raise ReplicateRateLimitError(retry_after_sec=8)
        if "429" in msg or "rate limit" in msg or "too many requests" in msg:
            raise ReplicateRateLimitError(retry_after_sec=8)
        return None

    url = _extract_replicate_output_url(output)
    if url:
        _IMAGE_CACHE[cache_key] = url
        return url
    return None
