"""
Wrapper to run the pipeline via existing pipeline_generate_json.py (legacy) or new impl.
"""

import json
from pathlib import Path
from typing import Optional

import torch

from src.utils.logger import logger

try:
    # prefer new impl if present
    from src.core import pipeline_impl as pgj
except ImportError:
    pgj = None
try:
    # fallback to legacy path
    from check_n_test_function import pipeline_generate_json as legacy_pgj  # type: ignore
except ImportError:
    legacy_pgj = None


def run_pipeline(
    manga_root: Path,
    output_json: Path,
    *,
    device: str = "cuda",
    use_vlm: bool = True,
    use_llm_translate: bool = True,
    translate_target_lang: str = "en",
    pages_per_batch: int = 2,
    ocr_batch_size: int = 16,
    max_long_edge: Optional[int] = 1600,
    fallback_to_cpu_on_oom: bool = True,
    use_language_detection: bool = True,
    text_language: str = "ja",
    max_chapters: Optional[int] = None,
) -> dict:
    if pgj is None and legacy_pgj is None:
        raise ImportError("No pipeline implementation found.")

    if device == "auto":
        device_t = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device_t = torch.device(device)

    impl = pgj if pgj is not None else legacy_pgj
    try:
        logger.info(
            f"[pipeline] start manga_root={manga_root} output={output_json} device={device_t} "
            f"use_vlm={use_vlm} use_llm_translate={use_llm_translate}"
        )
        impl.build_output_json(
            manga_root=manga_root,
            output_path=output_json,
            device=device_t,
            max_chapters=max_chapters,
            text_language=text_language,
            use_vlm=use_vlm,
            use_llm_translate=use_llm_translate,
            translate_target_lang=translate_target_lang,
            pages_per_batch=pages_per_batch,
            max_long_edge=max_long_edge,
            ocr_batch_size=ocr_batch_size,
            fallback_to_cpu_on_oom=fallback_to_cpu_on_oom,
            use_language_detection=use_language_detection,
        )
        return json.loads(output_json.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error(f"[pipeline] failed: {exc}", exc_info=True)
        raise
"""
Thin wrapper to run the real pipeline from code (no shell).

It reuses the existing implementation in `check_n_test_function/pipeline_generate_json.py`
to avoid duplication, but exposes a callable for Celery/servers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import torch

from src.utils.logger import logger
from src.core import pipeline_impl as pgj


def run_pipeline(
    manga_root: Path,
    output_json: Path,
    *,
    device: str = "cuda",
    use_vlm: bool = True,
    use_llm_translate: bool = True,
    translate_target_lang: str = "en",
    pages_per_batch: int = 2,
    ocr_batch_size: int = 16,
    max_long_edge: Optional[int] = 1600,
    fallback_to_cpu_on_oom: bool = True,
    use_language_detection: bool = True,
    text_language: str = "ja",
    max_chapters: Optional[int] = None,
) -> dict:
    """
    Run the manga pipeline and return the JSON object.

    Args:
        manga_root: Root directory containing chapter folders with images.
        output_json: Path to write JSON output.
        device: "cuda" | "cpu" | "auto".
        use_vlm: Whether to enable VLM captions.
        use_llm_translate: Whether to enable LLM translation.
        translate_target_lang: Target language for translation.
        pages_per_batch: Detection/OCR batch size (pages).
        ocr_batch_size: OCR batch size.
        max_long_edge: Resize long edge.
        fallback_to_cpu_on_oom: Fallback to CPU on CUDA OOM.
        use_language_detection: Enable fast-langdetect.
        text_language: Default text language if detection disabled.
        max_chapters: Limit chapters to process.

    Returns:
        Parsed JSON data (list of pages).
    """
    if device == "auto":
        device_t = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device_t = torch.device(device)

    try:
        logger.info(
            f"[pipeline] start manga_root={manga_root} output={output_json} device={device_t} "
            f"use_vlm={use_vlm} use_llm_translate={use_llm_translate}"
        )
        pgj.build_output_json(
            manga_root=manga_root,
            output_path=output_json,
            device=device_t,
            max_chapters=max_chapters,
            text_language=text_language,
            use_vlm=use_vlm,
            use_llm_translate=use_llm_translate,
            translate_target_lang=translate_target_lang,
            pages_per_batch=pages_per_batch,
            max_long_edge=max_long_edge,
            ocr_batch_size=ocr_batch_size,
            fallback_to_cpu_on_oom=fallback_to_cpu_on_oom,
            use_language_detection=use_language_detection,
        )
        return json.loads(output_json.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error(f"[pipeline] failed: {exc}", exc_info=True)
        raise

