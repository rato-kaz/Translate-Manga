"""
VLM wrapper for panel captioning (OpenAI-compatible).
"""

from pathlib import Path
from typing import Callable, Optional, Sequence

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from src.config import VLMConfig
from src.utils.image_processing import encode_image_base64
from src.utils.constants import (
    VLM_DEFAULT_MAX_TOKENS,
    VLM_DEFAULT_TEMPERATURE,
    VLM_MIN_DESCRIPTION_LENGTH,
)
from src.utils.logger import logger
from .prompts import build_vlm_prompt


class VLMDescriber:
    def __init__(self, config: VLMConfig):
        if OpenAI is None:
            raise ImportError("openai package not installed")
        if not config.is_valid():
            raise ValueError("Invalid VLM config")
        self.config = config
        self.client = OpenAI(base_url=config.base_url, api_key=config.api_key)

    def describe_panel(
        self,
        image_path: Path,
        texts: Sequence[str],
        max_tokens: int = VLM_DEFAULT_MAX_TOKENS,
        temperature: float = VLM_DEFAULT_TEMPERATURE,
    ) -> Optional[str]:
        try:
            image_base64, mime_type = encode_image_base64(image_path)
            prompt = build_vlm_prompt(texts)
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                            },
                        ],
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            description = response.choices[0].message.content.strip()
            if description and len(description) >= VLM_MIN_DESCRIPTION_LENGTH:
                return description
            logger.warning(f"Description too short for {image_path}")
            return None
        except Exception as exc:
            logger.error(f"VLM description failed for {image_path}: {exc}", exc_info=True)
            return None


def build_vlm_describer(config: Optional[VLMConfig] = None, use_vlm: bool = True) -> Optional[Callable[[Path, Sequence[str]], Optional[str]]]:
    if not use_vlm:
        return None
    if OpenAI is None:
        logger.warning("openai not installed; VLM disabled")
        return None
    if config is None:
        config = VLMConfig.from_env()
    if not config.is_valid():
        logger.warning("VLM config missing; VLM disabled")
        return None
    describer = VLMDescriber(config)
    return describer.describe_panel

