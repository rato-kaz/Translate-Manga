"""
Render translated text into speech bubbles using JSON output.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont


def _load_font(font_path: Path | None, size: int) -> ImageFont.FreeTypeFont:
    if font_path and font_path.exists():
        try:
            return ImageFont.truetype(str(font_path), size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    lines: List[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            w = draw.textbbox((0, 0), candidate, font=font)[2]
            if w <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def auto_fit_text(draw: ImageDraw.ImageDraw, text: str, bbox: Tuple[int, int, int, int], font_path: Path | None, max_font_size: int, min_font_size: int, padding: int, line_spacing: float = 1.2) -> Tuple[List[str], ImageFont.FreeTypeFont]:
    x1, y1, x2, y2 = bbox
    max_width = max(1, (x2 - x1) - 2 * padding)
    max_height = max(1, (y2 - y1) - 2 * padding)
    for size in range(max_font_size, min_font_size - 1, -2):
        font = _load_font(font_path, size)
        lines = _wrap_lines(draw, text, font, max_width)
        line_h = draw.textbbox((0, 0), "Ag", font=font)[3]
        total_h = int(len(lines) * line_h * line_spacing)
        max_line_w = max(draw.textbbox((0, 0), ln, font=font)[2] for ln in lines) if lines else 0
        if total_h <= max_height and max_line_w <= max_width:
            return lines, font
    font = _load_font(font_path, min_font_size)
    lines = _wrap_lines(draw, text, font, max_width)
    return lines, font


def draw_text_centered(draw: ImageDraw.ImageDraw, lines: Sequence[str], font: ImageFont.FreeTypeFont, bbox: Tuple[int, int, int, int], padding: int, line_spacing: float = 1.2, fill: str = "black") -> None:
    x1, y1, x2, y2 = bbox
    line_h = draw.textbbox((0, 0), "Ag", font=font)[3]
    total_h = int(len(lines) * line_h * line_spacing)
    cur_y = y1 + ((y2 - y1) - total_h) / 2 + padding
    for line in lines:
        w = draw.textbbox((0, 0), line, font=font)[2]
        cur_x = x1 + ((x2 - x1) - w) / 2
        draw.text((cur_x, cur_y), line, font=font, fill=fill)
        cur_y += line_h * line_spacing


def extract_bbox(bubble_entry: dict) -> Tuple[int, int, int, int]:
    pos = bubble_entry.get("bubble", {}).get("bubble_position") or {}
    return int(pos.get("x1", 0)), int(pos.get("y1", 0)), int(pos.get("x2", 0)), int(pos.get("y2", 0))


def extract_translated_text(bubble_entry: dict) -> str | None:
    translations = bubble_entry.get("translate") or []
    for item in translations:
        if item and item.get("text"):
            return str(item.get("text"))
    text = bubble_entry.get("text")
    return str(text) if text else None


def render_bubble(draw: ImageDraw.ImageDraw, bubble_entry: dict, font_path: Path | None, max_font_size: int, min_font_size: int, padding: int, line_spacing: float, fill_color: str = "white") -> None:
    text = extract_translated_text(bubble_entry)
    if not text:
        return
    bbox = extract_bbox(bubble_entry)
    draw.rectangle(bbox, fill=fill_color)
    lines, font = auto_fit_text(draw, text, bbox, font_path, max_font_size, min_font_size, padding, line_spacing)
    draw_text_centered(draw, lines, font, bbox, padding, line_spacing, fill="black")


def process_page_image(image_path: Path, page_entry: dict, font_path: Path | None, max_font_size: int, min_font_size: int, padding: int, line_spacing: float) -> Image.Image:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    for panel in page_entry.get("content", []):
        for bubble in panel.get("content", []):
            render_bubble(draw, bubble, font_path, max_font_size, min_font_size, padding, line_spacing)
    return image


def ensure_output_path(base_output: Path, relative_image_path: Path) -> Path:
    out_path = base_output / relative_image_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def resolve_image_path(images_root: Path, image_rel: str) -> Path | None:
    rel_path = Path(image_rel)
    candidates = [images_root / rel_path]
    if rel_path.parts and rel_path.parts[0] == images_root.name:
        candidates.append(images_root.parent / rel_path)
    for c in candidates:
        if c.exists():
            return c
    return None


def process_json(json_path: Path, images_root: Path, output_dir: Path, font_path: Path | None, max_font_size: int, min_font_size: int, padding: int, line_spacing: float) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    pages = data if isinstance(data, list) else data.get("data") or data
    for page_entry in pages:
        image_rel = page_entry.get("image")
        if not image_rel:
            continue
        image_path = resolve_image_path(images_root, image_rel)
        if not image_path:
            print(f"[WARN] Image not found (tried variations): {images_root / Path(image_rel)}")
            continue
        rendered = process_page_image(image_path, page_entry, font_path, max_font_size, min_font_size, padding, line_spacing)
        out_path = ensure_output_path(output_dir, Path(image_rel))
        rendered.save(out_path)
        print(f"[OK] Saved: {out_path}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render translated text into bubbles")
    p.add_argument("--json", required=True)
    p.add_argument("--images-root", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--font-path", default=None)
    p.add_argument("--max-font-size", type=int, default=48)
    p.add_argument("--min-font-size", type=int, default=12)
    p.add_argument("--padding", type=int, default=4)
    p.add_argument("--line-spacing", type=float, default=1.2)
    return p


def main():
    args = build_arg_parser().parse_args()
    process_json(
        json_path=Path(args.json),
        images_root=Path(args.images_root),
        output_dir=Path(args.output_dir),
        font_path=Path(args.font_path) if args.font_path else None,
        max_font_size=args.max_font_size,
        min_font_size=args.min_font_size,
        padding=args.padding,
        line_spacing=args.line_spacing,
    )


if __name__ == "__main__":
    main()
"""
Render translated text into detected speech bubbles.

