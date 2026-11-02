"""The big top interior - the film's master location.

The WIDE master angle (Scene 2 opening, the Scene 3 dissolves, the Scene 3 storm and
the Scene 7 finale) is always drawn from this one function with the same camera, so
the audience recognises the place as it changes: full -> half -> empty -> torn ->
rebuilt in the dark.

Layers (parallax depth): roof/walls/poles 0.6, stands + crowd 0.85, ring 1.0,
front row silhouettes 1.3.
"""
import math
from functools import lru_cache
import numpy as np
import skia
from lib.core import W, H, clamp, lerp, remap, smooth, hexc, mix, mul, paint, rng, vnoise, snoise, desat, twos
from lib.ink import S, shape, ink_line, fill, ellipse, spline, path_of
from lib.frame import new_surface
from config.palettes import ENV
from rigs.crowd import make_people, person, back_of_head
from scenes.common import painterly, radial, cone, rain
from lib.frame import Cam

CROWD_DARK = {1: "#3a1a10", 2: "#141a20", 3: "#05080a"}

CX, CY = 960.0, 800.0          # ring centre (home frame)
RRX, RRY = 640.0, 140.0        # ring radii
CURB = 26.0
TIERS = 7
SC = 1.5                       # cache supersampling
APEX = (960.0, -1500.0)


def eave_y(x):
    u = (x - CX) / 1300.0
    return 268 - 70 * (1 - u * u)


def tier_arc(k):
    rx = 780 + 70 * k
    ry = 214 + 38 * k
    return rx, ry


def arc_y(x, rx, ry):
    u = clamp(abs(x - CX) / rx, 0, 0.9999)
    return CY - ry * math.sqrt(1 - u * u)


def env(act):
    return ENV[act]


# ----------------------------------------------------------------------------- cached layers

def _surface_hi():
    s = new_surface(int(W * SC), int(H * SC))
    c = s.getCanvas()
    c.clear(0x00000000)
    c.scale(SC, SC)
    return s, c


