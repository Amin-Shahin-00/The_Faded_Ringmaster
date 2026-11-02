"""SCENE 2 - THE GOLDEN DAYS (0:18 - 0:48). Act 1: warm, saturated, bouncy, big arcs."""
import math
import numpy as np
import skia
from lib.core import W, H, Xf, keys, clamp, lerp, remap, smooth, ease_io, ease_out, ease_back, twos, paint, mix, rng, hexc
from lib.ink import S, shape, ink_line, fill, ellipse, spline, path_of
from lib.frame import Cam, text
from lib.motion import Walk, arm_swing_fk, follow
from config.palettes import GRADE, ENV
from config.timeline import BEATS
from rigs.silas import Silas
from rigs.cast import Bruno, Lena, Pip
from rigs.crowd import make_people, person, back_of_head, CROWD_COLS, SKINS
from scenes import tent
from scenes.common import radial, cone, painterly
from scenes.silas_moves import bow_pose, BOW_CAM, auto_blinks, breathing

ACT = 1
WIDE_CAM = dict(x=960.0, y=560.0, zoom=1.0)
RING_Y = 832.0          # Silas's ground line on the ring floor (wide)
WIDE_S = 0.42


def light():
    S.key = (-0.45, -0.89)
    S.shadow_col = "#6a1a30"
    S.shadow_a = 0.30
    S.rim = (0.55, -0.83)
    S.rim_col = "#ffe6a8"
    S.rim_a = 0.35


def grade(**kw):
    g = dict(GRADE[1])
    g.update(kw)
    return g


def popcorn(c, cam, t, n=40, seed=8):
    """Popcorn kernels tossed in the air above the stands (smooth 24 fps arcs)."""
    r = rng(seed)
    pars = r.random((n, 4))
    with cam.layer(c, 0.85):
        for (u, ph, k, sp) in pars:
            period = 1.4 + sp
            life = ((t + ph * period) % period) / period
            cyc = math.floor((t + ph * period) / period)
            x0 = 80 + ((u + cyc * 0.31) % 1.0) * (W - 160)
            y0 = tent.arc_y(x0, *tent.tier_arc(int(k * 6))) - 30
            vx = (k - 0.5) * 60
            vy = -260 - 120 * sp
            tt = life * period
            x = x0 + vx * tt
            y = y0 + vy * tt + 0.5 * 420 * tt * tt
            if y > y0 + 20:
                continue
            s = 3.2 + 2 * k
            blob = ellipse(x, y, s, s * 0.85, 8, rot=tt * 4)
            c.drawPath(path_of(blob), paint("#fff3d0"))
            c.drawCircle(x - s * 0.3, y - s * 0.2, s * 0.4, paint("#f2c46a", 0.8))


# ============================================================================ shots

