"""PROTOTYPE (LOP-27) - split a design's look_face picture into its two views (the cover, the motor side), each cropped to
the housing with a margin under a caption of its own. Run: split_view.py <design> "<cover caption>" "<motor side caption>".
Writes data/first_loop/<design>_cover_view.png and <design>_motor_side_view.png."""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
design = sys.argv[1]
captions = sys.argv[2:4]
im = Image.open(OUT / f"look_face_{design}.png").convert("RGB")
w, h = im.size
try:
    font = ImageFont.truetype("arial.ttf", 26)
except OSError:
    font = ImageFont.load_default()
for k, (name, caption) in enumerate(zip(("cover", "motor_side"), captions, strict=True)):
    panel = im.crop((k * w // 2 + 10, 50, (k + 1) * w // 2 - 10, h - 10))  # the caption band and the divider left out
    a = np.asarray(panel)
    body = np.argwhere(a.min(axis=2) < 200)
    y0, x0 = body.min(axis=0)
    y1, x1 = body.max(axis=0)
    m = 30
    view = panel.crop((max(0, x0 - m), max(0, y0 - m), min(panel.width, x1 + m), min(panel.height, y1 + m)))
    band = 50
    out_im = Image.new("RGB", (max(view.width, 700), view.height + band), "white")
    ImageDraw.Draw(out_im).text((14, 12), caption, fill="black", font=font)
    out_im.paste(view, ((out_im.width - view.width) // 2, band))
    out = OUT / f"{design}_{name}_view.png"
    out_im.save(out)
    print(out, out_im.size)
