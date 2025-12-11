"""
Image processing utilities.
"""

import base64
import io
from pathlib import Path
from typing import Tuple
from PIL import Image

from .constants import (
    VLM_MAX_LONG_EDGE,
    IMAGE_FORMAT_PNG,
    IMAGE_FORMAT_JPEG,
    IMAGE_MIME_TYPE_JPEG,
    IMAGE_MIME_TYPE_PNG,
)
from .logger import logger


def resize_image_for_vlm(image: Image.Image, max_long_edge: int = VLM_MAX_LONG_EDGE) -> Tuple[Image.Image, bool]:
    width, height = image.size
    long_edge = max(width, height)
    if long_edge <= max_long_edge:
        return image, False
    scale = max_long_edge / float(long_edge)
    new_w = max(1, int(width * scale))
    new_h = max(1, int(height * scale))
    resized = image.resize((new_w, new_h), Image.LANCZOS)
    logger.debug(f"Resized image from {width}x{height} to {new_w}x{new_h}")
    return resized, True


def encode_image_base64(image_path: Path, image_format: str = IMAGE_FORMAT_PNG) -> Tuple[str, str]:
    image = Image.open(image_path).convert("RGB")
    image, was_resized = resize_image_for_vlm(image)
    if was_resized:
        logger.debug(f"Image resized for VLM: {image_path}")

    buffered = io.BytesIO()
    image.save(buffered, format=image_format)
    image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    if image_format == IMAGE_FORMAT_JPEG:
        mime_type = IMAGE_MIME_TYPE_JPEG
    else:
        mime_type = IMAGE_MIME_TYPE_PNG
    return image_base64, mime_type

