#!/usr/bin/env python3
"""Inspect whether an image is a usable transparent cutout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def _has_alpha(image: Image.Image) -> bool:
    return "A" in image.getbands() or "transparency" in image.info


def _likely_checkerboard(rgb: np.ndarray, has_real_alpha: bool) -> bool:
    if has_real_alpha:
        return False
    height, width, _ = rgb.shape
    band = max(4, min(16, min(width, height) // 20))
    border = np.concatenate(
        [
            rgb[:band, :, :].reshape(-1, 3),
            rgb[-band:, :, :].reshape(-1, 3),
            rgb[band:-band, :band, :].reshape(-1, 3),
            rgb[band:-band, -band:, :].reshape(-1, 3),
        ],
        axis=0,
    )
    chroma = border.max(axis=1) - border.min(axis=1)
    neutral_bright = (chroma <= 16) & (border.min(axis=1) >= 220)
    if float(neutral_bright.mean()) < 0.9:
        return False
    levels = np.round(border[neutral_bright].mean(axis=1) / 8).astype(np.int16)
    _, counts = np.unique(levels, return_counts=True)
    strong_levels = int(np.count_nonzero(counts >= max(8, len(levels) * 0.05)))
    return strong_levels >= 2


def inspect(path: Path, alpha_threshold: int) -> dict:
    with Image.open(path) as source:
        source.load()
        original_mode = source.mode
        has_alpha = _has_alpha(source)
        rgba = source.convert("RGBA")
        rgb = np.asarray(rgba, dtype=np.uint8)[..., :3]
        alpha = np.asarray(rgba.getchannel("A"), dtype=np.uint8)

    visible = alpha > alpha_threshold
    transparent = alpha == 0
    partial = (alpha > 0) & (alpha < 255)
    total = alpha.size

    bbox = None
    padding = None
    if np.any(visible):
        ys, xs = np.nonzero(visible)
        left = int(xs.min())
        top = int(ys.min())
        right = int(xs.max()) + 1
        bottom = int(ys.max()) + 1
        bbox = [left, top, right, bottom]
        padding = {
            "left": left,
            "top": top,
            "right": int(alpha.shape[1] - right),
            "bottom": int(alpha.shape[0] - bottom),
        }

    has_transparent_pixels = bool(np.any(alpha < 255))
    valid_transparency = bool(has_alpha and has_transparent_pixels and np.any(visible))
    issues: list[str] = []
    warnings: list[str] = []

    if not has_alpha:
        issues.append("missing_alpha_channel")
    elif not has_transparent_pixels:
        issues.append("alpha_is_fully_opaque")
    if not np.any(visible):
        issues.append("no_visible_content")
    if padding and min(padding.values()) == 0:
        warnings.append("content_touches_canvas_edge")
    if valid_transparency and float(transparent.mean()) < 0.005:
        warnings.append("very_little_transparent_area")

    likely_checkerboard = _likely_checkerboard(rgb, has_alpha and has_transparent_pixels)
    if likely_checkerboard:
        warnings.append("likely_baked_checkerboard_background")

    return {
        "path": str(path),
        "format": "PNG" if path.suffix.lower() == ".png" else path.suffix.lower().lstrip("."),
        "mode": original_mode,
        "size": [int(alpha.shape[1]), int(alpha.shape[0])],
        "has_alpha_channel": has_alpha,
        "valid_transparency": valid_transparency,
        "alpha_min": int(alpha.min()),
        "alpha_max": int(alpha.max()),
        "transparent_fraction": round(float(transparent.sum() / total), 6),
        "partial_alpha_fraction": round(float(partial.sum() / total), 6),
        "content_bbox": bbox,
        "padding": padding,
        "likely_baked_checkerboard": likely_checkerboard,
        "issues": issues,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--alpha-threshold", type=int, default=1)
    args = parser.parse_args()

    if not args.image.is_file():
        parser.error(f"file not found: {args.image}")
    if not 0 <= args.alpha_threshold <= 254:
        parser.error("--alpha-threshold must be between 0 and 254")

    report = inspect(args.image, args.alpha_threshold)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid_transparency"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
