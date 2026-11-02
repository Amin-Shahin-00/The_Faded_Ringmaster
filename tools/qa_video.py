"""Automatic QA on the rendered picture: frame-to-frame jump/flicker detector.

Decodes the video at 192x108 grey, measures the mean absolute difference between
consecutive frames, and flags spikes that are not at a planned cut, transition,
lightning flash or the spotlight snap. Also reports frame count and duration.
"""
import subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.timeline import FPS, SHOTS, TRANSITIONS, BEATS, DURATION  # noqa: E402
import imageio_ffmpeg  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
w, h = 192, 108
video = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "video.mp4"
raw = subprocess.run([FF, "-loglevel", "error", "-i", str(video), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                     capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
n = len(frames)
print(f"frames: {n}  duration: {n / FPS:.3f}s  (timeline {DURATION}s)")
diff = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
expected = set()
for (_, _, a, b) in SHOTS:
    for f in range(int(round(a * FPS)) - 1, int(round(a * FPS)) + 2):
        expected.add(f)
for (tc, d, k) in TRANSITIONS:
    for f in range(int((tc - d / 2) * FPS) - 1, int((tc + d / 2) * FPS) + 2):
        expected.add(f)
flashes = BEATS["s1_lightning"] + BEATS["s3_thunder"] + BEATS["s3_bursts"] + [BEATS["s7_spot_off"], BEATS["s3_rip"]]
for t in flashes:
    for f in range(int(t * FPS) - 2, int((t + 0.7) * FPS)):
        expected.add(f)
med = np.median(diff)
thr = max(6.0, med * 8)
bad = [(i + 1, d) for i, d in enumerate(diff) if d > thr and (i + 1) not in expected]
print(f"median frame diff {med:.2f}, threshold {thr:.2f}")
print(f"unexpected jumps: {len(bad)}")
for f, d in bad[:60]:
    print(f"  frame {f:5d}  t={f / FPS:8.3f}s  diff={d:6.2f}")
# isolated single-frame flicker: a frame very different from BOTH neighbours while they match each other
flick = []
for i in range(1, n - 1):
    a, b, c = frames[i - 1], frames[i], frames[i + 1]
    ab, bc, ac = np.abs(a - b).mean(), np.abs(b - c).mean(), np.abs(a - c).mean()
    if ab > 4 and bc > 4 and ac < 0.35 * min(ab, bc) and i not in expected:
        flick.append((i, ab, bc, ac))
print(f"single-frame flickers: {len(flick)}")
for i, ab, bc, ac in flick[:40]:
    print(f"  frame {i:5d} t={i / FPS:8.3f}s  ({ab:.1f}, {bc:.1f}, {ac:.1f})")