def wide_full(c, lt, T, t):
    """Packed tent. Silas struts into the ring, turns to the crowd and spins his cane."""
    light()
    z = lerp(1.0, 1.07, ease_io(lt / 6.5))
    cam = Cam(960, lerp(560, 590, ease_io(lt / 6.5)), z)
    tq = twos(lt)
    fig = Silas(ACT)
    walk = Walk(0.0, 11, 84, 0.3, start_u=0.0, stance=12, bob=7, lift=18, toe=0.5)
    end_u = walk.pelvis(99)[0]
    origin = 960 + end_u * WIDE_S          # finishes at ring centre walking left
    wp = walk.pose(tq, s=WIDE_S, face=-1, origin_x=origin, ground_y=RING_Y)
    sw = walk.swing(tq)
    turn = keys(tq, [(3.3, 0.95), (3.9, 0.25, "back")])
    P = fig.pose(**wp)
    spin_t = remap(tq, 4.1, 5.8)
    P.update(turn=turn, smile=0.8, blink=auto_blinks(lt, 1), lean=0.06 * (tq < 3.3), crow=1.0,
             arm_f=arm_swing_fk(sw, 0.5, 0.3, "f") if tq < 3.3 else ("fk", -0.35, 0.4),
             hand_n="grip", cane=("hand_n", 0.0, "front"))
    if tq < 3.3:
        P["arm_n"] = ("fk", 0.35 - 0.4 * sw, 0.5)
        P["head_rot"] = 0.04 * math.sin(tq * 20)
    else:
        # step to face the crowd; cane goes up overhead and spins, then arms open wide
        up = keys(tq, [(3.6, 0.0), (4.1, 1.0, "back"), (5.8, 1.0), (6.2, 0.0)])
        hand = keys(tq, [(3.6, (60.0, -230.0)), (4.1, (20.0, -470.0), "back"), (5.8, (20.0, -470.0)), (6.2, (110.0, -330.0), "back")])
        P["arm_n"] = tuple(hand)
        spin = ease_io(spin_t, 1.6) * math.tau * 2.5
        P["cane"] = ("hand_n", -math.pi / 2 - spin * (1 if spin_t < 1 else 1), "front")
        P["pelvis"] = (0.0, keys(tq, [(3.6, 0.0), (4.0, 6.0), (4.25, -6.0), (4.5, 0.0)]))
        P["foot_n"] = (keys(tq, [(3.3, P["foot_n"][0]), (3.75, 18.0)]), max(0.0, math.sin(math.pi * remap(tq, 3.3, 3.75))) * 14)
        P["foot_f"] = (keys(tq, [(3.3, P["foot_f"][0]), (3.75, -16.0)]), 0.0)
        P["open"] = keys(tq, [(5.6, 0.0), (6.0, 0.5), (6.5, 0.2)])
        P["arm_f"] = ("fk", keys(tq, [(5.7, -0.35), (6.2, -1.6, "back")]), keys(tq, [(5.7, 0.4), (6.2, 0.15)]))
    P["tail_swing"] = -follow(lambda tt: walk.pose(tt, s=1)["x"] * 0.004, tq, k=60, zeta=0.3)

    def ring_chars(cv):
        with cam.layer(cv, 1.0):
            fig.draw(cv, P)
            if 0.0 < spin_t < 1.0:     # motion smear arcs on the spinning cane
                h = fig.hand_xf(fig.J, fig.M, "n")
                cxy = h(np.array([14.0, 0.0]))
                cv.drawCircle(float(cxy[0]), float(cxy[1]), 232 * WIDE_S * 0.5, paint("#ffffff", 0.08, stroke=3))
        popcorn(cv, cam, lt)

    tent.draw_tent(c, cam, lt, ACT, occupancy=1.0, mood="cheer",
                   spots=[((150, -40), (960, 800)), ((1770, -40), (960, 800))], after_stands=ring_chars)
    return grade()


def bow(c, lt, T, t):
    """Medium full figure: the Act 1 bow (mirrored exactly in Scene 7)."""
    light()
    cam = Cam(**BOW_CAM)
    tq = twos(lt)
    fig = Silas(ACT)
    u = tq + 0.0
    P = bow_pose(fig, u, ACT, extra=dict(blink=auto_blinks(lt, 3), breath=breathing(lt)))
    tent.draw_ring_medium(c, lt, ACT, xshift=-30)
    # warm spotlight pool on the floor
    radial(c, 900, 1010, 560, "#ffdf9a", 0.38, blend=skia.BlendMode.kScreen)
    fig.draw(c, P)
    return grade()