@lru_cache(None)
def roof_layer(act, torn=False, finale=False):
    s, c = _surface_hi()
    E = env(act)
    a_col, b_col = E["tent_a"], E["tent_b"]
    # back wall + roof as radial stripes from the apex
    n = 34
    edge = []
    for i in range(n + 1):
        x = -500 + (W + 1000) * i / n
        edge.append((x, eave_y(x) + 140))
    for i in range(n):
        x0, y0 = edge[i]; x1, y1 = edge[i + 1]
        col = a_col if i % 2 == 0 else b_col
        poly = np.array([APEX, (x0, y0), (x1, y1)])
        painterly(c, path_of(poly), col, seed=100 + i + act * 50, strength=0.35, angle=math.atan2(y0 - APEX[1], x0 - APEX[0]))
    # darkness toward the top of the canopy
    p = skia.Paint(AntiAlias=True)
    top_dark = "#120a10" if act == 1 else ("#0c1014" if act == 2 else "#030607")
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, -60), skia.Point(0, 420)],
                [skia.Color4f(*hexc(top_dark), 0.92), skia.Color4f(*hexc(top_dark), 0.45 if act == 1 else 0.7), skia.Color4f(*hexc(top_dark), 0.1)], [0, 0.6, 1]))
    c.drawRect(skia.Rect.MakeLTRB(-50, -50, W + 50, 480), p)
    # wall below the eaves (behind the stands)
    wall = np.array([(-60, eave_y(-60) + 120)] + [(x, eave_y(x) + 130) for x in np.linspace(-60, W + 60, 30)] + [(W + 60, 640), (-60, 640)])
    painterly(c, path_of(wall), mix(b_col, "#000000", 0.45), seed=180 + act, strength=0.4, angle=1.5)
    for i in range(16):   # wall stripes
        x = -40 + i * 130
        c.drawRect(skia.Rect.MakeLTRB(x, eave_y(x) + 128, x + 60, 640), paint(mix(a_col, "#000000", 0.5), 0.6))
    # holes in a torn roof show the night sky
    if torn:
        r = rng(77)
        for hcx, hcy, hr in [(560, 120, 120), (1350, 70, 150), (980, -10, 90), (250, 210, 70)]:
            pts = []
            for k in range(14):
                ang = math.tau * k / 14
                rr = hr * (0.65 + 0.5 * r.random())
                pts.append((hcx + math.cos(ang) * rr * 1.3, hcy + math.sin(ang) * rr * 0.7))
            c.drawPath(path_of(np.array(pts)), paint("#0d141b"))
            c.drawPath(path_of(np.array(pts)), paint("#1b2630", 0.6, stroke=3))
    # king poles (barber striped) + rigging
    for px in (700, 1220):
        pole_col = E["pole"]
        c.drawRect(skia.Rect.MakeLTRB(px - 13, -60, px + 13, 620), paint(pole_col))
        for j in range(-2, 40):
            y = j * 34
            stripe = np.array([(px - 13, y), (px + 13, y - 12), (px + 13, y + 2), (px - 13, y + 14)])
            c.drawPath(path_of(stripe), paint(a_col if not finale else mix(a_col, "#000", 0.3), 0.85))
        c.drawRect(skia.Rect.MakeLTRB(px - 13, -60, px - 6, 620), paint("#ffffff", 0.08 if act == 1 else 0.04))
        ink_line(c, np.array([(px - 13, -60), (px - 13, 620)]), 2.5, do_boil=False)
        ink_line(c, np.array([(px + 13, -60), (px + 13, 620)]), 2.5, do_boil=False)
        for ex in (-300, 200, 700, 1300, 1900, 2300):
            if abs(ex - px) < 300:
                continue
            ink_line(c, np.array([(px, 30), (ex, eave_y(ex) + 120)]), 1.3, alpha=0.45, do_boil=False)
    # trapeze high on the right
    c.drawLine(1420, -40, 1440, 150, paint("#2a1a14", stroke=2))
    c.drawLine(1530, -40, 1510, 150, paint("#2a1a14", stroke=2))
    c.drawRect(skia.Rect.MakeLTRB(1436, 147, 1514, 154), paint(E["pole"]))
    return s.makeImageSnapshot().withDefaultMipmaps()


@lru_cache(None)
def stands_layer(act, finale=False):
    s, c = _surface_hi()
    E = env(act)
    seat = E["seat"]
    riser = mix(seat, "#000000", 0.5)
    for k in range(TIERS - 1, -1, -1):
        rx, ry = tier_arc(k)
        xs = np.linspace(CX - rx * 0.999, CX + rx * 0.999, 80)
        top = np.array([(x, arc_y(x, rx, ry)) for x in xs])
        rx2, ry2 = tier_arc(k - 1) if k > 0 else (rx - 60, ry - 40)
        bot = np.array([(x, arc_y(x, rx, ry) + 48) for x in xs])
        poly = np.vstack([top, bot[::-1]])
        painterly(c, path_of(poly), riser, seed=300 + k, strength=0.3, angle=0.0)
        bench = np.vstack([top, (top + (0, 13))[::-1]])
        painterly(c, path_of(bench), seat, seed=320 + k, strength=0.4, angle=0.0)
        ink_line(c, top, 1.6, alpha=0.7, do_boil=False)
        # aisle stairs
    for ax in (CX - 470, CX + 470):
        pts = []
        for k in range(TIERS):
            rx, ry = tier_arc(k)
            pts.append((ax, arc_y(ax, rx, ry)))
        pts = np.array(pts)
        c.drawPath(path_of(np.vstack([pts + (-16, 0), (pts + (16, 50))[::-1]])), paint(mix(seat, "#000", 0.35)))
    # rail along the front of the stands
    rx, ry = tier_arc(0)
    xs = np.linspace(CX - rx, CX + rx, 80)
    rail = np.array([(x, arc_y(x, rx, ry) + 48) for x in xs])
    c.drawPath(path_of(np.vstack([rail, (rail + (0, 26))[::-1]])), paint(mix(E["ring"], "#000", 0.25)))
    ink_line(c, rail, 2.0, do_boil=False)
    trim = "#e8b23a" if act == 1 else ("#8d7a52" if act == 2 else "#6b604a")
    ink_line(c, rail + (0, 6), 2.0, color=trim, do_boil=False)
    return s.makeImageSnapshot().withDefaultMipmaps()


