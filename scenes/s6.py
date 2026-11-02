"""SCENE 6 - THE RISE (2:20 - 2:50). Montage cut on the beats of the 84 BPM Act 3 theme.
Danger is implied only: shadows, looks, silence. No violence."""
import math
from functools import lru_cache
import numpy as np
import skia
from lib.core import W, H, Xf, keys, clamp, lerp, remap, smooth, ease_io, ease_out, ease_back, twos, paint, mix, rng, hexc, vnoise
from lib.ink import S, shape, ink_line, fill, ellipse, spline, path_of
from lib.frame import Cam, text, text_width, new_surface
from config.palettes import GRADE
from config.timeline import BEATS, MONTAGE_BPM, MONTAGE_START
from rigs.silas import Silas
from rigs.cast import Bruno
from rigs.crowd import make_people, person
from scenes.common import radial, cone, painterly, cracked_hat, fog
from scenes.silas_moves import auto_blinks, breathing
from scenes.s5 import light3

BEAT = 60.0 / MONTAGE_BPM


def grade(**kw):
    g = dict(GRADE[3])
    g.update(kw)
    return g


def beat_pulse(t, k=7.0):
    """Short swell on each beat (used for a light push on the cuts)."""
    ph = ((t - MONTAGE_START) / BEAT) % 1.0
    return math.exp(-ph * k)


# ============================================================================ the long table

def table(c, lt, T, t):
    light3(rim=(-0.6, -0.8))
    tq = twos(lt)
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#060b0c"))
    for i in range(9):
        x0 = -40 + i * 230
        c.drawRect(skia.Rect.MakeLTRB(x0, 0, x0 + 226, 720), paint(mix("#0c1517", "#0a1214", i % 2)))
    # hanging lamp
    c.drawLine(900, -10, 900, 170, paint("#050505", stroke=3))
    shape(c, np.array([(840, 170), (960, 170), (1010, 230), (790, 230)]), "#1c2224", 2.5, seed=4000)
    radial(c, 900, 260, 900, "#e8d8a8", 0.28, blend=skia.BlendMode.kScreen)
    cone(c, (900, 230), (900, 760), 520, "#e8d8a8", a=0.12, soft=40)
    s = 1.0
    # Bruno stands behind the owners, arms folded, watching
    b = Bruno(3)
    BP = b.pose(x=700, y=820, s=1.0, turn=0.1, face=1, arm_n=(30.0, -250.0), arm_f=(-30.0, -248.0), hand_n="fist", hand_f="fist",
                blink=auto_blinks(lt, 80), breath=breathing(lt, 0.2), smile=-0.1, brow=-0.3, look=(0.4, 0.0))
    b.draw(c, BP)
    # three owners seated along the table, signing
    owners = make_people(81, 3, kid_ratio=0.0)
    signs = [b_ - 140.0 for b_ in BEATS["s6_sign"]]
    for i, op in enumerate(owners):
        op["hat"] = [2, 1, 2][i]
        op["kid"] = False
        x = 420 + i * 300
        person(c, x, 760, 46, op, lt, mood="still", act=3)
    # table
    shape(c, np.array([(200, 740), (1500, 740), (1530, 790), (170, 790)]), "#2a1c14", 3.5, seed=4010, rim=False)
    shape(c, np.array([(190, 790), (1510, 790), (1500, 812), (200, 812)]), "#1a120c", 3, seed=4011, rim=False)
    c.drawRect(skia.Rect.MakeLTRB(170, 812, 1530, 1080), paint("#030506"))
    # papers + pens + the scribbled signatures growing
    for i in range(3):
        x = 420 + i * 300
        paper = np.array([(x - 70, 744), (x + 60, 738), (x + 66, 772), (x - 64, 778)])
        shape(c, paper, "#d8d0bc", 2, seed=4020 + i, shadow=False)
        for k in range(3):
            c.drawLine(x - 54, 750 + k * 6, x + 40, 748 + k * 6, paint("#6a6a6a", 0.5, stroke=1.2))
        t_sign = signs[0] + i * 0.55 if i < 2 else signs[1] + 0.4
        u = remap(tq, t_sign, t_sign + 0.8)
        if u > 0:
            pts = np.array([(x - 40 + 70 * v, 768 + 4 * math.sin(v * 22) - 2 * math.sin(v * 9)) for v in np.linspace(0, u, max(3, int(u * 30)))])
            ink_line(c, pts, 1.8, color="#101830", do_boil=False, taper=0.2)
            pen = pts[-1]
            ink_line(c, np.array([pen, pen + (16, -40)]), 4, color="#0a0a0a", do_boil=False, taper=0.1)
    # Silas at the head of the table, tapping the silver handle into his palm on the beat
    si = Silas(3)
    taps = [b_ - 140.0 for b_ in BEATS["s6_taps"]]
    tap = 0.0
    for tp in taps:
        if tp - 0.2 <= tq <= tp + 0.15:
            tap = keys(tq, [(tp - 0.2, 0.0), (tp - 0.05, -1.0), (tp, 0.3, "in"), (tp + 0.15, 0.0)])
    SP = si.pose(x=1660, y=1060, s=1.3, turn=0.75, face=-1, foot_n=(14.0, 0.0), foot_f=(-12.0, 0.0),
                 arm_n=(70.0, -255.0 - 30 * (-tap)), handle=("hand_n", 1.4), hand_n="grip", wrist_n=-0.4,
                 arm_f=(62.0, -228.0), hand_f="open", smile=0.2, cold=1.0, narrow=0.2, brim_shadow=1.0,
                 blink=auto_blinks(lt, 81), breath=breathing(lt, 0.2))
    si.draw(c, SP)
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#020405", 0.18))
    return grade()