def bruno(c, lt, T, t):
    """Bruno lifts a cannon over his head."""
    light()
    cam = Cam(960, 690, 2.0)
    tq = twos(lt)
    tent.draw_ring_medium(c, lt, ACT, xshift=60)
    radial(c, 960, 1000, 560, "#ffdf9a", 0.36, blend=skia.BlendMode.kScreen)
    b = Bruno(ACT)
    up = BEATS["s2_cannon_up"] - 29.5     # 1.7
    # cannon centre (local units): floor -> chest -> overhead
    cy = keys(tq, [(0.0, -40.0), (0.55, -40.0), (1.15, -255.0, "io"), (up, -520.0, "back"), (3.0, -515.0), (4.0, -512.0)])
    wob = math.sin(tq * 9) * 2.5 * remap(tq, up, up + 0.3)
    pel = keys(tq, [(0, 0.0), (0.5, 46.0), (0.6, 50.0), (1.15, 18.0), (1.4, 26.0), (up, -4.0, "back"), (2.2, 0.0)])
    sq = keys(tq, [(0, 0.0), (0.55, -0.06), (1.15, 0.0), (up, 0.05), (2.0, 0.0)])
    P = b.pose(x=960, y=1010, s=1.18, turn=0.12, face=1, pelvis=(0.0, pel), squash=sq,
               foot_n=(-12.0, 0.0), foot_f=(12.0, 0.0), arm_n=(-70.0 + wob, cy), arm_f=(70.0 + wob, cy),
               hand_n="grip", hand_f="grip", lean=keys(tq, [(0, 0.0), (0.55, 0.25), (1.15, 0.05), (up, 0.0)]),
               smile=keys(tq, [(0, 0.3), (1.2, -0.1), (up + 0.4, 0.7)]), open=keys(tq, [(up + 0.3, 0.0), (up + 0.6, 0.3), (3.5, 0.2)]),
               brow=keys(tq, [(0.5, 0.0), (1.2, -0.6), (up + 0.4, 0.4)]), blink=auto_blinks(lt, 5),
               narrow=keys(tq, [(0.6, 0.0), (1.2, 0.6), (up + 0.3, 0.0)]), head_rot=keys(tq, [(0.5, 0.15), (1.2, -0.1), (up, -0.25)]))

    def cannon(cv, fig, J, M):
        hn, hf = J["hand_n"], J["hand_f"]
        mid = (hn + hf) / 2
        ang = math.atan2(hf[1] - hn[1], hf[0] - hn[0])
        X = M.t(*mid).r(ang)
        shape(cv, X(ellipse(-140, 0, 11, 11, 14)), "#2a2a30", fig.lw(), seed=1499, shade_depth=3)
        barrel = np.array([(-132, -10), (-124, -30), (-100, -33), (60, -21), (100, -20), (112, -26), (124, -25), (126, 0),
                           (124, 25), (112, 26), (100, 20), (60, 21), (-100, 33), (-124, 30), (-132, 10)])
        shape(cv, X(spline(barrel, closed=True, n=3)), "#2a2a30", fig.lw(), seed=1500, shade_depth=10)
        for xx, r in ((-104, 34), (40, 24), (106, 25)):
            shape(cv, X(np.array([(xx - 5, -r), (xx + 5, -r + 1), (xx + 5, r - 1), (xx - 5, r)])), "#e8b23a", fig.lw(0.6), seed=1501 + xx, shade_depth=3)
        shape(cv, X(ellipse(126, 0, 5, 18, 14)), "#0e0e12", fig.lw(0.6), seed=1505, shadow=False)
        cv.drawCircle(*map(float, X(np.array([-112.0, -26.0]))), 3.0 * fig._scale, paint("#0e0e12"))
        fill(cv, X(np.array([(-96, -24), (80, -15), (80, -10), (-96, -17)])), "#ffffff", alpha=0.18, do_boil=False)
    b.draw(c, P, props={"before": {"arm_f": cannon}})
    # strain sweat drops while pressing
    if 1.1 < tq < up + 0.6:
        hx = b.M(b.J["head_xf"](np.array([30.0, -70.0])))
        y = hx[1] + (tq - 1.1) * 90
        c.drawPath(path_of(ellipse(hx[0] + 12, y, 3.5, 5, 10)), paint("#dff4ff", 0.8))
    tent.draw_front_row(c, Cam(960, 540, 1.0), lt, ACT, mood="cheer", n=9, y=1150, size=36, seed=31)
    return grade()


def _knife_targets():
    return [(1468.0, 392.0), (1404.0, 458.0), (1540.0, 462.0), (1556.0, 690.0)]


