#!/usr/bin/env python3
"""Trim, pad and optionally add a white raster outline to an RGBA cutout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def _dilate(alpha: Image.Image, radius: int) -> Image.Image:
    result = alpha
    remaining = radius
    while remaining > 0:
        step = min(remaining, 7)
        result = result.filter(ImageFilter.MaxFilter(step * 2 + 1))
        remaining -= step
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--padding", type=int, default=64)
    parser.add_argument("--outline", type=int, default=0)
    parser.add_argument("--trim-threshold", type=int, default=1)
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"file not found: {args.input}")
    if args.input.resolve() == args.output.resolve():
        parser.error("input and output must be different files")
    if args.padding < 0 or args.outline < 0 or args.dpi <= 0:
        parser.error("padding and outline must be non-negative; dpi must be positive")
    if not 0 <= args.trim_threshold <= 254:
        parser.error("--trim-threshold must be between 0 and 254")

    with Image.open(args.input) as source:
        source.load()
        has_alpha = "A" in source.getbands() or "transparency" in source.info
        rgba = source.convert("RGBA")
    alpha_array = np.asarray(rgba.getchannel("A"), dtype=np.uint8)
    if not has_alpha or np.all(alpha_array == 255):
        parser.error("input does not contain meaningful transparency")

    visible = alpha_array > args.trim_threshold
    if not np.any(visible):
        parser.error("input contains no visible pixels")

    ys, xs = np.nonzero(visible)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    cropped = rgba.crop(bbox)
    margin = args.padding + args.outline
    canvas = Image.new(
        "RGBA",
        (cropped.width + margin * 2, cropped.height + margin * 2),
        (0, 0, 0, 0),
    )
    canvas.alpha_composite(cropped, (margin, margin))

    if args.outline > 0:
        source_alpha = canvas.getchannel("A")
        outline_alpha = _dilate(source_alpha, args.outline)
        white_underlay = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
        white_underlay.putalpha(outline_alpha)
        white_underlay.alpha_composite(canvas)
        canvas = white_underlay

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, format="PNG", dpi=(args.dpi, args.dpi))

    report = {
        "input": str(args.input),
        "output": str(args.output),
        "source_bbox": list(bbox),
        "output_size": [canvas.width, canvas.height],
        "padding_px": args.padding,
        "outline_px": args.outline,
        "dpi_metadata": args.dpi,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
