"""SCENE 5 - THE RECRUITMENT (1:45 - 2:20). Act 3: deep shadow, dark teal, hard rim light, rain.

Three visits, same pattern: Silas steps out of the shadows and holds out an old
ticket stamped ADMIT ONE. Then the four walk toward camera in slow motion."""
import math
from functools import lru_cache
import numpy as np
import skia
from lib.core import W, H, Xf, keys, clamp, lerp, remap, smooth, ease_io, ease_out, twos, paint, mix, rng, hexc, vnoise
from lib.ink import S, shape, ink_line, fill, ellipse, spline, path_of
from lib.frame import Cam, text, new_surface
from lib.motion import Walk, arm_swing_fk, follow
from config.palettes import GRADE
from config.timeline import BEATS
from rigs.silas import Silas
from rigs.cast import Bruno, Lena, Pip
from rigs.crowd import make_people, person
from scenes.common import radial, cone, painterly, rain, splashes, fog, draw_ticket, draw_lit
from scenes.silas_moves import auto_blinks, breathing


def light3(rim=(0.6, -0.8)):
    S.key = (-0.3, -0.95)
    S.shadow_col = "#02080a"
    S.shadow_a = 0.55
    S.rim = rim
    S.rim_col = "#c4ecf0"
    S.rim_a = 0.6


def grade(**kw):
    g = dict(GRADE[3])
    g.update(kw)
    return g


def _hi(scale=1.3):
    s = new_surface(int(W * scale), int(H * scale))
    c = s.getCanvas()
    c.clear(0x00000000)
    c.scale(scale, scale)
    return s, c


def _img(c, img, cam, depth):
    with cam.layer(c, depth):
        c.drawImageRect(img, skia.Rect.MakeWH(W, H), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNearest), paint())


def ticket_at(c, X, scale, angle=0.0):
    """Ticket held between thumb and fingers of hand transform X."""
    p = X(np.array([30.0, -6.0]))
    draw_ticket(c, float(p[0]), float(p[1]), scale, angle)


def silas_step_out(t, t0, x_from, x_to, n=3, sd=0.62, face=1, s=1.0, ground=1000.0):
    """Slow, controlled Act 3 walk out of the dark (feet planted)."""
    L = abs(x_to - x_from) / s / (n - 0.4)
    w = Walk(t0, n, L, sd, start_u=0.0, stance=10, bob=2.0, lift=8, toe=0.3)
    return w, w.pose(t, s=s, face=face, origin_x=x_from, ground_y=ground)


# ============================================================================ docks

@lru_cache(None)
def docks_bg():
    s, c = _hi()
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, 700)],
                [skia.Color4f(*hexc("#03090b")), skia.Color4f(*hexc("#0d2226"))], None))
    c.drawRect(skia.Rect.MakeWH(W, H), p)
    # crane + ship silhouettes
    c.drawPath(path_of(np.array([(1250, 640), (1280, 120), (1300, 120), (1330, 640)])), paint("#071214"))
    c.drawPath(path_of(np.array([(1290, 130), (1800, 170), (1800, 185), (1290, 150)])), paint("#071214"))
    c.drawLine(1700, 180, 1700, 420, paint("#0a1a1c", stroke=2))
    hull = np.array([(-40, 520), (900, 500), (980, 560), (960, 650), (-40, 650)])
    c.drawPath(path_of(hull), paint("#0a1719"))
    for i in range(9):
        c.drawCircle(80 + i * 95, 560, 8, paint("#c8a060", 0.35))
    # water
    painterly(c, path_of(np.array([(-40, 640), (W + 40, 640), (W + 40, 760), (-40, 760)])), "#0a2226", seed=3000, strength=0.6)
    for i in range(30):
        x = 40 + i * 64
        c.drawLine(x, 660 + (i % 4) * 22, x + 30, 660 + (i % 4) * 22, paint("#2a5a60", 0.35, stroke=2))
    # pier deck
    deck = np.array([(-40, 750), (W + 40, 750), (W + 40, H + 40), (-40, H + 40)])
    painterly(c, path_of(deck), "#1a2224", seed=3001, strength=0.7)
    for i in range(14):
        y = 760 + i * i * 2.2
        c.drawLine(-40, y, W + 40, y, paint("#0a1012", 0.6, stroke=2))
    # crate stacks: left (where Silas waits in the dark) and right
    for (x0, y0, nx, ny) in [(40, 760, 3, 3), (1560, 760, 2, 2)]:
        for i in range(nx):
            for j in range(ny):
                x, y = x0 + i * 120, y0 - (j + 1) * 110
                cr = np.array([(x, y), (x + 116, y), (x + 116, y + 108), (x, y + 108)])
                painterly(c, path_of(cr), "#3a3026", seed=3010 + i * 7 + j, strength=0.6)
                ink_line(c, cr, 2.4, closed=True, do_boil=False)
                ink_line(c, np.array([(x, y), (x + 116, y + 108)]), 1.6, do_boil=False, alpha=0.7)
    # lamp post
    c.drawRect(skia.Rect.MakeLTRB(1196, 200, 1208, 760), paint("#0c1416"))
    c.drawPath(path_of(np.array([(1170, 200), (1234, 200), (1220, 232), (1184, 232)])), paint("#0c1416"))
    return s.makeImageSnapshot().withDefaultMipmaps()


