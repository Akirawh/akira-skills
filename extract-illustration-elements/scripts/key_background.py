#!/usr/bin/env python3
"""Turn a generated flat or checkerboard background into real transparency."""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def _parse_color(value: str) -> np.ndarray:
    text = value.strip().lstrip("#")
    if len(text) == 6 and all(char in "0123456789abcdefABCDEF" for char in text):
        return np.array([int(text[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.int16)
    parts = value.split(",")
    if len(parts) == 3:
        channels = [int(part.strip()) for part in parts]
        if all(0 <= channel <= 255 for channel in channels):
            return np.array(channels, dtype=np.int16)
    raise argparse.ArgumentTypeError("color must be #RRGGBB or R,G,B")


def _border_pixels(rgb: np.ndarray, band: int) -> np.ndarray:
    height, width, _ = rgb.shape
    band = max(1, min(band, width // 3, height // 3))
    return np.concatenate(
        [
            rgb[:band, :, :].reshape(-1, 3),
            rgb[-band:, :, :].reshape(-1, 3),
            rgb[band:-band, :band, :].reshape(-1, 3),
            rgb[band:-band, -band:, :].reshape(-1, 3),
        ],
        axis=0,
    )


def _estimate_palette(rgb: np.ndarray, band: int, colors: int = 4) -> np.ndarray:
    border = _border_pixels(rgb, band)
    quantized = (border // 8) * 8 + 4
    counter = Counter(map(tuple, quantized.tolist()))
    selected = [np.array(color, dtype=np.int16) for color, _ in counter.most_common(colors)]
    if not selected:
        raise ValueError("could not estimate a background color")
    return np.stack(selected, axis=0)


def _candidate_mask(rgb: np.ndarray, palette: np.ndarray, tolerance: float) -> np.ndarray:
    pixels = rgb.astype(np.float32)
    palette_float = palette.astype(np.float32)
    distances = np.sqrt(
        np.sum(
            (pixels[:, :, None, :] - palette_float[None, None, :, :]) ** 2,
            axis=3,
        )
    )
    return distances.min(axis=2) <= tolerance


def _extend_for_neutral_grid(rgb: np.ndarray, candidate: np.ndarray, band: int) -> tuple[np.ndarray, bool]:
    border = _border_pixels(rgb, band).astype(np.int16)
    border_chroma = border.max(axis=1) - border.min(axis=1)
    looks_like_neutral_grid = float(
        np.mean((border_chroma <= 28) & (border.min(axis=1) >= 210))
    ) >= 0.8
    if not looks_like_neutral_grid:
        return candidate, False

    pixels = rgb.astype(np.int16)
    chroma = pixels.max(axis=2) - pixels.min(axis=2)
    neutral_bright = (chroma <= 32) & (pixels.min(axis=2) >= 205)
    return candidate | neutral_bright, True


def _border_connected(candidate: np.ndarray) -> np.ndarray:
    height, width = candidate.shape
    connected = np.zeros_like(candidate, dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        if candidate[0, x]:
            connected[0, x] = True
            queue.append((0, x))
        if candidate[height - 1, x] and not connected[height - 1, x]:
            connected[height - 1, x] = True
            queue.append((height - 1, x))
    for y in range(1, height - 1):
        if candidate[y, 0]:
            connected[y, 0] = True
            queue.append((y, 0))
        if candidate[y, width - 1] and not connected[y, width - 1]:
            connected[y, width - 1] = True
            queue.append((y, width - 1))

    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width:
                if candidate[ny, nx] and not connected[ny, nx]:
                    connected[ny, nx] = True
                    queue.append((ny, nx))
    return connected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--color", type=_parse_color, help="known flat background color")
    parser.add_argument("--tolerance", type=float, default=28.0)
    parser.add_argument("--border", type=int, default=12)
    parser.add_argument("--palette-colors", type=int, default=4)
    parser.add_argument("--feather", type=float, default=0.6)
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"file not found: {args.input}")
    if args.input.resolve() == args.output.resolve():
        parser.error("input and output must be different files")
    if args.tolerance <= 0 or args.border <= 0 or args.palette_colors <= 0:
        parser.error("tolerance, border and palette-colors must be positive")
    if args.feather < 0 or args.dpi <= 0:
        parser.error("feather must be non-negative and dpi must be positive")

    with Image.open(args.input) as source:
        source.load()
        rgb_image = source.convert("RGB")
    rgb = np.asarray(rgb_image, dtype=np.uint8)

    palette = (
        args.color.reshape(1, 3)
        if args.color is not None
        else _estimate_palette(rgb, args.border, args.palette_colors)
    )
    candidate = _candidate_mask(rgb, palette, args.tolerance)
    candidate, neutral_grid_mode = _extend_for_neutral_grid(rgb, candidate, args.border)
    background = _border_connected(candidate)
    foreground = (~background).astype(np.uint8) * 255

    alpha_image = Image.fromarray(foreground)
    if args.feather > 0:
        alpha_image = alpha_image.filter(ImageFilter.GaussianBlur(args.feather))

    rgba = rgb_image.convert("RGBA")
    rgba.putalpha(alpha_image)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(args.output, format="PNG", dpi=(args.dpi, args.dpi))

    alpha = np.asarray(alpha_image, dtype=np.uint8)
    report = {
        "input": str(args.input),
        "output": str(args.output),
        "palette": palette.astype(int).tolist(),
        "neutral_grid_mode": neutral_grid_mode,
        "tolerance": args.tolerance,
        "transparent_fraction": round(float(np.mean(alpha == 0)), 6),
        "partial_alpha_fraction": round(float(np.mean((alpha > 0) & (alpha < 255))), 6),
        "warning": "Inspect edges on both dark and light backgrounds; this fallback is not a semantic mask.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
