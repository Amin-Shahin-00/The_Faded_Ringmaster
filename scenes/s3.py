"""SCENE 3 - THE FALL (0:48 - 1:18). The same tent empties; the bank comes; the people leave;
the storm tears the canvas and the colors drain out in real time."""
import math
import numpy as np
import skia
from lib.core import W, H, Xf, keys, clamp, lerp, remap, smooth, ease_io, ease_out, twos, paint, mix, rng, hexc, vnoise
from lib.ink import S, shape, ink_line, fill, ellipse, spline, path_of
from lib.frame import Cam, text, new_surface
from lib.motion import Walk, arm_swing_fk, follow
from config.palettes import GRADE, ENV
from config.timeline import BEATS
from rigs.silas import Silas
from rigs.cast import Bruno, Lena, Pip
from scenes import tent
from scenes.common import radial, cone, painterly, rain, splashes, fog, lightning_flash
from scenes.silas_moves import auto_blinks, breathing
from scenes import s1, s2

G1, G2 = GRADE[1], GRADE[2]


def grade_mix(u, **kw):
    """Interpolate the grade from Act 1 (u=0) to Act 2 (u=1)."""
    g = {}
    for k in ("sat", "gamma", "glow"):
        g[k] = lerp(G1[k], G2[k], u)
    for k in ("tint", "lift"):
        g[k] = tuple(lerp(a, b, u) for a, b in zip(G1[k], G2[k]))
    g.update(kw)
    return g


# ============================================================================ nights

def _night(c, lt, k, tq):
    """One of the three nights on the master angle. k = 0 full, 1 half, 2 empty."""
    occ = [1.0, 0.42, 0.04][k]
    mood = ["cheer", "idle", "idle"][k]
    cam = Cam(**s2.WIDE_CAM)
    fig = Silas(1)
    if k == 0:
        wave = math.sin(tq * math.tau * 1.6)
        P = fig.pose(x=960, y=s2.RING_Y, s=s2.WIDE_S, turn=0.2, arm_n=(40.0 + 30 * wave, -470.0), hand_n="open",
                     arm_f=("fk", -1.4, 0.3), hand_f="grip", cane=("hand_f", 0.4, "front"), smile=0.9, open=0.3,
                     pelvis=(0.0, abs(wave) * 3), blink=auto_blinks(lt, 2))
    elif k == 1:
        b = 0.25 + 0.15 * math.sin(tq * 1.4)
        P = fig.pose(x=960, y=s2.RING_Y, s=s2.WIDE_S, turn=0.25, lean=b * 0.6, arm_n=(90.0, -300.0), hand_n="open",
                     arm_f=("fk", -0.6, 0.3), hand_f="grip", cane=("hand_f", 0.3, "front"), smile=0.45, blink=auto_blinks(lt, 3))
    else:
        br = breathing(lt, 0.2)
        P = fig.pose(x=960, y=s2.RING_Y, s=s2.WIDE_S, turn=0.15, lean=0.05, head_rot=0.12, arm_n=None, hand_n="relax",
                     arm_f=None, hand_f="grip", cane=("hand_f", -0.2, "front"), smile=-0.1, breath=br, blink=auto_blinks(lt, 4))

    def ring_chars(cv):
        with cam.layer(cv, 1.0):
            fig.draw(cv, P)
        if k == 0:
            s2.popcorn(cv, cam, lt + 8)

    tent.draw_tent(c, cam, lt, 1, occupancy=occ, mood=mood, spots=[((150, -40), (960, 800)), ((1770, -40), (960, 800))] if k < 2 else
                   [((1770, -40), (960, 800))], spot_a=[0.22, 0.16, 0.12][k], after_stands=ring_chars,
                   light_bright=[1.0, 0.75, 0.55][k], front_row=k == 0, front_mood="cheer")
    if k > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint("#0a0810", [0, 0.18, 0.32][k]))


