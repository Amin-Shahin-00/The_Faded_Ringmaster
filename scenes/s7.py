"""SCENE 7 - THE FINALE (2:50 - 3:10) + title card.

The rebuilt tent in the dark palette. The bow mirrors Scene 2 exactly in key poses
and framing (silas_moves.bow_pose / BOW_FRAME), played at Act 3 timing. The only
fully saturated color is the red silk lining of the coat, so the grade here keeps
saturation at 1.0 and the muted look comes from the Act 3 palettes themselves."""
import math
from functools import lru_cache
import numpy as np
import skia
from lib.core import W, H, Xf, keys, clamp, lerp, remap, smooth, ease_io, ease_out, twos, paint, mix, rng, hexc, vnoise
from lib.ink import S, shape, ink_line, fill, ellipse, spline, path_of
from lib.frame import Cam, text, text_width, new_surface, to_array
from config.palettes import GRADE
from config.timeline import BEATS
from rigs.silas import Silas
from rigs.cast import Bruno, Lena, Pip
from scenes import tent, s2
from scenes.common import radial, cone, fog, cracked_hat
from scenes.silas_moves import bow_pose, auto_blinks, breathing
from scenes.s5 import light3

ACT = 3
ACT3_TIME = 1.7       # the Act 3 bow is 1.7x slower than the Act 1 bow


def grade(**kw):
    g = dict(GRADE[3])
    g.update(sat=1.0, tint=(0.94, 1.0, 1.02))
    g.update(kw)
    return g


def _crew(c, t, scale, pos, lit=0.55):
    """Bruno, Lena and Pip standing at the edges of the ring, still, breathing."""
    for i, (cls, (x, y), face, turn) in enumerate(zip((Bruno, Lena, Pip), pos, (1, -1, 1), (0.35, 0.4, 0.2))):
        f = cls(3)
        P = f.pose(x=x, y=y, s=scale * (1.0 if cls is not Pip else 1.0), turn=turn, face=face, breath=breathing(t, 0.18 + i * 0.02),
                   blink=auto_blinks(t, 90 + i), smile=0.0)
        if cls is Bruno:
            P.update(arm_n=(30.0, -250.0), arm_f=(-30.0, -248.0), hand_n="fist", hand_f="fist", brow=-0.2)
        if cls is Pip:
            P.update(droop=0.9, smile=-0.2)
        c.saveLayer(None, None)
        f.draw(c, P)
        p = paint("#03070a", 1 - lit)
        p.setBlendMode(skia.BlendMode.kSrcATop)
        c.drawPaint(p)
        c.restore()


def wide_final(c, lt, T, t):
    light3(rim=(0.0, -1.0))
    tq = twos(lt)
    z = lerp(1.0, 1.1, ease_io(lt / 5.0, 1.5))
    cam = Cam(960, lerp(560, 600, ease_io(lt / 5.0)), z)
    fig = Silas(ACT)
    P = fig.pose(**dict(s2.BOW_FRAME if False else dict(x=960, y=s2.RING_Y, s=s2.WIDE_S, face=1, turn=0.3)))
    P.update(foot_n=(26.0, 0.0), foot_f=(-16.0, 0.0), arm_n=(96.0, -296.0), hand_n="open", arm_f=("fk", -0.45, 0.35),
             hand_f="grip", handle=("hand_f", 1.3), smile=0.25, cold=1.0, breath=breathing(lt, 0.2), blink=auto_blinks(lt, 95))

    def ring_chars(cv):
        with cam.layer(cv, 1.0):
            cone(cv, (960, -200), (960, 840), 120, "#e8f0f0", a=0.28, soft=30)
            radial(cv, 960, 838, 160, "#e8f0f0", 0.45, blend=skia.BlendMode.kScreen)
            _crew(cv, lt, s2.WIDE_S, [(470, 812), (1450, 812), (960, 930)], lit=0.4)
            fig.draw(cv, P)

    tent.draw_tent(c, cam, lt, ACT, occupancy=1.0, mood="still", finale=True, lights_on=0.0, light_bright=0.0,
                   after_stands=ring_chars, front_row=True, front_mood="still", front_col="#020405")
    fog(c, lt, 640, 200, "#1c2a2c", a=0.18, seed=97, drift=5)
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#000000", 0.12))
    return grade(vignette=1.4)


