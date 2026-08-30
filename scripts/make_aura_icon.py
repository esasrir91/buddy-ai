"""Generate Aura icon pack (PNG sizes + ICO) from the master artwork."""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC_CANDIDATES = [
    Path(r"C:\Users\hp\.cursor\projects\c-Projects-buddy\assets\aura-icon.png"),
    ROOT / "assets" / "aura-icon.png",
]
src = next((p for p in SRC_CANDIDATES if p.exists()), None)
if src is None:
    raise SystemExit("aura-icon.png not found")

out_dir = ROOT / "assets"
public = ROOT / "code" / "frontend" / "public"
static = ROOT / "code" / "server" / "static"
out_dir.mkdir(parents=True, exist_ok=True)
public.mkdir(parents=True, exist_ok=True)
static.mkdir(parents=True, exist_ok=True)

img = Image.open(src).convert("RGBA")
bbox = img.getbbox()
if bbox:
    pad = 12
    l, t, r, b = bbox
    l, t = max(0, l - pad), max(0, t - pad)
    r, b = min(img.width, r + pad), min(img.height, b + pad)
    img = img.crop((l, t, r, b))

# Make square
side = max(img.size)
square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
img = square

shutil.copy(src, out_dir / "aura-icon.png")

for s in (16, 24, 32, 48, 64, 128, 192, 256, 512):
    resized = img.resize((s, s), Image.Resampling.LANCZOS)
    resized.save(out_dir / f"aura-{s}.png")
    if s in (32, 192, 512):
        resized.save(public / f"aura-{s}.png")

master = img.resize((512, 512), Image.Resampling.LANCZOS)
master.save(out_dir / "aura.png")
master.save(public / "aura-icon.png")
master.save(static / "aura-icon.png")

ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ico_imgs = [img.resize(sz, Image.Resampling.LANCZOS) for sz in ico_sizes]
ico_path = out_dir / "aura.ico"
ico_imgs[-1].save(ico_path, format="ICO", sizes=ico_sizes, append_images=ico_imgs[:-1])
shutil.copy(ico_path, public / "favicon.ico")
shutil.copy(ico_path, static / "favicon.ico")
shutil.copy(ico_path, ROOT / "Aura.ico")

print(f"icon pack ready: {ico_path} ({ico_path.stat().st_size} bytes)")
