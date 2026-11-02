"""Tile still frames into one review image: python tools/tile.py out.jpg t1 t2 ... (times or paths)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
out = sys.argv[1]
items = sys.argv[2:]
cols = 2
tw, th = 960, 540
rows = (len(items) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
d = ImageDraw.Draw(sheet)
for i, it in enumerate(items):
    p = Path(it) if it.endswith(".png") else ROOT / "build" / "stills" / f"still_{float(it):07.2f}.png"
    im = Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS)
    x, y = (i % cols) * tw, (i // cols) * th
    sheet.paste(im, (x, y))
    d.rectangle([x, y, x + 90, y + 18], fill=(0, 0, 0))
    d.text((x + 4, y + 3), p.stem.replace("still_", ""), fill=(255, 255, 0))
sheet.save(out, quality=90)
print(out)
