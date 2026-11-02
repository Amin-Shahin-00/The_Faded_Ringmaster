"""SCENE 1 - COLD OPEN (0:00 - 0:18). Night, heavy rain, the torn tent; Silas alone in the ring."""
import math
from functools import lru_cache
import numpy as np
import skia
from lib.core import W, H, Xf, keys, clamp, lerp, remap, smooth, ease_io, twos, paint, mix, rng, hexc, vnoise
from lib.ink import S, shape, ink_line, fill, ellipse, spline, path_of
from lib.frame import Cam, text, new_surface
from config.palettes import GRADE, ENV
from config.timeline import BEATS
from rigs.silas import Silas
from scenes import tent
from scenes.common import radial, cone, painterly, rain, splashes, fog, lightning_flash
from scenes.silas_moves import auto_blinks, breathing

ACT = 2
E = ENV[2]


def light_cold():
    S.key = (0.15, -0.99)
    S.shadow_col = "#0a1420"
    S.shadow_a = 0.45
    S.rim = (0.1, -0.99)
    S.rim_col = "#c4d8e2"
    S.rim_a = 0.32


def grade(flash=0.0, **kw):
    g = dict(GRADE[2])
    g["lift"] = tuple(v + 0.10 * flash for v in g["lift"])
    g.update(kw)
    return g


# ============================================================================ exterior painting

def _hi(scale=1.4):
    s = new_surface(int(W * scale), int(H * scale))
    c = s.getCanvas()
    c.clear(0x00000000)
    c.scale(scale, scale)
    return s, c


@lru_cache(None)
def ext_sky(mode="night"):
    s, c = _hi()
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, 800)],
                [skia.Color4f(*hexc("#0b1118")), skia.Color4f(*hexc("#1c2833")), skia.Color4f(*hexc("#2a3640"))], [0, 0.6, 1]))
    c.drawRect(skia.Rect.MakeWH(W, H), p)
    r = rng(4)
    for i in range(26):   # heavy painted clouds
        x, y = r.random() * W, r.random() * 420
        rx = 200 + r.random() * 340
        col = mix("#26323c", "#3c4852", r.random()) if mode == "night" else mix("#5a5258", "#7a6e6c", r.random())
        c.drawOval(skia.Rect.MakeXYWH(x - rx, y - rx * 0.28, rx * 2, rx * 0.56), paint(col, 0.55, blur=40))
    # distant tree line and hills
    hills = [(x, 700 - 60 * vnoise(x * 0.004, 2) - 30 * vnoise(x * 0.02, 3)) for x in np.linspace(-20, W + 20, 80)]
    c.drawPath(path_of(np.array(hills + [(W + 20, 800), (-20, 800)])), paint("#141c22"))
    trees = []
    for x in np.linspace(-20, W + 20, 160):
        trees.append((x, 690 - 40 * vnoise(x * 0.01, 5) - 26 * abs(math.sin(x * 0.07)) * vnoise(x * 0.03, 6)))
    c.drawPath(path_of(np.array(trees + [(W + 20, 800), (-20, 800)])), paint("#10161b"))
    return s.makeImageSnapshot().withDefaultMipmaps()


