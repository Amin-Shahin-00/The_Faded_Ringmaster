"""Build THE FADED RINGMASTER end to end.

  python make.py                 everything (model sheets, voice, music, sfx, mix, picture, final mp4, style frames)
  python make.py audio           voice + music + sfx + mix only
  python make.py picture         render frames -> build/video.mp4
  python make.py final           mux build/video.mp4 + build/audio/mix.wav -> output/the_faded_ringmaster.mp4
  python make.py stills          style frames -> style_frames/
  python make.py sheets          model sheets -> model_sheets/
  Add --no-tts to reuse the existing voice files.
"""
import shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
sys.path.insert(0, str(ROOT))
import imageio_ffmpeg  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
STYLE_TIMES = {"s1_cold_open": 15.5, "s2_golden_days": 26.9, "s3_the_fall": 74.5, "s4_the_change": 103.5,
               "s5_the_recruitment": 133.0, "s6_the_rise": 159.0, "s7_the_finale": 179.76}


def run(*args):
    print(">", " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)


def audio(tts=True):
    if tts:
        run(PY, "audio/tts.py")
    run(PY, "audio/music.py")
    run(PY, "audio/sfx.py")
    run(PY, "audio/mix.py")


def picture():
    run(PY, "render.py", "video", "--workers", "11")


def final():
    out = ROOT / "output" / "the_faded_ringmaster.mp4"
    out.parent.mkdir(exist_ok=True)
    run(FF, "-y", "-loglevel", "error", "-i", ROOT / "build/video.mp4", "-i", ROOT / "build/audio/mix.wav",
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow", "-b:v", "16M", "-maxrate", "22M",
        "-bufsize", "32M", "-x264-params", "aq-mode=3", "-pix_fmt", "yuv420p",
        "-r", "24", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart",
        "-metadata", "title=The Faded Ringmaster", out)
    print("final ->", out)


def stills():
    d = ROOT / "style_frames"
    d.mkdir(exist_ok=True)
    for name, t in STYLE_TIMES.items():
        run(PY, "render.py", "still", str(t), str(d / f"{name}.png"))


def sheets():
    run(PY, "tools/model_sheets.py")


if __name__ == "__main__":
    what = [a for a in sys.argv[1:] if not a.startswith("--")] or ["all"]
    tts = "--no-tts" not in sys.argv
    for w in what:
        if w in ("all", "sheets"):
            sheets()
        if w in ("all", "audio"):
            audio(tts)
        if w in ("all", "picture"):
            picture()
        if w in ("all", "final"):
            final()
        if w in ("all", "stills"):
            stills()
