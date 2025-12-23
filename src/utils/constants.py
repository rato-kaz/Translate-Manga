"""
Common constants.
"""

LANGUAGE_NAMES = {
    "ja": "Japanese",
    "en": "English",
    "vi": "Vietnamese",
    "zh": "Chinese",
    "ko": "Korean",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
}

SUPPORTED_LANGUAGES = set(LANGUAGE_NAMES.keys())

DEFAULT_LANGUAGE = "ja"
DEFAULT_TARGET_LANGUAGE = "en"

VLM_MAX_LONG_EDGE = 2048
VLM_DEFAULT_MAX_TOKENS = 1024
VLM_DEFAULT_TEMPERATURE = 0.0
VLM_MIN_DESCRIPTION_LENGTH = 10

LLM_DEFAULT_MAX_TOKENS = 512
LLM_DEFAULT_TEMPERATURE = 0.3

TRANSLATION_SKIP_PATTERNS = [
    "translation:",
    "here is the translation",
    "the translation is",
    "translated text:",
]

IMAGE_FORMAT_PNG = "PNG"
IMAGE_FORMAT_JPEG = "JPEG"
IMAGE_MIME_TYPE_JPEG = "image/jpeg"
IMAGE_MIME_TYPE_PNG = "image/png"

# Render bubble constants
RENDER_MAX_FONT_SIZE = 48
RENDER_MIN_FONT_SIZE = 12
RENDER_PADDING = 4
RENDER_LINE_SPACING = 1.2

