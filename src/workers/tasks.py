"""
Celery worker for chapter processing.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from celery import Celery
from sqlalchemy.orm import Session

from src.db.session import SessionLocal
from src.db import models
from scripts.render_bubbles import process_json as render_bubbles_process_json
from src.config.config import LLMConfig
from src.core.pipeline_runner import run_pipeline
from src.utils.logger import logger

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Celery configuration
celery_app = Celery(
    "manga_pipeline",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _update_chapter_status(db: Session, chapter_id: int, status: str, **kwargs):
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if not chapter:
        return
    chapter.status = status
    for k, v in kwargs.items():
        setattr(chapter, k, v)
    db.commit()


def _save_chapter_json(db: Session, chapter_id: int, data: dict, json_path: Path):
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    chapter_json = models.ChapterJSON(chapter_id=chapter_id, data=data)
    db.merge(chapter_json)
    db.commit()
    return _hash_file(json_path)


def _save_summary(db: Session, chapter_id: int, summary_text: str, character_registry: dict):
    summary = models.ChapterSummary(chapter_id=chapter_id, summary_text=summary_text, character_registry=character_registry)
    db.merge(summary)
    db.commit()


def _create_placeholder_summary(json_data: dict) -> str:
    return "Summary placeholder."


def _create_placeholder_character_registry(json_data: dict) -> dict:
    return {"characters": []}


def _summarize_with_llm(json_data: dict, enabled: bool = True) -> tuple[str, dict]:
    if not enabled:
        return _create_placeholder_summary(json_data), _create_placeholder_character_registry(json_data)
    if OpenAI is None:
        return _create_placeholder_summary(json_data), _create_placeholder_character_registry(json_data)
    config = LLMConfig.from_env()
    if not config.is_valid():
        return _create_placeholder_summary(json_data), _create_placeholder_character_registry(json_data)
    client = (
        OpenAI(
            api_key=config.api_key,
            base_url=f"{config.api_base}/openai/deployments/{config.model_name}",
            default_query={"api-version": config.api_version},
        )
        if config.api_version
        else OpenAI(api_key=config.api_key, base_url=config.api_base)
    )
    sample_texts = []
    try:
        pages = json_data if isinstance(json_data, list) else json_data.get("data", [])
        for page in pages[:3]:
            for panel in page.get("content", [])[:3]:
                if panel.get("caption"):
                    sample_texts.append(f"Caption: {panel.get('caption')}")
                for bubble in panel.get("content", [])[:5]:
                    t = bubble.get("translate", [{}])
                    txt = t[0].get("text") if t else None
                    if not txt:
                        txt = bubble.get("text")
                    if txt:
                        sample_texts.append(txt)
            if len(sample_texts) > 30:
                break
    except Exception:
        pass
    prompt = (
        "Summarize the manga chapter concisely and list main characters with their speech style.\n"
        "Return JSON with keys: summary (string), characters (array of objects with name, tone, speech_style, quirks).\n"
        "Be concise; tone should reflect how they speak.\n\n"
        "Sample dialogue/captions:\n- " + "\n- ".join(sample_texts[:30])
    )
    try:
        resp = client.chat.completions.create(
            model=config.model_name,
            messages=[
                {"role": "system", "content": "You are a manga summarizer."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.3,
        )
        content = resp.choices[0].message.content.strip()
        parsed = json.loads(content)
        summary = parsed.get("summary") or _create_placeholder_summary(json_data)
        characters = parsed.get("characters") or []
        return summary, {"characters": characters}
    except Exception as exc:
        logger.warning(f"[summary] LLM summary failed: {exc}")
        return _create_placeholder_summary(json_data), _create_placeholder_character_registry(json_data)


def _render_bubbles(json_path: Path, images_root: Path, output_dir: Path, font_path: Path | None):
    output_dir.mkdir(parents=True, exist_ok=True)
    render_bubbles_process_json(
        json_path=json_path,
        images_root=images_root,
        output_dir=output_dir,
        font_path=font_path,
        max_font_size=48,
        min_font_size=12,
        padding=4,
        line_spacing=1.2,
    )
    rendered_zip = output_dir.with_suffix(".zip")
    shutil.make_archive(rendered_zip.with_suffix(""), "zip", output_dir)
    return rendered_zip


def _parse_bool(val: str | None, default: bool, name: str) -> bool:
    if val is None:
        return default
    v = val.lower().strip()
    if v in {"true", "1", "yes", "y"}:
        return True
    if v in {"false", "0", "no", "n"}:
        return False
    logger.warning(f"[env] {name} invalid '{val}', using default {default}")
    return default


def _parse_int(val: str | None, default: int, name: str) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        logger.warning(f"[env] {name} invalid '{val}', using default {default}")
        return default


def _run_pipeline(images_root: Path, output_json_path: Path) -> tuple[dict, bool]:
    device = os.getenv("PIPELINE_DEVICE", "cuda")
    use_vlm = _parse_bool(os.getenv("PIPELINE_USE_VLM"), True, "PIPELINE_USE_VLM")
    use_llm_translate = _parse_bool(os.getenv("PIPELINE_USE_LLM_TRANSLATE"), True, "PIPELINE_USE_LLM_TRANSLATE")
    translate_target_lang = os.getenv("PIPELINE_TRANSLATE_TARGET_LANG", "en")
    pages_per_batch = _parse_int(os.getenv("PIPELINE_PAGES_PER_BATCH"), 2, "PIPELINE_PAGES_PER_BATCH")
    ocr_batch_size = _parse_int(os.getenv("PIPELINE_OCR_BATCH_SIZE"), 16, "PIPELINE_OCR_BATCH_SIZE")
    max_long_edge = _parse_int(os.getenv("PIPELINE_MAX_LONG_EDGE"), 1600, "PIPELINE_MAX_LONG_EDGE")
    fallback_to_cpu_on_oom = _parse_bool(os.getenv("PIPELINE_FALLBACK_CPU_ON_OOM"), True, "PIPELINE_FALLBACK_CPU_ON_OOM")
    use_language_detection = _parse_bool(os.getenv("PIPELINE_USE_LANGUAGE_DETECTION"), True, "PIPELINE_USE_LANGUAGE_DETECTION")
    text_language = os.getenv("PIPELINE_TEXT_LANGUAGE", "ja")
    use_summary_llm = _parse_bool(os.getenv("PIPELINE_USE_SUMMARY_LLM"), True, "PIPELINE_USE_SUMMARY_LLM")

    pipeline_json = run_pipeline(
        manga_root=images_root,
        output_json=output_json_path,
        device=device,
        use_vlm=use_vlm,
        use_llm_translate=use_llm_translate,
        translate_target_lang=translate_target_lang,
        pages_per_batch=pages_per_batch,
        ocr_batch_size=ocr_batch_size,
        max_long_edge=max_long_edge,
        fallback_to_cpu_on_oom=fallback_to_cpu_on_oom,
        use_language_detection=use_language_detection,
        text_language=text_language,
    )
    return pipeline_json, use_summary_llm


@celery_app.task(name="process_chapter")
def process_chapter(series_id: int, chapter_number: int, zip_path: str, chapter_id: int):
    db = SessionLocal()
    zip_path = Path(zip_path)
    workdir = Path(tempfile.mkdtemp(prefix="chapter_"))
    try:
        logger.info(f"[task] start chapter_id={chapter_id} series={series_id} ch={chapter_number}")
        _update_chapter_status(db, chapter_id, "processing")

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(workdir / "images")
        images_root = workdir / "images"

        image_files = [p for p in images_root.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        if image_files:
            ch_dir = images_root / "ch_1"
            ch_dir.mkdir(parents=True, exist_ok=True)
            for img in image_files:
                shutil.move(str(img), ch_dir / img.name)

        output_json_path = Path(os.getenv("OUTPUT_JSON_DIR", "output/json")) / f"series{series_id}_ch{chapter_number}.json"
        pipeline_json, use_summary_llm = _run_pipeline(images_root, output_json_path)
        logger.info(f"[task] pipeline completed json_path={output_json_path}")

        json_hash = _save_chapter_json(db, chapter_id, pipeline_json, output_json_path)

        summary_text, character_registry = _summarize_with_llm(pipeline_json, enabled=use_summary_llm)
        _save_summary(db, chapter_id, summary_text, character_registry)

        rendered_dir = Path(os.getenv("OUTPUT_RENDER_DIR", "output/rendered")) / f"series{series_id}/ch_{chapter_number}"
        font_path_env = os.getenv("RENDER_FONT_PATH")
        font_path = Path(font_path_env) if font_path_env else None
        rendered_zip = _render_bubbles(output_json_path, images_root, rendered_dir, font_path)
        rendered_hash = _hash_file(rendered_zip)

        _update_chapter_status(
            db,
            chapter_id,
            "done",
            json_path=str(output_json_path),
            json_hash=json_hash,
            rendered_zip_path=str(rendered_zip),
            rendered_zip_hash=rendered_hash,
        )
        logger.info(f"[task] done chapter_id={chapter_id} json={output_json_path} render={rendered_zip}")
        return {
            "series_id": series_id,
            "chapter_number": chapter_number,
            "zip_path": str(zip_path),
            "chapter_id": chapter_id,
            "json_path": str(output_json_path),
            "rendered_zip": str(rendered_zip),
        }
    except Exception as exc:
        logger.error(f"[task] failed chapter_id={chapter_id}: {exc}", exc_info=True)
        _update_chapter_status(db, chapter_id, "failed")
        raise
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
"""
Celery worker for chapter processing (skeleton).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from celery import Celery
from sqlalchemy.orm import Session
from src.db.session import SessionLocal
from src.db import models
from scripts.render_bubbles import process_json as render_bubbles_process_json
from src.config.config import LLMConfig
from src.core.pipeline_runner import run_pipeline
from src.utils.logger import logger

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Celery configuration
celery_app = Celery(
    "manga_pipeline",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _update_chapter_status(db: Session, chapter_id: int, status: str, **kwargs):
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if not chapter:
        return
    chapter.status = status
    for k, v in kwargs.items():
        setattr(chapter, k, v)
    db.commit()


def _save_chapter_json(db: Session, chapter_id: int, data: dict, json_path: Path):
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    chapter_json = models.ChapterJSON(chapter_id=chapter_id, data=data)
    db.merge(chapter_json)
    db.commit()

    return _hash_file(json_path)


def _save_summary(db: Session, chapter_id: int, summary_text: str, character_registry: dict):
    summary = models.ChapterSummary(
        chapter_id=chapter_id,
        summary_text=summary_text,
        character_registry=character_registry,
    )
    db.merge(summary)
    db.commit()


def _create_placeholder_summary(json_data: dict) -> str:
    return "Summary placeholder."


def _create_placeholder_character_registry(json_data: dict) -> dict:
    return {"characters": []}


def _summarize_with_llm(json_data: dict, enabled: bool = True) -> tuple[str, dict]:
    """
    Use LLM to produce summary and character registry.
    Returns (summary_text, character_registry_dict).
    If LLM not available or fails, returns placeholders.
    """
    if not enabled:
        return _create_placeholder_summary(json_data), _create_placeholder_character_registry(json_data)

    if OpenAI is None:
        return _create_placeholder_summary(json_data), _create_placeholder_character_registry(json_data)

    config = LLMConfig.from_env()
    if not config.is_valid():
        return _create_placeholder_summary(json_data), _create_placeholder_character_registry(json_data)

    client = (
        OpenAI(
            api_key=config.api_key,
            base_url=f"{config.api_base}/openai/deployments/{config.model_name}",
            default_query={"api-version": config.api_version},
        )
        if config.api_version
        else OpenAI(api_key=config.api_key, base_url=config.api_base)
    )

    # Extract a small slice of content for prompt
    sample_texts = []
    try:
        pages = json_data if isinstance(json_data, list) else json_data.get("data", [])
        for page in pages[:3]:
            for panel in page.get("content", [])[:3]:
                if panel.get("caption"):
                    sample_texts.append(f"Caption: {panel.get('caption')}")
                for bubble in panel.get("content", [])[:5]:
                    t = bubble.get("translate", [{}])
                    txt = t[0].get("text") if t else None
                    if not txt:
                        txt = bubble.get("text")
                    if txt:
                        sample_texts.append(txt)
            if len(sample_texts) > 30:
                break
    except Exception:
        pass

    prompt = (
        "Summarize the manga chapter concisely and list main characters with their speech style.\n"
        "Return JSON with keys: summary (string), characters (array of objects with name, tone, speech_style, quirks).\n"
        "Be concise; tone should reflect how they speak.\n\n"
        "Sample dialogue/captions:\n- " + "\n- ".join(sample_texts[:30])
    )

    try:
        resp = client.chat.completions.create(
            model=config.model_name,
            messages=[
                {"role": "system", "content": "You are a manga summarizer."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.3,
        )
        content = resp.choices[0].message.content.strip()
        parsed = json.loads(content)
        summary = parsed.get("summary") or _create_placeholder_summary(json_data)
        characters = parsed.get("characters") or []
        return summary, {"characters": characters}
    except Exception as exc:
        logger.warning(f"[summary] LLM summary failed: {exc}")
        return _create_placeholder_summary(json_data), _create_placeholder_character_registry(json_data)


def _render_bubbles(json_path: Path, images_root: Path, output_dir: Path, font_path: Path | None):
    output_dir.mkdir(parents=True, exist_ok=True)
    render_bubbles_process_json(
        json_path=json_path,
        images_root=images_root,
        output_dir=output_dir,
        font_path=font_path,
        max_font_size=48,
        min_font_size=12,
        padding=4,
        line_spacing=1.2,
    )
    rendered_zip = output_dir.with_suffix(".zip")
    shutil.make_archive(rendered_zip.with_suffix(""), "zip", output_dir)
    return rendered_zip


def _parse_bool(val: str | None, default: bool, name: str) -> bool:
    if val is None:
        return default
    v = val.lower().strip()
    if v in {"true", "1", "yes", "y"}:
        return True
    if v in {"false", "0", "no", "n"}:
        return False
    logger.warning(f"[env] {name} invalid '{val}', using default {default}")
    return default


def _parse_int(val: str | None, default: int, name: str) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        logger.warning(f"[env] {name} invalid '{val}', using default {default}")
        return default


def _run_pipeline(images_root: Path, output_json_path: Path) -> tuple[dict, bool]:
    """
    Run internal pipeline (no shell) via src.core.pipeline_runner.
    Returns (pipeline_json, use_summary_llm_flag)
    """
    device = os.getenv("PIPELINE_DEVICE", "cuda")
    use_vlm = _parse_bool(os.getenv("PIPELINE_USE_VLM"), True, "PIPELINE_USE_VLM")
    use_llm_translate = _parse_bool(os.getenv("PIPELINE_USE_LLM_TRANSLATE"), True, "PIPELINE_USE_LLM_TRANSLATE")
    translate_target_lang = os.getenv("PIPELINE_TRANSLATE_TARGET_LANG", "en")
    pages_per_batch = _parse_int(os.getenv("PIPELINE_PAGES_PER_BATCH"), 2, "PIPELINE_PAGES_PER_BATCH")
    ocr_batch_size = _parse_int(os.getenv("PIPELINE_OCR_BATCH_SIZE"), 16, "PIPELINE_OCR_BATCH_SIZE")
    max_long_edge = _parse_int(os.getenv("PIPELINE_MAX_LONG_EDGE"), 1600, "PIPELINE_MAX_LONG_EDGE")
    fallback_to_cpu_on_oom = _parse_bool(os.getenv("PIPELINE_FALLBACK_CPU_ON_OOM"), True, "PIPELINE_FALLBACK_CPU_ON_OOM")
    use_language_detection = _parse_bool(os.getenv("PIPELINE_USE_LANGUAGE_DETECTION"), True, "PIPELINE_USE_LANGUAGE_DETECTION")
    text_language = os.getenv("PIPELINE_TEXT_LANGUAGE", "ja")
    use_summary_llm = _parse_bool(os.getenv("PIPELINE_USE_SUMMARY_LLM"), True, "PIPELINE_USE_SUMMARY_LLM")

    pipeline_json = run_pipeline(
        manga_root=images_root,
        output_json=output_json_path,
        device=device,
        use_vlm=use_vlm,
        use_llm_translate=use_llm_translate,
        translate_target_lang=translate_target_lang,
        pages_per_batch=pages_per_batch,
        ocr_batch_size=ocr_batch_size,
        max_long_edge=max_long_edge,
        fallback_to_cpu_on_oom=fallback_to_cpu_on_oom,
        use_language_detection=use_language_detection,
        text_language=text_language,
    )
    return pipeline_json, use_summary_llm


@celery_app.task(name="process_chapter")
def process_chapter(series_id: int, chapter_number: int, zip_path: str, chapter_id: int):
    """
    Unzip, run pipeline (placeholder), save JSONB, summary, character registry, render, update DB.
    Replace placeholder steps with real pipeline calls.
    """
    db = SessionLocal()
    zip_path = Path(zip_path)
    workdir = Path(tempfile.mkdtemp(prefix="chapter_"))

    try:
        logger.info(f"[task] start chapter_id={chapter_id} series={series_id} ch={chapter_number}")
        _update_chapter_status(db, chapter_id, "processing")

        # 1) Extract zip
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(workdir / "images")
        images_root = workdir / "images"

        # If images are directly under images_root (no subfolders), wrap into a chapter folder for compatibility
        image_files = [p for p in images_root.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        if image_files:
            ch_dir = images_root / "ch_1"
            ch_dir.mkdir(parents=True, exist_ok=True)
            for img in image_files:
                target = ch_dir / img.name
                shutil.move(str(img), target)
            images_root = images_root  # remains the root containing chapter folder

        # 2) Run pipeline
        output_json_path = Path(os.getenv("OUTPUT_JSON_DIR", "output/json")) / f"series{series_id}_ch{chapter_number}.json"
        pipeline_json, use_summary_llm = _run_pipeline(images_root, output_json_path)
        logger.info(f"[task] pipeline completed json_path={output_json_path}")

        # 3) Save JSON to disk + DB
        json_hash = _save_chapter_json(db, chapter_id, pipeline_json, output_json_path)

        # 4) Summary + character registry
        summary_text, character_registry = _summarize_with_llm(pipeline_json, enabled=use_summary_llm)
        _save_summary(db, chapter_id, summary_text, character_registry)

        # 5) Render bubbles
        rendered_dir = Path(os.getenv("OUTPUT_RENDER_DIR", "output/rendered")) / f"series{series_id}/ch_{chapter_number}"
        font_path_env = os.getenv("RENDER_FONT_PATH")
        font_path = Path(font_path_env) if font_path_env else None
        rendered_zip = _render_bubbles(output_json_path, images_root, rendered_dir, font_path)
        rendered_hash = _hash_file(rendered_zip)

        # 6) Update chapter status and paths
        _update_chapter_status(
            db,
            chapter_id,
            "done",
            json_path=str(output_json_path),
            json_hash=json_hash,
            rendered_zip_path=str(rendered_zip),
            rendered_zip_hash=rendered_hash,
        )
        logger.info(f"[task] done chapter_id={chapter_id} json={output_json_path} render={rendered_zip}")

        return {
            "series_id": series_id,
            "chapter_number": chapter_number,
            "zip_path": str(zip_path),
            "chapter_id": chapter_id,
            "json_path": str(output_json_path),
            "rendered_zip": str(rendered_zip),
        }
    except Exception as exc:
        logger.error(f"[task] failed chapter_id={chapter_id}: {exc}", exc_info=True)
        _update_chapter_status(db, chapter_id, "failed")
        raise exc
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

