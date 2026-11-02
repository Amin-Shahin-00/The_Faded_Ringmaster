# THE FADED RINGMASTER

A ~3-minute hand-drawn-style 2D animated short, built entirely in code: every frame is
drawn deterministically with Skia (Python), every sound is synthesized or generated
locally, and ffmpeg assembles the film.

## Deliverables

| File | What |
|---|---|
| `output/the_faded_ringmaster.mp4` | The film: 1920x1080, 24 fps, H.264 + AAC, mix normalized to -16 LUFS |
| `output/the_faded_ringmaster.srt` | Voiceover subtitles |
| `model_sheets/` | Character model sheets (front / 3/4 / side, palettes per act, expressions, props) and a cast line-up |
| `style_frames/` | One style frame per scene |

## Re-rendering

Requirements: Windows/macOS/Linux with Python 3.10+. Everything else installs into a venv:

```
python -m venv .venv
.venv\Scripts\pip install numpy scipy skia-python Pillow imageio-ffmpeg soundfile pyloudnorm kokoro-onnx
```

The Kokoro voice model files go in `assets/tts/` (`kokoro-v1.0.onnx`, `voices-v1.0.bin`, from the
kokoro-onnx GitHub releases). Fonts are in `assets/fonts/` (OFL / Apache licensed Google Fonts).

```
.venv\Scripts\python make.py              # everything: sheets, voice, music, sfx, mix, picture, final mp4, style frames
.venv\Scripts\python make.py audio        # only the sound (voice + music + sfx + mix); add --no-tts to keep the voice files
.venv\Scripts\python make.py picture      # only the frames -> build/video.mp4 (about 15-25 min on 12 cores)
.venv\Scripts\python make.py final        # mux picture + mix -> output/the_faded_ringmaster.mp4
```

Useful while working:

```
python render.py still 26.9                  # one frame at t = 26.9 s -> build/stills/
python render.py contact s3                  # contact sheet of a scene, one frame per 0.5 s (renders frames)
python tools/contact_video.py                # contact sheets from the rendered video, per scene
python tools/contact_video.py frames 97 98   # every frame in a time range (check fast motion / cuts)
python tools/qa_video.py                     # automatic jump / single-frame-flicker detector
python tools/model_sheets.py                 # model sheets
```

If `ELEVENLABS_API_KEY` is set, `audio/tts.py` uses ElevenLabs (voice id from `ELEVENLABS_VOICE_ID`,
default "Adam") instead of the local Kokoro model.

## Where to change things

| To change | Edit |
|---|---|
| Scene / shot timings, transitions, action beats (picture and SFX share them) | `config/timeline.py` (`SCENES`, `SHOTS`, `TRANSITIONS`, `BEATS`) |
| Voiceover lines and when each starts | `config/timeline.py` (`VO`) - then `python make.py audio` |
| Voice, speed, pitch, laugh | `audio/tts.py` (`VOICE_BLEND`, `SPEED`, `PITCH_SEMITONES`, `LAUGH_TEXT`) |
| Colors of characters, environments, grade per act | `config/palettes.py` |
| Character designs | `rigs/silas.py`, `rigs/cast.py` (Bruno, Lena, Pip), `rigs/crowd.py` |
| The bow (shared by Scene 2 and Scene 7) | `scenes/silas_moves.py` |
| A scene's staging and animation | `scenes/s1.py` ... `scenes/s7.py` (one file per scene, one function per shot) |
| Music (melody, cue sheet) | `audio/music.py` (`PHRASE_A/B`, `build()`) |
| Sound effects placement | `audio/sfx.py` (`build()`) |
| Mix levels, ducking depth, loudness target | `audio/mix.py` (top constants) |
| Line boil, ink, shading | `lib/ink.py`; grain/paper/vignette/grade in `lib/frame.py` (`post`) |

After changing timings, run `python audio/mix.py` - it prints a report showing that every
voiceover chunk starts and ends inside its scene, and the voice-to-background level for each line.

## How it works

* `lib/core.py` math, easing, keyframes, noise, transforms, two-bone IK (never stretches)
* `lib/ink.py` variable-width ink lines with subtle line boil (12 drawings/s), painted shadow and rim crescents
* `lib/motion.py` footstep-planned walks (planted feet cannot slide), follow-through springs
* `lib/frame.py` camera with parallax depth layers, text, film post (grade, bloom, paper texture, grain, vignette)
* `rigs/` one cross-section model per character, so front, 3/4 and side views come from the same proportions
* `scenes/` one module per scene; `render.py` evaluates a frame as a pure function of time,
  handles dissolves, renders in parallel and pipes frames to ffmpeg
* characters animate on twos (`core.twos`), camera moves and effects run at 24 fps
