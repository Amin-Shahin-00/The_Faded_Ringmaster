"""SCENE 4 - THE CHANGE (1:18 - 1:45). The trailer, the cracked mirror, one bare bulb.

Mirror shots are framed as the mirror's point of view: we look out of the glass at
Silas, with the cracks and the frame in front of him."""
import math
from functools import lru_cache
import numpy as np
import skia
from lib.core import W, H, Xf, keys, clamp, lerp, remap, smooth, ease_io, ease_out, twos, paint, mix, rng, hexc, vnoise
from lib.ink import S, shape, ink_line, fill, ellipse, spline, path_of
from lib.frame import Cam, text, new_surface
from config.palettes import GRADE
from config.timeline import BEATS, LAUGH_START
from rigs.silas import Silas
from scenes.common import radial, cone, painterly, rain
from scenes.silas_moves import auto_blinks, breathing


def light_bulb():
    S.key = (0.05, -1.0)
    S.shadow_col = "#140c14"
    S.shadow_a = 0.5
    S.rim = None
    S.rim_a = 0.0


def grade(**kw):
    g = dict(GRADE[2])
    g.update(kw)
    return g


def bulb_flicker(t):
    """Mostly steady; one soft dip near the end of the scene (ramped, never a 1-frame strobe)."""
    v = 1.0 - 0.04 * vnoise(t * 3.0, 9)
    for t0 in (103.9, 104.35):
        u = (t - t0) / 0.25
        if 0 <= u <= 1:
            v *= 1 - 0.55 * math.sin(math.pi * u)
    return v


# ============================================================================ trailer set

@lru_cache(None)
def trailer_bg():
    s = new_surface(int(W * 1.3), int(H * 1.3))
    c = s.getCanvas()
    c.scale(1.3, 1.3)
    c.clear(0xFF000000)
    # wooden plank walls
    for i in range(12):
        x0 = -20 + i * 170
        plank = np.array([(x0, -20), (x0 + 168, -20), (x0 + 168, 860), (x0, 860)])
        painterly(c, path_of(plank), mix("#3a2c26", "#2c2220", (i % 3) / 3), seed=2000 + i, strength=0.6, angle=1.57)
        ink_line(c, plank[[1, 2]], 1.6, alpha=0.5, do_boil=False)
    # floor
    painterly(c, path_of(np.array([(-20, 850), (W + 20, 850), (W + 20, H + 20), (-20, H + 20)])), "#241a16", seed=2020, strength=0.6)
    ink_line(c, np.array([(-20, 850), (W + 20, 850)]), 2.0, do_boil=False)
    # small window with rain (left)
    c.drawRect(skia.Rect.MakeLTRB(170, 220, 450, 470), paint("#18222c"))
    c.drawRect(skia.Rect.MakeLTRB(170, 220, 450, 470), paint("#120c0a", stroke=14))
    c.drawLine(310, 220, 310, 470, paint("#120c0a", stroke=8))
    # hanging costumes (old act costumes)
    for k, (x, col) in enumerate([(600, "#5a3a3a"), (680, "#3a4a5a"), (760, "#6a5a3a")]):
        c.drawLine(560, 260, 820, 260, paint("#1a1412", stroke=5))
        cost = np.array([(x - 30, 262), (x + 30, 262), (x + 44, 560), (x - 44, 560)])
        painterly(c, path_of(cost), col, seed=2030 + k, strength=0.5, angle=1.57)
        ink_line(c, cost, 1.8, closed=True, do_boil=False, alpha=0.8)
    # old poster on the wall (Marlowe's) - faded
    c.save(); c.translate(1000, 330); c.rotate(3)
    painterly(c, path_of(np.array([(-90, -120), (90, -120), (90, 120), (-90, 120)])), "#9a8a66", seed=2040, strength=0.5)
    text(c, "MARLOWE'S", 0, -70, "rye", 30, "#6a3a32")
    c.restore()
    return s.makeImageSnapshot().withDefaultMipmaps()