# ============================================================================ low angle on Silas

def lowangle(c, lt, T, t):
    light3(rim=(0.7, -0.7))
    tq = twos(lt)
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#040809"))
    # perspective: the bottom of frame is nearer the lens (looking up at him)
    m = skia.Matrix.MakeAll(1, 0, 0, 0, 1, 0, 0, -0.00034, 1)
    pre = skia.Matrix.Translate(-960, -60)
    post = skia.Matrix.Translate(960, 60)
    z = lerp(1.0, 1.06, ease_io(lt / 4.3))
    c.save()
    c.translate(960, 600); c.scale(z, z); c.translate(-960, -600)
    c.concat(post); c.concat(m); c.concat(pre)
    # ceiling beams + bulb above him
    for i in range(7):
        c.drawLine(-200 + i * 380, -100, 200 + i * 300, 500, paint("#0e1a1c", stroke=24))
    radial(c, 1060, 120, 120, "#ffe8b8", 0.85, blend=skia.BlendMode.kScreen)
    radial(c, 1060, 140, 760, "#d8c898", 0.18, blend=skia.BlendMode.kScreen)
    si = Silas(3)
    taps = [140.0 + BEAT * (k + 6) - 144.286 for k in range(0, 7)]
    tap = 0.0
    for tp in taps:
        if tp - 0.2 <= tq <= tp + 0.15:
            tap = keys(tq, [(tp - 0.2, 0.0), (tp - 0.05, -1.0), (tp, 0.25, "in"), (tp + 0.15, 0.0)])
    SP = si.pose(x=930, y=1240, s=2.0, turn=0.3, face=1, foot_n=(16.0, 0.0), foot_f=(-14.0, 0.0),
                 arm_n=(60.0, -258.0 + 25 * tap), handle=("hand_n", 1.5), hand_n="grip", wrist_n=-0.5,
                 arm_f=(48.0, -232.0), hand_f="open", smile=0.32, cold=1.0, narrow=0.3, brow=-0.4, brim_shadow=1.0,
                 look=(0.0, 0.7), head_rot=-0.12, blink=0.0, breath=breathing(lt, 0.2))
    si.draw(c, SP)
    c.restore()
    # owners' heads in the foreground (out of focus), looking up
    c.saveLayer(None, _blur(10))
    for i, (x, sz) in enumerate([(250, 120), (1700, 140)]):
        c.drawCircle(x, 1080 + sz * 0.3, sz, paint("#020405"))
        c.drawRect(skia.Rect.MakeLTRB(x - sz * 0.75, 1080 - sz * 2.2, x + sz * 0.75, 1080 - sz * 0.6), paint("#020405"))
        c.drawPath(path_of(ellipse(x, 1080 - sz * 0.6, sz * 1.25, sz * 0.22, 20)), paint("#020405"))
    c.restore()
    return grade(vignette=1.3)