@lru_cache(None)
def ring_layer(act):
    s, c = _surface_hi()
    E = env(act)
    floor = mix(E["ring_floor"], "#000000", 0.55)
    c.drawRect(skia.Rect.MakeLTRB(-100, 560, W + 100, H + 300), paint(floor))
    painterly(c, path_of(np.array([(-100, 600), (W + 100, 600), (W + 100, H + 300), (-100, H + 300)])), floor, seed=401, strength=0.5)
    wall = E["ring"]
    top = mix(wall, "#ffffff", 0.12)
    inner = mix(wall, "#000000", 0.45)
    c.drawPath(path_of(ellipse(CX, CY, RRX + 28, RRY + 8, 80)), paint(mix(wall, "#000", 0.2)))
    c.drawRect(skia.Rect.MakeLTRB(CX - RRX - 28, CY - CURB, CX + RRX + 28, CY), paint(mix(wall, "#000", 0.2)))
    c.drawPath(path_of(ellipse(CX, CY - CURB, RRX + 28, RRY + 8, 80)), paint(top))
    c.drawPath(path_of(ellipse(CX, CY - CURB, RRX, RRY, 80)), paint(inner))
    saw = E["ring_floor"]
    c.save()
    c.clipPath(path_of(ellipse(CX, CY - CURB, RRX, RRY, 80)), skia.ClipOp.kIntersect, True)
    fl = ellipse(CX, CY, RRX, RRY, 80)
    painterly(c, path_of(fl), saw, seed=410 + act, strength=0.9, angle=0.0, scale=0.8)
    c.restore()
    # gold stars on the curb wall
    trim = "#e8b23a" if act == 1 else ("#8d7a52" if act == 2 else "#6b604a")
    for i in range(13):
        ang = math.pi * (0.08 + 0.84 * i / 12)
        x = CX - math.cos(ang) * (RRX + 28)
        y = CY - CURB / 2 + math.sin(ang) * (RRY + 8)
        st = []
        for j in range(10):
            rr = 9 if j % 2 == 0 else 4
            a2 = -math.pi / 2 + j * math.pi / 5
            st.append((x + math.cos(a2) * rr, y + math.sin(a2) * rr))
        c.drawPath(path_of(np.array(st)), paint(trim, 0.9))
    front = ellipse(CX, CY - CURB, RRX + 28, RRY + 8, 60, 0, math.pi)
    ink_line(c, front, 2.4, color=trim, do_boil=False)
    ink_line(c, ellipse(CX, CY, RRX + 28, RRY + 8, 60, 0, math.pi), 2.6, do_boil=False)
    ink_line(c, ellipse(CX, CY - CURB, RRX, RRY, 80), 1.8, do_boil=False, alpha=0.8)
    return s.makeImageSnapshot().withDefaultMipmaps()


def draw_cached(c, img, cam, depth, blur=0.0):
    with cam.layer(c, depth):
        p = skia.Paint(AntiAlias=True)
        if blur:
            p.setImageFilter(skia.ImageFilters.Blur(blur, blur))
        c.drawImageRect(img, skia.Rect.MakeWH(W, H), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNearest), p)


# ----------------------------------------------------------------------------- live elements

@lru_cache(None)
def crowd_seats(seed=11):
    """Seat positions per tier with people records."""
    seats = []
    r = rng(seed)
    for k in range(TIERS):
        rx, ry = tier_arc(k)
        step = 44 - k * 1.5
        x = CX - rx * 0.97
        while x < CX + rx * 0.97:
            if abs(abs(x - CX) - 470) > 38:
                y = arc_y(x, rx, ry) + 6
                if -40 < x < W + 40:
                    seats.append((x + (r.random() - 0.5) * 8, y, k))
            x += step
    people = make_people(seed, len(seats), kid_ratio=0.28)
    return seats, people