def draw_trailer(c, cam):
    with cam.layer(c, 0.9):
        c.drawImageRect(trailer_bg(), skia.Rect.MakeWH(W, H), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNearest), paint())


def window_rain(c, cam, t):
    with cam.layer(c, 0.9):
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(177, 227, 443, 463))
        rain(c, t, seed=60, n=60, speed=900, length=20, a=0.4, area=(170, 220, 450, 470), angle=0.08)
        r = rng(61)
        for i in range(14):   # drops sliding on the glass
            x = 180 + r.random() * 260
            y = 220 + ((t * (20 + 30 * r.random()) + r.random() * 250) % 250)
            c.drawCircle(x, y, 2.5, paint("#8aa0b0", 0.6))
        c.restore()


def bulb(c, x, y, t, k=1.0, cord_top=-40):
    sway = math.sin(t * 0.9) * 6
    bx = x + sway
    c.drawLine(x, cord_top, bx, y - 22, paint("#0c0a0a", stroke=3))
    radial(c, bx, y, 900 * k, "#e8d8a8", 0.32 * k, blend=skia.BlendMode.kScreen)
    radial(c, bx, y, 160 * k, "#fff0c8", 0.7 * k, blend=skia.BlendMode.kScreen)
    c.drawRect(skia.Rect.MakeLTRB(bx - 9, y - 26, bx + 9, y - 10), paint("#3a3634"))
    shape(c, ellipse(bx, y, 14, 18, 16), mix("#7a7060", "#fffbe8", k), 2.0, seed=2050, shadow=False)
    return bx


# ============================================================================ mirror framing

CRACK_ORIGIN = (560.0, 300.0)


@lru_cache(None)
def crack_lines():
    r = rng(70)
    lines = []
    for i in range(11):
        ang = i * math.tau / 11 + r.random() * 0.3
        L = 300 + r.random() * 900
        pts = [np.array(CRACK_ORIGIN)]
        p = np.array(CRACK_ORIGIN)
        n = 7
        for j in range(n):
            ang += (r.random() - 0.5) * 0.4
            p = p + np.array([math.cos(ang), math.sin(ang)]) * L / n
            pts.append(p)
        lines.append(np.array(pts))
    rings = []
    for rr in (40, 95):
        rings.append(ellipse(CRACK_ORIGIN[0], CRACK_ORIGIN[1], rr, rr * 0.9, 18))
    return lines, rings


def mirror_overlay(c, t, k=1.0):
    """Cracks on the glass, dust, and the dark wooden mirror frame at the edges."""
    lines, rings = crack_lines()
    for l in lines:
        ink_line(c, l + 1.5, 2.2, color="#000000", alpha=0.5, do_boil=False, taper=0.5)
        ink_line(c, l, 1.4, color="#e8ecf0", alpha=0.55, do_boil=False, taper=0.5)
    for r_ in rings:
        ink_line(c, r_, 1.2, color="#e8ecf0", alpha=0.35, closed=True, do_boil=False)
    # a shard slightly offset (refraction)
    shard = np.array([CRACK_ORIGIN, lines[2][3], lines[3][3]])
    c.drawPath(path_of(shard), paint("#ffffff", 0.05))
    # glass sheen + frame
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(W, H)],
                [skia.Color4f(1, 1, 1, 0.05), skia.Color4f(1, 1, 1, 0.0), skia.Color4f(1, 1, 1, 0.04)], [0, 0.5, 1]))
    c.drawRect(skia.Rect.MakeWH(W, H), p)
    fr = "#1e1410"
    edge = 46
    outer = skia.Path(); outer.addRect(skia.Rect.MakeWH(W, H))
    inner = skia.Path(); inner.addRoundRect(skia.Rect.MakeLTRB(edge, edge * 0.8, W - edge, H - edge * 0.8), 60, 60)
    frame = skia.Op(outer, inner, skia.PathOp.kDifference_PathOp)
    c.drawPath(frame, paint(fr))
    c.drawPath(inner, paint("#000000", 0.8, stroke=5))
    c.drawPath(inner, paint("#6a5040", 0.4, stroke=2))