def docks(c, lt, T, t):
    light3()
    tq = twos(lt)
    wide = lt < 4.5
    cam = Cam(960, 560, lerp(1.0, 1.06, lt / 4.5)) if wide else Cam(lerp(1060, 1080, (lt - 4.5) / 4.5), 600, 1.75)
    _img(c, docks_bg(), cam, 0.8)
    with cam.layer(c, 0.8):
        radial(c, 1202, 230, 60, "#ffe0a0", 0.9, blend=skia.BlendMode.kScreen)
        cone(c, (1202, 232), (1150, 900), 330, "#e0c890", a=0.2, soft=30)
        radial(c, 1150, 930, 420, "#d8c090", 0.25, blend=skia.BlendMode.kScreen)
    rain(c, lt, seed=50, n=200, speed=1600, length=30, a=0.18, width=1.0, depth_layers=2)
    br = breathing(lt, 0.22)
    s = 0.95
    ground = 1000.0
    with cam.layer(c, 1.0):
        # Bruno carries a crate in from the right and sets it down
        b = Bruno(3)
        bw = Walk(0.0, 4, 90, 0.5, start_u=0.0, stance=12, bob=3, lift=10)
        bp = bw.pose(tq, s=s, face=-1, origin_x=1640, ground_y=ground)
        down = keys(tq, [(2.0, 0.0), (2.6, 1.0, "io"), (3.0, 1.0), (3.4, 0.0)])
        turned = remap(tq, 3.2, 3.6)
        P = b.pose(**bp)
        crate_y = lerp(-385.0, -70.0, down) if tq < 3.0 else (-70.0 if tq >= 2.6 else -385.0)
        P.update(turn=lerp(0.9, 0.55, turned), pelvis=(0.0, bp["pelvis"][1] + 60 * down), lean=0.35 * down,
                 arm_n=(40.0 + 30 * down, crate_y - 40 + 60 * down) if tq < 3.0 else ("fk", 0.15, 0.3),
                 arm_f=(-40.0 + 30 * down, crate_y - 40 + 60 * down) if tq < 3.0 else ("fk", -0.1, 0.3),
                 hand_n="open", hand_f="open", blink=auto_blinks(lt, 60), smile=0.0, brow=0.2,
                 look=(0.0, keys(tq, [(5.0, 0.0), (5.6, 0.8), (7.0, 0.8), (8.0, 0.0)])))
        took = tq >= BEATS["s5_take_bruno"] - 105.0

        # crate (on shoulder until set down, then on the deck)
        bx = bp["x"]
        cxw = bx - s * (10 + 40 * down)
        cyw = ground + s * (crate_y if tq < 2.6 else -70.0) if tq < 3.0 else ground - 70 * s
        if tq >= 2.6:
            cxw = 1640 - s * 360 - 60 * s
        crate = np.array([(-58, -55), (58, -55), (58, 55), (-58, 55)]) * s + np.array([cxw, cyw])
        # Silas steps out of the shadows between the crates
        si = Silas(3)
        t0 = BEATS["s5_steps_bruno"] - 105.0
        sw_, sp = silas_step_out(tq, t0, 380.0, 820.0, n=3, s=s, ground=ground)
        SP = si.pose(**sp)
        offer = remap(tq, 4.3, 5.0)
        take_b = BEATS["s5_take_bruno"] - 105.0
        arm_pos = tuple(keys(tq, [(4.3, (40.0, -170.0)), (5.0, (150.0, -270.0)), (take_b, (150.0, -270.0)), (take_b + 0.7, (40.0, -170.0))]))
        SP.update(turn=0.82, hand_n="pinch", arm_n=arm_pos if tq >= 4.3 else ("fk", 0.05 * sw_.swing(tq), 0.2),
                  handle=("hand_f", 1.3), hand_f="grip", arm_f=("fk", -0.15, 0.5), blink=auto_blinks(lt, 61), breath=br, smile=0.15, cold=1.0)
        lit = remap(sp["x"], 520.0, 780.0)

        # Bruno reaches for it
        reach = remap(tq, 6.8, 7.4)
        if tq > 6.6:
            P["arm_n"] = keys(tq, [(6.6, (-30.0, -150.0)), (7.4, (90.0, -265.0), "io"), (8.4, (40.0, -230.0))])
            P["arm_n"] = tuple(P["arm_n"])
            P["hand_n"] = "pinch"
        draw_lit(c, si, SP, lit)
        if tq < 2.6:
            b.draw(c, P, props={"before": {"arm_n": lambda cv, f, J, M: shape(cv, crate, "#4a3a2c", 3, seed=3050)}})
        else:
            shape(c, crate, "#4a3a2c", 3, seed=3050)
            b.draw(c, P)
        # the ticket
        if offer > 0 and not took:
            ticket_at(c, si.hand_xf(si.J, si.M, "n"), 0.95 * s, -0.08)
        elif took:
            ticket_at(c, b.hand_xf(b.J, b.M, "n"), 0.95 * s, 0.2)
        splashes(c, lt, ground + 4, seed=52, n=40, col="#9ac8d0", a=0.35, rate=2.4)
    fog(c, lt, 760, 120, "#1c3a3e", a=0.25, seed=53)
    rain(c, lt, seed=54, n=420, speed=2000, length=46, a=0.28, width=1.4)
    return grade()