def _blur(r):
    p = skia.Paint()
    p.setImageFilter(skia.ImageFilters.Blur(r, r))
    return p


# ============================================================================ the symbol spreads

def _tent_flag(c):
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#0a1416"))
    for i in range(14):   # striped canvas
        x0 = -40 + i * 150
        c.drawRect(skia.Rect.MakeLTRB(x0, 0, x0 + 150, H), paint("#3d4a4c" if i % 2 else "#4a2e2c"))
    c.drawPath(path_of(ellipse(960, 520, 300, 300, 50)), paint("#c8b060"))
    st = [(960 + math.cos(-math.pi / 2 + j * math.pi / 5) * (220 if j % 2 == 0 else 90),
           520 + math.sin(-math.pi / 2 + j * math.pi / 5) * (220 if j % 2 == 0 else 90)) for j in range(10)]
    c.drawPath(path_of(np.array(st)), paint("#7a2a2a"))
    text(c, "STAR CIRCUS", 960, 900, "rye", 80, "#c8b060")


def _truck(c):
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#081012"))
    body = np.array([(80, 200), (1840, 200), (1840, 860), (80, 860)])
    painterly(c, path_of(body), "#2a6a8a", seed=4100, strength=0.5)
    ink_line(c, body, 4, closed=True, do_boil=False)
    for k in range(6):
        c.drawLine(80, 260 + k * 110, 1840, 260 + k * 110, paint("#1a4a60", 0.6, stroke=3))
    text(c, "VOLTA", 960, 560, "bebas", 260, "#ffe23a")
    text(c, "ELECTRIC CIRCUS", 960, 680, "bebas", 90, "#ffffff")
    for x in (420, 1500):
        c.drawCircle(x, 900, 110, paint("#0a0a0a"))
        c.drawCircle(x, 900, 50, paint("#4a4a4a"))


