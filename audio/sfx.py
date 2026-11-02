"""Sound effects, synthesized and placed from config.timeline (BEATS / SHOTS).

Output: build/audio/sfx.wav (stereo) and build/audio/beds.wav (rain/crowd/ambience
beds, ducked a little under the voice by the mixer)."""
import math, sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.timeline import DURATION, BEATS, SHOTS, MONTAGE_BPM, MONTAGE_START  # noqa: E402

SR = 48000
N = int(DURATION * SR) + SR
rng = np.random.default_rng(77)


class Bus:
    def __init__(self):
        self.L = np.zeros(N, np.float32)
        self.R = np.zeros(N, np.float32)

    def add(self, x, t0, gain=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= N:
            return
        x = x[: N - i]
        self.L[i:i + len(x)] += x * gain * math.cos((pan + 1) * math.pi / 4)
        self.R[i:i + len(x)] += x * gain * math.sin((pan + 1) * math.pi / 4)


FX, BEDS = Bus(), Bus()


def noise(n):
    return rng.standard_normal(n).astype(np.float32)


def bp(x, lo, hi, o=2):
    return signal.sosfilt(signal.butter(o, [lo, min(hi, 23000)], "band", fs=SR, output="sos"), x).astype(np.float32)


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, "low", fs=SR, output="sos"), x).astype(np.float32)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, "high", fs=SR, output="sos"), x).astype(np.float32)


def fade(x, a=0.05, b=0.05):
    n = len(x)
    e = np.ones(n, np.float32)
    na, nb = int(a * SR), int(b * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nb: e[-nb:] = np.linspace(1, 0, nb)
    return x * e


def t_arr(dur):
    return np.arange(int(dur * SR)) / SR


# ----------------------------------------------------------------------------- sounds

def rain_bed(dur, heavy=1.0, muffled=False):
    n = int(dur * SR)
    x = bp(noise(n), 400, 9000) * 0.25 * heavy
    x += hp(noise(n), 3000) * 0.08 * heavy
    drops = np.zeros(n, np.float32)
    k = int(dur * 220 * heavy)
    idx = rng.integers(0, n - 400, k)
    for i in idx:
        L = rng.integers(60, 300)
        drops[i:i + L] += noise(L) * np.exp(-np.arange(L) / (L / 5)) * rng.uniform(0.1, 0.5)
    x += bp(drops, 800, 7000) * 0.6
    if muffled:
        x = lp(x, 900) * 1.6
    return fade(x, 0.6, 0.6)


def thunder(dur=4.0, close=0.7):
    t = t_arr(dur)
    x = lp(noise(len(t)), 180) * 3.0
    crack = bp(noise(len(t)), 300, 4000) * np.exp(-t * 12) * close
    env = (1 - np.exp(-t * 14)) * np.exp(-t * 0.9) * (1 + 0.5 * np.sin(t * 7) * np.exp(-t))
    return (x * env + crack) * 0.8


def applause(dur, density=1.0):
    n = int(dur * SR)
    x = np.zeros(n, np.float32)
    k = int(dur * 900 * density)
    idx = rng.integers(0, n - 800, k)
    for i in idx:
        L = rng.integers(200, 700)
        x[i:i + L] += noise(L) * np.exp(-np.arange(L) / rng.uniform(25, 70)) * rng.uniform(0.2, 1.0)
    return fade(bp(x, 700, 6000) * 0.25, 0.4, 0.8)


def laughter(dur, voices=14, kids=0.0, density=1.0):
    """Crowd laughter: formant-filtered 'ha' bursts from many voices."""
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    for v in range(voices):
        kid = rng.random() < kids
        f0 = rng.uniform(260, 420) if kid else rng.uniform(100, 230)
        rate = rng.uniform(4.5, 6.5)
        start = rng.uniform(0, dur * 0.25)
        length = rng.uniform(dur * 0.4, dur * 0.95) * density
        t = t_arr(dur)
        gate = ((t > start) & (t < start + length)).astype(np.float32)
        puls = np.clip(np.sin(2 * np.pi * rate * t + rng.random() * 6), 0, 1) ** 1.5
        vib = 1 + 0.03 * np.sin(2 * np.pi * 5 * t)
        ph = 2 * np.pi * f0 * np.cumsum(vib * (1 + 0.15 * np.exp(-((t - start) % (1 / rate)) * 8))) / SR
        src = np.sign(np.sin(ph)) * 0.5 + 0.35 * noise(n)            # buzzy + breathy
        f1, f2 = (850, 1500) if not kid else (1000, 1900)
        y = bp(src, f1 * 0.8, f1 * 1.25) + 0.6 * bp(src, f2 * 0.85, f2 * 1.2)
        env = gate * puls * np.minimum(1, (t - start) * 3) * np.exp(-np.clip(t - start, 0, None) / (length + 0.5))
        out += y * env * rng.uniform(0.4, 1.0)
    return fade(out * 0.12, 0.05, 0.6)


def murmur(dur, level=1.0):
    n = int(dur * SR)
    x = bp(noise(n), 200, 1200) * 0.15
    m = lp(np.abs(noise(n)), 3) * 4
    return fade(x * (0.5 + m) * level, 1.0, 1.0)


def tear(dur=1.5):
    """Canvas ripping: crackling noise with fast amplitude modulation, rising."""
    t = t_arr(dur)
    am = (np.abs(lp(noise(len(t)), 60)) * 6) ** 1.5
    x = bp(noise(len(t)), 600, 7000) * am
    sweep = np.sin(2 * np.pi * np.cumsum(300 + 1800 * t / dur) / SR) * 0.05
    env = np.minimum(1, t * 8) * np.exp(-np.maximum(0, t - dur * 0.7) * 6)
    return (x + sweep) * env * 0.5


def bulb_pop():
    t = t_arr(0.9)
    x = bp(noise(len(t)), 1500, 9000) * np.exp(-t * 40) * 1.2
    tink = np.zeros(len(t), np.float32)
    for k in range(6):
        f = rng.uniform(3000, 7000); t0 = rng.uniform(0.04, 0.35)
        m = t > t0
        tink[m] += np.sin(2 * np.pi * f * (t[m] - t0)) * np.exp(-(t[m] - t0) * 25) * 0.15
    zap = np.sin(2 * np.pi * 120 * t) * np.exp(-t * 20) * 0.2
    return x + tink + zap


def hammer():
    t = t_arr(0.6)
    thunk = np.sin(2 * np.pi * 140 * t * (1 - 0.4 * t)) * np.exp(-t * 18)
    click = bp(noise(len(t)), 2000, 8000) * np.exp(-t * 90)
    ring = np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 12) * 0.15
    return (thunk + click + ring) * 0.8