# ============================================================================ bar

@lru_cache(None)
def bar_bg():
    s, c = _hi()
    c.clear(0xFF05090a)
    # back wall, panelled
    for i in range(10):
        x0 = -40 + i * 220
        painterly(c, path_of(np.array([(x0, -20), (x0 + 216, -20), (x0 + 216, 700), (x0, 700)])), mix("#14201f", "#101a1a", i % 2), seed=3100 + i, strength=0.5, angle=1.57)
    # shelves with bottles (left)
    for row in range(3):
        y = 180 + row * 120
        c.drawRect(skia.Rect.MakeLTRB(60, y, 640, y + 10), paint("#2a2018"))
        r = rng(3110 + row)
        x = 80
        while x < 620:
            w = 16 + r.random() * 14; h = 50 + r.random() * 40
            col = ["#1a4a3a", "#4a2a1a", "#2a3a4a", "#3a3a1a"][int(r.random() * 4)]
            c.drawRect(skia.Rect.MakeLTRB(x, y - h, x + w, y), paint(col, 0.9))
            c.drawRect(skia.Rect.MakeLTRB(x + w * 0.3, y - h - 16, x + w * 0.7, y - h), paint(col, 0.9))
            x += w + 8 + r.random() * 10
    # dartboard (right wall)
    bx, by = 1500, 380
    for i, (r_, col) in enumerate([(120, "#1a1a1a"), (104, "#2a5a3a"), (94, "#e8dcc0"), (64, "#8a2a2a"), (54, "#e8dcc0"), (16, "#2a5a3a"), (7, "#8a2a2a")]):
        c.drawCircle(bx, by, r_, paint(col))
    for k in range(20):
        a = k * math.tau / 20
        c.drawLine(bx + math.cos(a) * 16, by + math.sin(a) * 16, bx + math.cos(a) * 104, by + math.sin(a) * 104, paint("#1a1a1a", 0.7, stroke=1.5))
    # floor + table
    painterly(c, path_of(np.array([(-40, 690), (W + 40, 690), (W + 40, H + 40), (-40, H + 40)])), "#120e0c", seed=3120, strength=0.6)
    return s.makeImageSnapshot().withDefaultMipmaps()