def mirror_bg(c, t, k):
    """What the mirror sees behind Silas: the dim trailer."""
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#120e10"))
    for i in range(10):
        x0 = -40 + i * 220
        c.drawRect(skia.Rect.MakeLTRB(x0, 0, x0 + 216, H), paint(mix("#2a201c", "#221a18", i % 2)))
    c.drawRect(skia.Rect.MakeLTRB(1420, 120, 1660, 900), paint("#16100e"))   # door
    c.drawCircle(1630, 520, 8, paint("#5a4a3a"))
    radial(c, 960, 160, 1100, "#e8d8a8", 0.2 * k, blend=skia.BlendMode.kScreen)


# ============================================================================ shots

def trailer(c, lt, T, t):
    light_bulb()
    k = bulb_flicker(t)
    z = lerp(1.22, 1.4, ease_io(lt / 5.5))
    cam = Cam(lerp(1080, 1120, ease_io(lt / 5.5)), 590, z)
    draw_trailer(c, cam)
    window_rain(c, cam, lt)
    tq = twos(lt)
    fig = Silas(2)
    br = breathing(lt, 0.22)
    with cam.layer(c, 1.0):
        # vanity table + mirror (right)
        shape(c, np.array([(1150, 700), (1700, 700), (1700, 730), (1150, 730)]), "#3a2a22", 3, seed=2100)
        shape(c, np.array([(1180, 730), (1210, 730), (1210, 860), (1180, 860)]), "#2c201a", 2.5, seed=2101)
        shape(c, np.array([(1640, 730), (1670, 730), (1670, 860), (1640, 860)]), "#2c201a", 2.5, seed=2102)
        mx = np.array([(1360, 290), (1640, 290), (1640, 690), (1360, 690)])
        shape(c, mx + np.array([(-18, -18), (18, -18), (18, 10), (-18, 10)]), "#1e1410", 3, seed=2103)
        c.drawPath(path_of(mx), paint("#1c2226"))
        # reflection: Silas seen from the front, smaller, inside the mirror
        c.save()
        c.clipPath(path_of(mx), skia.ClipOp.kIntersect, True)
        ref = Silas(2)
        RP = ref.pose(x=1500, y=790, s=1.1, turn=0.12, face=-1, pelvis=(0.0, 70.0), makeup=1.0, brim_shadow=0.3, hat_drop=2,
                      smile=0.0, blink=auto_blinks(lt, 50), breath=br, arm_n=(30.0, -220.0), arm_f=(-30.0, -220.0))
        ref.draw(c, RP)
        c.drawRect(skia.Rect.MakeLTRB(1300, 250, 1700, 720), paint("#a0b0c0", 0.08))
        c.restore()
        lines, _ = crack_lines()
        for l in lines[:6]:
            ll = (l - np.array(CRACK_ORIGIN)) * 0.22 + np.array([1430, 380])
            ink_line(c, ll, 1.0, color="#e8ecf0", alpha=0.6, do_boil=False)
        # stool + Silas in profile facing the mirror
        shape(c, np.array([(700, 760), (840, 760), (830, 860), (710, 860)]), "#2c201a", 3, seed=2110)
        P = fig.pose(x=800, y=860, s=0.95, turn=0.92, face=1, pelvis=(0.0, 92.0), lean=0.12, foot_n=(70.0, 0.0), foot_f=(55.0, 0.0),
                     arm_n=(150.0, -150.0), arm_f=(140.0, -158.0), hand_n="relax", hand_f="relax", makeup=1.0, brim_shadow=0.4,
                     hat_drop=3.0, smile=0.0, blink=auto_blinks(lt, 51), breath=br, head_rot=0.08)
        fig.draw(c, P)
        bulb(c, 1500, 220, t, k, cord_top=-60)
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#05040a", 0.25))
    return grade(vignette=1.35)


