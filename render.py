"""THE FADED RINGMASTER - deterministic frame renderer.

Every frame is a pure function of its time t, so frames can be rendered in any
order and in parallel. Usage:

  python render.py still 12.5 [out.png]         one frame
  python render.py contact s3 [step]            contact sheet of a scene (default every 0.5 s)
  python render.py stills                       one style frame per scene -> style_frames/
  python render.py video [t0 t1] [--workers N]  render picture -> build/video.mp4
"""
import argparse, importlib, math, os, subprocess, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config.timeline import FPS, W, H, DURATION, SHOTS, TRANSITIONS, SCENES, shot_of  # noqa: E402
from lib.frame import new_surface, to_array, post  # noqa: E402
from lib.core import boil_index, smooth, clamp  # noqa: E402
from lib.ink import S  # noqa: E402
import imageio_ffmpeg  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
BUILD = ROOT / "build"

_modules = {}


def scene_module(sid):
    if sid not in _modules:
        _modules[sid] = importlib.import_module(f"scenes.{sid}")
    return _modules[sid]


def reset_style():
    S.boil_amp = 0.75
    S.line_scale = 1.0
    S.key = (-0.55, -0.83)
    S.shadow_col = "#2a1a2a"
    S.shadow_a = 0.32
    S.rim = None
    S.rim_a = 0.0
    S.shade_blur = 2.2


def render_shot(sid, shot, a, b, t, frame_idx):
    """Render one shot at absolute time t -> uint8 RGB (post applied)."""
    reset_style()
    S.boil = boil_index(t)
    surf = new_surface()
    c = surf.getCanvas()
    c.clear(0xFF000000)
    fn = scene_module(sid).SHOTS[shot]
    params = fn(c, t - a, b - a, t) or {}
    rgba = to_array(surf)
    return post(rgba, frame_idx, **params)


def render_frame(t):
    frame_idx = int(round(t * FPS))
    sid, shot, a, b = shot_of(t)
    for (tc, d, kind) in TRANSITIONS:
        if tc - d / 2 <= t < tc + d / 2:
            prev = next((s for s in SHOTS if abs(s[3] - tc) < 1e-6), None)
            nxt = next((s for s in SHOTS if abs(s[2] - tc) < 1e-6), None)
            if prev is None or nxt is None:
                break
            u = (t - (tc - d / 2)) / d
            if kind == "dissolve":
                A = render_shot(*prev, t, frame_idx).astype(np.float32)
                B = render_shot(*nxt, t, frame_idx).astype(np.float32)
                w = smooth(u)
                return (A * (1 - w) + B * w + 0.5).astype(np.uint8)
            if kind == "black":
                if u < 0.5:
                    img = render_shot(*prev, t, frame_idx).astype(np.float32)
                    k = 1 - smooth(u / 0.5)
                else:
                    img = render_shot(*nxt, t, frame_idx).astype(np.float32)
                    k = smooth((u - 0.5) / 0.5)
                return (img * k + 0.5).astype(np.uint8)
    return render_shot(sid, shot, a, b, t, frame_idx)


def still(t, out):
    img = render_frame(t)
    Image.fromarray(img).save(out)
    return out


# ---------------------------------------------------------------- contact sheets