def bar(c, lt, T, t):
    light3(rim=(-0.7, -0.7))
    tq = twos(lt)
    cam = Cam(lerp(960, 1000, lt / 8.5), 560, lerp(1.0, 1.08, lt / 8.5))
    _img(c, bar_bg(), cam, 0.8)
    with cam.layer(c, 0.85):
        radial(c, 1500, 380, 360, "#e0b070", 0.25, blend=skia.BlendMode.kScreen)
        # hanging lamp over the table
        c.drawLine(760, -20, 760, 300, paint("#0a0a0a", stroke=3))
        shape(c, np.array([(720, 300), (800, 300), (830, 340), (690, 340)]), "#2a2a20", 2.5, seed=3150)
        radial(c, 760, 360, 520, "#e8b878", 0.32, blend=skia.BlendMode.kScreen)
        cone(c, (760, 340), (760, 760), 260, "#e8b878", a=0.12, soft=30)
    s = 0.95
    ground = 1000.0
    darts = [b - 114.0 for b in BEATS["s5_darts"]]
    with cam.layer(c, 1.0):
        # table, patron, coins
        shape(c, np.array([(300, 760), (640, 760), (640, 784), (300, 784)]), "#2a1e16", 3, seed=3160)
        shape(c, np.array([(460, 784), (480, 784), (480, 1000), (460, 1000)]), "#1e1610", 2.5, seed=3161)
        pp = make_people(71, 1, kid_ratio=0.0)[0]
        pp["hat"] = 1
        person(c, 590, 770, 34, pp, lt, mood="idle", act=3)
        n_coins = sum(1 for d in darts if tq > d + 0.3)
        for i in range(n_coins * 2):
            c.drawPath(path_of(ellipse(380 + i * 14, 754, 9, 4, 10)), paint("#c8a860"))
            c.drawPath(path_of(ellipse(380 + i * 14, 754, 9, 4, 10)), paint("#3a2a10", stroke=1.2))
        # Lena throwing darts (profile, facing the board)
        L = Lena(3)
        P = L.pose(x=1060, y=ground, s=s, turn=0.88, face=1, foot_n=(26.0, 0.0), foot_f=(-22.0, 0.0), blink=auto_blinks(lt, 62),
                   breath=breathing(lt), smile=0.0, arm_f=("fk", -0.1, 0.3), hand_f="relax")
        arm, lean = (-0.15, 0.4), 0.0
        for d in darts:
            a0, rel = d - 0.45, d - 0.16
            if a0 <= tq <= rel + 0.3:
                arm = keys(tq, [(a0, (-0.15, 0.4)), (a0 + 0.1, (0.9, 2.0)), (rel - 0.06, (0.7, 2.3)), (rel, (1.4, 0.2), "out"), (rel + 0.3, (-0.15, 0.4))])
                lean = keys(tq, [(a0, 0.0), (rel, 0.08, "out"), (rel + 0.3, 0.0)])
        take = BEATS["s5_take_lena"] - 114.0
        if tq > 4.6:
            # she turns her head to him; takes the ticket quickly, without a word
            P["turn"] = keys(tq, [(4.6, 0.88), (5.2, 0.65)])
            arm = None
            P["arm_n"] = keys(tq, [(take - 0.25, (20.0, -150.0)), (take, (125.0, -250.0), "out"), (take + 0.35, (40.0, -190.0))])
            P["arm_n"] = tuple(P["arm_n"])
            P["hand_n"] = "pinch"
        if arm is not None:
            P["arm_n"] = ("fk", arm[0], arm[1])
            P["hand_n"] = "pinch"
        P["lean"] = lean
        # Silas emerges from the smoke behind her (left), facing right
        si = Silas(3)
        appear = remap(tq, 3.6, 4.6)
        SP = si.pose(x=lerp(1470, 1390, ease_io(appear)), y=ground, s=s, turn=0.8, face=-1, foot_n=(14.0, 0.0), foot_f=(-12.0, 0.0),
                     hand_n="pinch", handle=("hand_f", 1.3), hand_f="grip", arm_f=("fk", -0.15, 0.5), smile=0.15, cold=1.0,
                     blink=auto_blinks(lt, 63), breath=breathing(lt))
        offer = remap(tq, 4.6, 5.3)
        SP["arm_n"] = tuple(keys(tq, [(4.6, (40.0, -170.0)), (5.3, (150.0, -262.0))])) if tq < take else tuple(keys(tq, [(take, (150.0, -262.0)), (take + 0.6, (40.0, -170.0))]))
        if appear > 0:
            c.saveLayerAlpha(None, int(255 * appear))
            draw_lit(c, si, SP, lit=0.25 + 0.6 * appear)
            c.restore()
        L.draw(c, P)
        if tq >= 4.6 and tq < take:
            ticket_at(c, si.hand_xf(si.J, si.M, "n"), 0.95 * s, -0.06)
        elif tq >= take:
            ticket_at(c, L.hand_xf(L.J, L.M, "n"), 0.95 * s, 0.3)
    # darts in flight and in the bullseye (board in background layer coords)
    with cam.layer(c, 0.8):
        for i, d in enumerate(darts):
            rel = d - 0.16
            tgt = np.array([1500 - 8 + i * 6, 380 - 4 + i * 4])
            src = np.array([1180, 560])
            if tq >= d:
                _dart(c, tgt[0], tgt[1], math.pi * 0.0)
            elif tq >= rel:
                u = (tq - rel) / (d - rel)
                p = src + (tgt - src) * u + np.array([0, -40 * math.sin(math.pi * u)])
                _dart(c, p[0], p[1], math.atan2(tgt[1] - src[1], tgt[0] - src[0]))
    fog(c, lt, 400, 500, "#5a6a6a", a=0.12, seed=73, drift=18, n=9)
    fog(c, lt, 800, 300, "#4a5a5a", a=0.1, seed=74, drift=10, n=7)
    return grade()