def nights(c, lt, T, t):
    s2.light()
    tq = twos(lt)
    d1, d2 = BEATS["s3_dissolves"][0] - 48.0, BEATS["s3_dissolves"][1] - 48.0
    dd = 0.7
    if lt < d1 - dd / 2:
        _night(c, lt, 0, tq)
    elif lt < d1 + dd / 2:
        _night(c, lt, 0, tq)
        c.saveLayerAlpha(None, int(255 * smooth((lt - (d1 - dd / 2)) / dd)))
        _night(c, lt, 1, tq)
        c.restore()
    elif lt < d2 - dd / 2:
        _night(c, lt, 1, tq)
    elif lt < d2 + dd / 2:
        _night(c, lt, 1, tq)
        c.saveLayerAlpha(None, int(255 * smooth((lt - (d2 - dd / 2)) / dd)))
        _night(c, lt, 2, tq)
        c.restore()
    else:
        _night(c, lt, 2, tq)
    return grade_mix(remap(lt, 0, 8) * 0.35)


# ============================================================================ posters

def silas_poster(c, x, y, w, h, wear=0.3):
    """Marlowe's poster: Act 1 illustration of Silas (drawn with the rig) + lettering."""
    c.save()
    rect = skia.Rect.MakeLTRB(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
    painterly(c, path_of(np.array([(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)])),
              "#efdcae", seed=1300, strength=0.6)
    c.drawRect(skia.Rect.MakeLTRB(x - w / 2 + 14, y - h / 2 + 14, x + w / 2 - 14, y + h / 2 - 14), paint("#b8242c", stroke=6))
    text(c, "MARLOWE'S", x, y - h / 2 + 92, "rye", 66, "#b8242c")
    text(c, "MARVELOUS CIRCUS", x, y - h / 2 + 140, "oldstd_b", 34, "#2a1a14")
    c.clipRect(skia.Rect.MakeLTRB(x - w / 2 + 20, y - h / 2 + 160, x + w / 2 - 20, y + h / 2 - 110))
    radial(c, x, y + 60, 300, "#f6c050", 0.6)
    fig = Silas(1)
    P = fig.pose(x=x - 10, y=y + h / 2 + 300, s=1.25, turn=0.3, arm_n=(110.0, -330.0), hand_n="open", arm_f=("fk", -0.4, 0.4),
                 hand_f="grip", cane=("hand_f", 0.3, "front"), smile=0.9)
    old = S.boil_amp
    S.boil_amp = 0.0       # a printed poster does not boil
    fig.draw(c, P)
    S.boil_amp = old
    c.restore()
    text(c, "EVERY NIGHT  -  ALL WELCOME", x, y + h / 2 - 60, "oldstd_b", 30, "#2a1a14")
    # weathering
    r = rng(14)
    for i in range(int(40 * wear)):
        xx, yy = x - w / 2 + r.random() * w, y - h / 2 + r.random() * h
        c.drawPath(path_of(ellipse(xx, yy, 2 + 8 * r.random(), 1 + 4 * r.random(), 8)), paint("#8a7a5a", 0.35))


def rival_poster(c, x, y, w, h):
    """The rival's bright, modern poster."""
    pts = np.array([(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)])
    c.drawPath(path_of(pts), paint("#14a0d8"))
    # sunburst
    for i in range(16):
        a0 = i * math.tau / 16
        tri = np.array([(x, y - 40), (x + math.cos(a0) * 900, y - 40 + math.sin(a0) * 900),
                        (x + math.cos(a0 + 0.2) * 900, y - 40 + math.sin(a0 + 0.2) * 900)])
        c.save(); c.clipRect(skia.Rect.MakeLTRB(x - w / 2, y - h / 2, x + w / 2, y + h / 2))
        c.drawPath(path_of(tri), paint("#30c0f0", 0.8))
        c.restore()
    bolt = np.array([(x + 30, y - 210), (x - 70, y - 20), (x + 2, y - 20), (x - 50, y + 140), (x + 90, y - 60), (x + 18, y - 60), (x + 80, y - 210)])
    c.drawPath(path_of(bolt), paint("#ffe23a"))
    ink_line(c, np.vstack([bolt, bolt[:1]]), 4, color="#10202a", do_boil=False)
    text(c, "VOLTA", x, y - h / 2 + 110, "bebas", 120, "#ffe23a")
    text(c, "ELECTRIC CIRCUS", x, y - h / 2 + 170, "bebas", 56, "#ffffff")
    text(c, "MODERN!  DAZZLING!  NEW!", x, y + h / 2 - 70, "bebas", 50, "#ffe23a")


def poster(c, lt, T, t):
    s2.light()
    tq = twos(lt)
    z = lerp(1.0, 1.06, ease_io(lt / 5))
    c.save()
    c.translate(960, 540); c.scale(z, z); c.translate(-960, -540)
    # weathered board wall
    for i in range(9):
        x0 = -40 + i * 230
        plank = np.array([(x0, -40), (x0 + 226, -40), (x0 + 226, H + 40), (x0, H + 40)])
        painterly(c, path_of(plank), mix("#6a4a32", "#4e3828", (i % 3) / 3), seed=1350 + i, strength=0.6, angle=1.57)
        ink_line(c, plank[[1, 2]], 2.0, do_boil=False, alpha=0.6)
    pw, ph = 620, 860
    px, py = 960, 540
    silas_poster(c, px, py, pw, ph)
    # rival poster unrolls from the top while a brush pastes it down
    t0 = BEATS["s3_paste"] - 56.0
    u = ease_io(remap(tq, t0, t0 + 2.0), 1.6)
    if u > 0:
        hh = ph * u
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(px - pw / 2 - 6, py - ph / 2 - 6, px + pw / 2 + 6, py - ph / 2 + hh))
        rival_poster(c, px, py, pw + 10, ph + 10)
        # wet paste sheen fading
        c.drawRect(skia.Rect.MakeLTRB(px - pw / 2, py - ph / 2, px + pw / 2, py - ph / 2 + hh), paint("#ffffff", 0.06 * (1 - remap(tq, t0 + 2, t0 + 3.5))))
        c.restore()
        if u < 1:   # the roll
            ry = py - ph / 2 + hh
            roll = skia.Rect.MakeLTRB(px - pw / 2 - 10, ry - 16, px + pw / 2 + 10, ry + 16)
            c.drawRoundRect(roll, 16, 16, paint("#0e7aa8"))
            c.drawRoundRect(roll, 16, 16, paint("#10202a", stroke=3))
        # paste brush on a gloved arm sweeping across the fresh paper
        if t0 <= tq <= t0 + 2.6:
            bx = px + 260 * math.sin((tq - t0) * 5.2)
            by = py - ph / 2 + max(40.0, hh - 60)
            arm = np.array([(W + 80, by + 140), (bx + 120, by + 40), (bx + 110, by + 70), (W + 80, by + 190)])
            shape(c, arm, "#3a3a44", 4, seed=1360)
            shape(c, np.array([(bx - 70, by - 12), (bx + 70, by - 12), (bx + 70, by + 14), (bx - 70, by + 14)]), "#c8a060", 3, seed=1361)
            shape(c, np.array([(bx - 66, by + 14), (bx + 66, by + 14), (bx + 60, by + 40), (bx - 60, by + 40)]), "#e8e0c8", 2.5, seed=1362)
            shape(c, ellipse(bx + 118, by + 50, 26, 22, 14), "#2a2a30", 3, seed=1363)
    c.restore()
    return grade_mix(0.4)