def contact(sid, step=0.5, cols=6, thumb=320, t0=None, t1=None):
    sc = next(s for s in SCENES if s[0] == sid)
    a, b = (t0 if t0 is not None else sc[1]), (t1 if t1 is not None else sc[2])
    times = list(np.arange(a, b - 1e-6, step))
    th = int(thumb * H / W)
    rows = math.ceil(len(times) / cols)
    sheet = Image.new("RGB", (cols * thumb, rows * (th + 18)), (20, 20, 20))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    with Pool(min(11, os.cpu_count() - 1)) as pool:
        imgs = pool.map(render_frame, times)
    for i, (t, img) in enumerate(zip(times, imgs)):
        im = Image.fromarray(img).resize((thumb, th), Image.LANCZOS)
        x, y = (i % cols) * thumb, (i // cols) * (th + 18)
        sheet.paste(im, (x, y + 18))
        d.text((x + 4, y + 3), f"{t:6.2f}s  {shot_of(t)[1]}", fill=(230, 230, 230))
    out = BUILD / "contact" / f"{sid}_{a:.1f}-{b:.1f}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    return out


# ---------------------------------------------------------------- video

def _render_chunk(args):
    i, f0, f1 = args
    out = BUILD / "segments" / f"chunk_{i:03d}.mp4"
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", "-x264-params", "keyint=48",
           str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t_start = time.time()
    for f in range(f0, f1):
        img = render_frame(f / FPS)
        p.stdin.write(np.ascontiguousarray(img).tobytes())
    p.stdin.close()
    p.wait()
    return i, f1 - f0, time.time() - t_start


def _done_chunks():
    """Chunks recorded as finished in build/render_log.txt (written only after ffmpeg closed the file)."""
    import re
    done = set()
    for log in BUILD.glob("render_log*.txt"):
        raw = log.read_bytes()
        txt = raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8", errors="ignore")
        done |= {int(m) for m in re.findall(r"chunk\s+(\d+)\s+\d+ frames", txt)}
    return done


def video(t0=0.0, t1=DURATION, workers=11, chunk=48, resume=False):
    (BUILD / "segments").mkdir(parents=True, exist_ok=True)
    done = _done_chunks() if resume else set()
    if not resume:
        for old in (BUILD / "segments").glob("chunk_*.mp4"):
            old.unlink()
    f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    jobs, all_jobs, i = [], [], 0
    for a in range(f0, f1, chunk):
        all_jobs.append((i, a, min(a + chunk, f1)))
        if i not in done or not (BUILD / "segments" / f"chunk_{i:03d}.mp4").exists():
            jobs.append(all_jobs[-1])
        i += 1
    print(f"rendering {len(jobs)} of {len(all_jobs)} chunks", flush=True)
    t = time.time()
    done = 0
    with Pool(workers) as pool:
        for i, n, dt in pool.imap_unordered(_render_chunk, jobs):
            done += n
            print(f"chunk {i:3d}  {n} frames  {dt:6.1f}s   total {done}/{f1 - f0}  elapsed {time.time() - t:7.1f}s", flush=True)
    lst = BUILD / "segments" / "list.txt"
    lst.write_text("".join(f"file 'chunk_{j:03d}.mp4'\n" for j in range(len(all_jobs))))
    out = BUILD / "video.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], check=True)
    print("video ->", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--resume", action="store_true", help="keep chunks the log records as finished")
    a = ap.parse_args()
    if a.cmd == "still":
        t = float(a.args[0])
        out = a.args[1] if len(a.args) > 1 else str(BUILD / "stills" / f"still_{t:07.2f}.png")
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        print(still(t, out))
    elif a.cmd == "stills":
        times = [float(x) for x in a.args]
        (BUILD / "stills").mkdir(parents=True, exist_ok=True)
        with Pool(min(len(times), 11)) as pool:
            outs = pool.starmap(still, [(t, str(BUILD / "stills" / f"still_{t:07.2f}.png")) for t in times])
        print("\n".join(outs))
    elif a.cmd == "contact":
        step = float(a.args[1]) if len(a.args) > 1 else 0.5
        t0 = float(a.args[2]) if len(a.args) > 2 else None
        t1 = float(a.args[3]) if len(a.args) > 3 else None
        print(contact(a.args[0], step, t0=t0, t1=t1))
    elif a.cmd == "video":
        t0 = float(a.args[0]) if a.args else 0.0
        t1 = float(a.args[1]) if len(a.args) > 1 else DURATION
        video(t0, t1, a.workers, resume=a.resume)