def _dart(c, x, y, ang):
    X = Xf.T(x, y).r(ang)
    shape(c, X(np.array([(-46, -2), (0, -2), (6, 0), (0, 2), (-46, 2)])), "#c4ccd2", 1.4, seed=3170, shadow=False)
    shape(c, X(np.array([(-46, 0), (-60, -9), (-56, 0), (-60, 9)])), "#8a2a2a", 1.2, seed=3171, shadow=False)


# ============================================================================ street corner

@lru_cache(None)
def corner_bg():
    s, c = _hi()
    c.clear(0xFF040809)
    # brick wall
    for row in range(26):
        y = row * 30
        off = 40 if row % 2 else 0
        for col in range(26):
            x = col * 80 - off
            g = 0.75 + 0.25 * ((row * 7 + col * 13) % 5) / 5
            c.drawRect(skia.Rect.MakeLTRB(x + 2, y + 2, x + 78, y + 28), paint(mix("#1a1414", "#2a1e1c", g)))
    # shop window (closed) with sign
    c.drawRect(skia.Rect.MakeLTRB(980, 240, 1560, 700), paint("#0a1214"))
    c.drawRect(skia.Rect.MakeLTRB(980, 240, 1560, 700), paint("#1a1010", stroke=16))
    c.drawRect(skia.Rect.MakeLTRB(1180, 420, 1360, 490), paint("#c8b890", 0.8))
    text(c, "CLOSED", 1270, 468, "oldstd_b", 38, "#3a1a1a")
    # torn awning
    for i in range(10):
        x0 = 950 + i * 64
        c.drawPath(path_of(np.array([(x0, 200), (x0 + 64, 200), (x0 + 70, 250), (x0 + 6, 250)])), paint("#4a2e2c" if i % 2 else "#3d4a4c"))
    # pavement + curb + street
    painterly(c, path_of(np.array([(-40, 760), (W + 40, 760), (W + 40, 900), (-40, 900)])), "#1a2022", seed=3200, strength=0.7)
    c.drawRect(skia.Rect.MakeLTRB(-40, 900, W + 40, 930), paint("#2a3032"))
    painterly(c, path_of(np.array([(-40, 930), (W + 40, 930), (W + 40, H + 40), (-40, H + 40)])), "#0e1416", seed=3201, strength=0.6)
    # street lamp (left)
    c.drawRect(skia.Rect.MakeLTRB(300, 140, 312, 900), paint("#0c1214"))
    c.drawPath(path_of(np.array([(270, 140), (342, 140), (326, 176), (286, 176)])), paint("#0c1214"))
    return s.makeImageSnapshot().withDefaultMipmaps()


