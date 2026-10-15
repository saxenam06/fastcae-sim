"""PROTOTYPE (LOP-27) - a comparison sheet: picture rows stacked, each under its label band. Run:
look_sheet.py <out.png> <image1> "<label1>" [<image2> "<label2>" ...]   (images and out relative to data/first_loop)"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
out = OUT / sys.argv[1]
pairs = list(zip(sys.argv[2::2], sys.argv[3::2], strict=True))
images = [Image.open(OUT / name).convert("RGB") for name, _ in pairs]
w = max(im.width for im in images)
band = 60
sheet = Image.new("RGB", (w, sum(im.height + band for im in images)), "white")
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("arial.ttf", 30)
except OSError:
    font = ImageFont.load_default()
y = 0
for im, (_, label) in zip(images, pairs, strict=True):
    draw.rectangle([0, y, w, y + band], fill=(235, 235, 235))
    draw.text((16, y + 14), label, fill="black", font=font)
    sheet.paste(im, (0, y + band))
    y += im.height + band
sheet = sheet.resize((sheet.width // 2, sheet.height // 2))
sheet.save(out)
print(out, sheet.size)