# ============================================================================ the bank notice

def notice(c, lt, T, t):
    s1.light_cold()
    tq = twos(lt)
    hits = [b - 61.0 for b in BEATS["s3_hammer"]]
    shake = 0.0
    for h in hits:
        if 0 <= tq - h < 0.15:
            shake = (1 - (tq - h) / 0.15)
    # background: blurred tent canvas stripes
    for i in range(12):
        x0 = -60 + i * 180
        c.drawRect(skia.Rect.MakeLTRB(x0, -10, x0 + 180, H + 10), paint("#7e4c44" if i % 2 else "#a9a593"))
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#1a1a20", 0.45))
    # the pole
    pole = np.array([(820, -20), (1100, -20), (1100, H + 20), (820, H + 20)])
    painterly(c, path_of(pole), "#5a4030", seed=1400, strength=0.8, angle=1.57)
    for k in range(6):
        ink_line(c, np.array([(840 + k * 45, -20), (845 + k * 45 + 8 * math.sin(k), H + 20)]), 1.5, alpha=0.4, do_boil=False)
    ink_line(c, pole[[0, 3]], 4, do_boil=False)
    ink_line(c, pole[[1, 2]], 4, do_boil=False)
    # notice paper
    nx, ny = 962 + shake * 2, 520 + shake * 1.5
    c.save()
    c.translate(nx, ny)
    c.rotate(-2 + 0.8 * math.sin(lt * 1.3) * remap(tq, hits[-1] + 0.5, hits[-1] + 1.5))
    paper = np.array([(-190, -250), (190, -250), (186, 250), (-188, 246)])
    shape(c, paper, "#e8e0cc", 3, seed=1410, shade_depth=8)
    text(c, "FIRST NATIONAL BANK", 0, -190, "oldstd_b", 30, "#1a1a1a")
    text(c, "NOTICE OF FORECLOSURE", 0, -146, "oldstd", 24, "#1a1a1a")
    for k in range(5):
        c.drawRect(skia.Rect.MakeLTRB(-150, -100 + k * 26, 150 - (k % 2) * 40, -96 + k * 26), paint("#5a5a5a", 0.5))
    c.save(); c.rotate(-8)
    text(c, "FORECLOSED", 0, 106, "rye", 46, "#b01a22", 0.92)
    c.drawRect(skia.Rect.MakeLTRB(-160, 56, 160, 126), paint("#b01a22", 0.9, stroke=5))
    c.restore()
    text(c, "PROPERTY OF THE BANK", 0, 215, "oldstd", 22, "#1a1a1a")
    c.restore()
    # nail head appears with the first hit
    if tq >= hits[0]:
        depth = min(1.0, sum(1 for h in hits if tq >= h) / 3)
        c.drawCircle(nx, ny - 232, 9 - 2 * depth, paint("#6a6a70"))
        c.drawCircle(nx, ny - 232, 9 - 2 * depth, paint("#1a1a1a", stroke=2))
    # the hand holding the notice (left) withdraws after the last hit
    out = ease_io(remap(tq, hits[-1] + 0.35, hits[-1] + 1.1))
    hx = lerp(760, 300, out)
    arm = np.array([(-60, 560), (hx - 40, 470), (hx + 10, 500), (-60, 640)])
    shape(c, arm, "#2c2c34", 4, seed=1420)
    shape(c, spline(np.array([(hx - 30, 460), (hx + 40, 450), (hx + 70, 470), (hx + 60, 500), (hx + 10, 510), (hx - 30, 500)]), closed=True, n=3),
          "#d8c0a8", 3.5, seed=1421, shadow_col="#8a6a5a")
    # the hammer arm (right): wind up and strike on each beat
    ang = 0.0
    for h in hits:
        if h - 0.45 <= tq <= h + 0.2:
            ang = keys(tq, [(h - 0.45, 0.0), (h - 0.12, -1.1), (h, 0.05, "in"), (h + 0.2, 0.0)])
    retreat = ease_io(remap(tq, hits[-1] + 0.4, hits[-1] + 1.2))
    piv = np.array([nx + 470 + 500 * retreat, ny - 232.0])
    X = Xf.T(*piv).r(ang)
    shape(c, X(np.array([(300, -40), (0, -26), (0, 26), (300, 50)])), "#2c2c34", 4, seed=1430)
    shape(c, X(spline(np.array([(-20, -30), (30, -34), (40, 0), (30, 30), (-20, 30), (-34, 0)]), closed=True, n=3)), "#d8c0a8", 3.5,
          seed=1431, shadow_col="#8a6a5a")
    shape(c, X(np.array([(-10, -8), (-460, -10), (-460, 10), (-10, 8)])), "#7a5a3a", 3, seed=1432)
    shape(c, X(np.array([(-500, -46), (-440, -46), (-440, 46), (-500, 46)])), "#5a5a62", 3.5, seed=1433, shade_depth=8)
    return grade_mix(0.6)