def corner(c, lt, T, t):
    light3(rim=(-0.8, -0.6))
    tq = twos(lt)
    cam = Cam(lerp(940, 1000, lt / 8.5), 590, lerp(1.08, 1.18, lt / 8.5))
    _img(c, corner_bg(), cam, 0.85)
    with cam.layer(c, 0.85):
        radial(c, 306, 172, 60, "#ffe0a0", 0.9, blend=skia.BlendMode.kScreen)
        cone(c, (306, 176), (520, 920), 330, "#e0c890", a=0.16, soft=30)
    rain(c, lt, seed=80, n=220, speed=1600, length=30, a=0.18, width=1.0, depth_layers=2)
    s = 0.95
    take = BEATS["s5_take_pip"] - 122.5
    with cam.layer(c, 1.0):
        # Pip sitting on the curb, hugging his knees, paint running in the rain
        p = Pip(3)
        shiver = math.sin(tq * 31) * 0.6
        look_up = remap(tq, 3.6, 4.4)
        shake = (math.sin(tq * 40) * 4) * remap(tq, 4.6, 5.0) * (1 - remap(tq, take - 0.1, take))
        P = p.pose(x=1060, y=925, s=1.2, turn=0.35, face=-1, pelvis=(0.0, 104.0), lean=0.3 - 0.25 * look_up,
                   foot_n=(52.0, 0.0), foot_f=(40.0, 0.0), head_rot=0.35 - 0.45 * look_up + 0.01 * shiver,
                   arm_n=(55.0, -95.0), arm_f=(48.0, -92.0), hand_n="grip", hand_f="grip", paint_run=clamp(0.4 + lt / 8.5),
                   droop=1.0, smile=-0.6, brow=0.5 * look_up, look=(0.0, -0.5 * look_up), blink=auto_blinks(lt, 64))
        if tq > 4.6:
            P["arm_n"] = tuple(keys(tq, [(4.6, (55.0, -95.0)), (5.4, (100.0 + shake, -170.0)), (take - 0.1, (118.0 + shake, -186.0)),
                                         (take + 0.1, (128.0, -192.0), "out"), (take + 0.8, (70.0, -130.0))]))
            P["hand_n"] = "pinch"
        si = Silas(3)
        t0 = 1.0
        sw_, sp = silas_step_out(tq, t0, 520.0, 800.0, n=3, s=s, ground=930.0)
        SP = si.pose(**sp)
        SP.update(turn=0.75, hand_n="pinch", handle=("hand_f", 1.3), hand_f="grip", arm_f=("fk", -0.15, 0.5), smile=0.15, cold=1.0,
                  blink=auto_blinks(lt, 65), breath=breathing(lt), lean=0.12 * remap(tq, 3.0, 3.6), head_rot=0.15 * remap(tq, 3.0, 3.6))
        SP["arm_n"] = tuple(keys(tq, [(3.0, (30.0, -170.0)), (3.7, (150.0, -215.0)), (take, (150.0, -215.0)), (take + 0.7, (40.0, -170.0))]))
        lit = remap(sp["x"], 560.0, 760.0)
        draw_lit(c, si, SP, lit)
        p.draw(c, P)
        if 3.7 <= tq < take:
            ticket_at(c, si.hand_xf(si.J, si.M, "n"), 0.95 * s, -0.1)
        elif tq >= take:
            ticket_at(c, p.hand_xf(p.J, p.M, "n"), 0.95 * 1.2, 0.4)
        splashes(c, lt, 935, seed=82, n=50, col="#9ac8d0", a=0.35, rate=2.4)
    rain(c, lt, seed=84, n=440, speed=2000, length=46, a=0.28, width=1.4)
    return grade()