def bow_final(c, lt, T, t):
    light3(rim=(0.0, -1.0))
    tq = twos(lt)
    fig = Silas(ACT)
    u = tq / ACT3_TIME
    end_smile = remap(tq, 7.9, 8.6)

    def crew_fn(cv):
        _crew(cv, lt, 0.62, [(330, 640), (1610, 640), (1240, 652)], lit=0.35)

    tent.draw_ring_medium(c, lt, ACT, xshift=-30, occupancy=1.0, mood="still", finale=True, lights=False, mid_fn=crew_fn, blur=6.0)
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#000000", 0.35))
    # one spotlight on Silas
    cone(c, (900, -300), (900, 1030), 300, "#e8f0f0", a=0.22, soft=40)
    radial(c, 900, 1025, 420, "#e8f0f0", 0.42, blend=skia.BlendMode.kScreen)
    P = bow_pose(fig, u, ACT, extra=dict(blink=auto_blinks(lt, 96) if u > 4.6 else 0.0, breath=breathing(lt, 0.2),
                                          handle=("hand_f", 1.3), cane=None, lining_boost=0.25))
    if u > 4.6:   # after the bow: the small, cold smile widens
        P["smile"] = 0.3 + 0.25 * end_smile
        P["narrow"] = 0.25 + 0.15 * end_smile
    fig.draw(c, P)
    return grade(vignette=1.35)


@lru_cache(None)
def title_card():
    """Old circus-poster lettering, faded and cracked (rendered once, crisp)."""
    s = new_surface(W, H)
    c = s.getCanvas()
    c.clear(0x00000000)
    cream = "#e6d6b0"
    red = "#7a2626"
    # ornamental rules
    for y in (330, 760):
        c.drawRect(skia.Rect.MakeLTRB(560, y, 1360, y + 3), paint(cream, 0.6))
        for x in (540, 1380):
            st = [(x + math.cos(-math.pi / 2 + j * math.pi / 5) * (12 if j % 2 == 0 else 5),
                   y + 1.5 + math.sin(-math.pi / 2 + j * math.pi / 5) * (12 if j % 2 == 0 else 5)) for j in range(10)]
            c.drawPath(path_of(np.array(st)), paint(cream, 0.6))
    text(c, "THE", 960, 410, "oldstd_b", 54, cream, 0.85)
    for (txt, y, size) in (("FADED", 560, 150), ("RINGMASTER", 712, 132)):
        text(c, txt, 966, y + 6, "rye", size, red, 0.85)        # offset print shadow
        text(c, txt, 960, y, "rye", size, cream, 1.0)
    # fade + cracks: erase hairline cracks and speckles out of the lettering
    r = rng(99)
    clear = skia.Paint(AntiAlias=True)
    clear.setBlendMode(skia.BlendMode.kDstOut)
    clear.setStyle(skia.Paint.kStroke_Style)
    for i in range(16):
        x, y = 560 + r.random() * 800, 440 + r.random() * 300
        pts = [(x, y)]
        ang = r.random() * math.tau
        for j in range(6):
            ang += (r.random() - 0.5) * 1.2
            x += math.cos(ang) * (10 + r.random() * 22); y += math.sin(ang) * (10 + r.random() * 22)
            pts.append((x, y))
        clear.setStrokeWidth(1.2 + r.random() * 1.6)
        clear.setColor4f(skia.Color4f(0, 0, 0, 0.9))
        c.drawPath(path_of(np.array(pts), closed=False), clear)
    fillclear = skia.Paint(AntiAlias=True)
    fillclear.setBlendMode(skia.BlendMode.kDstOut)
    for i in range(500):
        x, y = 560 + r.random() * 800, 450 + r.random() * 300
        fillclear.setColor4f(skia.Color4f(0, 0, 0, 0.25 + 0.5 * r.random()))
        c.drawCircle(x, y, 0.8 + r.random() * 2.6, fillclear)
    return s.makeImageSnapshot().withDefaultMipmaps()


def title(c, lt, T, t):
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#000000"))
    a = smooth(remap(lt, 1.0, 2.0)) * (1 - smooth(remap(lt, 5.0, 6.0)))
    if a > 0:
        radial(c, 960, 560, 700, "#2a1e18", 0.6 * a)
        c.drawImage(title_card(), 0, 0, skia.SamplingOptions(), paint("#ffffff", a))
        cracked_hat(c, 960, 880, 0.55, 1.0, col="#5a4a3a", crack_col="#3a1a1a", alpha=0.7 * a, drips=False, seed=999)
    return dict(sat=1.0, tint=(1.0, 0.98, 0.94), lift=(0, 0, 0), gamma=1.0, glow=0.0, grain=0.03, vignette=1.2)


SHOTS = dict(wide_final=wide_final, bow_final=bow_final, title=title)
