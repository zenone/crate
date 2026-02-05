#!/usr/bin/env python3
"""Generate a GitHub-friendly screenshot-style image of CLI output.

We intentionally render *sanitized* sample output (no user paths, no real filenames)
so it's safe to include in public docs.

Output: docs/assets/cli.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    out_path = Path("docs/assets/cli.png")

    text = (
        "$ crate /Music/DJ/Incoming --recursive --dry-run -v\n"
        "Scanning...\n"
        "DRY   Test Artist - Test Title [8A 128].mp3\n"
        "DRY   Another Artist - Deep Cut [9A 124].mp3\n"
        "SKIP  Unknown Artist - Unknown Title.mp3  (missing metadata)\n"
        "\n"
        "Summary\n"
        "  Total:   3\n"
        "  Renamed: 2 (dry-run)\n"
        "  Skipped: 1\n"
        "  Errors:  0\n"
    )

    # Prefer a monospace font if available.
    font_paths = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/Library/Fonts/Menlo.ttc",
    ]
    font = None
    for fp in font_paths:
        p = Path(fp)
        if p.exists():
            font = ImageFont.truetype(str(p), 28)
            break
    if font is None:
        font = ImageFont.load_default()

    padding = 40
    line_spacing = 12

    # Measure
    dummy = Image.new("RGB", (10, 10))
    d = ImageDraw.Draw(dummy)
    lines = text.splitlines() or [""]
    widths = [d.textlength(line, font=font) for line in lines]
    max_w = int(max(widths) if widths else 0)
    ascent, descent = font.getmetrics()
    line_h = ascent + descent + line_spacing
    img_w = max_w + padding * 2
    img_h = line_h * len(lines) + padding * 2

    # Render
    bg = (15, 17, 26)  # dark terminal-ish
    fg = (230, 230, 230)
    subtle = (120, 130, 160)

    img = Image.new("RGB", (img_w, img_h), bg)
    draw = ImageDraw.Draw(img)

    # Faux window header
    header_h = 56
    draw.rounded_rectangle(
        (16, 16, img_w - 16, img_h - 16), radius=18, outline=(40, 45, 70), width=2
    )
    draw.rectangle((16, 16, img_w - 16, 16 + header_h), fill=(20, 22, 34))

    # Traffic lights
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        x = 36 + i * 28
        y = 16 + 18
        draw.ellipse((x, y, x + 14, y + 14), fill=c)

    # Title
    draw.text((36 + 3 * 28 + 10, 16 + 12), "Terminal — Crate", font=font, fill=subtle)

    x0 = 36
    y0 = 16 + header_h + 26
    for idx, line in enumerate(lines):
        y = y0 + idx * line_h
        draw.text((x0, y), line, font=font, fill=fg)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
