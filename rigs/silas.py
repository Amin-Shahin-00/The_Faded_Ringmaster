"""SILAS MARLOWE - the ringmaster.

Design constants (model sheet):
  * height 440 to crown, top hat adds ~102; long face, sharp nose, thin curled mustache
  * red tailcoat: 6 gold buttons (2 columns x 3), gold trim on lapels, front edge, hem, cuffs
  * swallow tails with silk lining; cream breeches; black riding boots
  * black top hat with red band; white gloves; black cane with silver ball handle (r=9)
  * Act 2/3: same costume faded; near (right) coat-tail torn short; cracked hat band;
    LEFT glove missing (bare left hand); cane snapped in Scene 4 -> silver handle only.
"""
import math
import numpy as np
import skia
from lib.core import Xf, clamp, lerp, mix, mul, hexc, rot, paint, smooth
from lib.ink import shape, ink_line, fill, ellipse, spline, bez, S, boil, path_of
from rigs.figure import Figure, proj, ext, draw_hand
from config.palettes import SILAS, SILAS_MAKEUP

# ---- head outlines (head-local, chin bottom ~ (0,0), crown ~ (0,-93)) --------------
HEAD_FRONT = np.array([(0, -93), (15, -91), (25, -81), (29, -66), (29.5, -50), (27, -35), (21.5, -20),
                       (12.5, -7), (0, -1), (-12.5, -7), (-21.5, -20), (-27, -35), (-29.5, -50), (-29, -66),
                       (-25, -81), (-15, -91)], float)
HEAD_SIDE = np.array([(2, -94), (22, -88), (30, -74), (32, -61), (30.5, -46), (29.5, -31), (28.5, -17),
                      (24, -5), (12, -1), (-4, -5), (-16, -15), (-27, -33), (-35, -50), (-36, -68),
                      (-30, -84), (-15, -92)], float)

MUSTACHE_HALF = np.array([(-1.5, -33.2), (-8, -34.6), (-15, -33.4), (-21, -30.6), (-25.6, -31.6),
                          (-27.4, -35.6), (-25.4, -38.6), (-22.6, -37.2)], float)
BUTTONS = [(-0.30, -52), (-0.30, -71), (-0.30, -90), (0.30, -52), (0.30, -71), (0.30, -90)]

TORSO = [(-127, 17, 13, 15), (-121, 42, 17, 21), (-113, 51, 21, 24), (-97, 47, 27, 24),
         (-72, 39, 25, 21), (-48, 32, 21, 18), (-30, 31, 20, 19), (-12, 31, 20, 22), (5, 31, 19, 25)]


def hem_y(phi):
    a = abs(phi)
    if a < 0.18:
        return -22.0
    if a < 1.45:
        return lerp(-22.0, 5.0, smooth((a - 0.18) / 1.27))
    return 5.0


