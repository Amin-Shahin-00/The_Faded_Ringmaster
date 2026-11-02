"""Probe Kokoro male voices: measure median F0 so we can pick the deepest narrator."""
import sys, numpy as np, soundfile as sf
from pathlib import Path
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parents[1]
k = Kokoro(str(ROOT / "assets/tts/kokoro-v1.0.onnx"), str(ROOT / "assets/tts/voices-v1.0.bin"))
text = "They used to call me the happiest man alive. Funny thing about happiness."
out = ROOT / "build/voice_probe"
out.mkdir(parents=True, exist_ok=True)


def f0_median(x, sr):
    hop, win = 256, 1024
    f0s = []
    for i in range(0, len(x) - win, hop):
        fr = x[i:i + win] * np.hanning(win)
        if np.sqrt(np.mean(fr ** 2)) < 0.02:
            continue
        ac = np.correlate(fr, fr, "full")[win - 1:]
        lo, hi = int(sr / 300), int(sr / 55)
        lag = lo + np.argmax(ac[lo:hi])
        if ac[lag] > 0.3 * ac[0]:
            f0s.append(sr / lag)
    return float(np.median(f0s)) if f0s else 0.0


for v in ["am_onyx", "bm_george", "bm_lewis", "am_fenrir", "am_michael", "bm_daniel", "am_eric", "am_adam"]:
    try:
        a, sr = k.create(text, voice=v, speed=0.85, lang="en-us" if v.startswith("a") else "en-gb")
    except Exception as e:
        print(v, "ERR", e); continue
    sf.write(out / f"{v}.wav", a, sr)
    print(f"{v:12s} dur={len(a)/sr:5.2f}s f0~{f0_median(a, sr):6.1f}Hz")