# ============================================================================ leaving

def _suitcase(cv, fig, X, col="#6a4a2a"):
    sw = 0.0
    body = np.array([(-34, 18), (34, 18), (34, 80), (-34, 80)])
    shape(cv, X(body), col, fig.lw(), seed=1500, shade_depth=6)
    ink_line(cv, X(np.array([(-12, 18), (-10, 6), (10, 6), (12, 18)])), fig.lw(0.8), seed=1501)
    for sx in (-22, 22):
        cv.drawRect(skia.Rect.MakeLTRB(*X(np.array([sx - 3, 18.0])), *X(np.array([sx + 3, 80.0]))), paint("#2a1a10", 0.8))


def leaving(c, lt, T, t):
    S.key = (-0.6, -0.8); S.shadow_col = "#2a2030"; S.shadow_a = 0.32; S.rim = None; S.rim_a = 0
    cam = Cam(960, 560, lerp(1.0, 1.04, lt / 6))
    s1._img(c, s1.ext_sky("dusk"), cam, 0.15)
    s1._img(c, s1.ext_tent(False), cam, 0.7)
    with cam.layer(c, 1.0):
        ground = np.array([(-200, 760), (W + 200, 760), (W + 200, H + 200), (-200, H + 200)])
        painterly(c, path_of(ground), "#4a4438", seed=1550, strength=0.6)
    tq = twos(lt)
    starts = [b - 65.0 for b in BEATS["s3_leave"]]
    figs = [(Bruno(2), 0.62, 120.0, 0.5, "#5a3a24"), (Lena(2), 0.64, 104.0, 0.46, "#3a2a2a"), (Pip(2), 0.78, 80.0, 0.4, "#7a5a3a")]
    with cam.layer(c, 1.0):
        for k in (2, 1, 0):
            fig, sc, L, sd, col = figs[k]
            ts = starts[k]
            if tq < ts:
                continue
            walk = Walk(ts, 24, L, sd, start_u=0.0, stance=10, bob=3.0, lift=10, toe=0.35)
            wp = walk.pose(tq, s=sc, face=1, origin_x=945, ground_y=800 + k * 10)
            sw = walk.swing(tq)
            P = fig.pose(**wp)
            P.update(turn=0.9, lean=0.08, head_rot=0.18, smile=-0.3, blink=auto_blinks(lt, 40 + k),
                     arm_n=("fk", 0.05 - 0.12 * sw, 0.15), hand_n="grip", arm_f=arm_swing_fk(sw, 0.25, 0.25, "f"))
            if k == 2:
                P["droop"] = 1.0
            # emerge from the dark entrance: fade from the doorway silhouette over the first steps
            emerge = remap(tq, ts, ts + 0.6)
            c.saveLayerAlpha(None, int(255 * emerge))
            fig.draw(c, P, props={"after": {"arm_n": lambda cv, f, J, M, col=col: _suitcase(
                cv, f, Xf.T(*M(J["hand_n"])).s(f._scale).t(0, -8), col)}})
            c.restore()
    # redraw the doorway edges over the emerging figures' backs (they step out of it)
    return grade_mix(0.75)