class Silas(Figure):
    hip_h = 200.0
    hip_w = 15.0
    thigh, shin, ankle = 99.0, 97.0, 5.0
    sh_y, sh_w = -112.0, 47.0
    upper, fore = 82.0, 76.0
    neck_y, neck_len = -124.0, 11.0
    head_scale = 1.0
    torso_levels = TORSO
    leg_w = (15.5, 10.5, 7.5)
    arm_w = (10.5, 8.2, 6.6)
    foot_len = 36.0
    line = 3.0

    def __init__(self, act=1):
        super().__init__(act)
        self.C = dict(SILAS[act])
        self.dark = act >= 2

    def pose_defaults(self):
        return dict(hat="head", hat_tilt=0.0, hat_drop=6.0 if self.dark else 0.0, cane=None, handle=None,
                    tail_swing=0.0, tail_flare=0.0, coat_open=0.0, brim_shadow=1.0 if self.dark else 0.0,
                    makeup=0.0, wipe=0.0, lining_boost=0.0, smile=0.75 if not self.dark else 0.0,
                    cold=0.0 if not self.dark else 0.6, crow=1.0 if not self.dark else 0.0,
                    hat_xf=None, cane_pieces=None, button_top=1.0)

    def neck_dx(self, th):
        return 2.0 * math.sin(th)

    # ------------------------------------------------------------------ helpers
    def hand_xf(self, J, M, k):
        P = self.P
        e, h = J["elbow_" + k], J["hand_" + k]
        a = math.atan2(h[1] - e[1], h[0] - e[0]) + P["wrist_" + k]
        return M.t(*h).r(a)

    def bare(self, k):
        """Left glove missing in Acts 2-3. Physical left = far hand."""
        return self.dark and k == "f"

    # ------------------------------------------------------------------ parts
    def draw_back(self, canvas, J, M):
        """Coat-tails (behind the legs) with their silk lining."""
        P, C, th = self.P, self.C, J["th"]
        T = M @ J["torso"]
        lean = P["lean"] + P["chest"] * 0.5
        lift = clamp(lean * 1.4 + P["lining_boost"])
        for side in (1, -1):        # far tail first
            phi = math.pi - side * 0.62
            x0, z = proj(phi, 31, 22, th)
            torn = self.dark and side == -1
            length = 104.0 if not torn else 78.0
            ang = -lean * 0.88 + P["tail_swing"] * (1.0 if side == 1 else 0.86)
            flare = (P["tail_flare"] + lift * 0.28) * (-1 if x0 < 0 else 1) * (0.4 + 0.6 * math.cos(th))
            X = T.t(x0, 2).r(ang + flare * 0.5)
            wtop, wbot = 15.0, 10.5
            out = side * (1 if math.cos(th) > 0.3 else 0.4)
            if not torn:
                tip = [(out * 4 + wbot, length - 6), (out * 4 - wbot * 0.2, length + 4), (out * 4 - wbot, length - 2)]
            else:
                tip = [(wbot, length - 4), (6, length + 3), (2, length - 6), (-3, length + 2), (-wbot, length - 3)]
            pts = np.array([(-wtop, 0), (wtop, 0), (wtop * 0.9, length * 0.5)] + tip + [(-wtop * 0.95, length * 0.5)], float)
            pts = spline(pts, closed=True, n=4) if not torn else pts
            lining = C["lining"]
            sid = 300 + (side + 1) * 10
            shape(canvas, X(pts), lining, self.lw(), seed=sid, shade_depth=6)
            # outer cloth leaves a lining band on the inner edge that widens as he bows
            band = 3.0 + 15.0 * lift
            inner = -1 if out > 0 else 1
            o = np.array(pts)
            o[:, 0] = np.clip(o[:, 0], -wtop + (band if inner < 0 else 0), wtop - (band if inner > 0 else 0))
            shape(canvas, X(o), C["coat"], self.lw(0.8), seed=sid + 3, shade_depth=7, shadow_col=C["coat_shade"])
            # gold trim along the hem of the tail
            ink_line(canvas, X(o[len(o) // 2 - 2:len(o) // 2 + 3]), self.lw(0.9), color=C["trim"], seed=sid + 6, taper=0.1)

    def draw_leg(self, canvas, J, M, k):
        P, C, th = self.P, self.C, J["th"]
        hip, knee, ank = J["hip_" + k], J["knee_" + k], J["ankle_" + k]
        sid = 100 if k == "n" else 120
        lw = self.lw()
        # breeches
        leg = self.limb_poly(hip + np.array([0, -8]), knee, ank, (self.leg_w[0] + 2, self.leg_w[1] + 1, self.leg_w[2]), bulge=3)
        shape(canvas, M(leg), C["breeches"], lw, seed=sid, shadow_col=C["breeches_shade"])
        # riding boot from just below the knee
        top = knee + (ank - knee) * 0.06
        d = ank - knee
        n = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-9)
        bw0, bw1 = self.leg_w[1] + 1.6, self.leg_w[2] + 1.0
        cuff_tilt = n * 0 + np.array([0, 0])
        boot = np.array([top + n * bw0 + np.array([0, -4]), top + (ank - top) * 0.5 + n * (bw0 + bw1) / 2 * 1.02,
                         ank + n * bw1, ank - n * bw1, top + (ank - top) * 0.5 - n * (bw0 + bw1) / 2 * 1.02,
                         top - n * bw0 + np.array([0, 3])])
        boot = spline(boot, closed=True, n=4)
        shape(canvas, M(boot), C["boot"], lw, seed=sid + 4, shade_depth=5)
        self.draw_foot(canvas, J, M, k, ank, C["boot"], sid + 8)

    def draw_foot(self, canvas, J, M, k, ank, col, sid):
        P, th = self.P, J["th"]
        flen = self.foot_len * lerp(0.42, 1.0, math.sin(th))
        toe = P["toe_" + k]
        heel = 9.0
        X = M.t(*ank)
        if toe:
            X = M.t(ank[0] + flen * 0.7, ank[1] + 6).r(-toe).t(-flen * 0.7, -6)
        hgt = 9.5
        pts = np.array([(-heel, -hgt * 0.6), (-heel - 1, hgt * 0.4), (-heel + 1, hgt), (flen * 0.6, hgt),
                        (flen + 2, hgt - 1), (flen + 3, hgt * 0.35), (flen * 0.75, -hgt * 0.3), (flen * 0.3, -hgt * 0.8), (0, -hgt)], float)
        if th < 0.35:   # front view: rounded toe facing the camera
            pts = np.array([(-8.5, -hgt), (-10, 0), (-9, hgt), (0, hgt + 2), (9, hgt), (10, 0), (8.5, -hgt)], float)
        pts = spline(pts, closed=True, n=4)
        shape(canvas, X(pts), col, self.lw(), seed=sid, shade_depth=4)
        # sole line
        ink_line(canvas, X(np.array([(-heel + 1, hgt - 1.5), (flen, hgt - 1.5)]) if th >= 0.35 else
                 np.array([(-8, hgt - 1), (8, hgt - 1)])), self.lw(0.6), seed=sid + 2, alpha=0.7)

    def coat_outline(self, J):
        """Coat body silhouette with the projected cutaway hem."""
        P, th = self.P, J["th"]
        ct, st = math.cos(th), math.sin(th)
        right, left = [], []
        for (y, hw, df, db) in TORSO[:-2]:
            fr, bk = ext(hw, df, db, th)
            right.append((fr, y)); left.append((bk, y))
        hw, hd = 31.0, 21.0
        phi0 = math.atan2(hd * ct, hw * st)
        phis = np.linspace(phi0, phi0 - math.pi, 30)
        hem = []
        for ph in phis:
            x, z = proj(ph, hw, hd, th)
            hem.append((x, hem_y(ph)))
        pts = right + hem + left[::-1]
        return np.array(pts, float)

    def draw_torso(self, canvas, J, M):
        P, C, th = self.P, self.C, J["th"]
        T = M @ J["chest"]
        T0 = M @ J["torso"]
        lw = self.lw()
        # neck + collar (behind coat collar)
        hb = J["head_xf"]
        nb = J["neck_base"]
        top = hb(np.array([-2.0, -4.0]))
        neck = np.array([nb + (-9, 4), top + (-8, 0), top + (8, 0), nb + (9, 4)])
        shape(canvas, M(neck), C["skin"], lw, seed=200, shadow_col=C["skin_shade"])
        # coat body (split upper/lower so the chest bend reads)
        outline = self.coat_outline(J)
        shape(canvas, T(outline), C["coat"], lw, seed=210, shadow_col=C["coat_shade"], shade_depth=14)
        # breathing seam + side seam (secondary line work)
        sx, _ = proj(-1.15, 40, 24, th)
        ink_line(canvas, T(np.array([(sx * 0.9, -100), (sx * 0.95, -70), (sx, -40)])), lw * 0.45, seed=215, alpha=0.5)
        # shirt V, bow tie, lapels
        def P3(phi, y, hw=36.0, hd=24.0):
            x, z = proj(phi, hw, hd, th)
            return (x, y), z
        vis = lambda z: z > -1.0
        op = P["coat_open"]
        sv = [P3(-0.17 - 0.3 * op, -124 + 6 * op), P3(0.17 + 0.3 * op, -124 + 6 * op), P3(0.05 + 0.22 * op, -84 + 30 * op), P3(-0.05 - 0.22 * op, -84 + 30 * op)]
        if all(vis(z) for _, z in sv[2:]):
            shirt = "#efe9dc" if not self.dark else "#b8b2a6"
            shape(canvas, T(np.array([p for p, _ in sv])), shirt, lw * 0.8, seed=220, shade_depth=3)
        for sgn in (-1, 1):
            lap = [P3(sgn * (0.17 + 0.3 * op), -125 + 6 * op), P3(sgn * (0.52 + 0.25 * op), -109 + 8 * op), P3(sgn * (0.36 + 0.25 * op), -94 + 14 * op),
                   P3(sgn * (0.05 + 0.22 * op), -84 + 30 * op)]
            if sum(vis(z) for _, z in lap) >= 3:
                pts = np.array([p for p, _ in lap])
                shape(canvas, T(pts), C["coat"], lw * 0.8, seed=230 + sgn, shadow_col=C["coat_shade"], shade_depth=4)
                ink_line(canvas, T(pts[[0, 1, 2]]), lw * 0.95, color=C["trim"], seed=233 + sgn, taper=0.05)
        # bow tie
        bt, z = P3(0.0, -121)
        if z > 0:
            bx = bt[0]
            wing = 9 * (0.45 + 0.55 * math.cos(th))
            tie = np.array([(bx - wing, -126), (bx - 1.5, -122), (bx - wing, -117), (bx + wing, -117), (bx + 1.5, -122), (bx + wing, -126)])
            shape(canvas, T(tie), "#16131a", lw * 0.6, seed=240, shadow=False)
        # front edge trim + hem trim (gold)
        fe = [P3(0.05, y) for y in np.linspace(-84, -34, 6)]
        if fe[0][1] > 0 and op < 0.05:
            ink_line(canvas, T(np.array([p for p, _ in fe])), lw * 0.9, color=C["trim"], seed=245, taper=0.05)
        hw, hd = 31.0, 21.0
        hem = []
        for ph in np.linspace(-1.4, 1.4, 22):
            x, z = proj(ph, hw, hd, th)
            if z > 0.5:
                hem.append((x, hem_y(ph) - 2.5))
        if len(hem) > 2:
            ink_line(canvas, T(np.array(hem)), lw * 0.95, color=C["trim"], seed=247, taper=0.06)
        # buttons: 6, two columns x three
        for i, (phi, y) in enumerate(BUTTONS):
            if op > 0.05 and y < -84 + 34 * op:
                continue
            hwb = {-52: 32, -71: 38, -90: 45}[y]
            x, z = proj(phi, hwb, 26, th)
            if z > 2:
                r = 4.2 * (0.55 + 0.45 * min(1, z / 20))
                bp = ellipse(x, y, r, 4.2, 12)
                shape(canvas, T(bp), C["button"], lw * 0.55, seed=250 + i, shade_depth=1.6)
                fill(canvas, T(ellipse(x - 1.2, y - 1.3, 1.2, 1.1, 8)), "#fff6d0" if not self.dark else "#b7a982",
                     alpha=0.9 if not self.dark else 0.5, do_boil=False)
        # coat collar standing behind the neck
        cx0, _ = proj(math.pi, 18, 15, th)

    def draw_arm(self, canvas, J, M, k):
        P, C = self.P, self.C
        sh, el, hd = J["sh_" + k], J["elbow_" + k], J["hand_" + k]
        lw = self.lw()
        sid = 400 if k == "n" else 440
        if P.get("cane") and P["cane"][0] == "hand_" + k and P["cane"][2] == "behind":
            self.draw_cane(canvas, J, M)
        arm = self.limb_poly(sh, el, hd, self.arm_w, bulge=1.5)
        shape(canvas, M(arm), C["coat"], lw, seed=sid, shadow_col=C["coat_shade"])
        # gold cuff
        d = hd - el
        n = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-9)
        a, b = el + d * 0.80, el + d * 0.97
        w0, w1 = self.arm_w[2] + 1.6, self.arm_w[2] + 1.4
        cuff = np.array([a + n * w0, b + n * w1, b - n * w1, a - n * w0])
        shape(canvas, M(cuff), C["trim"], lw * 0.7, seed=sid + 5, shade_depth=2)
        # hand
        X = self.hand_xf(J, M, k)
        kind = P["hand_" + k]
        bare = self.bare(k)
        col = C["skin"] if bare else C["glove"]
        holds_cane = P.get("cane") and P["cane"][0] == "hand_" + k and P["cane"][2] != "behind"
        holds_handle = P.get("handle") and P["handle"][0] == "hand_" + k
        if holds_cane and not P.get("cane_free"):
            self.draw_cane(canvas, J, M)
        if holds_handle:
            self.draw_handle(canvas, J, M)
        draw_hand(canvas, X, kind, col, lw * 0.85, seed=sid + 10, glove=not bare, size=1.0)
        if P.get("hat") and P["hat"][0] == "hand_" + k:
            self.draw_hat(canvas, J, M)

    # ------------------------------------------------------------------ props
    def cane_xf(self, J, M):
        P = self.P
        spec = P["cane"]
        if spec[0].startswith("hand"):
            X = self.hand_xf(J, M, spec[0][-1])
            if len(spec) > 3 and spec[3] == "abs":     # planted cane: absolute angle in local space
                p = X(np.array([14.0, 0.0]))
                return Xf.T(*p) @ Xf(np.diag([M.m[0, 0] / abs(M.m[0, 0]) * M.scale, M.scale, 1.0])).r(spec[1])
            return X.t(14, 0).r(spec[1])
        _, x, y, a, _ = spec
        return M.t(x, y).r(a)

    def draw_cane(self, canvas, J, M, X=None):
        """Cane in its local frame: grip point at origin, shaft along +x? No - shaft along +y
        (downward) from the grip, silver ball just above the grip (-y)."""
        C = self.C
        X = X or self.cane_xf(J, M)
        lw = self.lw()
        L = 232.0
        shaft = np.array([(-3.4, -8), (3.4, -8), (2.9, L - 3), (0, L), (-2.9, L - 3)])
        shape(canvas, X(shaft), C["cane"], lw * 0.7, seed=500, shade_depth=1.5)
        ink_line(canvas, X(np.array([(-1.2, 4), (-0.8, L - 20)])), lw * 0.4, color="#6a6670", seed=503, alpha=0.6)
        self.draw_ball(canvas, X)

    def draw_ball(self, canvas, X):
        C = self.C
        lw = self.lw()
        collar = np.array([(-4.5, -9), (4.5, -9), (4, -14), (-4, -14)])
        shape(canvas, X(collar), C["silver"], lw * 0.5, seed=505, shade_depth=1.5)
        shape(canvas, X(ellipse(0, -22, 9.2, 9.2, 22)), C["silver"], lw * 0.7, seed=507, shade_depth=4)
        fill(canvas, X(ellipse(-3, -25.5, 2.6, 2.2, 10)), "#ffffff", alpha=0.85, do_boil=False)

    def draw_handle(self, canvas, J, M):
        """Snapped cane: only the silver ball handle with a jagged black stub."""
        P, C = self.P, self.C
        spec = P["handle"]
        X = self.hand_xf(J, M, spec[0][-1]).t(14, 0).r(spec[1])
        lw = self.lw()
        stub = np.array([(-3.4, -8), (3.4, -8), (3.2, 30), (1.0, 34), (-0.6, 29), (-2.2, 36), (-3.4, 31)])
        shape(canvas, X(stub), C["cane"], lw * 0.7, seed=510, shade_depth=1.5)
        self.draw_ball(canvas, X)

    # ------------------------------------------------------------------ head
    def hat_xf_head(self, J, M):
        P = self.P
        hth = J["hth"]
        x0 = lerp(0.0, -3.0, math.sin(hth))
        return M @ J["head_xf"] @ Xf.T(x0, -80 + P["hat_drop"]).r(P["hat_tilt"])

    def draw_hat(self, canvas, J, M, X=None):
        P, C = self.P, self.C
        if X is None and P.get("hat_xf") is not None and P["hat"] != "head":
            X = P["hat_xf"]
        if X is None:
            spec = P["hat"]
            if spec == "head":
                X = self.hat_xf_head(J, M)
            elif spec[0].startswith("hand"):
                X = self.hand_xf(J, M, spec[0][-1]) @ spec[1]
            else:
                X = spec[1]
        lw = self.lw()
        # brim (back part), crown, band, front brim
        brim = ellipse(0, 0, 47, 8.5, 36)
        shape(canvas, X(brim), C["hat_shade"], lw, seed=600, shadow=False)
        crown = spline([(-27, -1), (-27.5, -45), (-29.5, -88), (-14, -91.5), (0, -92), (14, -91.5), (29.5, -88), (27.5, -45), (27, -1)], n=4)
        if self.dark:   # a dent in the crown
            crown = spline([(-27, -1), (-27.5, -45), (-29.5, -88), (-16, -91.5), (-3, -87), (8, -90.5), (29.5, -88), (27.5, -45), (27, -1)], n=4)
        shape(canvas, X(crown), C["hat"], lw, seed=602, shadow_col=C["hat_shade"], shade_depth=12)
        # silk sheen
        fill(canvas, X(np.array([(-16, -8), (-11, -8), (-12, -82), (-17, -82)])), "#ffffff",
             alpha=0.10 if not self.dark else 0.05, blur=2.5, do_boil=False)
        band = np.array([(-27.2, -2), (-27.4, -18), (27.4, -18), (27.2, -2)])
        shape(canvas, X(band), C["band"], lw * 0.7, seed=604, shade_depth=5)
        if self.dark:   # the cracked band
            ink_line(canvas, X(np.array([(5, -18), (8, -13), (6, -9), (10, -5), (9, -2)])), lw * 0.7, seed=606, taper=0.1)
            ink_line(canvas, X(np.array([(8, -13), (13, -12)])), lw * 0.45, seed=607)
            fill(canvas, X(np.array([(-20, -18), (-14, -18), (-16, -14)])), C["hat"], do_boil=False)
            ink_line(canvas, X(np.array([(-21, -11), (-17, -6), (-19, -3)])), lw * 0.5, seed=608)
        front = np.vstack([ellipse(0, 0, 47, 8.5, 24, 0, math.pi), ellipse(0, 1.8, 40, 5.2, 18, math.pi, 0)])
        shape(canvas, X(front), C["hat"], lw, seed=610, shadow=False)

    def draw_head(self, canvas, J, M):
        P, C = self.P, self.C
        hth = J["hth"]
        st, ct = math.sin(hth), math.cos(hth)
        X = M @ J["head_xf"]
        lw = self.lw()
        w = st
        outline = spline(HEAD_FRONT * (1 - w) + HEAD_SIDE * w, closed=True, n=5)
        x0 = lerp(0.0, -3.0, w)
        R, D = 27.5, 31.0

        def fp(u, y, r=R, d=D):
            phi = clamp(u / r, -1.25, 1.25)
            x, z = proj(phi, r, d, hth)
            extra = u - phi * r
            if extra:
                x += extra * math.cos(phi + hth)
            return np.array([x0 + x, y]), z

        # ears (far ear behind head)
        for side in (1, -1):
            phi = side * math.pi / 2
            x, z = proj(phi, R + 1, D, hth)
            if z < -12:
                continue
            ex = x0 + x
            ear = np.array([(ex - 3, -59), (ex + 4 * (1 if x >= 0 else -1) * 0.6, -61), (ex + 6 * (1 if x >= 0 else -1), -52),
                            (ex + 4 * (1 if x >= 0 else -1), -42), (ex - 2, -41)])
            if z < 2:
                shape(canvas, X(spline(ear, closed=True, n=4)), C["skin"], lw * 0.8, seed=700 + side, shadow_col=C["skin_shade"])
        shape(canvas, X(outline), C["skin"], lw, seed=710, shadow_col=C["skin_shade"], shade_depth=9)
        # near ear on top when turned
        for side in (-1,):
            x, z = proj(side * math.pi / 2, R + 1, D, hth)
            if z >= 2:
                ex = x0 + x
                ear = spline(np.array([(ex + 5, -60), (ex - 2, -62), (ex - 6, -53), (ex - 4, -43), (ex + 3, -41)]), n=4)
                ear = np.vstack([ear, [(ex + 3, -50)]])
                shape(canvas, X(ear), C["skin"], lw * 0.8, seed=705, shadow_col=C["skin_shade"])
                ink_line(canvas, X(np.array([(ex + 1, -57), (ex - 2, -52), (ex + 0.5, -46)])), lw * 0.5, seed=706)
                # sideburn / back hair under the hat
                hair = np.array([(ex + 6, -76), (ex + 8, -62), (ex + 5, -58), (ex - 6, -64), (ex - 14, -74)])
                shape(canvas, X(hair), "#3a2c26" if not self.dark else "#4a4440", lw * 0.6, seed=707, shadow=False)
        # hair at the sides in front view
        if ct > 0.5:
            for side in (-1, 1):
                hx = x0 + side * 26 * ct
                hair = np.array([(hx, -78), (hx + side * 4, -66), (hx + side * 1, -58), (hx - side * 4, -70)])
                shape(canvas, X(hair), "#3a2c26" if not self.dark else "#4a4440", lw * 0.6, seed=708 + side, shadow=False)
        # stage makeup (Scene 4): pale base + rosy cheeks, wiped off the near half
        if P["makeup"] > 0:
            self.draw_makeup(canvas, X, outline, fp, hth)
        # ----- eyes
        blink, narrow = P["blink"], P["narrow"]
        lx, ly = P["look"]
        for side in (-1, 1):
            c, z = fp(side * 11.5, -58)
            if z < 4:
                continue
            fsh = clamp(z / D) ** 0.7
            ew = 5.6 * fsh
            open_ = (1 - blink) * (1 - narrow * 0.55)
            eh = 3.6 * open_
            ex, ey = c
            if eh > 0.4:
                eye = np.vstack([ellipse(ex, ey, ew, eh, 14, math.pi, 2 * math.pi), ellipse(ex, ey, ew, eh * 0.75, 12, 0, math.pi)])
                fill(canvas, X(eye), "#f6f1e6" if not self.dark else "#cfc8bb", do_boil=False)
                px = ex + lx * 2.2 * fsh + (st * 1.5)
                fill(canvas, X(ellipse(px, ey + ly * 1.0 + 0.3, 2.4 * fsh + 0.4, min(2.6, eh * 0.95), 10)), C["eye"], do_boil=False)
                fill(canvas, X(ellipse(px - 0.8, ey - 0.8, 0.7, 0.7, 6)), "#ffffff", alpha=0.9, do_boil=False)
            lid_y = ey - eh * 0.95
            ink_line(canvas, X(np.array([(ex - ew * 1.15, ey + 0.5), (ex - ew * 0.3, lid_y - 0.4), (ex + ew * 0.5, lid_y - 0.2), (ex + ew * 1.2, ey + 0.2)])),
                     lw * 0.85, seed=720 + side, taper=0.3)
            if eh <= 0.4:
                pass
            # crow's feet (Act 1 smiling) / tired under-eye line (dark acts)
            if P["crow"] > 0.2 and P["smile"] > 0.4:
                ox = ex + side * ew * 1.5
                for j in range(2):
                    ink_line(canvas, X(np.array([(ox, ey - 1 + j * 3), (ox + side * 4 * fsh, ey - 2.5 + j * 4)])), lw * 0.35, seed=724 + j + side, alpha=0.7)
            if self.dark:
                ink_line(canvas, X(np.array([(ex - ew * 0.8, ey + 4.5), (ex, ey + 5.6), (ex + ew * 0.8, ey + 4.5)])), lw * 0.35, seed=728 + side, alpha=0.6)
        # ----- brows
        for side in (-1, 1):
            c, z = fp(side * 12.0, -67)
            if z < 4:
                continue
            fsh = clamp(z / D) ** 0.7
            bx, by = c
            raise_ = P["brow"] * 3.0
            inner_drop = P["cold"] * 2.2
            pts = np.array([(bx - side * 6 * fsh, by - raise_ + inner_drop), (bx, by - 2.2 - raise_ * 1.2), (bx + side * 6.5 * fsh, by - raise_ * 0.6)])
            if side < 0:
                pts = pts
            ink_line(canvas, X(spline(pts, n=5)), lw * 1.0, color=C["mustache"], seed=730 + side, taper=0.35)
        # ----- nose (long, sharp)
        b, _ = fp(0, -61)
        tipx = b[0] + 15.5 * st + 1.2 * ct
        basex = b[0] + 5.5 * st
        nose = np.array([(b[0] - 0.5 * ct, -62), (tipx, -38.5), (basex + 1.2, -34.2), (b[0] - 2.5 * ct, -35.5)])
        fill(canvas, X(nose), C["skin"], do_boil=False)
        if st > 0.15:
            ink_line(canvas, X(spline(np.array([(b[0] + 1, -61), (b[0] + 8 * st, -50), (tipx, -38.5), (basex + 3 * st, -35), (basex - 1, -34.5)]), n=4)),
                     lw * 0.85, seed=740, taper=0.25)
        else:
            ink_line(canvas, X(np.array([(b[0] - 2.2, -60), (b[0] - 1.2, -48), (b[0] + 0.5, -39), (b[0] + 2, -36.5)])), lw * 0.7, seed=741, taper=0.3)
        nb_c, _ = fp(0, -35)
        if ct > 0.3:
            ink_line(canvas, X(np.array([(nb_c[0] - 5 * ct, -36.5), (nb_c[0] - 3 * ct, -34.5), (nb_c[0] - 0.8, -35.0)])), lw * 0.55, seed=742)
            ink_line(canvas, X(np.array([(nb_c[0] + 0.8, -35.0), (nb_c[0] + 3 * ct, -34.5), (nb_c[0] + 5 * ct, -36.5)])), lw * 0.55, seed=743)
        # ----- mouth
        self.draw_mouth(canvas, X, fp, hth)
        # ----- mustache (thin, curled) - same shape every view
        for side in (-1, 1):
            half = MUSTACHE_HALF.copy()
            if side == 1:
                half[:, 0] = -half[:, 0]
            pts, ok = [], []
            for u, y in half:
                p, z = fp(u, y, r=R + 2.5, d=D + 3)
                pts.append(p); ok.append(z > -1.5)
            pts = np.array(pts)
            if sum(ok) >= 3:
                pts = pts[np.array(ok)]
                ink_line(canvas, X(spline(pts, n=4)), lw * 1.25, color=C["mustache"], seed=750 + side, taper=0.45, var=0.2)
        # laugh lines / smile folds
        sm = P["smile"]
        if sm > 0.35 and not self.dark:
            for side in (-1, 1):
                a, za = fp(side * 9.5, -41)
                b2, zb = fp(side * 16, -27)
                if za > 3 and zb > 3:
                    ink_line(canvas, X(np.array([a, (a + b2) / 2 + (side * 2.0, 0), b2])), lw * 0.4, seed=760 + side, alpha=0.65)
        if self.dark:
            for side in (-1, 1):
                a, za = fp(side * 8.5, -42)
                b2, zb = fp(side * 14.5, -26)
                if za > 3 and zb > 3:
                    ink_line(canvas, X(np.array([a, (a + b2) / 2 + (side * 1.4, 0), b2])), lw * 0.4, seed=762 + side, alpha=0.55)
            # cheek hollow
            c1, z1 = fp(-19, -44)
            if z1 > 3:
                ink_line(canvas, X(np.array([c1 + (0, -6), c1, c1 + (2, 6)])), lw * 0.3, seed=764, alpha=0.45)
        # ----- hair (slicked back, side part; grey at the temples in the dark acts)
        hair_col = "#2e211b" if not self.dark else "#3b3532"
        line_pts = [fp(u, -76.5 - 3.0 * math.cos(u / 14.0))[0] for u in np.linspace(-34, 34, 15)]
        xe = x0 + proj(-math.pi / 2 * 0.9, R + 1, D, hth)[0]
        front = np.array([p for p in line_pts if p[0] > xe + 2]) if st > 0.2 else np.array(line_pts)
        if len(front):
            if st > 0.2:
                capp = np.vstack([[(xe - 3, -50), (xe - 3, front[0][1])], front, [(70, front[-1][1]), (70, -130), (-70, -130), (-70, -50)]])
            else:
                capp = np.vstack([[(-70, front[0][1])], front, [(70, front[-1][1]), (70, -130), (-70, -130)]])
            canvas.save()
            canvas.clipPath(path_of(X(outline)), skia.ClipOp.kIntersect, True)
            fill(canvas, X(capp), hair_col, seed=780)
            # comb lines + part
            for j in range(4):
                yy = -86 + j * 3
                ink_line(canvas, X(np.array([fp(-18 + j * 2, yy)[0], fp(4, yy - 2)[0], fp(22, yy + 1)[0]])), lw * 0.35,
                         color="#5a4a40" if not self.dark else "#7a7470", seed=782 + j, alpha=0.7)
            if self.dark:
                for side in (-1, 1):
                    gp, gz = fp(side * 25, -72)
                    if gz > 0:
                        fill(canvas, X(ellipse(gp[0], gp[1], 4, 7, 10)), "#9a948c", alpha=0.8, do_boil=False)
            canvas.restore()
            ink_line(canvas, X(front), lw * 0.6, seed=781, taper=0.3)
        # ----- hat
        if P["hat"] == "head":
            self.draw_hat(canvas, J, M)
            if P["brim_shadow"] > 0:
                self.draw_brim_shadow(canvas, J, M, X, outline)

    def draw_makeup(self, canvas, X, outline, fp, hth):
        P = self.P
        m = SILAS_MAKEUP
        path = path_of(X(outline))
        canvas.save()
        canvas.clipPath(path, skia.ClipOp.kIntersect, True)
        if P["wipe"] > 0:
            # the rag wipes the near (screen-left) half; a soft edge follows the rag
            edge_x = lerp(-34, -1, P["wipe"])
            keep = np.array([(edge_x, -100), (40, -100), (40, 10), (edge_x - 4, 10)])
            canvas.clipPath(path_of(X(keep)), skia.ClipOp.kIntersect, True)
        canvas.drawPath(path, paint(m["base"], 0.78 * P["makeup"]))
        for side in (-1, 1):
            c, z = fp(side * 15, -44)
            if z > 3:
                canvas.drawPath(path_of(X(ellipse(c[0], c[1], 6, 4.5, 14))), paint(m["cheek"], 0.6 * P["makeup"], blur=3))
        canvas.restore()
        if P["wipe"] > 0:   # smear at the wipe edge
            edge_x = lerp(-34, -1, P["wipe"])
            canvas.save()
            canvas.clipPath(path, skia.ClipOp.kIntersect, True)
            canvas.drawPath(path_of(X(np.array([(edge_x - 7, -95), (edge_x, -95), (edge_x - 4, 5), (edge_x - 11, 5)]))),
                            paint(m["base"], 0.35 * P["makeup"], blur=4))
            canvas.restore()

    def draw_mouth(self, canvas, X, fp, hth):
        P, C = self.P, self.C
        lw = self.lw()
        sm, op, cold = P["smile"], P["open"], P["cold"]
        width = lerp(10.5, 7.5, cold) * (1 + 0.25 * max(sm, 0))
        us = np.linspace(-width, width, 9)
        pts, zs = [], []
        for u in us:
            k = u / width
            lift = sm * 4.2 * k * k
            if cold > 0:
                lift = lerp(lift, (3.4 if k < 0 else 0.5) * max(k * k, 0) + (1.2 * k if k < 0 else 0) * -1 - 0.2, cold)
            p, z = fp(u, -26.5 - lift + sm * 1.4 * (1 - k * k))
            pts.append(p); zs.append(z)
        pts = np.array(pts); zs = np.array(zs)
        okm = zs > 0
        if okm.sum() < 3:
            return
        top = pts[okm]
        if op > 0.05:
            bottom = top.copy()
            k = np.linspace(-1, 1, len(bottom))
            bottom[:, 1] += op * 11 * (1 - k ** 2) ** 0.8
            mouth = np.vstack([top, bottom[::-1]])
            fill(canvas, X(mouth), "#3a1418")
            teeth = np.vstack([top, (top + np.array([0, 3.2 * op]))[::-1]])
            fill(canvas, X(teeth), "#f4efe2")
            tongue = ellipse(top[len(top) // 2][0], top[len(top) // 2][1] + op * 8, width * 0.45, op * 3, 12)
            fill(canvas, X(tongue), "#b04650", alpha=0.85)
            ink_line(canvas, X(bottom), lw * 0.7, seed=772, taper=0.3)
        ink_line(canvas, X(top), lw * 0.9, seed=770, taper=0.3)
        # lower lip hint
        mid = top[len(top) // 2]
        ink_line(canvas, X(np.array([mid + (-3, 4.5 + op * 11), mid + (3, 4.5 + op * 11)])), lw * 0.45, seed=774, alpha=0.6)

    def draw_brim_shadow(self, canvas, J, M, X, outline):
        """Dark acts: the hat brim throws the eyes into shadow."""
        P = self.P
        HX = self.hat_xf_head(J, M)
        canvas.save()
        canvas.clipPath(path_of(X(outline)), skia.ClipOp.kIntersect, True)
        # soft gradient from the brim edge down past the eyes
        a = HX(np.array([0.0, 0.0])); b = HX(np.array([0.0, 34.0]))
        sh = skia.GradientShader.MakeLinear(
            [skia.Point(*a), skia.Point(*b)],
            [skia.Color4f(0.04, 0.035, 0.06, 0.82 * P["brim_shadow"]),
             skia.Color4f(0.04, 0.035, 0.06, 0.55 * P["brim_shadow"]),
             skia.Color4f(0.04, 0.035, 0.06, 0.0)], [0.0, 0.55, 1.0])
        p = skia.Paint(AntiAlias=True)
        p.setShader(sh)
        canvas.drawPath(path_of(HX(np.array([(-70, -4), (70, -4), (70, 40), (-70, 40)]))), p)
        canvas.restore()
        # eye glints remain visible in the shadow
        hth = J["hth"]
        R, D = 27.5, 31.0
        x0 = lerp(0.0, -3.0, math.sin(hth))
        if P["blink"] < 0.5:
            for side in (-1, 1):
                x, z = proj(side * 11.5 / R, R, D, hth)
                if z > 6:
                    fill(canvas, X(ellipse(x0 + x + P["look"][0] * 2, -58, 1.1, 0.9, 8)), "#e8f0f0",
                         alpha=0.55 * P["brim_shadow"], do_boil=False)

    def draw_front(self, canvas, J, M):
        P = self.P
        if P["hat"] != "head" and P["hat"] is not None and P["hat"][0] == "world":
            self.draw_hat(canvas, J, M)
        if P.get("cane") and P["cane"][0] == "world":
            self.draw_cane(canvas, J, M)