# ============================================================================ the walk (slow motion)

F = 1000.0          # focal (px per unit at depth F)
HORIZON = 560.0
CAM_H = 470.0


def proj_y(z):
    return HORIZON + CAM_H * F / z


@lru_cache(None)
def street_bg():
    s, c = _hi()
    c.clear(0xFF030607)
    vp = (960, HORIZON)
    # buildings receding on both sides
    for side in (-1, 1):
        for k in range(7):
            z0, z1 = 3000 - k * 330, 3000 - (k + 1) * 330
            x0, x1 = 960 + side * 700 * F / z0, 960 + side * 700 * F / z1
            top0, top1 = HORIZON - 900 * F / z0, HORIZON - 900 * F / z1
            b0, b1 = proj_y(z0), proj_y(z1)
            poly = np.array([(x0, top0), (x1, top1), (x1, b1), (x0, b0)])
            painterly(c, path_of(poly), mix("#0a1517", "#0e1c1e", k % 2), seed=3300 + k + side * 10, strength=0.4)
            for wnd in range(3):
                u = 0.25 + wnd * 0.25
                wx = lerp(x0, x1, u)
                wy = lerp(top0, top1, u) + (lerp(b0, b1, u) - lerp(top0, top1, u)) * 0.3
                ww = abs(x1 - x0) * 0.08
                if (k + wnd + side) % 3 == 0:
                    c.drawRect(skia.Rect.MakeLTRB(wx - ww, wy, wx + ww, wy + ww * 2.2), paint("#c8a060", 0.25))
    # wet street with reflections
    road = np.array([(-40, proj_y(3000)), (W + 40, proj_y(3000)), (W + 40, H + 40), (-40, H + 40)])
    painterly(c, path_of(road), "#0c1416", seed=3320, strength=0.5)
    for z in range(1000, 3000, 140):
        y = proj_y(z)
        c.drawLine(-40, y, W + 40, y, paint("#1a2a2c", 0.35, stroke=1.2))
    return s.makeImageSnapshot().withDefaultMipmaps()