def crack_snap():
    t = t_arr(0.7)
    x = bp(noise(len(t)), 800, 9000) * np.exp(-t * 35) * 1.4
    x += bp(noise(len(t)), 200, 1200) * np.exp(-t * 12) * 0.5
    splinter = np.zeros(len(t), np.float32)
    for k in range(10):
        t0 = rng.uniform(0.02, 0.2); m = t > t0
        splinter[m] += bp(noise(m.sum()), 3000, 9000) * np.exp(-(t[m] - t0) * 80) * 0.2
    return x + splinter


def footstep(wet=True, heavy=1.0):
    t = t_arr(0.5)
    thud = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 25) * heavy
    x = thud + bp(noise(len(t)), 300, 2000) * np.exp(-t * 30) * 0.3
    if wet:
        x += bp(noise(len(t)), 1200, 7000) * np.exp(-t * 14) * 0.45 * (1 + 0.6 * np.sin(t * 60))
    return x * 0.5


def thunk(f=180, wood=True):
    t = t_arr(0.35)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 22) + bp(noise(len(t)), 1200, 5000) * np.exp(-t * 70) * 0.6
    return x * 0.6


def whoosh(dur=0.7, up=True):
    t = t_arr(dur)
    env = np.sin(np.pi * t / dur) ** 2
    x = noise(len(t))
    out = np.zeros_like(x)
    seg = len(x) // 8
    for k in range(8):   # moving band
        fc = 400 + 2600 * (k / 7 if up else 1 - k / 7)
        out[k * seg:(k + 1) * seg] = bp(x, fc * 0.7, fc * 1.4)[k * seg:(k + 1) * seg]
    return out * env * 0.5


def pen(dur=0.8):
    t = t_arr(dur)
    am = 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 9 * t + np.sin(t * 13)))
    return bp(noise(len(t)), 2500, 9000) * am * 0.15 * fade(np.ones(len(t), np.float32), 0.05, 0.1)


def brush(dur=0.6):
    t = t_arr(dur)
    return bp(noise(len(t)), 500, 4000) * np.sin(np.pi * t / dur) * 0.25


def spot_snap():
    t = t_arr(1.4)
    clunk = np.sin(2 * np.pi * 85 * t) * np.exp(-t * 10) * 1.0 + bp(noise(len(t)), 600, 4000) * np.exp(-t * 50)
    boom = lp(noise(len(t)), 90) * np.exp(-t * 2.5) * 2.0
    return (clunk + boom) * 0.7


def hum(dur, f=60):
    t = t_arr(dur)
    return (np.sin(2 * np.pi * f * t) * 0.5 + np.sin(2 * np.pi * 2 * f * t) * 0.3 + np.sin(2 * np.pi * 3 * f * t) * 0.1) * 0.04