def _posters(c):
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#0c0e0e"))
    r = rng(4200)
    names = ["GRAND", "WONDER", "ROYAL", "GOLDEN", "STAR", "VOLTA"]
    for k in range(6):
        x = 170 + (k % 3) * 600 + (r.random() - 0.5) * 40
        y = 270 + (k // 3) * 520
        c.save(); c.translate(x, y); c.rotate((r.random() - 0.5) * 6)
        col = ["#8a3a2a", "#3a6a8a", "#8a7a2a", "#5a3a6a", "#2a6a4a", "#2a8aa8"][k]
        painterly(c, path_of(np.array([(-140, -220), (140, -220), (140, 220), (-140, 220)])), col, seed=4210 + k, strength=0.4)
        text(c, names[k], 0, -120, "rye", 56, "#e8dcc0")
        text(c, "CIRCUS", 0, -60, "oldstd_b", 34, "#e8dcc0")
        c.restore()



def paint_shot(c, lt, T, t):
    from lib.core import paint as P_
    light3()
    tq = twos(lt)
    seg = 4 * BEAT        # each reveal lasts 4 beats
    k = min(int(lt / seg), 2)
    l2 = lt - k * seg
    z = lerp(1.0, 1.08, l2 / seg)
    c.save()
    c.translate(960, 540); c.scale(z, z); c.translate(-960, -540)
    [_tent_flag, _truck, _posters][k](c)
    if k < 2:
        u = ease_io(remap(twos(l2), 0.35, 2.2), 1.4)
        cracked_hat(c, 960, 680 if k == 0 else 760, 3.2, u, seed=4300 + k)
        # the brush follows the reveal front
        if 0 < u < 1:
            band = min(int(u * 3), 2)
            fx = 960 + (-80 + 160 * clamp(u * 3 - band)) * 3.2
            fy = (680 if k == 0 else 760) + [-95, -48, -2][band] * 3.2
            _brush(c, fx, fy)
    else:
        # posters across the wall get the symbol one after another, on the beats
        for j in range(6):
            x = 170 + (j % 3) * 600
            y = 270 + (j // 3) * 520
            u = ease_out(remap(l2, 0.25 + j * BEAT * 0.62, 0.25 + j * BEAT * 0.62 + 0.5), 2)
            if u > 0:
                cracked_hat(c, x, y + 120, 1.6, u, seed=4310 + j)
    c.restore()
    return grade(sat=0.9)


def _brush(c, x, y):
    from lib.core import paint as P_
    X = Xf.T(x, y).r(-0.5)
    shape(c, X(np.array([(-28, -50), (28, -50), (24, 10), (-24, 10)])), "#141012", 3, seed=4400)
    shape(c, X(np.array([(-30, -90), (30, -90), (28, -50), (-28, -50)])), "#a8a8a8", 3, seed=4401)
    shape(c, X(np.array([(-10, -360), (10, -360), (12, -90), (-12, -90)])), "#6a4a2a", 3, seed=4402)
    shape(c, X(spline(np.array([(-30, -300), (30, -310), (44, -260), (30, -220), (-30, -230)]), closed=True, n=3)), "#c9c6bc", 3, seed=4403)


# ============================================================================ newspapers

HEADLINES = ["WHO IS THE RINGMASTER?", "CIRCUS EMPIRE GROWS", "EVERY BIG TOP ANSWERS TO ONE MAN"]


@lru_cache(None)
def newspaper(k):
    """Pre-rendered newspaper page (crisp text), 1100 x 760."""
    from lib.core import paint as P_
    w, h = 1100, 760
    s = new_surface(w, h)
    c = s.getCanvas()
    c.clear(0x00000000)
    painterly(c, path_of(np.array([(0, 0), (w, 0), (w, h), (0, h)])), "#ddd5c0", seed=4500 + k, strength=0.4)
    text(c, "THE EVENING HERALD", w / 2, 78, "oldstd_b", 64, "#1a1a1a")
    c.drawRect(skia.Rect.MakeLTRB(40, 98, w - 40, 102), P_("#1a1a1a"))
    text(c, ["VOL. XII", "VOL. XII", "VOL. XIII"][k] + "   -   EXTRA EDITION   -   ONE PENNY", w / 2, 126, "oldstd", 20, "#1a1a1a")
    c.drawRect(skia.Rect.MakeLTRB(40, 138, w - 40, 140), P_("#1a1a1a"))
    head = HEADLINES[k]
    size = 92
    while text_width(head, "oldstd_b", size) > w - 90:
        size -= 2
    text(c, head, w / 2, 240, "oldstd_b", size, "#101010")
    # photo with the symbol + columns of type
    c.drawRect(skia.Rect.MakeLTRB(60, 290, 470, 700), P_("#2a2a2a"))
    cracked_hat(c, 265, 600, 2.1, 1.0, col="#0a0a0a", crack_col="#3a1010", drips=False, seed=4510)
    radial(c, 265, 470, 200, "#8a8a8a", 0.2)
    r = rng(4520 + k)
    for col in range(3):
        x0 = 500 + col * 196
        for row in range(26):
            y = 300 + row * 15.5
            ln = 150 + r.random() * 30 if row % 9 != 8 else 90
            c.drawRect(skia.Rect.MakeLTRB(x0, y, x0 + ln, y + 6), P_("#4a4a4a", 0.55))
    return s.makeImageSnapshot().withDefaultMipmaps()


def papers(c, lt, T, t):
    from lib.core import paint as P_
    light3()
    c.drawRect(skia.Rect.MakeWH(W, H), P_("#060a0b"))
    radial(c, 960, 540, 900, "#3a5a5c", 0.35)
    seg = 3 * BEAT
    k = min(int(lt / seg), 2)
    l2 = lt - k * seg
    # previous page stays underneath, darker
    for j in range(k + 1):
        lj = lt - j * seg
        u = ease_out(remap(lj, 0.0, 0.85), 2.4)
        spin = (1 - u) * math.tau * 2.0
        sc = lerp(0.08, 1.0, u)
        rot_final = [-4.0, 3.0, -2.0][j]
        img = newspaper(j)
        dim = 0.55 if j < k else 1.0
        c.save()
        c.translate(960 + (j - 1) * 30 * (j < k), 540)
        c.rotate(math.degrees(spin) + rot_final)
        c.scale(sc * 1.35, sc * 1.35)
        c.drawImage(img, -550, -380, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNearest), P_("#ffffff"))
        if dim < 1:
            c.drawRect(skia.Rect.MakeLTRB(-550, -380, 550, 380), P_("#000000", 1 - dim))
        c.restore()
    return grade(sat=0.85, vignette=1.25)


# ============================================================================ the map

@lru_cache(None)
def map_data():
    r = rng(4600)
    # a fictional country: smooth noisy blob
    pts = []
    for a in np.linspace(0, math.tau, 90, endpoint=False):
        rr = 1.0 + 0.18 * math.sin(a * 3 + 1) + 0.1 * math.sin(a * 7 + 2) + 0.06 * math.sin(a * 13)
        pts.append((960 + math.cos(a) * 640 * rr, 540 + math.sin(a) * 360 * rr))
    cities = [(700, 560)]
    while len(cities) < 22:
        x, y = 420 + r.random() * 1080, 260 + r.random() * 560
        if all(math.hypot(x - cx, y - cy) > 120 for cx, cy in cities):
            cities.append((x, y))
    # spread order: by distance from the first city (like a contagion)
    order = sorted(range(len(cities)), key=lambda i: math.hypot(cities[i][0] - 700, cities[i][1] - 560))
    links = []
    for i in order[1:]:
        prev = min((j for j in order[:order.index(i)]), key=lambda j: math.hypot(cities[i][0] - cities[j][0], cities[i][1] - cities[j][1]))
        links.append((prev, i))
    return np.array(pts), cities, order, links


@lru_cache(None)
def map_bg():
    from lib.core import paint as P_
    s = new_surface(W, H)
    c = s.getCanvas()
    painterly(c, path_of(np.array([(0, 0), (W, 0), (W, H), (0, H)])), "#c8b894", seed=4610, strength=0.7)
    land, cities, order, links = map_data()
    c.drawPath(path_of(land + 6), P_("#000000", 0.25, blur=8))
    painterly(c, path_of(land), "#a89a72", seed=4611, strength=0.6)
    ink_line(c, np.vstack([land, land[:1]]), 3, do_boil=False)
    for i in range(1, 8):   # contour hatching near the coast
        inner = (land - (960, 540)) * (1 - i * 0.012) + (960, 540)
        ink_line(c, np.vstack([inner, inner[:1]]), 0.8, alpha=0.25, do_boil=False)
    for (a, b) in links:   # rail lines
        pa, pb = np.array(cities[a]), np.array(cities[b])
        ink_line(c, np.array([pa, pb]), 1.6, alpha=0.5, do_boil=False)
    for (x, y) in cities:
        c.drawCircle(x, y, 7, P_("#2a2016"))
    # compass rose
    for k in range(8):
        a = k * math.pi / 4
        L = 60 if k % 2 == 0 else 30
        c.drawLine(1640, 880, 1640 + math.cos(a) * L, 880 + math.sin(a) * L, P_("#2a2016", stroke=3 if k % 2 == 0 else 1.5))
    text(c, "N", 1640, 800, "oldstd_b", 30, "#2a2016")
    return s.makeImageSnapshot().withDefaultMipmaps()


def map_shot(c, lt, T, t):
    from lib.core import paint as P_
    light3()
    z = lerp(1.35, 1.0, ease_io(lt / T, 1.5))
    land, cities, order, links = map_data()
    cx = lerp(700, 960, ease_io(lt / T))
    cy = lerp(560, 540, ease_io(lt / T))
    c.save()
    c.translate(960, 540); c.scale(z, z); c.translate(-cx, -cy)
    c.drawImage(map_bg(), 0, 0)
    n = len(order)
    for idx, i in enumerate(order):
        t_on = 0.15 + idx * (T - 1.2) / n
        u = remap(lt, t_on, t_on + 0.35)
        if u <= 0:
            continue
        x, y = cities[i]
        # red spreading line from the previous city
        for (a, b) in links:
            if b == i:
                pa, pb = np.array(cities[a]), np.array(cities[b])
                ink_line(c, np.array([pa, pa + (pb - pa) * clamp(u * 1.5)]), 4, color="#7a1a1a", do_boil=False, taper=0.0)
        radial(c, x, y, 70 * u, "#5a0a0a", 0.4 * u)
        sc = 0.42 * (1.6 - 0.6 * ease_out(u, 3))
        cracked_hat(c, x, y + 18, sc, 1.0, alpha=min(1.0, u * 2), drips=False, seed=4620 + i)
    c.restore()
    c.drawRect(skia.Rect.MakeWH(W, H), P_("#000000", 0.25))
    return grade(sat=0.8, vignette=1.35)


SHOTS = dict(table=table, lowangle=lowangle, paint=paint_shot, papers=papers, map=map_shot)