def lena(c, lt, T, t):
    """Lena throws knives around a smiling volunteer's silhouette."""
    light()
    cam = Cam(960, 690, 2.0)
    tq = twos(lt)
    tent.draw_ring_medium(c, lt, ACT, xshift=-140)
    radial(c, 1460, 760, 420, "#ffdf9a", 0.3, blend=skia.BlendMode.kScreen)
    radial(c, 430, 900, 380, "#ffdf9a", 0.22, blend=skia.BlendMode.kScreen)
    # the board + volunteer
    board_c = (1465, 600)
    shape(c, np.array([(1452, 980), (1478, 980), (1474, 640), (1456, 640)]), "#6a4026", 3, seed=1600)
    for i, (r, col) in enumerate([(240, "#f3e3c0"), (200, "#c8202a"), (150, "#f3e3c0"), (100, "#c8202a"), (50, "#f3e3c0")]):
        shape(c, ellipse(board_c[0], board_c[1], r * 0.72, r, 40), col, 3 if i == 0 else 1.5, seed=1601 + i, shadow=i == 0)
    # volunteer: a dark silhouette with a big smile
    vt = math.sin(lt * 1.6) * 2
    flinch = 0.0
    hits = [b - 33.5 for b in BEATS["s2_knives"]]
    for h in hits:
        if 0 <= tq - h < 0.25:
            flinch = 1 - (tq - h) / 0.25
    vol = np.array([(1418, 985), (1424, 790), (1414, 760), (1412, 640), (1372, 640), (1338, 662), (1330, 640), (1368, 600),
                    (1420, 560), (1465, 548), (1510, 560), (1562, 600), (1600, 640), (1592, 662), (1558, 640), (1518, 640),
                    (1516, 760), (1506, 790), (1512, 985), (1478, 985), (1468, 830), (1462, 830), (1452, 985)], float)
    vol[:, 1] += flinch * 4
    shape(c, spline(vol, closed=True, n=2), "#2a1e2a", 3, seed=1610)
    hy = 486 + vt * 0.3 + flinch * 6
    shape(c, ellipse(1465, hy, 42, 44, 24), "#2a1e2a", 3, seed=1611)
    eye_c = 0.0 if flinch < 0.3 else 1.0
    for sx in (-12, 12):
        if eye_c < 0.5:
            c.drawCircle(1465 + sx, hy - 6, 4, paint("#fff6e0"))
        else:
            c.drawLine(1465 + sx - 5, hy - 6, 1465 + sx + 5, hy - 6, paint("#fff6e0", stroke=2.5))
    ink_line(c, spline(np.array([(1448, hy + 12), (1465, hy + 22), (1482, hy + 12)]), n=5), 3.5, color="#fff6e0", seed=1612)
    # knives in the board (after each hit) and in flight
    L = Lena(ACT)
    rel_dt = 0.26
    tg = _knife_targets()
    hand_pos = None
    P = L.pose(x=430, y=1012, s=1.25, turn=0.85, face=1, foot_n=(30.0, 0.0), foot_f=(-26.0, 0.0), blink=auto_blinks(lt, 9),
               smile=0.05, breath=breathing(lt))
    # throwing arm (near) cycle per knife
    arm = (-0.25, 0.6)
    lean = 0.0
    for i, h in enumerate(hits):
        a0, rel = h - 0.62, h - rel_dt
        if a0 <= tq <= rel + 0.35:
            arm = keys(tq, [(a0, (-0.25, 0.6)), (a0 + 0.12, (0.3, 1.3)), (rel - 0.12, (-1.9, 2.0), "io"), (rel, (1.35, 0.15), "out"),
                            (rel + 0.18, (1.15, 0.25)), (rel + 0.35, (-0.25, 0.6))])
            lean = keys(tq, [(a0, 0.0), (rel - 0.12, -0.12), (rel, 0.16, "out"), (rel + 0.35, 0.0)])
            break
    P.update(arm_n=("fk", arm[0], arm[1]), hand_n="pinch", lean=lean, arm_f=("fk", -0.15, 0.35), hand_f="relax",
             pelvis=(0.0, abs(lean) * 10))
    L.draw(c, P)
    hand = L.hand_xf(L.J, L.M, "n")(np.array([18.0, 0.0]))
    for i, h in enumerate(hits):
        rel = h - rel_dt
        tx, ty = tg[i]
        if tq >= h:
            quiver = math.sin((tq - h) * 60) * 4 * math.exp(-(tq - h) * 9)
            _knife(c, tx - 28, ty, math.radians(quiver), 1.0, stuck=True)
        elif tq >= rel:
            u = (tq - rel) / rel_dt
            sx, sy = 560, 700 - 30 * i
            x = lerp(sx, tx - 28, u)
            y = lerp(sy, ty, u) - 60 * math.sin(math.pi * u)
            ang = math.atan2((ty - sy) - 60 * math.pi * math.cos(math.pi * u), tx - 28 - sx)
            for k in (2, 1):
                _knife(c, x - k * 30, y + k * 2, ang, 0.22 / k)
            _knife(c, x, y, ang, 1.0)
        elif i == 0 or tq >= hits[i - 1]:
            pass
    tent.draw_front_row(c, Cam(960, 540, 1.0), lt, ACT, mood="cheer", n=9, y=1150, size=36, seed=33)
    return grade()


