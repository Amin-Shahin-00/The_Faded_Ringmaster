"""Original score, synthesized. ONE waltz melody that changes with Silas:

  Act 1  cheerful circus waltz  - calliope, oom-pah brass, snare, glockenspiel (C major, 168 bpm)
  Act 2  broken music box       - same melody, slow, C minor, out of tune, winding down
  Act 3  dark heavy theme       - same melody in low strings + bass + slow drum (C minor, 84 bpm)

Output: build/audio/music.wav (48 kHz stereo float)
"""
import math, sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.timeline import DURATION, MONTAGE_BPM, MONTAGE_START, BEATS  # noqa: E402

SR = 48000
N = int(DURATION * SR) + SR
L = np.zeros(N, np.float32)
R = np.zeros(N, np.float32)
rng = np.random.default_rng(2024)

# ----------------------------------------------------------------------------- the theme
# (scale degree, beats). Degree 1 = tonic; 8 = tonic an octave up.
PHRASE_A = [[(3, 1), (5, 1), (8, 1)], [(7, 2), (5, 1)], [(6, 1), (4, 1), (6, 1)], [(5, 3)],
            [(4, 1), (6, 1), (9, 1)], [(8, 2), (6, 1)], [(5, 1), (3, 1), (2, 1)], [(1, 3)]]
PHRASE_B = [[(5, 1), (5, 1), (6, 1)], [(5, 2), (3, 1)], [(4, 1), (4, 1), (5, 1)], [(4, 2), (2, 1)],
            [(3, 1), (5, 1), (8, 1)], [(10, 2), (8, 1)], [(7, 1), (9, 1), (7, 1)], [(8, 3)]]
CHORDS_A = [1, 5, 4, 1, 4, 1, 5, 1]
CHORDS_B = [5, 1, 5, 5, 1, 6, 5, 1]
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]


def deg(d, scale):
    d -= 1
    return 12 * (d // 7) + scale[d % 7]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def triad(root_deg, scale, harmonic_v=False):
    out = [deg(root_deg, scale), deg(root_deg + 2, scale), deg(root_deg + 4, scale)]
    if harmonic_v and root_deg == 5 and scale is MINOR:
        out[1] += 1          # raised leading tone in the dominant (B natural)
    return out


# ----------------------------------------------------------------------------- instruments

def env(n, a=0.01, d=0.1, s=0.7, r=0.1, sr=SR):
    t = np.arange(n) / sr
    dur = n / sr
    e = np.ones(n, np.float32) * s
    ai = t < a
    e[ai] = t[ai] / max(a, 1e-4)
    di = (t >= a) & (t < a + d)
    e[di] = 1 - (1 - s) * (t[di] - a) / max(d, 1e-4)
    ri = t > dur - r
    e[ri] *= np.clip((dur - t[ri]) / max(r, 1e-4), 0, 1)
    return e


def lowpass(x, fc, order=2):
    sos = signal.butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def bandpass(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, min(hi, SR * 0.45)], "band", fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def calliope(f, dur, vel=1.0, detune=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 6.2 * t) * np.clip(t / 0.15, 0, 1)
    ph = 2 * np.pi * f * (1 + detune) * np.cumsum(vib) / SR
    x = np.sin(ph) + 0.55 * np.sin(2 * ph) + 0.35 * np.sin(3 * ph) + 0.18 * np.sin(4 * ph) + 0.08 * np.sin(6 * ph)
    breath = bandpass(rng.standard_normal(n).astype(np.float32), f * 1.5, f * 4) * 0.12
    return (x + breath) * env(n, 0.02, 0.08, 0.8, 0.06) * vel * 0.3


def brass(f, dur, vel=1.0, bright=1800):
    n = int(dur * SR)
    t = np.arange(n) / SR
    saw = 2 * ((f * t) % 1.0) - 1
    saw2 = 2 * ((f * 1.003 * t) % 1.0) - 1
    x = lowpass((saw + saw2) * 0.5, bright * (0.6 + 0.4 * vel))
    return x * env(n, 0.03, 0.1, 0.7, 0.08) * vel * 0.35


def music_box(f, dur, vel=1.0, detune_cents=0.0, decay=1.6):
    n = int(max(dur, decay) * SR)
    t = np.arange(n) / SR
    f = f * 2 ** (detune_cents / 1200)
    x = np.zeros(n, np.float32)
    for k, (m, a, dk) in enumerate([(1.0, 1.0, decay), (2.76, 0.35, decay * 0.4), (5.4, 0.18, decay * 0.2), (8.93, 0.08, decay * 0.1)]):
        x += a * np.sin(2 * np.pi * f * m * t + k) * np.exp(-t / dk)
    click = np.zeros(n, np.float32)
    click[:60] = rng.standard_normal(60) * np.exp(-np.arange(60) / 10) * 0.3
    return (x + click) * vel * 0.32


def strings(f, dur, vel=1.0, attack=0.35, bright=1400):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for dt in (-0.006, 0.0, 0.0055):
        vib = 1 + 0.004 * np.sin(2 * np.pi * (5.2 + dt * 40) * t + dt * 100)
        ph = f * (1 + dt) * np.cumsum(vib) / SR
        x += 2 * (ph % 1.0) - 1
    x = lowpass(x / 3, bright, 2)
    return x * env(n, attack, 0.2, 0.85, min(0.6, dur * 0.4)) * vel * 0.3


def bass(f, dur, vel=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    x = np.tanh(x * 1.5)
    return x * env(n, 0.01, 0.15, 0.6, 0.1) * vel * 0.4


def drum(dur=1.2, vel=1.0, f0=90, f1=45):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 18)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.0)
    x += lowpass(rng.standard_normal(n).astype(np.float32), 900) * np.exp(-t * 30) * 0.4
    return x * vel * 0.7


