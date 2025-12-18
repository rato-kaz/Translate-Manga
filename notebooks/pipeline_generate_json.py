"""
Generate structured JSON metadata for downloaded MangaDex chapters.

This script ties together the MAGI-V2 detection pipeline and produces an
`example_json.json`-style output for the downloaded chapter images located
inside the `downloads/` directory. It optionally supports enriching the data
with panel descriptions through Gemini if the corresponding API key is
available.

Example:
    python pipeline_generate_json.py \
        --manga-root downloads/Princess_Reincarnation \
        --output data/example_json.json \
        --device cuda
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from dotenv import load_dotenv

import numpy as np
import torch
from PIL import Image
from transformers import AutoModel


# -----------------------------------------------------------------------------
# Data helpers
# -----------------------------------------------------------------------------


BBOX = Sequence[float]


@dataclass
class PageImage:
    path: Path
    array: np.ndarray
    width: int
    height: int


def read_image(image_path: Path) -> PageImage:
    with open(image_path, "rb") as handle:
        image = Image.open(handle).convert("RGB")
        array = np.array(image)
    height, width = array.shape[:2]
    return PageImage(path=image_path, array=array, width=width, height=height)


def resize_long_edge(array: np.ndarray, max_long_edge: Optional[int]) -> np.ndarray:
    if not max_long_edge:
        return array
    h, w = array.shape[:2]
    long_edge = max(h, w)
    if long_edge <= max_long_edge:
        return array
    scale = max_long_edge / float(long_edge)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    img = Image.fromarray(array)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    return np.array(img)


def list_chapter_image_paths(root: Path) -> Dict[str, List[Path]]:
    """
    Return a mapping of chapter label -> ordered list of image paths.

    Any directory that contains image files is treated as a chapter folder.
    """
    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    chapter_map: Dict[str, List[Path]] = {}

    for directory in sorted(root.rglob("*")):
        if not directory.is_dir():
            continue
        images = sorted(
            path
            for path in directory.iterdir()
            if path.suffix.lower() in image_exts and path.is_file()
        )
        if images:
            chapter_key = str(directory.relative_to(root))
            chapter_map[chapter_key] = images

    if not chapter_map:
        raise FileNotFoundError(f"No chapter images found under {root}")

    return chapter_map


def parse_chapter_number(label: str, fallback: int) -> int:
    match = re.search(r"(\d+(?:\.\d+)?)", label)
    if not match:
        return fallback
    try:
        value = float(match.group(1))
        if math.isfinite(value):
            return int(value) if value.is_integer() else value
    except ValueError:
        pass
    return fallback


def bbox_center(bbox: BBOX) -> Tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def is_point_inside(point: Tuple[float, float], bbox: BBOX) -> bool:
    x, y = point
    x1, y1, x2, y2 = bbox
    return x1 <= x <= x2 and y1 <= y <= y2


def ensure_panel_bboxes(panel_boxes: List[BBOX], width: int, height: int) -> List[BBOX]:
    if panel_boxes:
        return panel_boxes
    return [[0.0, 0.0, float(width), float(height)]]


def bbox_size_and_position(bbox: BBOX) -> Tuple[Dict[str, float], Dict[str, float]]:
    x1, y1, x2, y2 = bbox
    size = {"width": float(x2 - x1), "height": float(y2 - y1)}
    position = {"x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2)}
    return size, position


def find_panel_index(bbox: BBOX, panels: Sequence[BBOX]) -> int:
    center = bbox_center(bbox)
    for idx, panel_bbox in enumerate(panels):
        if is_point_inside(center, panel_bbox):
            return idx
    # fallback to nearest panel by area overlap heuristic
    areas = [intersection_area(bbox, panel_bbox) for panel_bbox in panels]
    return int(np.argmax(areas)) if areas else 0


def intersection_area(a: BBOX, b: BBOX) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0
    return (inter_x2 - inter_x1) * (inter_y2 - inter_y1)


def format_character_entry(
    character_id: int,
    bbox: BBOX,
    name: str,
) -> Dict[str, object]:
    size, position = bbox_size_and_position(bbox)
    return {
        "character_id": character_id,
        "character_name": name,
        "character_size": size,
        "character_position": position,
    }


def format_bubble_entry(
    bubble_id: int,
    bbox: BBOX,
    text: str,
    lang: str,
    speaker: Dict[str, Optional[object]],
) -> Dict[str, object]:
    size, position = bbox_size_and_position(bbox)
    return {
        "bubble": {
            "bubble_id": bubble_id,
            "bubble_size": size,
            "bubble_position": position,
        },
        "speaker": speaker,
        "text": text,
        "lang": lang,
        "translate": [{"text": None, "lang": None}],
    }


# -----------------------------------------------------------------------------
# Model helpers
# -----------------------------------------------------------------------------


def load_magiv2(device: torch.device):
    model = (
        AutoModel.from_pretrained("ragavsachdeva/magiv2", trust_remote_code=True)
        .to(device)
        .eval()
    )
    return model


def prepare_images(
    image_paths: List[Path],
    *,
    max_long_edge: Optional[int],
) -> Tuple[List[PageImage], List[np.ndarray]]:
    pages = [read_image(path) for path in image_paths]
    arrays = [resize_long_edge(page.array, max_long_edge) for page in pages]
    return pages, arrays


def chunk_indices(n_items: int, batch_size: int) -> Iterable[range]:
    if batch_size <= 0:
        batch_size = n_items
    for start in range(0, n_items, batch_size):
        end = min(n_items, start + batch_size)
        yield range(start, end)


# -----------------------------------------------------------------------------
# Optional Gemini integration
# -----------------------------------------------------------------------------


def build_gemini_describer(use_gemini: bool) -> Optional[Callable[[Path, Sequence[str]], Optional[str]]]:
    if not use_gemini:
        return None

    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Gemini support requested but google-generativeai is not installed."
        ) from exc
        
    load_dotenv()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in environment for Gemini usage.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    def _extract_text_from_response(response) -> Optional[str]:
        # Safely extract text without relying on response.text
        try:
            candidates = getattr(response, "candidates", None) or []
            for cand in candidates:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if not parts:
                    continue
                texts = []
                for p in parts:
                    # Some SDK versions expose 'text' directly; others via dict-like
                    t = getattr(p, "text", None)
                    if t is None and isinstance(p, dict):
                        t = p.get("text")
                    if t:
                        texts.append(t)
                if texts:
                    combined = " ".join(texts).strip()
                    if combined:
                        return combined
        except Exception:
            return None
        return None

    def describe_panel(image_path: Path, texts: Sequence[str]) -> Optional[str]:
        prompt = (
            "You are a concise narrator for manga panels. "
            "Describe the given panel in one or two sentences. "
            "Mention key characters and visible actions. "
            "Avoid safety-sensitive or explicit details. "
            "Avoid saying 'in a manga panel'."
        )
        combined_text = "\n".join(filter(None, texts))
        if combined_text:
            prompt += f"\nThe panel text includes:\n{combined_text}"
        image = Image.open(image_path)
        response = model.generate_content([prompt, image])
        return _extract_text_from_response(response)

    return describe_panel


# -----------------------------------------------------------------------------
# Core pipeline
# -----------------------------------------------------------------------------


def generate_json_for_chapter(
    model,
    device: torch.device,
    manga_name: str,
    chapter_label: str,
    chapter_number: int,
    images: List[Path],
    text_language: str,
    describe_panel: Optional[Callable[[Path, Sequence[str]], Optional[str]]] = None,
    *,
    pages_per_batch: int = 2,
    max_long_edge: Optional[int] = None,
    ocr_batch_size: int = 16,
    fallback_to_cpu_on_oom: bool = True,
) -> List[Dict[str, object]]:
    pages, arrays = prepare_images(images, max_long_edge=max_long_edge)

    detection_results: List[Dict[str, object]] = []
    ocr_results: List[List[str]] = []

    with torch.no_grad():
        for batch_idx_range in chunk_indices(len(arrays), pages_per_batch):
            batch_arrays = [arrays[i] for i in batch_idx_range]
            try:
                det_batch = model.predict_detections_and_associations(batch_arrays)
            except RuntimeError as err:
                if "out of memory" in str(err).lower() and fallback_to_cpu_on_oom and device.type == "cuda":
                    print("CUDA OOM during detection; falling back to CPU for this batch.")
                    torch.cuda.empty_cache()
                    cpu_model = model.to(torch.device("cpu")).eval()
                    det_batch = cpu_model.predict_detections_and_associations(batch_arrays)
                    model = cpu_model  # continue on CPU
                else:
                    raise

            detection_results.extend(det_batch)

            try:
                ocr_batch = model.predict_ocr(
                    batch_arrays,
                    [result["texts"] for result in det_batch],
                    batch_size=ocr_batch_size,
                    max_new_tokens=64,
                    use_tqdm=False,
                )
            except RuntimeError as err:
                if "out of memory" in str(err).lower() and fallback_to_cpu_on_oom and device.type == "cuda":
                    print("CUDA OOM during OCR; falling back to CPU for this batch.")
                    torch.cuda.empty_cache()
                    cpu_model = model.to(torch.device("cpu")).eval()
                    ocr_batch = cpu_model.predict_ocr(
                        batch_arrays,
                        [result["texts"] for result in det_batch],
                        batch_size=max(1, ocr_batch_size // 2),
                        max_new_tokens=64,
                        use_tqdm=False,
                    )
                    model = cpu_model
                else:
                    raise
            ocr_results.extend(ocr_batch)

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    chapter_entries: List[Dict[str, object]] = []

    for page_idx, (page, detections, ocr_texts) in enumerate(
        zip(pages, detection_results, ocr_results)
    ):
        page_entry = {
            "manga_name": manga_name,
            "chapter": chapter_number,
            "page": {
                "page_id": page_idx + 1,
                "page_size": {"width": page.width, "height": page.height},
            },
            "image": str(page.path.relative_to(page.path.parents[2])),
            "content": [],
        }

        panel_bboxes = ensure_panel_bboxes(detections.get("panels", []), page.width, page.height)
        characters = detections.get("characters", [])
        character_names = detections.get("character_names", [])
        texts = detections.get("texts", [])
        is_essential = detections.get("is_essential_text", [])
        text_char_assoc = detections.get("text_character_associations", [])

        panel_entries: List[Dict[str, object]] = []
        panel_char_maps: List[Dict[int, int]] = []
        panel_bubble_counters: List[int] = []

        for panel_idx, panel_bbox in enumerate(panel_bboxes):
            panel_id = panel_idx + 1
            panel_size, panel_position = bbox_size_and_position(panel_bbox)
            panel_entries.append(
                {
                    "panel": {
                        "panel_id": panel_id,
                        "panel_size": panel_size,
                        "panel_position": panel_position,
                    },
                    "character": [],
                    "caption": None,
                    "content": [],
                }
            )
            panel_char_maps.append({})
            panel_bubble_counters.append(0)

        def ensure_character_in_panel(global_char_idx: int, target_panel_idx: int) -> int:
            panel_map = panel_char_maps[target_panel_idx]
            if global_char_idx in panel_map:
                return panel_map[global_char_idx]

            character_id = len(panel_map) + 1
            panel_map[global_char_idx] = character_id

            name = (
                character_names[global_char_idx]
                if global_char_idx < len(character_names)
                else f"Character_{global_char_idx}"
            )
            char_entry = format_character_entry(
                character_id=character_id,
                bbox=characters[global_char_idx],
                name=name,
            )
            panel_entries[target_panel_idx]["character"].append(char_entry)
            return character_id

        for char_idx, char_bbox in enumerate(characters):
            panel_idx = find_panel_index(char_bbox, panel_bboxes)
            ensure_character_in_panel(char_idx, panel_idx)

        text_to_chars: Dict[int, List[int]] = defaultdict(list)
        for text_idx, char_idx in text_char_assoc:
            text_to_chars[int(text_idx)].append(int(char_idx))

        for text_idx, (text_bbox, text_content) in enumerate(zip(texts, ocr_texts)):
            panel_idx = find_panel_index(text_bbox, panel_bboxes)
            panel = panel_entries[panel_idx]
            panel_bubble_counters[panel_idx] += 1

            speaker: Dict[str, Optional[object]] = {"type": "narrator", "character_id": None}
            associated_chars = text_to_chars.get(text_idx, [])
            if associated_chars:
                primary_char_idx = associated_chars[0]
                local_id = ensure_character_in_panel(primary_char_idx, panel_idx)
                speaker_name = (
                    character_names[primary_char_idx]
                    if primary_char_idx < len(character_names)
                    else f"Character_{primary_char_idx}"
                )
                speaker = {"type": "character", "character_id": local_id, "character_name": speaker_name}

            bubble_entry = format_bubble_entry(
                bubble_id=panel_bubble_counters[panel_idx],
                bbox=text_bbox,
                text=text_content,
                lang=text_language,
                speaker=speaker,
            )

            bubble_entry["is_dialogue"] = bool(
                is_essential[text_idx] if text_idx < len(is_essential) else False
            )

            panel["content"].append(bubble_entry)

        if describe_panel:
            for panel, panel_bbox in zip(panel_entries, panel_bboxes):
                bubble_texts = [bubble["text"] for bubble in panel["content"]]
                try:
                    description = describe_panel(page.path, bubble_texts)
                except Exception as exc:  # pragma: no cover - external service
                    print(f"Gemini description failed for {page.path}: {exc}")
                    description = None
                if description:
                    panel["caption"] = description

        page_entry["content"] = panel_entries
        chapter_entries.append(page_entry)

    return chapter_entries


def build_output_json(
    manga_root: Path,
    output_path: Path,
    device: torch.device,
    max_chapters: Optional[int],
    text_language: str,
    use_gemini: bool,
    *,
    pages_per_batch: int,
    max_long_edge: Optional[int],
    ocr_batch_size: int,
    fallback_to_cpu_on_oom: bool,
):
    manga_name = manga_root.name
    chapter_map = list_chapter_image_paths(manga_root)
    describe_panel = build_gemini_describer(use_gemini)

    model = load_magiv2(device)

    all_entries: List[Dict[str, object]] = []
    for idx, (chapter_label, image_paths) in enumerate(sorted(chapter_map.items())):
        if max_chapters is not None and idx >= max_chapters:
            break

        chapter_number = parse_chapter_number(chapter_label, idx + 1)
        print(f"Processing chapter '{chapter_label}' -> chapter {chapter_number} ({len(image_paths)} pages)")
        entries = generate_json_for_chapter(
            model=model,
            device=device,
            manga_name=manga_name,
            chapter_label=chapter_label,
            chapter_number=chapter_number,
            images=image_paths,
            text_language=text_language,
            describe_panel=describe_panel,
            pages_per_batch=pages_per_batch,
            max_long_edge=max_long_edge,
            ocr_batch_size=ocr_batch_size,
            fallback_to_cpu_on_oom=fallback_to_cpu_on_oom,
        )
        all_entries.extend(entries)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(all_entries, handle, indent=2, ensure_ascii=False)
    print(f"Saved {len(all_entries)} pages to {output_path}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate example_json-style output from downloaded MangaDex chapters."
    )
    parser.add_argument(
        "--manga-root",
        required=True,
        type=Path,
        help="Path to the downloaded manga directory (e.g. downloads/Princess...).",
    )
    parser.add_argument(
        "--output",
        default=Path("example_json_generated.json"),
        type=Path,
        help="Where to write the resulting JSON file.",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Device to run MAGI-V2 on (default: auto).",
    )
    parser.add_argument(
        "--pages-per-batch",
        type=int,
        default=2,
        help="Number of pages to process per detection/OCR batch (default: 2).",
    )
    parser.add_argument(
        "--ocr-batch-size",
        type=int,
        default=16,
        help="OCR batch size passed to model.predict_ocr (default: 16).",
    )
    parser.add_argument(
        "--max-long-edge",
        type=int,
        default=1600,
        help="Resize pages so that the longest edge is at most this many pixels (default: 1600).",
    )
    parser.add_argument(
        "--no-fallback-cpu",
        action="store_true",
        help="Disable automatic fallback to CPU on CUDA OOM.",
    )
    parser.add_argument(
        "--max-chapters",
        type=int,
        default=None,
        help="Limit the number of chapter folders processed.",
    )
    parser.add_argument(
        "--text-language",
        default="ja",
        help="Language code to attach to OCR text entries (default: ja).",
    )
    parser.add_argument(
        "--use-gemini",
        action="store_true",
        help="If set, use Gemini to add panel descriptions (requires GEMINI_API_KEY).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    manga_root = args.manga_root.resolve()
    if not manga_root.exists():
        raise FileNotFoundError(f"Manga root not found: {manga_root}")

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    build_output_json(
        manga_root=manga_root,
        output_path=args.output.resolve(),
        device=device,
        max_chapters=args.max_chapters,
        text_language=args.text_language,
        use_gemini=args.use_gemini,
        pages_per_batch=args.pages_per_batch,
        max_long_edge=args.max_long_edge,
        ocr_batch_size=args.ocr_batch_size,
        fallback_to_cpu_on_oom=not args.no_fallback_cpu,
    )


if __name__ == "__main__":
    main()