@lru_cache(None)
def ext_tent(torn=True):
    """The torn, faded big top (static painted parts)."""
    s, c = _hi()
    a_col, b_col = "#6e4640", "#8f8c7e"
    base_y, wall_top = 770, 590
    x0, x1 = 420, 1500
    peaks = [(800, 300), (1120, 300)]
    # roof: stripes fanning down from the two peaks to the wall top
    n = 22
    for i in range(n):
        xa = x0 - 30 + (x1 - x0 + 60) * i / n
        xb = x0 - 30 + (x1 - x0 + 60) * (i + 1) / n
        pk = peaks[0] if (xa + xb) / 2 < 960 else peaks[1]
        mid = (960, 340)
        if abs((xa + xb) / 2 - 960) < 120:
            pk = mid
        poly = np.array([pk, (xa, wall_top + 8 * math.sin(i)), (xb, wall_top + 8 * math.sin(i + 1))])
        painterly(c, path_of(poly), a_col if i % 2 == 0 else b_col, seed=600 + i, strength=0.5, angle=1.2)
    # roof shading (rain darkened, lit from above by the sky)
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 300), skia.Point(0, 600)],
                [skia.Color4f(0.05, 0.07, 0.09, 0.15), skia.Color4f(0.03, 0.04, 0.05, 0.5)], None))
    c.drawPath(path_of(np.array([peaks[0], (960, 340), peaks[1], (x1 + 30, wall_top), (x0 - 30, wall_top)])), p)
    # walls with vertical stripes and a scalloped valance
    for i in range(18):
        xa = x0 + (x1 - x0) * i / 18
        xb = x0 + (x1 - x0) * (i + 1) / 18
        poly = np.array([(xa, wall_top), (xb, wall_top), (xb, base_y), (xa, base_y)])
        painterly(c, path_of(poly), mix(a_col if i % 2 else b_col, "#000", 0.25), seed=640 + i, strength=0.5, angle=1.57)
    for i in range(18):
        xa = x0 + (x1 - x0) * i / 18
        sc = ellipse(xa + (x1 - x0) / 36, wall_top, (x1 - x0) / 36, 26, 12, 0, math.pi)
        c.drawPath(path_of(np.vstack([[(xa, wall_top)], sc, [(xa + (x1 - x0) / 18, wall_top)]])), paint(mix(a_col, "#000", 0.1)))
    # holes in the canvas
    r = rng(9)
    for hx, hy, hr in ([(640, 470, 34), (1240, 430, 40), (980, 520, 22), (560, 680, 20), (1390, 660, 26)] if torn else []):
        pts = [(hx + math.cos(a) * hr * (0.5 + 0.7 * r.random()) * 0.7, hy + math.sin(a) * hr * (0.6 + 0.8 * r.random()) * 1.4)
               for a in np.linspace(0, math.tau, 15, endpoint=False)]
        c.drawPath(path_of(np.array(pts)), paint("#0a0d10"))
        ink_line(c, np.array(pts + [pts[0]]), 2.0, do_boil=False, alpha=0.7)
    # entrance: dark arch, flaps tied back
    arch = np.vstack([[(890, base_y)], ellipse(960, 640, 70, 70, 20, math.pi, 2 * math.pi), [(1030, base_y)]])
    c.drawPath(path_of(arch), paint("#07090b"))
    for sd in (-1, 1):
        flap = np.array([(960 + sd * 70, 620), (960 + sd * 120, base_y), (960 + sd * 80, base_y), (960 + sd * 66, 680)])
        painterly(c, path_of(flap), mix(b_col, "#000", 0.35), seed=690 + sd, strength=0.4)
        ink_line(c, flap, 1.8, closed=True, do_boil=False)
    # poles
    for (px, py) in peaks:
        c.drawRect(skia.Rect.MakeLTRB(px - 6, py - 70, px + 6, py + 4), paint("#2a2420"))
    ink_line(c, np.array([peaks[0], (960, 340), peaks[1], (x1 + 30, wall_top), (x1, base_y), (x0, base_y), (x0 - 30, wall_top), peaks[0]]),
             3.0, do_boil=False, alpha=0.85)
    # guy ropes + stakes
    for (ax, ay, bx) in [(x0 - 30, wall_top, 250), (x0 + 140, wall_top + 4, 330), (x1 + 30, wall_top, 1700), (x1 - 140, wall_top + 4, 1610)]:
        c.drawLine(ax, ay, bx, base_y + 30, paint("#1c1814", 0.8, stroke=1.6))
        c.drawRect(skia.Rect.MakeLTRB(bx - 3, base_y + 18, bx + 3, base_y + 34), paint("#2a2018"))
    # dead light bulbs along the valance
    for i in range(30):
        x = x0 + (x1 - x0) * i / 29
        y = wall_top + 40 + 12 * math.sin(math.pi * ((i % 6) / 5))
        c.drawCircle(x, y, 4, paint("#3a3832"))
    return s.makeImageSnapshot().withDefaultMipmaps()


@lru_cache(None)
def ext_ground():
    s, c = _hi()
    ground = np.array([(-20, 760), (W + 20, 760), (W + 20, H + 20), (-20, H + 20)])
    painterly(c, path_of(ground), "#1d241f", seed=700, strength=0.8, angle=0.0)
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 760), skia.Point(0, 1080)],
                [skia.Color4f(0.12, 0.16, 0.18, 0.5), skia.Color4f(0.0, 0.0, 0.0, 0.0)], None))
    c.drawPath(path_of(ground), p)
    # puddles reflect the sky
    for (x, y, rx) in [(620, 860, 160), (1180, 900, 220), (300, 990, 140), (1600, 1000, 180), (930, 1040, 120)]:
        c.drawPath(path_of(ellipse(x, y, rx, rx * 0.16, 30)), paint("#33434d"))
        c.drawPath(path_of(ellipse(x - rx * 0.2, y - 2, rx * 0.5, rx * 0.05, 20)), paint("#4f606a", 0.6))
    # broken sign on a post (left), spelled out and faded
    c.save()
    c.translate(300, 830)
    c.rotate(-7)
    c.drawRect(skia.Rect.MakeLTRB(-8, -40, 8, 160), paint("#2c241c"))
    board = np.array([(-180, -150), (180, -150), (176, -30), (-176, -36)])
    painterly(c, path_of(board), "#5a4a3a", seed=710, strength=0.6)
    ink_line(c, board, 2.5, closed=True, do_boil=False)
    text(c, "MARLOWE'S", 2, -86, "rye", 50, "#1e1612", 0.7)
    text(c, "MARLOWE'S", 0, -88, "rye", 50, "#d8b880", 0.95)
    text(c, "MARVELOUS CIRCUS", 0, -48, "oldstd_b", 25, "#e2d2a8", 0.9)
    # peeling paint
    r = rng(3)
    for i in range(14):
        x, y = -170 + r.random() * 340, -145 + r.random() * 110
        c.drawPath(path_of(ellipse(x, y, 4 + r.random() * 10, 2 + r.random() * 5, 8)), paint("#4a3c30", 0.8))
    c.restore()
    return s.makeImageSnapshot().withDefaultMipmaps()