def draw_crowd(c, cam, t, act, occupancy=1.0, mood="cheer", finale=False, light_fn=None):
    seats, people = crowd_seats()
    with cam.layer(c, 0.85):
        for (x, y, k), p in sorted(zip(seats, people), key=lambda e: -e[0][2]):
            if p["present"] > occupancy:
                continue
            q = dict(p)
            if finale:
                q["kid"] = False
                q["hat"] = 2 if p["hat"] < 3 else 1
            size = 11.5 - k * 0.55
            person(c, x, y, size, q, t, mood=mood, act=act)


def string_lights(act):
    """Bulb positions along garlands draped between the poles and the eaves."""
    bulbs = []
    garlands = [((-80, 300), (700, 120)), ((700, 120), (1220, 120)), ((1220, 120), (2000, 300)),
                ((150, 330), (700, 200)), ((1220, 200), (1770, 330))]
    for gi, (a, b) in enumerate(garlands):
        n = 14
        for i in range(n + 1):
            u = i / n
            x = lerp(a[0], b[0], u)
            y = lerp(a[1], b[1], u) + 70 * math.sin(math.pi * u)
            bulbs.append((x, y, gi, i))
    return garlands, bulbs


def draw_lights(c, cam, t, act, on=None, burst_times=None, bright=1.0):
    """String lights. on: fraction lit (index order) or None for all. burst_times:
    dict bulb_index -> time it bursts (spark, then dark)."""
    garlands, bulbs = string_lights(act)
    E = env(act)
    with cam.layer(c, 0.62):
        for (a, b) in garlands:
            pts = []
            for i in range(25):
                u = i / 24
                pts.append((lerp(a[0], b[0], u), lerp(a[1], b[1], u) + 70 * math.sin(math.pi * u)))
            ink_line(c, np.array(pts), 1.6, alpha=0.8, do_boil=False)
        for idx, (x, y, gi, i) in enumerate(bulbs):
            lit = True
            spark = 0.0
            if on is not None and idx / len(bulbs) > on:
                lit = False
            if burst_times and idx in burst_times:
                tb = burst_times[idx]
                if t >= tb:
                    lit = False
                    spark = math.exp(-(t - tb) * 7) if t - tb < 0.6 else 0.0
            col = ["#ffd27a", "#ff9a6a", "#fff0b0"][(gi + i) % 3] if act == 1 else "#e9e2c0"
            if lit:
                flick = 0.85 + 0.15 * vnoise(t * 6 + idx * 3.1, idx)
                radial(c, x, y + 6, 26 * bright, col, 0.55 * flick * bright, blend=skia.BlendMode.kScreen)
                c.drawCircle(x, y + 6, 4.2, paint(col))
            else:
                c.drawCircle(x, y + 6, 4.0, paint("#3a3630"))
            c.drawRect(skia.Rect.MakeLTRB(x - 2.5, y - 1, x + 2.5, y + 3), paint("#1a1614"))
            if spark > 0:
                radial(c, x, y + 6, 70 * spark + 10, "#fff6d8", 0.9 * spark, blend=skia.BlendMode.kScreen)
                r = rng(idx * 13)
                for j in range(7):
                    ang = r.random() * math.tau
                    L = (20 + r.random() * 40) * (1 - spark * 0.4)
                    d = (1 - spark) * 30
                    c.drawLine(x + math.cos(ang) * d, y + 6 + math.sin(ang) * d + (1 - spark) * 25,
                               x + math.cos(ang) * (d + L * 0.4), y + 6 + math.sin(ang) * (d + L * 0.4) + (1 - spark) * 25,
                               paint("#fff2c0", spark, stroke=1.6))
    return bulbs


