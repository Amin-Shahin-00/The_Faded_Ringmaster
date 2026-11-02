"""Final mix: voiceover over music + effects, with ducking, limiting and -16 LUFS loudness.

Also writes output/the_faded_ringmaster.srt and prints a VO clarity report.
"""
import json, math, re, subprocess, sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.timeline import VO, SCENES, DURATION, LAUGH_START, LAUGH_END  # noqa: E402
import imageio_ffmpeg  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
A = ROOT / "build" / "audio"
OUT = ROOT / "output"

# stem levels (linear) and ducking depth
G_VO, G_MUSIC, G_BEDS, G_SFX = 1.0, 0.30, 0.42, 0.5
DUCK_MUSIC_DB, DUCK_BEDS_DB = -8.0, -4.0
TARGET_LUFS, TRUE_PEAK = -16.0, -1.5


def load(name):
    x, sr = sf.read(A / name, dtype="float32")
    assert sr == SR
    n = int(DURATION * SR)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    return np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]


def ramp_mask(intervals, n, ramp=0.18):
    m = np.zeros(n, np.float32)
    for a, b in intervals:
        m[max(0, int(a * SR)):min(n, int(b * SR))] = 1.0
    k = int(ramp * SR)
    kernel = np.ones(k, np.float32) / k
    return np.clip(np.convolve(m, kernel, mode="same"), 0, 1)


def limiter(x, ceiling=0.89, look=0.005, release=0.08):
    peak = np.max(np.abs(x), axis=1)
    w = int(look * SR)
    peak = ndimage.maximum_filter1d(peak, size=2 * w + 1)
    g = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    # smooth gain: fast attack (already looked ahead), slow release
    a = math.exp(-1.0 / (release * SR))
    out = np.empty_like(g)
    cur = 1.0
    for i in range(0, len(g), 64):              # block-wise one-pole release
        blk = g[i:i + 64].min()
        cur = blk if blk < cur else blk + (cur - blk) * a ** 64
        out[i:i + 64] = cur
    return x * out[:, None]


def main():
    n = int(DURATION * SR)
    durs = json.loads((ROOT / "build" / "vo" / "durations.json").read_text())
    vo = np.zeros(n, np.float32)
    intervals = []
    report = []
    for sid, cid, t0, text in VO:
        x, sr = sf.read(ROOT / "build" / "vo" / f"{cid}.wav", dtype="float32")
        i = int(t0 * SR)
        vo[i:i + len(x)] += x[: n - i]
        t1 = t0 + len(x) / SR
        intervals.append((t0 - 0.12, t1 + 0.3))
        sc = next(s for s in SCENES if s[0] == sid)
        report.append((cid, t0, t1, sc[1], sc[2], sc[1] <= t0 and t1 <= sc[2]))
    # the low laugh in Scene 4 (faded out so it ends inside the scene)
    lx, _ = sf.read(ROOT / "build" / "vo" / "laugh.wav", dtype="float32")
    ln = int((LAUGH_END - LAUGH_START) * SR)
    lx = lx[:ln]
    f = min(len(lx), int(0.9 * SR))
    lx[-f:] *= np.linspace(1, 0, f)
    i = int(LAUGH_START * SR)
    vo[i:i + len(lx)] += lx * 0.85
    vo_st = np.stack([vo, vo], 1) * G_VO

    duck = ramp_mask(intervals, n)
    music = load("music.wav") * G_MUSIC * (10 ** (DUCK_MUSIC_DB * duck / 20))[:, None]
    beds = load("beds.wav") * G_BEDS * (10 ** (DUCK_BEDS_DB * duck / 20))[:, None]
    sfx = load("sfx.wav") * G_SFX
    mix = vo_st + music + beds + sfx
    mix = limiter(mix)
    pre = A / "premix.wav"
    sf.write(pre, mix.astype(np.float32), SR, subtype="FLOAT")

    # two-pass loudness normalisation (EBU R128)
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(pre), "-af",
                        f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.findall(r"\{[^{}]*\}", r.stderr, re.S)[-1])
    af = (f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    final = A / "mix.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(pre), "-af", af, "-ar", str(SR), "-c:a", "pcm_s24le", str(final)], check=True)
    r2 = subprocess.run([FFMPEG, "-hide_banner", "-i", str(final), "-af", f"loudnorm=I={TARGET_LUFS}:print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True)
    m2 = json.loads(re.findall(r"\{[^{}]*\}", r2.stderr, re.S)[-1])
    print(f"final loudness {m2['input_i']} LUFS, true peak {m2['input_tp']} dBTP")

    # VO clarity: voice level vs everything else while each line plays
    bg = music + beds + sfx
    print("\nVO chunk     start    end    scene        inside  VO-vs-bg dB")
    for (cid, t0, t1, a, b, ok), _ in zip(report, VO):
        i0, i1 = int(t0 * SR), int(t1 * SR)
        v = np.sqrt(np.mean(vo_st[i0:i1] ** 2) + 1e-12)
        g = np.sqrt(np.mean(bg[i0:i1] ** 2) + 1e-12)
        print(f"{cid:6s} {t0:8.2f} {t1:7.2f}   {a:6.1f}-{b:6.1f}   {'yes' if ok else 'NO!'}   {20 * math.log10(v / g):6.1f}")

    # subtitles
    OUT.mkdir(exist_ok=True)

    def ts(t):
        h, rem = divmod(t, 3600); mi, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(mi):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"
    lines = []
    for k, (sid, cid, t0, text) in enumerate(VO, 1):
        t1 = t0 + durs[cid]
        lines.append(f"{k}\n{ts(t0)} --> {ts(t1 + 0.25)}\n{text}\n")
    (OUT / "the_faded_ringmaster.srt").write_text("\n".join(lines), encoding="utf-8")
    print("\nsrt ->", OUT / "the_faded_ringmaster.srt")


if __name__ == "__main__":
    main()