def _knife(c, x, y, ang, alpha, stuck=False):
    X = Xf.T(x, y).r(ang)
    blade = np.array([(0, -5), (52, -3), (64, 0), (52, 3), (0, 5)])
    if stuck:
        blade = np.array([(0, -5), (30, -3), (30, 3), (0, 5)])
    shape(c, X(blade), "#e8ecf0", 1.8, seed=1700, alpha=alpha, shade_depth=2)
    shape(c, X(np.array([(-34, -6), (0, -6), (0, 6), (-34, 6)])), "#c8202a", 1.8, seed=1701, alpha=alpha, shade_depth=2)
    shape(c, X(np.array([(-3, -10), (3, -10), (3, 10), (-3, 10)])), "#e8b23a", 1.4, seed=1702, alpha=alpha, shadow=False)


def _balls(tq, b, hands, slip_t, floor=996.0):
    """3-ball cascade from hand positions; after the slip the balls fall free."""
    out = []
    starts = [(0.0, "n"), (b, "f"), (2 * b, "n")]
    g = 1400.0
    for i, (t0, h0) in enumerate(starts):
        tt = min(tq, slip_t)
        k = math.floor((tt - t0) / (3 * b)) if tt >= t0 else -1
        if tt < t0:
            # waiting in its starting hand
            pos = hands[h0]
            out.append(pos); continue
        tk = t0 + k * 3 * b
        frm = h0 if k % 2 == 0 else ("f" if h0 == "n" else "n")
        to = "f" if frm == "n" else "n"
        u = (tt - tk) / (2 * b)
        if u <= 1.0:
            a, z = hands[frm], hands[to]
            x = lerp(a[0], z[0], u)
            y = lerp(a[1], z[1], u) - 4 * 200 * u * (1 - u)
            pos = np.array([x, y])
        else:
            pos = hands[to]
        if tq > slip_t:
            dt = tq - slip_t
            v0 = np.array([(-1) ** i * 90.0, -260.0])
            p = pos + v0 * dt + np.array([0, 0.5 * g * dt * dt])
            if p[1] > floor:   # bounce
                tb = (-v0[1] + math.sqrt(v0[1] ** 2 + 2 * g * (floor - pos[1]))) / g if (v0[1] ** 2 + 2 * g * (floor - pos[1])) > 0 else dt
                d2 = dt - tb
                vb = 0.45 * (v0[1] + g * tb)
                p = np.array([pos[0] + v0[0] * dt, floor - vb * d2 + 0.5 * g * d2 * d2])
                if p[1] > floor:
                    p[1] = floor
            pos = p
        out.append(pos)
    return out