Given a JSON output from `pipeline_generate_json.py` (with bubble bboxes and
translated text), this script will:
1) Load each page image.
2) Blank out the bubble area.
3) Auto-fit the translated text into the bubble rectangle.
4) Save the rendered page to an output directory, preserving relative paths.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont


# --------------------------------------------------------------------------- #
# Text fitting utilities
# --------------------------------------------------------------------------- #


def _load_font(font_path: Path | None, size: int) -> ImageFont.FreeTypeFont:
    """Load TrueType font, fallback to default if unavailable."""
    if font_path and font_path.exists():
        try:
            return ImageFont.truetype(str(font_path), size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """
    Greedy word wrap based on pixel width.
    Splits on whitespace; keeps existing newline boundaries.
    """
    lines: List[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            w = draw.textbbox((0, 0), candidate, font=font)[2]
            if w <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def auto_fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    bbox: Tuple[int, int, int, int],
    font_path: Path | None,
    max_font_size: int,
    min_font_size: int,
    padding: int,
    line_spacing: float = 1.2,
) -> Tuple[List[str], ImageFont.FreeTypeFont]:
    """
    Find the largest font size that fits text into bbox with wrapping.
    Returns wrapped lines and the chosen font.
    """
    x1, y1, x2, y2 = bbox
    max_width = max(1, (x2 - x1) - 2 * padding)
    max_height = max(1, (y2 - y1) - 2 * padding)

    for size in range(max_font_size, min_font_size - 1, -2):
        font = _load_font(font_path, size)
        lines = _wrap_lines(draw, text, font, max_width)
        if not lines:
            continue

        # Measure height
        line_h = draw.textbbox((0, 0), "Ag", font=font)[3]
        total_h = int(len(lines) * line_h * line_spacing)
        max_line_w = 0
        for line in lines:
            w = draw.textbbox((0, 0), line, font=font)[2]
            max_line_w = max(max_line_w, w)

        if total_h <= max_height and max_line_w <= max_width:
            return lines, font

    # Fallback to minimum font size result
    font = _load_font(font_path, min_font_size)
    lines = _wrap_lines(draw, text, font, max_width)
    return lines, font


def draw_text_centered(
    draw: ImageDraw.ImageDraw,
    lines: Sequence[str],
    font: ImageFont.FreeTypeFont,
    bbox: Tuple[int, int, int, int],
    padding: int,
    line_spacing: float = 1.2,
    fill: str = "black",
) -> None:
    """Draw wrapped lines centered inside bbox."""
    x1, y1, x2, y2 = bbox
    line_h = draw.textbbox((0, 0), "Ag", font=font)[3]
    total_h = int(len(lines) * line_h * line_spacing)
    cur_y = y1 + ((y2 - y1) - total_h) / 2 + padding

    for line in lines:
        w = draw.textbbox((0, 0), line, font=font)[2]
        cur_x = x1 + ((x2 - x1) - w) / 2
        draw.text((cur_x, cur_y), line, font=font, fill=fill)
        cur_y += line_h * line_spacing


# --------------------------------------------------------------------------- #
# Bubble rendering
# --------------------------------------------------------------------------- #


def extract_bbox(bubble_entry: dict) -> Tuple[int, int, int, int]:
    """Get (x1, y1, x2, y2) from bubble entry."""
    pos = bubble_entry.get("bubble", {}).get("bubble_position") or {}
    x1 = int(pos.get("x1", 0))
    y1 = int(pos.get("y1", 0))
    x2 = int(pos.get("x2", 0))
    y2 = int(pos.get("y2", 0))
    return x1, y1, x2, y2


def extract_translated_text(bubble_entry: dict) -> str | None:
    """Get translated text if present; fallback to original text."""
    translations = bubble_entry.get("translate") or []
    for item in translations:
        if item and item.get("text"):
            return str(item.get("text"))
    # Fallback to original text
    text = bubble_entry.get("text")
    return str(text) if text else None


def render_bubble(
    draw: ImageDraw.ImageDraw,
    bubble_entry: dict,
    font_path: Path | None,
    max_font_size: int,
    min_font_size: int,
    padding: int,
    line_spacing: float,
    fill_color: str = "white",
) -> None:
    """Blank bubble area and draw translated text."""
    text = extract_translated_text(bubble_entry)
    if not text:
        return

    bbox = extract_bbox(bubble_entry)
    draw.rectangle(bbox, fill=fill_color)

    lines, font = auto_fit_text(
        draw=draw,
        text=text,
        bbox=bbox,
        font_path=font_path,
        max_font_size=max_font_size,
        min_font_size=min_font_size,
        padding=padding,
        line_spacing=line_spacing,
    )
    draw_text_centered(
        draw=draw,
        lines=lines,
        font=font,
        bbox=bbox,
        padding=padding,
        line_spacing=line_spacing,
        fill="black",
    )


# --------------------------------------------------------------------------- #
# Main processing
# --------------------------------------------------------------------------- #


def process_page_image(
    image_path: Path,
    page_entry: dict,
    font_path: Path | None,
    max_font_size: int,
    min_font_size: int,
    padding: int,
    line_spacing: float,
) -> Image.Image:
    """Render all translated bubbles on a single page image."""
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    panels = page_entry.get("content", [])
    for panel in panels:
        for bubble in panel.get("content", []):
            render_bubble(
                draw=draw,
                bubble_entry=bubble,
                font_path=font_path,
                max_font_size=max_font_size,
                min_font_size=min_font_size,
                padding=padding,
                line_spacing=line_spacing,
            )
    return image


def ensure_output_path(base_output: Path, relative_image_path: Path) -> Path:
    """Create mirrored directory structure for output image."""
    out_path = base_output / relative_image_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def resolve_image_path(images_root: Path, image_rel: str) -> Path | None:
    """
    Resolve image path with a few fallbacks to handle duplicated folder segments
    in JSON (e.g., images_root already includes the first segment of image_rel).
    """
    rel_path = Path(image_rel)
    candidates = [images_root / rel_path]

    # If image_rel already starts with images_root.name, try stripping that segment
    if rel_path.parts and rel_path.parts[0] == images_root.name:
        candidates.append(images_root.parent / rel_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def process_json(
    json_path: Path,
    images_root: Path,
    output_dir: Path,
    font_path: Path | None,
    max_font_size: int,
    min_font_size: int,
    padding: int,
    line_spacing: float,
) -> None:
    """Entry point: read JSON, render bubbles, write images."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    pages = data if isinstance(data, list) else data.get("data") or data

    for page_entry in pages:
        image_rel = page_entry.get("image")
        if not image_rel:
            continue
        image_path = resolve_image_path(images_root, image_rel)
        if not image_path:
            print(f"[WARN] Image not found (tried variations): {images_root / Path(image_rel)}")
            continue

        rendered = process_page_image(
            image_path=image_path,
            page_entry=page_entry,
            font_path=font_path,
            max_font_size=max_font_size,
            min_font_size=min_font_size,
            padding=padding,
            line_spacing=line_spacing,
        )

        out_path = ensure_output_path(output_dir, Path(image_rel))
        rendered.save(out_path)
        print(f"[OK] Saved: {out_path}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render translated text into manga bubbles.")
    parser.add_argument("--json", required=True, help="Path to JSON file produced by pipeline_generate_json.py")
    parser.add_argument("--images-root", required=True, help="Root directory containing original page images")
    parser.add_argument("--output-dir", required=True, help="Directory to write rendered images")
    parser.add_argument("--font-path", default=None, help="Path to TTF font (e.g., NotoSansJP-Regular.otf). Default: PIL default font")
    parser.add_argument("--max-font-size", type=int, default=48, help="Maximum font size to try")
    parser.add_argument("--min-font-size", type=int, default=12, help="Minimum font size to allow")
    parser.add_argument("--padding", type=int, default=4, help="Padding inside bubble rectangle")
    parser.add_argument("--line-spacing", type=float, default=1.2, help="Line spacing multiplier")
    return parser


def main():
    args = build_arg_parser().parse_args()

    json_path = Path(args.json)
    images_root = Path(args.images_root)
    output_dir = Path(args.output_dir)
    font_path = Path(args.font_path) if args.font_path else None

    process_json(
        json_path=json_path,
        images_root=images_root,
        output_dir=output_dir,
        font_path=font_path,
        max_font_size=args.max_font_size,
        min_font_size=args.min_font_size,
        padding=args.padding,
        line_spacing=args.line_spacing,
    )


if __name__ == "__main__":
    main()