def water(dur):
    n = int(dur * SR)
    x = lp(noise(n), 500) * (0.6 + 0.4 * np.sin(np.arange(n) / SR * 2 * np.pi * 0.4))
    return fade(x * 0.25, 1, 1)


def wind(dur, level=1.0):
    n = int(dur * SR)
    m = 0.5 + 0.5 * lp(noise(n), 1.5) * 8
    return fade(bp(noise(n), 200, 1500) * np.clip(m, 0, 2) * 0.25 * level, 1, 1)


def coin():
    t = t_arr(0.6)
    return (np.sin(2 * np.pi * 3200 * t) + 0.6 * np.sin(2 * np.pi * 4700 * t)) * np.exp(-t * 9) * 0.15


def tick():
    t = t_arr(0.12)
    return (np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 60) + bp(noise(len(t)), 2000, 6000) * np.exp(-t * 90)) * 0.4


def shot(name):
    s = next(x for x in SHOTS if x[1] == name)
    return s[2], s[3]


# ----------------------------------------------------------------------------- placement

def build():
    # --- Scene 1: storm outside, drips inside
    BEDS.add(rain_bed(8.4, 1.2), 0.0, 0.9)
    BEDS.add(rain_bed(11.0, 0.7), 7.0, 0.7)
    BEDS.add(wind(18, 0.8), 0.0, 0.7)
    for t0 in BEATS["s1_lightning"]:
        FX.add(thunder(4.5, 0.9 if t0 < 5 else 0.5), t0 + 0.25, 0.9)
    for k in range(10):
        FX.add(thunk(1400 + 200 * (k % 3)) * 0.25, 8.6 + k * 0.95, 0.5, pan=0.1)   # drips from the brim
    # --- Scene 2: the crowd
    BEDS.add(murmur(30, 1.2), 18.0, 0.8)
    BEDS.add(applause(6.0, 1.0), 18.2, 0.8)
    BEDS.add(applause(3.0, 1.4), BEATS["s2_bow_hat"] + 0.6, 0.9)
    BEDS.add(applause(3.0, 1.2), BEATS["s2_cannon_up"] + 0.1, 0.85)
    FX.add(thunk(90) * 1.5, 29.5 + 0.55, 0.6)                     # cannon lifted off the floor
    for t0 in BEATS["s2_knives"]:
        FX.add(whoosh(0.25), t0 - 0.26, 0.4, pan=0.4)
        FX.add(thunk(220), t0, 0.8, pan=0.5)
    BEDS.add(applause(2.5, 1.0), BEATS["s2_knives"][-1] + 0.3, 0.8)
    FX.add(whoosh(0.4, up=False), BEATS["s2_pip_slip"], 0.5)
    FX.add(thunk(80) * 1.4, BEATS["s2_pip_slip"] + 0.42, 0.9)
    for k in range(3):
        FX.add(thunk(300 + 60 * k) * 0.5, BEATS["s2_pip_slip"] + 0.75 + k * 0.22, 0.6, pan=-0.3 + 0.3 * k)
    BEDS.add(laughter(4.0, voices=22, kids=0.8), BEATS["s2_pip_slip"] + 0.45, 1.0)
    FX.add(whoosh(0.5), BEATS["s2_peanut_toss"], 0.3, pan=0.3)
    BEDS.add(laughter(3.5, voices=10, kids=0.6), BEATS["s2_peanut_toss"] + 0.9, 0.7)
    BEDS.add(applause(4.0, 1.6), 46.0, 1.0)
    for i in range(11):                                            # Silas's strut steps
        FX.add(footstep(False, 0.6), 18.0 + i * 0.3 + 0.216, 0.25)
    # --- Scene 3: the nights empty
    BEDS.add(applause(2.8, 1.2), 48.0, 0.8)
    BEDS.add(applause(2.6, 0.12), 50.6, 0.7)
    FX.add(thunk(400) * 0.3, 54.6, 0.4)                             # a single seat creak in the empty tent
    FX.add(brush(0.5), BEATS["s3_paste"] + 0.2, 0.6, pan=0.3)
    FX.add(brush(0.5), BEATS["s3_paste"] + 0.8, 0.6, pan=0.1)
    FX.add(brush(0.6), BEATS["s3_paste"] + 1.4, 0.6, pan=0.3)
    for t0 in BEATS["s3_hammer"]:
        FX.add(hammer(), t0, 1.0, pan=0.2)
    BEDS.add(wind(6, 0.5), 65.0, 0.5)
    for k, (t0, sd, n, w) in enumerate([(65.4, 0.5, 11, 1.2), (67.2, 0.46, 8, 0.7), (69.0, 0.4, 5, 0.5)]):
        for i in range(n):
            FX.add(footstep(False, w), t0 + i * sd + sd * 0.72, 0.3, pan=-0.2 + 0.05 * i)
    BEDS.add(wind(7.5, 1.6), 70.5, 0.9)
    BEDS.add(rain_bed(7.5, 1.4), 71.0, 0.8)
    for t0 in BEATS["s3_thunder"]:
        FX.add(thunder(4.0, 1.0), t0 + 0.2, 1.0)
    FX.add(tear(1.6), BEATS["s3_rip"], 1.0, pan=-0.2)
    for i, t0 in enumerate(BEATS["s3_bursts"]):
        FX.add(bulb_pop(), t0, 0.7, pan=-0.6 + 0.24 * i)
    # --- Scene 4: rain on the trailer roof, bulb buzz, the snap
    BEDS.add(rain_bed(27.5, 0.8, muffled=True), 77.6, 0.9)
    BEDS.add(hum(27, 60), 78.0, 0.8)
    for k in range(3):
        FX.add(brush(0.7) * 0.6, 84.0 + k * 1.3, 0.5)              # rag wipes
    FX.add(crack_snap(), BEATS["s4_cane_snap"], 1.0)
    FX.add(thunk(160) * 0.7, BEATS["s4_cane_snap"] + 0.55, 0.6, pan=-0.3)   # shaft hits the floor
    # --- Scene 5: docks / bar / corner / walk
    BEDS.add(rain_bed(9.5, 1.0), 104.8, 0.8)
    BEDS.add(water(9.5), 105.0, 0.7)
    FX.add(thunk(110) * 1.3, 105.0 + 2.6, 0.8, pan=0.4)             # crate set down
    for i in range(3):
        FX.add(footstep(True, 0.9), BEATS["s5_steps_bruno"] + i * 0.62 + 0.45, 0.6, pan=-0.4)
    BEDS.add(murmur(9.0, 0.8), 113.8, 0.7)
    for t0 in BEATS["s5_darts"]:
        FX.add(whoosh(0.2), t0 - 0.17, 0.3, pan=0.3)
        FX.add(thunk(260), t0, 0.7, pan=0.5)
        FX.add(coin(), t0 + 0.32, 0.6, pan=-0.3)
    BEDS.add(rain_bed(9.0, 1.1), 122.0, 0.8)
    for i in range(3):
        FX.add(footstep(True, 0.9), 123.5 + i * 0.62 + 0.45, 0.6, pan=-0.3)
    BEDS.add(rain_bed(9.5, 0.9), 130.6, 0.7)
    sd = 92.0 / ((2300 - 860) / 9.0)
    for i in range(int(9 / sd)):                                     # slow-motion steps, deep and wet
        x = footstep(True, 1.4)
        x = lp(np.concatenate([x, np.zeros(int(0.3 * SR), np.float32)]), 1200) * 1.6
        FX.add(x, 131.0 + i * sd + 0.2, 0.55, pan=0.0)
    # --- Scene 6: montage
    for t0 in BEATS["s6_taps"]:
        FX.add(tick(), t0, 0.6, pan=0.4)
    for t0 in BEATS["s6_sign"]:
        FX.add(pen(0.8), t0, 0.6, pan=-0.2)
    beat = 60.0 / MONTAGE_BPM
    a, b = shot("paint")
    for k in range(3):
        for j in range(3):
            FX.add(brush(0.45), a + k * 4 * beat + 0.35 + j * 0.6, 0.5, pan=-0.2 + 0.2 * j)
    a, b = shot("papers")
    for k in range(3):
        FX.add(whoosh(0.8), a + k * 3 * beat, 0.7)
    a, b = shot("map")
    for k in range(22):
        FX.add(thunk(140) * 0.5, a + 0.15 + k * (b - a - 1.2) / 22, 0.35, pan=-0.5 + k / 22)
    # --- Scene 7: silence of the owners, spotlight hum, the snap
    BEDS.add(hum(14, 50) * 1.5, 170.0, 0.8)
    FX.add(spot_snap(), BEATS["s7_spot_off"], 1.0)

    for bus, name in ((FX, "sfx.wav"), (BEDS, "beds.wav")):
        st = np.stack([bus.L, bus.R], 1)[: int(DURATION * SR)]
        # the spotlight snap kills the hum and beds instantly
        if name == "beds.wav":
            i0 = int(BEATS["s7_spot_off"] * SR)
            st[i0:] = 0
        out = ROOT / "build" / "audio"
        out.mkdir(parents=True, exist_ok=True)
        sf.write(out / name, st.astype(np.float32), SR, subtype="FLOAT")
        print(name, f"peak {np.max(np.abs(st)):.2f}")


if __name__ == "__main__":
    build()