def _mirror_silas(c, lt, t, s, cx, ground, extra):
    fig = Silas(2)
    br = breathing(lt, 0.22)
    P = fig.pose(x=cx, y=ground, s=s, turn=0.06, face=1, pelvis=(0.0, 92.0), breath=br, makeup=1.0, brim_shadow=0.25,
                 hat_drop=2.0, smile=0.0, blink=auto_blinks(lt, 52), look=(0.0, 0.0))
    P.update(extra)
    return fig, P


def wipe(c, lt, T, t):
    light_bulb()
    k = bulb_flicker(t)
    tq = twos(lt)
    mirror_bg(c, lt, k)
    s = 2.7
    fig, P = _mirror_silas(c, lt, t, s, 960, 1030 + 92 * s * 0 + 260, {})
    # rag strokes across his right cheek (screen-left), three passes
    strokes = [(1.0, 1.8), (2.3, 3.1), (3.6, 4.6)]
    wipe_u = 0.0
    rag = np.array([-10.0, -360.0])
    for i, (a, b) in enumerate(strokes):
        if tq >= a:
            wipe_u = (i + remap(tq, a, b)) / 3
    xs = keys(tq, [(0.3, -60.0), (1.0, -40.0), (1.8, -8.0), (2.3, -42.0), (3.1, -8.0), (3.6, -44.0), (4.6, -6.0), (5.4, -60.0)])
    ys = keys(tq, [(0.3, -120.0), (1.0, -300.0), (1.8, -296.0), (2.3, -282.0), (3.1, -276.0), (3.6, -268.0), (4.6, -262.0), (5.4, -120.0)])
    P.update(wipe=clamp(wipe_u), arm_n=(xs, ys), hand_n="fist", wrist_n=-1.2, look=(0.2, 0.0), narrow=0.15)
    fig.draw(c, P, props={"after": {"arm_n": _rag}})
    mirror_overlay(c, lt, k)
    bx = 960 + math.sin(t * 0.9) * 6
    radial(c, bx, -40, 300, "#fff0c8", 0.4 * k, blend=skia.BlendMode.kScreen)
    return grade(vignette=1.2)


def _rag(cv, fig, J, M):
    X = fig.hand_xf(J, M, "n")
    cloth = spline(np.array([(4, -16), (26, -20), (40, -6), (36, 14), (14, 22), (-4, 12)]), closed=True, n=3)
    shape(cv, X(cloth), "#d8d0c0", fig.lw(), seed=2200, shade_depth=4)
    ink_line(cv, X(np.array([(10, -8), (28, 4)])), fig.lw(0.4), seed=2201)
    fill(cv, X(ellipse(30, 2, 7, 5, 10)), "#f0e4dc", alpha=0.7)


def coat(c, lt, T, t):
    light_bulb()
    k = bulb_flicker(t)
    tq = twos(lt)
    mirror_bg(c, lt, k)
    s = 2.3
    # reach for the lapels, slide the coat open... stop... close it and button it
    op = keys(tq, [(0.6, 0.0), (1.6, 0.0), (2.4, 0.75, "io"), (3.4, 0.75), (4.6, 0.0, "io3"), (6.0, 0.0)])
    hn = keys(tq, [(0, (-34.0, -96.0)), (0.9, (-20.0, -214.0)), (1.6, (-19.0, -216.0)), (2.4, (-46.0, -206.0)), (3.4, (-46.0, -206.0)),
                   (4.6, (-18.0, -214.0)), (5.0, (-10.0, -200.0)), (6.0, (-10.0, -198.0))])
    hf = keys(tq, [(0, (34.0, -96.0)), (0.9, (20.0, -214.0)), (1.6, (19.0, -216.0)), (2.4, (46.0, -206.0)), (3.4, (46.0, -206.0)),
                   (4.6, (18.0, -214.0)), (5.0, (8.0, -196.0)), (6.0, (8.0, -194.0))])
    fig, P = _mirror_silas(c, lt, t, s, 960, 1290, dict(coat_open=op, arm_n=tuple(hn), arm_f=tuple(hf), hand_n="pinch", hand_f="pinch",
                                                      wipe=1.0, look=(0.0, 0.25 if 2.4 < tq < 3.8 else 0.0),
                                                      brow=keys(tq, [(2.2, 0.0), (2.8, 0.4), (3.8, -0.2)])))
    P["lean"] = -0.02 * op
    fig.draw(c, P)
    mirror_overlay(c, lt, k)
    radial(c, 960 + math.sin(t * 0.9) * 6, -40, 300, "#fff0c8", 0.4 * k, blend=skia.BlendMode.kScreen)
    return grade(vignette=1.2)