def snare(vel=1.0):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = bandpass(rng.standard_normal(n).astype(np.float32), 1500, 7000) * np.exp(-t * 22)
    x += np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.4
    return x * vel * 0.35


def glock(f, vel=1.0):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 3.9 * t)) * np.exp(-t * 4)
    return x * vel * 0.18


def add(x, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N or i + len(x) <= 0:
        return
    if i < 0:
        x = x[-i:]; i = 0
    x = x[:N - i]
    lg = gain * math.cos((pan + 1) * math.pi / 4)
    rg = gain * math.sin((pan + 1) * math.pi / 4)
    L[i:i + len(x)] += x * lg
    R[i:i + len(x)] += x * rg


def bars_of(phrases):
    out = []
    for ph in phrases:
        out += ph
    return out


# ----------------------------------------------------------------------------- sections

def act1_waltz(t0, bars, tonic=72, bpm=168.0, layers=("calliope", "brass", "snare", "glock", "bass"), vel=1.0, melody_start_bar=1,
               tempo_curve=None):
    """Oom-pah-pah waltz. Returns end time."""
    beat = 60.0 / bpm
    mel = bars_of([PHRASE_A, PHRASE_B, PHRASE_A, PHRASE_B])
    ch = CHORDS_A + CHORDS_B + CHORDS_A + CHORDS_B
    t = t0
    for b in range(bars):
        bt = beat if tempo_curve is None else beat * tempo_curve(b)
        mi = b - melody_start_bar
        chord_root = ch[mi % len(ch)] if mi >= 0 else 1
        tri = triad(chord_root, MAJOR)
        if "bass" in layers:
            add(bass(hz(tonic - 36 + tri[0]), bt * 0.9, 0.9 * vel), t, 0.9)
        if "brass" in layers:
            for k in (1, 2):
                for m in tri:
                    add(brass(hz(tonic - 12 + m), bt * 0.6, 0.55 * vel), t + k * bt, 0.5, pan=-0.3)
        if "snare" in layers:
            for k in (1, 2):
                add(snare(0.5 * vel), t + k * bt, 0.6, pan=0.2)
        if mi >= 0 and "calliope" in layers:
            tt = t
            for (d, beats) in mel[mi % len(mel)]:
                f = hz(tonic + deg(d, MAJOR))
                add(calliope(f, beats * bt * 0.95, vel), tt, 0.85, pan=0.1)
                add(calliope(f, beats * bt * 0.95, vel * 0.5, detune=0.004), tt + 0.012, 0.6, pan=-0.2)
                if "glock" in layers and beats >= 2:
                    add(glock(f * 2, vel), tt, 0.6, pan=0.4)
                tt += beats * bt
        t += 3 * bt
    return t


def broken_box(t0, phrase_bars, tonic=72, bpm=66.0, vel=0.9, wind_down=False, detune=18.0, gain=0.8):
    """Music box plays the theme in C minor, slow and out of tune. wind_down: tempo
    and pitch sag like a spring running out."""
    beat = 60.0 / bpm
    t = t0
    k = 0
    total = sum(sum(bt for _, bt in bar) for bar in phrase_bars)
    acc = 0
    for bar in phrase_bars:
        for (d, beats) in bar:
            u = acc / total
            stretch = 1.0 + (2.2 * u ** 2 if wind_down else 0.0)
            sag = -180 * u ** 2 if wind_down else 0.0
            cents = rng.normal(0, detune) + sag
            f = hz(tonic + deg(d, MINOR))
            add(music_box(f, beats * beat * stretch, vel * (1 - 0.4 * u if wind_down else 1.0), cents), t, gain, pan=0.15)
            if k % 3 == 0:   # a thin low note under it
                add(music_box(f / 4, beats * beat * stretch, vel * 0.45, cents * 0.5, decay=2.4), t, gain * 0.7, pan=-0.2)
            t += beats * beat * stretch
            acc += beats
            k += 1
    return t


def dark_theme(t0, bars, start_bar=0, tonic=48, melody=True, drums="one", brass_lead=False, ostinato=False, vel=1.0,
               strings_gain=1.0, melody_from=2):
    """Act 3: low strings carry the melody; bass + slow drum. Bar grid at 84 bpm."""
    beat = 60.0 / MONTAGE_BPM
    mel = bars_of([PHRASE_A, PHRASE_B, PHRASE_A, PHRASE_B])
    ch = CHORDS_A + CHORDS_B + CHORDS_A + CHORDS_B
    for b in range(bars):
        t = t0 + b * 3 * beat
        gb = start_bar + b
        mi = gb - melody_from
        root = ch[mi % len(ch)] if mi >= 0 else 1
        tri = triad(root, MINOR, harmonic_v=True)
        add(bass(hz(tonic - 12 + tri[0]), 3 * beat * 0.98, 0.9 * vel), t, 0.9)
        for m in tri:   # sustained pad
            add(strings(hz(tonic + m), 3 * beat * 1.02, 0.45 * vel * strings_gain, attack=0.6, bright=900), t, 0.55, pan=-0.35 + 0.35 * (m % 3))
        if drums in ("one", "all"):
            add(drum(1.6, 0.9 * vel), t, 0.9)
        if drums == "all":
            for k in (1, 2):
                add(drum(0.8, 0.5 * vel, f0=120, f1=70), t + k * beat, 0.7)
        if ostinato:
            for k in range(6):
                m = tri[k % 3] + 12
                add(strings(hz(tonic + m), beat * 0.45, 0.35 * vel, attack=0.02, bright=2200), t + k * beat / 2, 0.45, pan=0.3)
        if melody and mi >= 0:
            tt = t
            for (d, beats) in mel[mi % len(mel)]:
                f = hz(tonic + 12 + deg(d, MINOR) + (1 if (d % 7 == 0 and root == 5) else 0))
                add(strings(f, beats * beat * 0.98, 0.8 * vel * strings_gain, attack=0.15, bright=1800), tt, 0.8, pan=0.05)
                if brass_lead:
                    add(brass(f / 2, beats * beat * 0.9, 0.8 * vel, bright=900), tt, 0.7, pan=-0.05)
                tt += beats * beat


def drone(t0, t1, f, gain=0.3, bright=500, trem=0.0):
    n = int((t1 - t0) * SR)
    t = np.arange(n) / SR
    x = strings(f, t1 - t0, 1.0, attack=1.5, bright=bright)
    if trem:
        x = x * (1 - trem * 0.5 * (1 + np.sin(2 * np.pi * 4 * t)))
    add(x, t0, gain)


def swell(t0, dur, gain=0.4, rev=True):
    """Reverse-cymbal style noise swell (transition into the flashback)."""
    n = int(dur * SR)
    x = bandpass(rng.standard_normal(n).astype(np.float32), 2000, 12000)
    e = (np.arange(n) / n) ** 3
    add(x * e * 0.5, t0, gain, pan=-0.2)
    add(np.roll(x, 300) * e * 0.5, t0, gain, pan=0.2)


def hit(t0, gain=0.8):
    """Low orchestral hit: drum + string stab."""
    add(drum(2.5, 1.0, f0=70, f1=32), t0, gain)
    for m in (0, 3, 7, 12):
        add(strings(hz(36 + m), 1.2, 1.0, attack=0.01, bright=1200), t0, gain * 0.5)


def reverb(x, rt=2.2, wet=0.22, seed=3):
    r = np.random.default_rng(seed)
    n = int(SR * rt)
    t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-6.9 * t / rt)
    ir = signal.sosfilt(signal.butter(2, [150, 6000], "band", fs=SR, output="sos"), ir)
    ir[: int(0.02 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    y = signal.fftconvolve(x, ir)[: len(x)]
    return x + wet * y.astype(np.float32)


# ----------------------------------------------------------------------------- the cue sheet

def build():
    # S1 - broken music box under the cold open, swell into the flashback
    broken_box(0.8, PHRASE_A[:6], bpm=60, vel=0.8, detune=22, gain=0.7)
    drone(0.0, 17.5, hz(36), 0.18, bright=300)
    swell(15.8, 2.4, 0.5)
    # S2 - the waltz: one intro bar, then A B A + the start of B, ending exactly at 48.0
    act1_waltz(18.0, 28, bpm=168.0, vel=1.0)
    # S3 nights - same waltz thinning out, slowing down
    act1_waltz(48.0, 2, bpm=168.0, vel=0.95, melody_start_bar=-27)
    act1_waltz(50.6, 2, bpm=140.0, layers=("calliope", "bass"), vel=0.6, melody_start_bar=-1)
    t = 53.2
    for (d, b) in [(3, 1.5), (5, 1.5), (8, 3), (7, 4)]:   # a lonely calliope, unresolved
        add(calliope(hz(72 + deg(d, MAJOR)), b * 0.45, 0.45), t, 0.6)
        t += b * 0.45
    # S3 fall - broken box in minor, then it winds down in the storm
    drone(56.0, 71.0, hz(36), 0.16, bright=320)
    broken_box(56.4, PHRASE_A[:4], bpm=64, vel=0.7, detune=26, gain=0.65)
    hit(61.0 + 1.0, 0.25)
    broken_box(65.2, PHRASE_B[:3], bpm=64, vel=0.7, detune=30, gain=0.6)
    broken_box(71.0, PHRASE_A[:6], bpm=90, vel=0.8, detune=30, gain=0.65, wind_down=True)
    drone(70.0, 78.0, hz(31), 0.22, bright=250, trem=0.4)
    # S4 - near silence; music-box fragments; the snap; strings creep in
    drone(78.0, 99.0, hz(36), 0.14, bright=260)
    for (t0, notes) in [(80.2, [(5, 1), (3, 1)]), (84.6, [(6, 1), (4, 1), (6, 2)]), (90.5, [(5, 3)])]:
        broken_box(t0, [notes], bpm=56, vel=0.55, detune=35, gain=0.55)
    hit(BEATS["s4_cane_snap"], 0.55)
    for i, m in enumerate((0, 1, 3, 6, 7)):     # dark cluster rising under the smile
        n0 = 99.4 + i * 0.6
        add(strings(hz(36 + m), 105.0 - n0, 0.6, attack=2.0, bright=900), n0, 1.0, pan=-0.4 + 0.2 * i)
    # S5 + S6 + S7 - the dark theme on the 84 bpm grid that lands bar 16 on 140.0
    bar = 3 * 60.0 / MONTAGE_BPM
    g0 = MONTAGE_START - 16 * bar                  # 105.714
    dark_theme(g0, 12, start_bar=0, melody=True, drums="one", vel=0.75, strings_gain=0.8, melody_from=2)
    dark_theme(g0 + 12 * bar, 4, start_bar=12, melody=True, drums="one", vel=0.95, strings_gain=1.1, melody_from=2)  # the slow walk
    dark_theme(MONTAGE_START, 14, start_bar=16, melody=True, drums="all", brass_lead=True, ostinato=True, vel=1.0, melody_from=16)
    # S7 finale: grand but dark, then silence at the spotlight snap
    dark_theme(170.0, 6, start_bar=30, melody=True, drums="one", brass_lead=True, vel=0.95, strings_gain=1.2, melody_from=30)
    add(strings(hz(48), 1.0, 0.0), 184.0, 0.0)
    # title: the theme's first notes on the broken music box, then it fades
    broken_box(185.3, PHRASE_A[:2], bpm=58, vel=0.7, detune=20, gain=0.6)

    mixL = reverb(L, 2.4, 0.25, 1)
    mixR = reverb(R, 2.4, 0.25, 2)
    st = np.stack([mixL, mixR], 1)
    # hard cut for the spotlight snap: silence from 184.0 (short 8 ms fade) until the title
    i0, i1 = int(184.0 * SR), int(185.25 * SR)
    fade = int(0.008 * SR)
    st[i0:i0 + fade] *= np.linspace(1, 0, fade)[:, None]
    st[i0 + fade:i1] = 0
    st = st[: int(DURATION * SR)]
    st /= max(1e-6, np.max(np.abs(st))) / 0.8
    out = ROOT / "build" / "audio"
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / "music.wav", st.astype(np.float32), SR, subtype="FLOAT")
    print("music ->", out / "music.wav", f"{len(st) / SR:.1f}s")


if __name__ == "__main__":
    build()
