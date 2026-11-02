"""Contact sheets from the rendered video (one frame every STEP seconds), per scene.

  python tools/contact_video.py [video] [step]       -> build/contact/video_<scene>.jpg
  python tools/contact_video.py frames t0 t1 [video] -> every frame between t0 and t1 (cut/fast-motion check)
"""
import subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.timeline import SCENES, FPS, shot_of  # noqa: E402
import imageio_ffmpeg  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
TW, TH = 384, 216


def grab(video, t):
    cmd = [FF, "-loglevel", "error", "-ss", f"{t:.4f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={TW}:{TH}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return Image.frombytes("RGB", (TW, TH), raw) if len(raw) == TW * TH * 3 else Image.new("RGB", (TW, TH))


def sheet(times, video, out, cols=5):
    rows = (len(times) + cols - 1) // cols
    img = Image.new("RGB", (cols * TW, rows * (TH + 16)), (15, 15, 15))
    d = ImageDraw.Draw(img)
    for i, t in enumerate(times):
        x, y = (i % cols) * TW, (i // cols) * (TH + 16)
        img.paste(grab(video, t), (x, y + 16))
        d.text((x + 3, y + 2), f"{t:7.3f}s {shot_of(t)[1]}", fill=(255, 230, 120))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=85)
    print(out)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "frames":
        t0, t1 = float(sys.argv[2]), float(sys.argv[3])
        video = Path(sys.argv[4]) if len(sys.argv) > 4 else ROOT / "build" / "video.mp4"
        times = [f / FPS + 0.5 / FPS for f in range(int(round(t0 * FPS)), int(round(t1 * FPS)))]
        sheet(times, video, ROOT / "build" / "contact" / f"frames_{t0:.2f}-{t1:.2f}.jpg", cols=6)
    else:
        video = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "video.mp4"
        step = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
        for sid, a, b, act in SCENES:
            times = list(np.arange(a + 0.25, b, step))
            sheet(times, video, ROOT / "build" / "contact" / f"video_{sid}.jpg", cols=6)