def cane(c, lt, T, t):
    light_bulb()
    k = bulb_flicker(t)
    tq = twos(lt)
    cam = Cam(900, 560, 1.75)
    draw_trailer(c, cam)
    snap = BEATS["s4_cane_snap"] - 95.0      # 2.0
    fig = Silas(2)
    br = breathing(lt, 0.22)
    s = 0.95
    # the cane is a free object: centre + angle (local units, relative to Silas's root)
    cx = keys(tq, [(0, 70.0), (0.6, 70.0), (1.4, 50.0), (snap - 0.15, 56.0), (snap, 70.0, "in")])
    cy = keys(tq, [(0, -100.0), (0.6, -100.0), (1.4, -262.0, "out"), (snap - 0.15, -272.0), (snap, -150.0, "in")])
    ca = keys(tq, [(0, -1.45), (0.6, -1.45), (1.4, 0.0), (snap, 0.0)])
    knee_up = keys(tq, [(0.8, 0.0), (1.6, 34.0), (snap, 38.0), (snap + 0.6, 20.0)])
    with cam.layer(c, 1.0):
        shape(c, np.array([(700, 760), (840, 760), (830, 860), (710, 860)]), "#2c201a", 3, seed=2110)
        root = np.array([800.0, 860.0])
        P = fig.pose(x=root[0], y=root[1], s=s, turn=0.85, face=1, pelvis=(0.0, 92.0), lean=keys(tq, [(1.4, 0.0), (snap, 0.22, "in"), (snap + 0.5, 0.1)]),
                     foot_n=(66.0, knee_up), foot_f=(50.0, 0.0), hand_n="grip", hand_f="grip", makeup=1.0, wipe=1.0, brim_shadow=0.5,
                     hat_drop=keys(tq, [(2.5, 3.0), (4.5, 8.0)]), smile=0.0, blink=auto_blinks(lt, 53), breath=br,
                     narrow=keys(tq, [(snap - 0.2, 0.0), (snap, 0.5), (snap + 0.3, 0.1)]), cold=keys(tq, [(2.5, 0.0), (4.4, 0.6)]),
                     cane_free=True)
        ang = ca
        d = np.array([math.cos(ang), math.sin(ang)])
        center = np.array([cx, cy])
        if tq < snap:
            P["arm_n"] = tuple(center + d * 70)
            P["arm_f"] = tuple(center - d * 70)
            P["cane"] = ("hand_n", 0.0, "front")
        else:
            # handle piece stays in the near hand and is rolled between the fingers
            roll = math.sin((tq - snap - 0.6) * 5.0) * 0.5 * remap(tq, snap + 0.5, snap + 0.9)
            hpos = keys(tq, [(snap, tuple(center + d * 70)), (snap + 0.6, (84.0, -228.0)), (4.5, (84.0, -230.0))])
            P["arm_n"] = tuple(hpos)
            P["handle"] = ("hand_n", 1.2 + roll)
            P["wrist_n"] = -0.6
            P["arm_f"] = keys(tq, [(snap, tuple(center - d * 70)), (snap + 0.5, (60.0, -100.0))])
            P["arm_f"] = tuple(P["arm_f"])
            P["hand_f"] = "relax"
        fig.draw(c, P)
        M = fig.M
        if tq < snap:
            # whole cane: ball at the near-hand end
            X = M.t(*(center + d * 112)).r(ang + math.pi / 2)
            fig.draw_cane(c, fig.J, M, X=X)
            fig.draw_arm(c, fig.J, M, "n")     # near hand back on top of the cane
        else:
            # far piece falls to the floor, tumbling, then lies still
            dt = tq - snap
            p0 = center - d * 10
            g = 900.0
            fall_y = min(p0[1] + 0.5 * g * dt * dt + 20 * dt, -6.0)
            fx = p0[0] - 40 * dt
            rot_ = ang + min(dt * 3.0, 1.4)
            X = M.t(fx, fall_y).r(rot_)
            shaft = np.array([(-100, -3.2), (85, -2.8), (90, 0), (85, 2.8), (-100, 3.2), (-96, 0.5), (-103, -1)])
            shape(c, X(shaft), fig.C["cane"], fig.lw(0.7), seed=2300, shade_depth=1.5)
            # splinters at the snap
            if dt < 0.5:
                r = rng(80)
                for i in range(8):
                    a = r.random() * math.tau
                    sp = 80 + r.random() * 160
                    q = M((center + np.array([math.cos(a), math.sin(a) - 0.3]) * sp * dt + np.array([0, 0.5 * g * dt * dt * 0.4])))
                    c.drawLine(float(q[0]), float(q[1]), float(q[0]) + 6 * math.cos(a), float(q[1]) + 6 * math.sin(a),
                               paint("#3a2a20", 1 - dt * 2, stroke=2))
        bulb(c, 1250, 300, t, k, cord_top=-60)
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#05040a", 0.2))
    return grade(vignette=1.3)