def _img(c, img, cam, depth, scale=1.4):
    with cam.layer(c, depth):
        c.drawImageRect(img, skia.Rect.MakeWH(W, H), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNearest), paint())


def grass(c, cam, t, seed=12):
    r = rng(seed)
    blades = r.random((140, 4))
    with cam.layer(c, 1.5):
        for (u, h, ph, k) in blades:
            x = -100 + u * (W + 200)
            y = 1090 + k * 40
            L = 60 + 120 * h
            sway = math.sin(t * 1.6 + ph * 6) * 10 + math.sin(t * 4.3 + ph * 9) * 3
            pts = np.array([(x, y), (x + sway * 0.4, y - L * 0.5), (x + sway, y - L)])
            ink_line(c, pts, 5 + 4 * k, color=mix("#0c1210", "#18221c", k), seed=int(ph * 100), taper=0.9, do_boil=False)


def flapping_strips(c, cam, t, flash):
    with cam.layer(c, 0.75):
        for i, (x, y, L) in enumerate([(636, 512, 90), (1236, 480, 110), (1388, 690, 50), (558, 702, 40)]):
            sw = math.sin(t * (2.1 + 0.4 * i) + i * 1.3) * 0.5 + math.sin(t * 6 + i) * 0.1
            pts = []
            for j in range(8):
                u = j / 7
                a = sw * u
                pts.append((x + math.sin(a) * L * u + u * 12, y + math.cos(a) * L * u))
            pts = np.array(pts)
            wv = np.linspace(9, 4, len(pts))[:, None]
            strip = np.vstack([pts - np.hstack([wv, 0 * wv]), (pts + np.hstack([wv, 0 * wv]))[::-1]])
            shape(c, strip, mix("#7e4c44", "#a9a593", i % 2), 1.6, seed=760 + i, shadow=False)


# ============================================================================ shots

def ext_tent_shot(c, lt, T, t):
    light_cold()
    z = lerp(1.0, 1.28, ease_io(lt / 8.2, 1.6))
    cam = Cam(lerp(960, 960, lt / 8), lerp(560, 630, ease_io(lt / 8.2)), z)
    flash = lightning_flash(t, BEATS["s1_lightning"])
    _img(c, ext_sky(), cam, 0.15)
    if flash > 0:
        with cam.layer(c, 0.15):
            c.drawRect(skia.Rect.MakeLTRB(-500, -500, W + 500, 760), paint("#c8dcff", 0.45 * flash, blend=skia.BlendMode.kScreen))
            # the bolt itself, far left
            if flash > 0.3:
                r = rng(int(BEATS["s1_lightning"][0] * 10))
                x, y = 380.0, -20.0
                pts = [(x, y)]
                while y < 560:
                    x += (r.random() - 0.5) * 70; y += 40 + r.random() * 40
                    pts.append((x, y))
                ink_line(c, np.array(pts), 4 * flash, color="#eef4ff", do_boil=False, taper=0.3)
    rain(c, lt, seed=2, n=240, speed=1500, length=30, a=0.18, width=1.0, depth_layers=2)
    _img(c, ext_tent(), cam, 0.7)
    flapping_strips(c, cam, lt, flash)
    _img(c, ext_ground(), cam, 1.0)
    with cam.layer(c, 1.0):
        splashes(c, lt, 840, seed=4, n=70, a=0.45)
    fog(c, lt, 770, 80, "#3a4a54", a=0.18, seed=6)
    grass(c, cam, lt)
    rain(c, lt, seed=7, n=520, speed=2100, length=52, a=0.30, width=1.6)
    if flash > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint("#dce8ff", 0.18 * flash, blend=skia.BlendMode.kScreen))
    return grade(flash)


def _sky_holes(c):
    pass


