"""Voiceover generation.

If ELEVENLABS_API_KEY is set, each chunk is generated with ElevenLabs; otherwise the
local Kokoro-82M model is used (voice VOICE_BLEND below). Every chunk is generated
separately, then processed: pitch lowered with formants preserved, warmth EQ, light
saturation, compression and a small room reverb.

Output: build/vo/<chunk>.wav (48 kHz mono, processed) + build/vo/durations.json
"""
import json, os, subprocess, sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.timeline import VO  # noqa: E402
import imageio_ffmpeg  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OUT = ROOT / "build" / "vo"
SR = 48000

# --- voice settings (change the voice here) ---------------------------------
VOICE_BLEND = {"am_onyx": 0.8, "bm_lewis": 0.2}   # deepest Kokoro voices, blended
SPEED = 0.80                                       # slower, deliberate delivery
PITCH_SEMITONES = -1.6                             # lower slightly, formants kept
LAUGH_TEXT = "Hm. hm. hm. Heh heh heh. Ha. ha. ha. ha. hah..."


def kokoro_tts(text):
    from kokoro_onnx import Kokoro
    k = kokoro_tts.k = getattr(kokoro_tts, "k", None) or Kokoro(
        str(ROOT / "assets/tts/kokoro-v1.0.onnx"), str(ROOT / "assets/tts/voices-v1.0.bin"))
    style = sum(k.get_voice_style(v) * w for v, w in VOICE_BLEND.items())
    a, sr = k.create(text, voice=style, speed=SPEED, lang="en-us")
    return np.asarray(a, np.float32), sr


def elevenlabs_tts(text):
    import urllib.request
    key = os.environ["ELEVENLABS_API_KEY"]
    voice = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # "Adam", deep narrator
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_44100",
        data=json.dumps({"text": text, "model_id": "eleven_multilingual_v2",
                         "voice_settings": {"stability": 0.6, "similarity_boost": 0.8, "style": 0.3}}).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"})
    pcm = urllib.request.urlopen(req).read()
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768, 44100


def ffmpeg_filter(x, sr, chain):
    """Run mono float audio through an ffmpeg filter chain, return 48k float."""
    tmp_in, tmp_out = OUT / "_in.wav", OUT / "_out.wav"
    sf.write(tmp_in, x, sr, subtype="FLOAT")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(tmp_in), "-af", chain,
                    "-ar", str(SR), "-ac", "1", "-c:a", "pcm_f32le", str(tmp_out)], check=True)
    y, _ = sf.read(tmp_out, dtype="float32")
    return y


def room_ir(sr, rt60=0.55, seed=7):
    rng = np.random.default_rng(seed)
    n = int(sr * rt60 * 1.2)
    t = np.arange(n) / sr
    ir = rng.standard_normal(n) * np.exp(-6.9 * t / rt60)
    ir = signal.sosfilt(signal.butter(2, [180, 5000], "band", fs=sr, output="sos"), ir)
    for d, g in [(0.011, 0.5), (0.019, 0.35), (0.027, 0.3), (0.041, 0.22)]:   # early reflections
        ir[int(d * sr)] += g * 4
    ir[:int(0.006 * sr)] = 0
    return ir / np.sqrt(np.sum(ir ** 2))


def trim(x, thr=0.01, pad=0.04):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    a, b = max(0, idx[0] - int(pad * SR)), min(len(x), idx[-1] + int(pad * 2 * SR))
    return x[a:b]


def process(x, sr):
    ratio = 2 ** (PITCH_SEMITONES / 12)
    chain = (f"rubberband=pitch={ratio:.4f}:formant=preserved:transients=smooth,"
             "highpass=f=55,equalizer=f=110:t=q:w=0.9:g=3.5,equalizer=f=260:t=q:w=1.2:g=1.5,"
             "equalizer=f=3200:t=q:w=1.4:g=-2.5,equalizer=f=7500:t=q:w=1:g=-3,"
             "acompressor=threshold=-22dB:ratio=3:attack=8:release=160:makeup=3")
    y = ffmpeg_filter(x, sr, chain)
    y = np.tanh(y * 1.6) / np.tanh(1.6)                          # gentle saturation = grit/warmth
    wet = signal.fftconvolve(y, room_ir(SR))[:len(y) + int(0.5 * SR)]
    dry = np.pad(y, (0, len(wet) - len(y)))
    out = dry + 0.13 * wet
    out = trim(out, thr=0.004, pad=0.03)
    return (out / (np.max(np.abs(out)) + 1e-9) * 0.89).astype(np.float32)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tts = elevenlabs_tts if os.environ.get("ELEVENLABS_API_KEY") else kokoro_tts
    engine = "elevenlabs" if tts is elevenlabs_tts else f"kokoro:{VOICE_BLEND}"
    only = set(sys.argv[1:])
    dur_file = OUT / "durations.json"
    durs = json.loads(dur_file.read_text()) if dur_file.exists() else {}
    jobs = [(cid, text) for _, cid, _, text in VO] + [("laugh", LAUGH_TEXT)]
    for cid, text in jobs:
        if only and cid not in only:
            continue
        a, sr = tts(text)
        a = trim(a / (np.max(np.abs(a)) + 1e-9), thr=0.01)
        if cid == "laugh":
            a = ffmpeg_filter(a, sr, "atempo=0.85"); sr = SR      # draw the laugh out
        y = process(a, sr)
        sf.write(OUT / f"{cid}.wav", y, SR, subtype="PCM_24")
        durs[cid] = round(len(y) / SR, 3)
        print(f"{cid:6s} {durs[cid]:5.2f}s  {text}")
    durs["_engine"] = engine
    dur_file.write_text(json.dumps(durs, indent=1))


if __name__ == "__main__":
    main()