def smile(c, lt, T, t):
    light_bulb()
    k = bulb_flicker(t)
    tq = twos(lt)
    mirror_bg(c, lt, k)
    z = lerp(1.0, 1.12, ease_io(lt / 5.5))
    c.save(); c.translate(960, 420); c.scale(z, z); c.translate(-960, -420)
    s = 3.3
    laugh0 = LAUGH_START - 99.5
    laughing = tq > laugh0
    shake = math.sin(tq * math.tau * 4.0) * remap(tq, laugh0, laugh0 + 0.4) * (1 - remap(tq, 5.0, 5.5))
    smile_ = keys(tq, [(0.3, 0.0), (1.1, 0.85, "out"), (2.0, 0.8), (3.6, 0.35, "io")])
    cold = keys(tq, [(2.0, 0.0), (3.6, 1.0, "io")])
    fig, P = _mirror_silas(c, lt, t, s, 960, 1500, dict(
        wipe=1.0, smile=smile_, cold=cold, crow=keys(tq, [(1.0, 1.0), (2.6, 0.0)]),
        brow=keys(tq, [(0.4, 0.0), (1.1, 0.8), (2.0, 0.7), (3.6, -0.5)]), narrow=keys(tq, [(2.0, 0.0), (3.6, 0.4)]),
        open=0.22 * abs(shake) if laughing else 0.0, head_rot=keys(tq, [(2.0, 0.0), (3.6, 0.06)]) + 0.012 * shake,
        hat_drop=keys(tq, [(2.4, 2.0), (4.2, 9.0)]), brim_shadow=keys(tq, [(2.4, 0.25), (4.2, 0.85)]),
        pelvis=(0.0, 92.0 + 2.5 * abs(shake)), look=(0.0, keys(tq, [(2.0, 0.0), (3.0, 0.4)])),
        blink=auto_blinks(lt, 54) if tq < 2.0 else 0.0))
    fig.draw(c, P)
    c.restore()
    mirror_overlay(c, lt, k)
    radial(c, 960 + math.sin(t * 0.9) * 6, -40, 300, "#fff0c8", 0.4 * k, blend=skia.BlendMode.kScreen)
    dark = 1 - k
    if dark > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint("#000000", 0.6 * dark))
    return grade(vignette=1.25)


SHOTS = dict(trailer=trailer, wipe=wipe, coat=coat, cane=cane, smile=smile)