def pip(c, lt, T, t):
    """Pip juggles, slips on purpose, the children laugh."""
    light()
    cam = Cam(960, 690, 2.0)
    tq = twos(lt)
    tent.draw_ring_medium(c, lt, ACT, xshift=140)
    radial(c, 960, 990, 520, "#ffdf9a", 0.36, blend=skia.BlendMode.kScreen)
    p = Pip(ACT)
    slip = BEATS["s2_pip_slip"] - 38.0   # 2.2
    b = 0.3
    s = 1.55
    ox = keys(tq, [(0, 880.0), (slip, 960.0)])
    # slip: feet shoot forward, body rotates back, lands on his bottom (squash)
    land = slip + 0.42
    pel_y = keys(tq, [(slip, 0.0), (slip + 0.12, -14.0, "out"), (land, 100.0, "in"), (land + 0.08, 104.0), (land + 0.25, 96.0)])
    lean = keys(tq, [(slip, 0.0), (slip + 0.2, -0.9, "out"), (land, -0.45), (land + 0.3, -0.2), (4.5, -0.15)])
    sq = keys(tq, [(land - 0.02, 0.0), (land + 0.04, -0.14), (land + 0.2, 0.04), (land + 0.32, 0.0)])
    fn = keys(tq, [(slip, (10.0, 0.0)), (slip + 0.2, (70.0, 70.0), "out"), (land, (80.0, 6.0)), (4.5, (82.0, 0.0))])
    ff = keys(tq, [(slip, (-10.0, 0.0)), (slip + 0.25, (40.0, 30.0)), (land, (58.0, 0.0)), (4.5, (60.0, 0.0))])
    walkb = 0.0 if tq > slip else abs(math.sin(tq * math.pi / 0.6)) * 3
    # juggling hands (local) circle in sync with the throws
    ph = (tq % (2 * b)) / (2 * b)
    hn_ = np.array([-26 + 8 * math.cos(math.tau * ph), -150 + 6 * math.sin(math.tau * ph)])
    hf_ = np.array([26 - 8 * math.cos(math.tau * ph), -150 - 6 * math.sin(math.tau * ph)])
    if tq > slip:
        k = remap(tq, slip, slip + 0.25)
        hn_ = lerp(hn_, np.array([-70.0, -240.0]), k)
        hf_ = lerp(hf_, np.array([70.0, -235.0]), k)
        if tq > land + 0.3:
            k2 = remap(tq, land + 0.3, land + 0.8)
            hn_ = lerp(hn_, np.array([-40.0, -60.0]), k2)
            hf_ = lerp(hf_, np.array([55.0, -140.0 + 30 * math.sin(tq * 3)]), k2)
    P = p.pose(x=ox, y=1012, s=s, turn=0.15, face=1, pelvis=(0.0, pel_y - walkb), lean=lean, squash=sq,
               foot_n=tuple(fn), foot_f=tuple(ff), arm_n=tuple(hn_), arm_f=tuple(hf_), hand_n="open", hand_f="open",
               smile=keys(tq, [(0, 0.6), (slip, 0.0), (land + 0.2, -0.3), (land + 0.6, 0.9)]),
               open=keys(tq, [(slip, 0.0), (slip + 0.1, 0.8), (land + 0.3, 0.2), (land + 0.7, 0.5)]),
               brow=keys(tq, [(slip, 0.0), (slip + 0.1, 1.0), (land + 0.6, 0.6)]), droop=0.2,
               look=(0.0, keys(tq, [(0, -1.0), (slip, -1.0), (slip + 0.2, 0.5), (land + 0.6, 0.0)])),
               blink=auto_blinks(lt, 11), head_rot=keys(tq, [(0, -0.12), (slip, -0.12), (land, 0.2), (land + 0.6, -0.05)]))
    p.draw(c, P)
    # balls (world positions from local hand positions)
    hands = {"n": p.M(p.J["hand_n"]), "f": p.M(p.J["hand_f"])}
    if tq <= slip:
        hp = hands
    else:
        hp = {"n": p.M(np.array([-26.0 + 0, -150.0])), "f": p.M(np.array([26.0, -150.0]))}
    for i, (pos, col) in enumerate(zip(_balls(tq, b, hp, slip, floor=1012 - 16), ["#d7262f", "#f2c14a", "#2f6fbf"])):
        x, y = pos
        shape(c, ellipse(x, y, 15, 15, 16), col, 2.4, seed=1800 + i, shade_depth=5)
        c.drawCircle(x - 5, y - 5, 4, paint("#ffffff", 0.5))
    # children laughing in the front row
    kids = make_people(41, 8, kid_ratio=1.0)
    laughing = tq > land
    fcam = Cam(960, 540, 1.0)
    with fcam.layer(c, 1.3):
        for i, kp in enumerate(kids):
            x = 80 + i * 250
            back_of_head(c, x, 1150 + (i % 2) * 20, 40, kp, lt * (2.0 if laughing else 1.0), act=ACT, mood="cheer" if laughing else "idle")
    return grade()