# ============================================================================ the storm

TEAR = np.array([(380, 230), (520, 160), (700, 140), (880, 90), (1060, 110), (1240, 60), (1420, 120), (1560, 180)], float)


def _tear_poly(u, t):
    """Opening in the roof that grows along TEAR as u goes 0->1."""
    path = TEAR
    seg = np.hypot(*np.diff(path, axis=0).T)
    L = seg.sum()
    s_tip = u * L
    pts_up, pts_dn = [], []
    acc = 0.0
    n = 60
    cum = np.concatenate([[0], np.cumsum(seg)])
    for i in range(n + 1):
        s = s_tip * i / n
        j = min(np.searchsorted(cum, s) - 1, len(seg) - 1)
        j = max(j, 0)
        f = (s - cum[j]) / seg[j]
        p = path[j] + (path[j + 1] - path[j]) * f
        d = (path[j + 1] - path[j]) / seg[j]
        nrm = np.array([-d[1], d[0]])
        w = min(62.0, (s_tip - s) * 0.22) * (0.85 + 0.3 * math.sin(s * 0.021))
        jag = 3.5 * math.sin(s * 0.23) + 2 * math.sin(s * 0.61)
        pts_up.append(p - nrm * (w * 0.35 + jag * 0.3))
        pts_dn.append(p + nrm * (w + jag))
    return np.array(pts_up), np.array(pts_dn)


