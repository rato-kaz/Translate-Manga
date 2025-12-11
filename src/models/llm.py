"""
LLM wrapper for translation.
"""

from typing import Callable, Dict, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from src.config import LLMConfig
from src.utils.constants import (
    LLM_DEFAULT_MAX_TOKENS,
    LLM_DEFAULT_TEMPERATURE,
    DEFAULT_TARGET_LANGUAGE,
)
from src.utils.logger import logger
from .prompts import (
    build_llm_system_prompt,
    build_llm_user_prompt,
    clean_translation,
)


class LLMTranslator:
    def __init__(self, config: LLMConfig, target_lang: str = DEFAULT_TARGET_LANGUAGE):
        if OpenAI is None:
            raise ImportError("openai package not installed")
        if not config.is_valid():
            raise ValueError("Invalid LLM config")
        self.config = config
        self.target_lang = target_lang
        if config.api_version:
            self.client = OpenAI(
                api_key=config.api_key,
                base_url=f"{config.api_base}/openai/deployments/{config.model_name}",
                default_query={"api-version": config.api_version},
            )
        else:
            self.client = OpenAI(api_key=config.api_key, base_url=config.api_base)

    def translate_text(
        self,
        text: str,
        source_lang: str,
        context: Optional[Dict] = None,
        max_tokens: int = LLM_DEFAULT_MAX_TOKENS,
        temperature: float = LLM_DEFAULT_TEMPERATURE,
    ) -> Optional[str]:
        if not text or not text.strip():
            logger.debug("Empty text provided, skip translate")
            return None
        try:
            system_prompt = build_llm_system_prompt()
            user_prompt = build_llm_user_prompt(text, source_lang, self.target_lang, context)
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            translation = response.choices[0].message.content.strip()
            translation = clean_translation(translation)
            if translation:
                return translation
            logger.warning("Translation empty")
            return None
        except Exception as exc:
            logger.error(f"LLM translation failed: {exc}", exc_info=True)
            return None


def build_llm_translator(config: Optional[LLMConfig] = None, use_llm_translate: bool = True, target_lang: str = DEFAULT_TARGET_LANGUAGE) -> Optional[Callable[[str, str, Dict], Optional[str]]]:
    if not use_llm_translate:
        return None
    if OpenAI is None:
        logger.warning("openai not installed; LLM disabled")
        return None
    if config is None:
        config = LLMConfig.from_env()
    if not config.is_valid():
        logger.warning("LLM config missing; LLM disabled")
        return None
    translator = LLMTranslator(config, target_lang)
    return translator.translate_text