def ring_alone(c, lt, T, t):
    """Push in on old Silas sitting alone in the empty ring; rain drips from the brim."""
    light_cold()
    u = ease_io(lt / 10.5, 1.5)
    k = lerp(1.0, 1.6, u)
    piv = (960.0, 700.0)
    tq = twos(lt)
    flash = lightning_flash(t, BEATS["s1_lightning"])
    c.save()
    c.translate(piv[0], piv[1]); c.scale(k, k); c.translate(-piv[0], -piv[1])
    tent.draw_ring_medium(c, lt, ACT, xshift=0, occupancy=0.0, torn=True, lights_on=0.0, flaps=1.0, wind=0.35, blur=4.0)
    # darkness everywhere except the moonlight
    c.drawRect(skia.Rect.MakeLTRB(-400, -400, W + 400, H + 400), paint("#05080c", 0.58))
    radial(c, 960, 905, 380, "#9fb8c8", 0.5, blend=skia.BlendMode.kScreen)
    cone(c, (1060, -120), (960, 880), 230, "#a8c4d6", a=0.15 + 0.08 * flash, soft=40)
    fig = Silas(2)
    s = 0.95
    br = breathing(lt, 0.2)
    P = fig.pose(x=958, y=900, s=s, turn=0.32, face=1, pelvis=(4.0, 76.0 + br * 1.2), lean=0.36, chest=0.16,
                 head_rot=0.28 + 0.02 * br, head_dx=4.0, foot_n=(46.0, 0.0), foot_f=(10.0, 0.0), breath=br, hat_tilt=0.12,
                 hand_n="grip", smile=-0.1, cold=0.0, brim_shadow=1.0, blink=auto_blinks(lt, 13), hat_drop=17.0)
    J = fig.solve(P)
    tap = 2.0 * max(0.0, math.sin(tq * 2.4)) ** 8
    P["arm_n"] = (58.0, -228.0)
    P["cane"] = ("hand_n", 0.04, "front", "abs")
    kf = J["knee_f"]
    P["arm_f"] = (float(kf[0]) - 6.0, float(kf[1]) - 8.0 - tap)
    P["hand_f"] = "relax"
    _pedestal(c, 960, 900, s)
    fig.draw(c, P)
    _brim_drips(c, fig, lt)
    splashes(c, lt, 910, seed=15, n=30, x0=640, x1=1280, col="#aac4d2", a=0.35, rate=2.0, scale=1.0)
    rain(c, lt, seed=21, n=200, speed=1300, length=34, a=0.38, width=1.3, area=(760, -120, 1180, 910), angle=0.05)
    c.restore()
    rain(c, lt, seed=22, n=160, speed=1700, length=40, a=0.12, width=1.0)
    if flash > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint("#dce8ff", 0.16 * flash, blend=skia.BlendMode.kScreen))
    return grade(flash, vignette=1.3)


def _pedestal(c, x, y, s=0.42):
    """Circus drum pedestal (scuffed) he sits on."""
    w, h = 64 * s, 120 * s
    body = np.array([(x - w, y), (x - w * 0.9, y - h), (x + w * 0.9, y - h), (x + w, y)])
    shape(c, body, "#4a3a36", 3.0 * s, seed=980, shade_depth=12 * s)
    for i in range(1, 4):
        yy = y - h * i / 4
        c.drawLine(x - w * 0.95, yy, x + w * 0.95, yy, paint("#8a7a52", 0.55, stroke=2.4 * s))
    st = []
    for j in range(10):
        rr = (16 if j % 2 == 0 else 7) * s
        a2 = -math.pi / 2 + j * math.pi / 5
        st.append((x + math.cos(a2) * rr, y - h * 0.5 + math.sin(a2) * rr))
    c.drawPath(path_of(np.array(st)), paint("#8a7a52", 0.6))
    shape(c, ellipse(x, y - h, w * 0.9, 9 * s, 20), "#5e4a44", 2.4 * s, seed=981, shadow=False)

def _brim_drips(c, fig, t):
    """Drops gather on the front of the hat brim and fall (smooth 24 fps)."""
    J, M = fig.J, fig.M
    HX = fig.hat_xf_head(J, M)
    for k, (bx, period, off) in enumerate([(38.0, 1.1, 0.0), (-30.0, 1.4, 0.5), (12.0, 0.9, 0.3)]):
        p0 = HX(np.array([bx, 8.0]))
        ph = ((t + off) % period) / period
        grow = min(1.0, ph / 0.55)
        if ph < 0.55:
            r = 0.6 + 1.6 * grow
            c.drawCircle(float(p0[0]), float(p0[1]) + r, r, paint("#cfe2ec", 0.85))
        else:
            dt = (ph - 0.55) * period
            y = p0[1] + 2.2 + 0.5 * 1800 * dt * dt
            if y < p0[1] + 200:
                c.drawPath(path_of(ellipse(float(p0[0]), y, 1.6, 2.6, 8)), paint("#cfe2ec", 0.85))


SHOTS = dict(ext_tent=ext_tent_shot, ring_alone=ring_alone)