def _kid(c, x, y, s, t, catch, cheer):
    """Front-row child (more detailed than the crowd): cap, freckles, arms."""
    skin = "#f0c49a"
    shirt = "#3a6ab0"
    tq = twos(t)
    bounce = abs(math.sin(tq * 6)) * 4 * cheer
    body = np.array([(x - 46 * s, y + 80 * s), (x - 42 * s, y - 30 * s - bounce), (x - 18 * s, y - 50 * s - bounce),
                     (x + 18 * s, y - 50 * s - bounce), (x + 42 * s, y - 30 * s - bounce), (x + 46 * s, y + 80 * s)])
    shape(c, spline(body, closed=True, n=3), shirt, 2.6, seed=1900)
    hy = y - 92 * s - bounce
    shape(c, ellipse(x, hy, 38 * s, 40 * s, 24), skin, 2.6, seed=1901, shadow_col="#c98f6a")
    cap = np.vstack([ellipse(x, hy - 12 * s, 40 * s, 32 * s, 16, math.pi, 2 * math.pi), [(x + 62 * s, hy - 12 * s)]])
    shape(c, cap, "#c8202a", 2.4, seed=1902, shadow=False)
    blink = auto_blinks(t, 21)
    for sx in (-13, 13):
        if blink < 0.5 and cheer < 0.8:
            c.drawCircle(x + sx * s, hy + 2 * s, 4 * s, paint("#20140f"))
        else:
            ink_line(c, np.array([(x + (sx - 6) * s, hy + 3 * s), (x + sx * s, hy - 2 * s), (x + (sx + 6) * s, hy + 3 * s)]), 2.4, seed=1903 + sx)
    for fx in (-20, -16, 16, 20):
        c.drawCircle(x + fx * s, hy + 12 * s, 1.6 * s, paint("#c8704a", 0.7))
    mo = 0.3 + 0.7 * cheer
    m = np.vstack([ellipse(x, hy + 18 * s, 13 * s, 2 * s, 10, math.pi, 2 * math.pi), ellipse(x, hy + 18 * s, 13 * s, 12 * s * mo, 12, 0, math.pi)])
    shape(c, m, "#6a1a1a", 2.0, seed=1905, shadow=False)
    # arms up to catch
    for sd in (-1, 1):
        sh = np.array([x + sd * 34 * s, y - 34 * s - bounce])
        hand = np.array([x + sd * (14 + 20 * (1 - catch)) * s, y - (40 + 110 * catch) * s - bounce])
        el = (sh + hand) / 2 + np.array([sd * 22 * s, 10 * s])
        ink_line(c, np.array([sh, el, hand]), 22 * s, color=shirt, seed=1910 + sd, taper=0.0, var=0.05)
        shape(c, ellipse(hand[0], hand[1], 11 * s, 11 * s, 12), skin, 2.0, seed=1912 + sd, shadow=False)