def walk(c, lt, T, t):
    light3(rim=(0.0, -1.0))
    tq = twos(lt)
    slow = 0.45
    c.drawImageRect(street_bg(), skia.Rect.MakeWH(W, H), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNearest), paint())
    # the one flickering streetlight overhead, which they pass beneath
    fl = 0.75 + 0.25 * vnoise(t * 2.2, 5)
    for t0 in (133.2, 136.4, 138.1):
        u = (t - t0) / 0.35
        if 0 <= u <= 1:
            fl *= 1 - 0.6 * math.sin(math.pi * u)
    lz = 1500.0
    lx = 960 - 520 * F / lz
    ltop = HORIZON - 760 * F / lz
    c.drawLine(lx, proj_y(lz), lx, ltop, paint("#0c1416", stroke=10))
    c.drawLine(lx, ltop, 960, ltop, paint("#0c1416", stroke=7))
    radial(c, 960, ltop + 10, 70, "#ffe0a8", 0.95 * fl, blend=skia.BlendMode.kScreen)
    cone(c, (960, ltop + 14), (960, proj_y(lz) + 60), 420, "#e8d8a8", a=0.22 * fl, soft=40)
    radial(c, 960, proj_y(lz) + 30, 520, "#d8c898", 0.22 * fl, blend=skia.BlendMode.kScreen)
    # the four, side by side, walking toward camera (feet locked in perspective)
    crew = [(Lena(3), -360.0, 0.15, 1.0), (Silas(3), -110.0, 0.0, 1.0), (Bruno(3), 160.0, 0.3, 1.0), (Pip(3), 410.0, 0.45, 1.0)]
    z_start, z_end = 2300.0, 860.0
    order = sorted(range(4), key=lambda i: -abs(crew[i][1]))
    draws = []
    for i, (fig, lat, ph, _) in enumerate(crew):
        speed = (z_start - z_end) / 9.0                      # world units per second (slow motion)
        step_len = 92.0 if not isinstance(fig, Pip) else 62.0
        sd = step_len / speed
        w = Walk(-2.0 * sd - ph * sd, 40, step_len, sd, start_u=0.0, stance=0.0, bob=3.0, lift=12.0, toe=0.0)
        pu, bob = w.pelvis(tq)
        u0 = w.pelvis(0.0)[0]
        fe = w.feet(tq)
        z_root = z_start - (pu - u0)
        s = F / z_root
        y_root = proj_y(z_root)
        x_root = 960 + lat * s
        feet = {}
        for key in ("n", "f"):
            fu, lift, _ = fe[key]
            zf = z_start - (fu - u0)
            dy = proj_y(zf) - y_root                    # a planted foot nearer the camera sits lower on screen
            feet[key] = (0.0, lift - dy / s)
        P = fig.pose(x=x_root, y=y_root, s=s, turn=0.0, face=1, pelvis=(0.0, bob), foot_n=feet["n"], foot_f=feet["f"],
                     blink=auto_blinks(lt, 66 + i), breath=breathing(lt))
        sw = clamp((fe["n"][0] - fe["f"][0]) / step_len, -1, 1)
        if isinstance(fig, Silas):
            P.update(smile=0.25, cold=1.0, narrow=0.2, handle=("hand_f", 1.3), hand_f="grip", hand_n="relax",
                     arm_n=("fk", 0.08 * sw, 0.15), arm_f=("fk", -0.05 * sw, 0.5), brim_shadow=1.0)
        elif isinstance(fig, Pip):
            P.update(smile=-0.1, droop=0.9, paint_run=1.0, arm_n=("fk", 0.12 * sw, 0.2), arm_f=("fk", -0.12 * sw, 0.2))
        else:
            P.update(smile=0.0, arm_n=("fk", 0.1 * sw, 0.15), arm_f=("fk", -0.1 * sw, 0.15))
        draws.append((z_root, fig, P, sw))
    for z_root, fig, P, sw in sorted(draws, key=lambda d: -d[0]):
        fig.draw(c, P)
    splashes(c, lt * slow, 900, seed=90, n=60, col="#9ac8d0", a=0.3, rate=1.6, scale=1.2)
    fog(c, lt, 760, 200, "#1c3a3e", a=0.2, seed=91, drift=6)
    rain(c, lt, seed=92, n=480, speed=2000, length=46, a=0.3, width=1.4, slow=slow)
    return grade()


SHOTS = dict(docks=docks, bar=bar, corner=corner, walk=walk)