def storm(c, lt, T, t):
    s2.light()
    cam = Cam(**s2.WIDE_CAM)
    tq = twos(lt)
    rip_t = BEATS["s3_rip"] - 71.0
    bursts_abs = BEATS["s3_bursts"]
    _, bulbs = tent.string_lights(1)
    r = rng(5)
    order = r.permutation(len(bulbs))
    burst = {int(idx): bursts_abs[i % len(bursts_abs)] - 71.0 + 0.04 * (i // len(bursts_abs)) for i, idx in enumerate(order)}
    flash = lightning_flash(t, BEATS["s3_thunder"])
    wind = 0.6 + 0.4 * math.sin(lt * 1.7)
    u = ease_out(remap(lt, rip_t, rip_t + 1.6), 1.6)
    n_burst = sum(1 for b in bursts_abs if lt >= b - 71.0)

    def sky_fn(cv):
        pass

    def ring_chars(cv):
        pass

    # draw the tent with the bursting lights, then cut the tear into the roof
    tent.draw_tent(c, cam, lt, 1, occupancy=0.0, mood="idle", bursts=burst, wind=wind, front_row=False,
                   spots=[((1770, -40), (960, 800))] if n_burst < 3 else None, spot_a=0.12, after_stands=ring_chars)
    if u > 0:
        up, dn = _tear_poly(u, lt)
        with cam.layer(c, 0.6):
            hole = np.vstack([up, dn[::-1]])
            c.save()
            c.clipPath(path_of(hole), skia.ClipOp.kIntersect, True)
            c.drawRect(skia.Rect.MakeLTRB(-200, -400, W + 200, 600), paint("#0d141b"))
            c.drawRect(skia.Rect.MakeLTRB(-200, -400, W + 200, 600), paint("#c8dcff", 0.5 * flash))
            rain(c, lt, seed=33, n=200, speed=1900, length=40, a=0.5, area=(300, -100, 1600, 400))
            c.restore()
            ink_line(c, up, 2.5, do_boil=False)
            # the torn lower edge hangs down as a flap, whipping in the wind
            wl = np.minimum(1.0, np.linspace(1.0, 0.0, len(dn)) * 3)[:, None]
            flap_len = (30 + 40 * u) * wl[:, 0]
            wave = np.sin(np.linspace(0, 4, len(dn)) + lt * 4.0) * 10 * wind * wl[:, 0]
            flap_bot = dn + np.stack([wave, flap_len], 1)
            flap = np.vstack([dn, flap_bot[::-1]])
            shape(c, flap, "#a8483e", 2.2, seed=1600, shade_depth=8)
        # rain pours in through the opening onto the ring
        with cam.layer(c, 0.85):
            rain(c, lt, seed=34, n=int(340 * u), speed=2000, length=50, a=0.35, area=(380, 100, 1560, 900), angle=0.12)
    # darkness grows as the lights die
    c.drawRect(skia.Rect.MakeWH(W, H), paint("#05060a", 0.08 * n_burst))
    if flash > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint("#dce8ff", 0.2 * flash, blend=skia.BlendMode.kScreen))
    # colors drain in real time, from the first burst to the end of the scene
    drain = ease_io(remap(lt, bursts_abs[0] - 71.0, 6.8), 1.4)
    return _storm_grade(drain, flash)


def _storm_grade(drain, flash):
    g = grade_mix(drain)
    g["lift"] = tuple(v + 0.08 * flash for v in g["lift"])
    return g


SHOTS = dict(nights=nights, poster=poster, notice=notice, leaving=leaving, storm=storm)