def peanut(c, lt, T, t):
    """Silas tosses a peanut to a child and laughs - a real, wide laugh."""
    light()
    cam = Cam(960, 690, 1.9)
    tq = twos(lt)
    kid_x, kid_y = 1430.0, 318.0
    toss_ = BEATS["s2_peanut_toss"] - 42.5
    catch_t_ = toss_ + 0.8
    catch_ = keys(tq, [(0, 0.0), (toss_ + 0.2, 0.0), (catch_t_ - 0.15, 1.0), (catch_t_ + 0.6, 0.92)])

    def front_seats(cv):
        nb = make_people(51, 5, kid_ratio=0.0)
        for i, (xx, pp) in enumerate(zip((1120, 1260, 1600, 1745), nb)):
            person(cv, xx, 566, 34, pp, lt, mood="cheer" if tq > catch_t_ else "idle", act=ACT)
        _kid(cv, kid_x, 560, 1.35, lt, catch_, 1.0 if tq > catch_t_ else 0.2)
        if tq > catch_t_:
            X = Xf.T(kid_x, 560 - 150 * 1.35 * catch_ - 40 * 1.35).r(0.3)
            shape(cv, X(spline(np.array([(-9, -4), (-2, -6), (2, -3), (9, -5), (11, 2), (2, 5), (-2, 3), (-10, 4)]), closed=True, n=3)),
                  "#d8a860", 1.8, seed=1950, shade_depth=2)
    tent.draw_ring_medium(c, lt, ACT, xshift=220, mid_fn=front_seats)
    radial(c, 700, 1000, 560, "#ffdf9a", 0.36, blend=skia.BlendMode.kScreen)
    fig = Silas(ACT)
    toss = BEATS["s2_peanut_toss"] - 42.5     # 0.8
    laugh = BEATS["s2_laugh"] - 42.5          # 2.1
    catch_t = toss + 0.8
    shake = math.sin(tq * math.tau * 5) if tq > laugh else 0.0
    lean = keys(tq, [(0, 0.0), (toss - 0.3, 0.08), (toss, -0.05), (toss + 0.3, 0.06), (laugh, -0.18, "out"), (laugh + 0.6, -0.12), (4.0, -0.14)])
    hand = keys(tq, [(0, (40.0, -250.0)), (toss - 0.3, (-30.0, -170.0)), (toss, (95.0, -330.0), "out"), (toss + 0.4, (110.0, -310.0)),
                     (laugh, (30.0, -230.0)), (4.0, (32.0, -228.0))])
    P = fig.pose(x=680, y=1010, s=1.3, turn=0.45, face=1, lean=lean, pelvis=(0.0, abs(shake) * 2.5 * (tq > laugh)),
                 foot_n=(22.0, 0.0), foot_f=(-18.0, 0.0), arm_n=tuple(hand), hand_n="open" if tq > toss else "pinch",
                 arm_f=("fk", 0.15, 0.4) if tq < laugh else ("rel", 30.0, 105.0), hand_f="grip", cane=("hand_f", 0.2, "front"),
                 smile=keys(tq, [(0, 0.7), (laugh - 0.3, 0.8), (laugh, 1.0)]), open=keys(tq, [(laugh - 0.15, 0.1), (laugh + 0.05, 0.95, "out"), (4.0, 0.85)]) + 0.06 * shake,
                 narrow=keys(tq, [(laugh - 0.1, 0.0), (laugh + 0.1, 0.75)]), head_rot=keys(tq, [(0, 0.0), (laugh, -0.32, "out"), (4.0, -0.28)]) + 0.03 * shake,
                 head_turn=keys(tq, [(0, 0.45), (catch_t, 0.7)]), look=(0.6, 0.3), blink=auto_blinks(lt, 4) if tq < laugh else 0.0,
                 breath=breathing(lt))
    P["tail_swing"] = -follow(lambda tt: keys(tt, [(0, 0.0), (laugh, -0.18), (4, -0.14)]), tq, k=50, zeta=0.3)
    fig.draw(c, P)
    # peanut: arc from Silas's hand to the child
    if tq < toss:
        hp = fig.hand_xf(fig.J, fig.M, "n")(np.array([24.0, -4.0]))
        pn = hp
    elif tq < catch_t:
        u = (tq - toss) / (catch_t - toss)
        a = fig.hand_xf(fig.J, fig.M, "n")(np.array([24.0, -4.0])) if False else np.array([830.0, 600.0])
        z = np.array([kid_x, kid_y])
        pn = a + (z - a) * u + np.array([0.0, -300 * 4 * u * (1 - u)])
    else:
        pn = None
    if pn is not None:
        X = Xf.T(*pn).r(tq * 9)
        shape(c, X(spline(np.array([(-9, -4), (-2, -6), (2, -3), (9, -5), (11, 2), (2, 5), (-2, 3), (-10, 4)]), closed=True, n=3)),
              "#d8a860", 1.8, seed=1950, shade_depth=2)

    return grade()


def wide_cheer(c, lt, T, t):
    """Back on the wide master: full house on its feet, Silas waving. (Scene 3 opens on this angle.)"""
    light()
    cam = Cam(**WIDE_CAM)
    tq = twos(lt)
    fig = Silas(ACT)
    wave = math.sin(tq * math.tau * 1.6)
    P = fig.pose(x=960, y=RING_Y, s=WIDE_S, turn=0.2, face=1, arm_n=(40.0 + 30 * wave, -470.0), hand_n="open",
                 arm_f=("fk", -1.4, 0.3), hand_f="grip", cane=("hand_f", 0.4, "front"), smile=0.9, open=0.3,
                 pelvis=(0.0, abs(wave) * 3), blink=auto_blinks(lt, 2))

    def ring_chars(cv):
        with cam.layer(cv, 1.0):
            fig.draw(cv, P)
        popcorn(cv, cam, lt + 6.5)

    tent.draw_tent(c, cam, lt, ACT, occupancy=1.0, mood="cheer",
                   spots=[((150, -40), (960, 800)), ((1770, -40), (960, 800))], after_stands=ring_chars)
    return grade()


SHOTS = dict(wide_full=wide_full, bow=bow, bruno=bruno, lena=lena, pip=pip, peanut=peanut, wide_cheer=wide_cheer)