def draw_bunting(c, cam, t, act, wind=0.0):
    E = env(act)
    cols = E["bunting"]
    with cam.layer(c, 0.66):
        for (a, b, y0, n) in [((-60, 380), (700, 250), 0, 12), ((1220, 250), (1980, 380), 0, 12)]:
            pts = []
            for i in range(n + 1):
                u = i / n
                x = lerp(a[0], b[0], u)
                y = lerp(a[1], b[1], u) + 40 * math.sin(math.pi * u)
                pts.append((x, y))
            ink_line(c, np.array(pts), 1.4, alpha=0.8, do_boil=False)
            for i in range(n):
                (x0, y0_), (x1, y1) = pts[i], pts[i + 1]
                sw = math.sin(t * 3 + i) * (3 + wind * 14)
                tip = ((x0 + x1) / 2 + sw, (y0_ + y1) / 2 + 30)
                c.drawPath(path_of(np.array([(x0, y0_), (x1, y1), tip])), paint(cols[i % 3]))


def draw_spots(c, cam, t, act, targets, col=None, a=0.22, sweep=True):
    E = env(act)
    col = col or E["spot"]
    with cam.layer(c, 0.75):
        for i, (src, tgt) in enumerate(targets):
            tx, ty = tgt
            if sweep:
                tx += 160 * math.sin(t * 0.7 + i * 2.1)
            cone(c, src, (tx, ty), 120, col, a=a)
            radial(c, src[0], src[1], 40, col, 0.8, blend=skia.BlendMode.kScreen)


def draw_front_row(c, cam, t, act, mood="cheer", n=14, y=1075, size=28, seed=21, col=None):
    people = make_people(seed, n, kid_ratio=0.35)
    with cam.layer(c, 1.3):
        for i, p in enumerate(people):
            x = -80 + i * (W + 160) / (n - 1) + (p["ph"] % 1 - 0.5) * 40
            back_of_head(c, x, y + (p["ph"] % 0.7) * 30, size * (0.9 + 0.2 * (p["ph"] % 1)), p, t, act=act, mood=mood,
                         col_override=col or mix(["#2a1418", "#1e1420", "#2a1a12", "#181418"][i % 4], CROWD_DARK[act], 0.3))


def draw_tent(c, cam, t, act, occupancy=1.0, mood="cheer", torn=False, finale=False, lights_on=None, bursts=None,
              spots=None, spot_a=0.22, front_row=True, bg_blur=0.0, sky_fn=None, flaps=0.0, wind=0.0, after_stands=None,
              light_bright=1.0, front_mood=None, front_col=None):
    """The master big-top view. after_stands(c) draws extra things (e.g. characters
    far in the ring) between the stands and the ring layers when needed."""
    E = env(act)
    with cam.layer(c, 0.55):
        c.drawRect(skia.Rect.MakeLTRB(-2000, -2000, 4000, 4000), paint(E["sky"]))
        if sky_fn:
            sky_fn(c)
    if bg_blur:
        c.saveLayer(None, _blur_paint(bg_blur))
    draw_cached(c, roof_layer(act, torn, finale), cam, 0.6)
    if flaps > 0:
        tear_flaps(c, cam, t, act, holes_open=flaps, wind=wind)
    draw_bunting(c, cam, t, act, wind=wind)
    draw_lights(c, cam, t, act, on=lights_on, burst_times=bursts, bright=light_bright)
    draw_cached(c, stands_layer(act, finale), cam, 0.85)
    if occupancy > 0:
        draw_crowd(c, cam, t, act, occupancy=occupancy, mood=mood, finale=finale)
    if bg_blur:
        c.restore()
    if spots:
        draw_spots(c, cam, t, act, spots, a=spot_a)
    draw_cached(c, ring_layer(act), cam, 1.0)
    if after_stands:
        after_stands(c)
    if front_row:
        draw_front_row(c, cam, t, act, mood=front_mood or mood, col=front_col)


def _blur_paint(r):
    p = skia.Paint()
    p.setImageFilter(skia.ImageFilters.Blur(r, r))
    return p


