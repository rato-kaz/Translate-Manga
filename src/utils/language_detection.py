"""
Language detection utilities.
"""

from typing import Optional

from .constants import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from .logger import logger

try:
    from fast_langdetect import detect as fast_detect
except ImportError:
    fast_detect = None


def detect_text_language(text: str, fallback_lang: str = DEFAULT_LANGUAGE) -> str:
    if not text or not text.strip():
        return fallback_lang
    if fast_detect is None:
        return fallback_lang
    try:
        results = fast_detect(text, model="full", k=1)
        if results and len(results) > 0:
            detected_lang = results[0].get("lang", fallback_lang)
            if detected_lang in SUPPORTED_LANGUAGES:
                return detected_lang
            logger.debug(f"Detected unsupported language: {detected_lang}, using fallback")
    except Exception as e:
        logger.debug(f"Language detection failed: {e}, using fallback: {fallback_lang}")
    return fallback_lang