def tear_flaps(c, cam, t, act, holes_open=1.0, wind=0.5):
    """Torn canvas strips hanging from the roof holes, swaying in the wind."""
    E = env(act)
    with cam.layer(c, 0.6):
        for i, (x, y, L) in enumerate([(520, 170, 150), (610, 160, 110), (1300, 130, 170), (1420, 120, 120), (960, 60, 90), (280, 250, 80)]):
            L *= holes_open
            if L < 4:
                continue
            sw = math.sin(t * (1.8 + i * 0.3) + i) * 0.35 * wind + math.sin(t * 5.1 + i) * 0.08 * wind
            pts = []
            for j in range(9):
                u = j / 8
                ang = sw * u * u
                pts.append((x + math.sin(ang) * L * u, y + math.cos(ang) * L * u))
            pts = np.array(pts)
            wv = 22
            left = pts + (-wv / 2, 0)
            right = (pts + (wv / 2, 0))[::-1]
            col = E["tent_a"] if i % 2 else E["tent_b"]
            shape(c, np.vstack([left, right]), mix(col, "#000", 0.25), 1.6, seed=950 + i, shadow=False)


# ----------------------------------------------------------------------------- medium-shot backdrop

@lru_cache(None)
def floor_layer(act, curb_y=600):
    """Sawdust floor + the inner wall of the ring curb, seen from inside the ring."""
    s = new_surface(W, H)
    c = s.getCanvas()
    c.clear(0x00000000)
    E = env(act)
    saw = E["ring_floor"]
    pts = [(x, curb_y - 14 * (1 - ((x - 960) / 1500) ** 2)) for x in np.linspace(-20, W + 20, 40)]
    floor = np.array(pts + [(W + 20, H + 20), (-20, H + 20)])
    painterly(c, path_of(floor), saw, seed=500 + act, strength=1.0, angle=0.05, scale=1.2)
    p = skia.Paint(AntiAlias=True)
    dk = hexc(mix(saw, "#000000", 0.55))
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, curb_y), skia.Point(0, curb_y + 160)],
                [skia.Color4f(*dk, 0.55), skia.Color4f(*dk, 0.0)], None))
    c.drawPath(path_of(floor), p)
    # inner wall of the curb (a long band across the frame)
    top = np.array([(x, y - 46) for x, y in pts])
    wall = np.vstack([top, np.array(pts)[::-1]])
    painterly(c, path_of(wall), mix(E["ring"], "#000000", 0.35), seed=520 + act, strength=0.5)
    ink_line(c, top, 2.6, do_boil=False)
    ink_line(c, np.array(pts), 2.2, do_boil=False, alpha=0.8)
    trim = "#e8b23a" if act == 1 else ("#8d7a52" if act == 2 else "#6b604a")
    ink_line(c, top + (0, 7), 2.2, color=trim, do_boil=False)
    cap = np.vstack([top + (0, -12), top[::-1]])
    c.drawPath(path_of(cap), paint(mix(E["ring"], "#ffffff", 0.1)))
    ink_line(c, top + (0, -12), 2.2, do_boil=False)
    return s.makeImageSnapshot().withDefaultMipmaps()


def draw_ring_medium(c, t, act, xshift=0.0, occupancy=1.0, mood="cheer", finale=False, blur=7.0, lights=True,
                     torn=False, crowd_fn=None, sky_fn=None, roof=True, mid_fn=None, lights_on=None, flaps=0.0, wind=0.0):
    """Camera standing inside the ring: blurred stands and crowd behind the curb."""
    E = env(act)
    cam = Cam(960 + xshift, 640, 2.1)
    c.drawRect(skia.Rect.MakeWH(W, H), paint(E["sky"]))
    if sky_fn:
        sky_fn(c)
    c.saveLayer(None, _blur_paint(blur))
    if roof:
        draw_cached(c, roof_layer(act, torn, finale), cam, 0.6)
    if flaps > 0:
        tear_flaps(c, cam, t, act, holes_open=flaps, wind=wind)
    if lights:
        draw_lights(c, cam, t, act, on=lights_on)
    draw_cached(c, stands_layer(act, finale), cam, 0.85)
    if occupancy > 0:
        draw_crowd(c, cam, t, act, occupancy=occupancy, mood=mood, finale=finale)
    if crowd_fn:
        crowd_fn(c, cam)
    c.restore()
    if mid_fn:
        mid_fn(c)
    c.drawImage(floor_layer(act), 0, 0)
    return cam
