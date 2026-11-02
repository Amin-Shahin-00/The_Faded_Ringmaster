"""Shared 2D puppet rig.

Local units: ground at y=0, up is negative y, +x is the facing direction.
`turn` rotates the character from front view (0) through three-quarter (0.5) to
profile (1). Every body part is described as a cross-section (half-width hw
and front/back depth) so all views come from ONE model - that is what keeps
proportions and costume details identical between the model sheet and shots.

Limbs use two-bone IK that never stretches (see core.ik2). Feet are given as
explicit ground positions, so a planted foot cannot slide.
"""
import math
import numpy as np
from lib.core import Xf, ik2, clamp, lerp, mix, mul, hexc, rot
from lib.ink import shape, ink_line, fill, ellipse, spline, bez, S, boil, path_of
from lib.core import paint
import skia


def proj(phi, hw, hd, th):
    """Point at azimuth phi on an elliptical cross-section (half-width hw, half-depth
    hd), body rotated by th. Returns (screen x, z toward viewer)."""
    sp, cp = math.sin(phi), math.cos(phi)
    st, ct = math.sin(th), math.cos(th)
    return hw * sp * ct + hd * cp * st, -hw * sp * st + hd * cp * ct


def ext(hw, df, db, th):
    """Silhouette half-extents (front side, back side) of a cross-section."""
    st, ct = math.sin(th), math.cos(th)
    return math.hypot(hw * ct, df * st), -math.hypot(hw * ct, db * st)


DEFAULT_POSE = dict(
    x=0.0, y=0.0, s=1.0, face=1, turn=0.5, head_turn=None,
    pelvis=(0.0, 0.0), lean=0.0, chest=0.0, head_rot=0.0, head_dx=0.0, squash=0.0,
    foot_n=(6.0, 0.0), foot_f=(-6.0, 0.0), toe_n=0.0, toe_f=0.0, knee_n=None, knee_f=None,
    arm_n=None, arm_f=None, hand_n="relax", hand_f="relax", wrist_n=0.0, wrist_f=0.0,
    elbow_n=None, elbow_f=None,
    blink=0.0, look=(0.0, 0.0), brow=0.0, smile=0.3, open=0.0, cold=0.0, narrow=0.0,
    breath=0.0, shake=0.0,
)


class Figure:
    # ---- proportions (override per character) --------------------------------
    hip_h = 200.0           # pelvis height above ground
    hip_w = 16.0            # hip joint half spacing (front view)
    thigh = 99.0
    shin = 97.0
    ankle = 5.0
    sh_y = -118.0           # shoulder height relative to pelvis (when upright)
    sh_w = 50.0             # shoulder half spacing (front)
    sh_d = 4.0
    upper = 82.0
    fore = 76.0
    neck_y = -128.0
    neck_len = 20.0
    head_scale = 1.0
    torso_levels = []       # (y, hw, df, db)
    leg_w = (15.0, 11.0, 8.0)   # half widths at hip, knee, ankle
    arm_w = (10.0, 8.0, 6.5)
    foot_len = 34.0
    line = 3.0

    def __init__(self, act=1):
        self.act = act

    # ------------------------------------------------------------------ helpers
    def pose(self, **kw):
        p = dict(DEFAULT_POSE)
        p.update(self.pose_defaults())
        p.update(kw)
        return p

    def pose_defaults(self):
        return {}

    def lw(self, k=1.0):
        return max(1.0, min(7.5, self.line * self._scale * k))

    # ------------------------------------------------------------------ solve
    def solve(self, P):
        th = clamp(P["turn"]) * math.pi / 2
        hth = (clamp(P["head_turn"]) if P["head_turn"] is not None else clamp(P["turn"])) * math.pi / 2
        J = dict(th=th, hth=hth)
        pel = np.array([P["pelvis"][0], -self.hip_h + P["pelvis"][1] + P["breath"] * 0.0])
        J["pelvis"] = pel
        # upper body transform: rotate about pelvis by lean, then chest bend at waist
        sq = P["squash"]
        torso = Xf.T(*pel).r(P["lean"]).s(1 - sq * 0.5, 1 + sq)
        J["torso"] = torso
        waist_y = -40.0
        chest = torso.t(0, waist_y).r(P["chest"]).t(0, -waist_y)
        J["chest"] = chest
        breath = 1.0 + 0.012 * P["breath"]
        J["breath"] = breath
        # shoulders: physical right (-1) is near when facing +x
        st, ct = math.sin(th), math.cos(th)
        for side, key in ((-1, "n"), (1, "f")):
            sx = side * self.sh_w * ct + self.sh_d * st * 0.0
            J["sh_" + key] = chest(np.array([sx, self.sh_y * breath]))
            hx = side * self.hip_w * ct
            J["hip_" + key] = pel + np.array([hx, 0.0])
        # neck/head
        neck_base = chest(np.array([self.neck_dx(th), self.neck_y * breath]))
        J["neck_base"] = neck_base
        ang = P["lean"] + P["chest"]
        head_base = neck_base + rot(np.array([P["head_dx"], -self.neck_len]), ang * 0.6)
        J["head_xf"] = Xf.T(*head_base).r(ang * 0.4 + P["head_rot"]).s(self.head_scale)
        # legs (IK, knee bends forward)
        for side, key in ((-1, "n"), (1, "f")):
            fx, lift = P["foot_" + key]
            # foot x is measured from the ground point under its own hip, so a front
            # view stands with feet apart and a profile walk uses the given values
            fx = fx + side * self.hip_w * 1.25 * ct
            ankle = np.array([fx, -self.ankle - lift])
            kb = -lerp(0.35, 1.0, clamp(P["turn"] * 1.6))
            if P["knee_" + key] is not None:
                knee = np.array(P["knee_" + key], float)
                end = ankle
            else:
                knee, end = ik2(J["hip_" + key], ankle, self.thigh, self.shin, bend=kb)
            J["knee_" + key], J["ankle_" + key] = knee, end
        # arms (IK). Target None = relaxed hang
        for side, key in ((-1, "n"), (1, "f")):
            sh = J["sh_" + key]
            tgt = P["arm_" + key]
            if tgt is None:
                hang = chest(np.array([side * self.sh_w * ct * 1.0 + st * 7, self.sh_y + self.upper + self.fore - 9 - 12 * st]))
                tgt = hang
            if isinstance(tgt, tuple) and isinstance(tgt[0], str):
                if tgt[0] == "fk":
                    # angles from straight down; positive swings forward (+x)
                    base = (P["lean"] + P["chest"]) * 0.5
                    u1 = rot(np.array([0.0, 1.0]), -(tgt[1] + base))
                    u2 = rot(u1, -tgt[2])
                    elbow = sh + u1 * self.upper
                    J["elbow_" + key], J["hand_" + key] = elbow, elbow + u2 * self.fore
                    continue
                if tgt[0] == "rel":
                    tgt = sh + np.array(tgt[1:3], float)
            tgt = np.asarray(tgt, float)
            eb = P["elbow_" + key]
            if eb is None:
                eb = 1.0 if P["turn"] >= 0.3 else -side * 0.6
            elbow, hand = ik2(sh, tgt, self.upper, self.fore, bend=eb)
            J["elbow_" + key], J["hand_" + key] = elbow, hand
        return J

    def neck_dx(self, th):
        return 0.0

    # ------------------------------------------------------------------ draw
    def root_xf(self, P):
        return Xf.T(P["x"], P["y"]).s(P["s"] * P["face"], P["s"])

    def draw(self, canvas, P, props=None):
        """props: optional callables (canvas, figure, J, M, which) for held objects."""
        self.P = P
        M = self.root_xf(P)
        self._scale = abs(P["s"])
        self.M = M
        J = self.solve(P)
        self.J = J
        props = props or {}
        far_behind = P["turn"] > 0.28
        order = []
        if far_behind:
            order += ["arm_f"]
        order += ["back", "leg_f", "leg_n", "torso", "head"]
        if not far_behind:
            order += ["arm_f"]
        order += ["arm_n", "front"]
        for part in order:
            if part in props.get("before", {}):
                props["before"][part](canvas, self, J, M)
            if part == "back":
                self.draw_back(canvas, J, M)
            elif part.startswith("leg"):
                self.draw_leg(canvas, J, M, part[-1])
            elif part == "torso":
                self.draw_torso(canvas, J, M)
            elif part == "head":
                self.draw_head(canvas, J, M)
            elif part.startswith("arm"):
                self.draw_arm(canvas, J, M, part[-1])
            elif part == "front":
                self.draw_front(canvas, J, M)
            if part in props.get("after", {}):
                props["after"][part](canvas, self, J, M)
        return J

    # parts - override in characters
    def draw_back(self, canvas, J, M):
        pass

    def draw_front(self, canvas, J, M):
        pass

    def torso_outline(self, J, th, levels=None, xf=None):
        levels = levels or self.torso_levels
        right, left = [], []
        for (y, hw, df, db) in levels:
            fr, bk = ext(hw, df, db, th)
            right.append((fr, y)); left.append((bk, y))
        pts = np.array(right + left[::-1], float)
        return pts

    def limb_poly(self, a, b, c, w, bulge=0.0):
        """Tapered two-segment limb outline through joints a-b-c with half widths w."""
        a, b, c = (np.asarray(v, float) for v in (a, b, c))
        def nrm(p, q):
            d = q - p
            n = np.hypot(*d) + 1e-9
            return np.array([-d[1], d[0]]) / n
        n1, n2 = nrm(a, b), nrm(b, c)
        nb = n1 + n2
        nb = nb / (np.hypot(*nb) + 1e-9)
        m1 = (a + b) / 2 + n1 * bulge
        m2 = (b + c) / 2 + n2 * bulge * 0.6
        left = [a + n1 * w[0], m1 + n1 * (w[0] + w[1]) / 2 * 1.04, b + nb * w[1], m2 + n2 * (w[1] + w[2]) / 2, c + n2 * w[2]]
        right = [c - n2 * w[2], m2 - n2 * (w[1] + w[2]) / 2, b - nb * w[1], m1 - n1 * (w[0] + w[1]) / 2 * 1.04, a - n1 * w[0]]
        L = spline(left, n=5)
        R = spline(right, n=5)
        cap_c = ellipse(c[0], c[1], w[2], w[2], 10, 0, 0)  # unused placeholder
        return np.vstack([L, R])

    def draw_leg(self, canvas, J, M, k):
        pass

    def draw_arm(self, canvas, J, M, k):
        pass

    def draw_head(self, canvas, J, M):
        pass

    def draw_torso(self, canvas, J, M):
        pass


# ============================================================================ generic head

def head_proj(hth, R, D, x0):
    """Return fp(u, y) -> (point, z): projects a face-surface point at lateral
    offset u (negative = character's right) onto the turned head."""
    def fp(u, y, r=R, d=D):
        phi = clamp(u / r, -1.25, 1.25)
        x, z = proj(phi, r, d, hth)
        extra = u - phi * r
        if extra:
            x += extra * math.cos(phi + hth)
        return np.array([x0 + x, y]), z
    return fp


def draw_face(fig, canvas, X, hth, cfg, P, lw):
    """Eyes, brows, nose, mouth for the supporting cast (cfg = per character)."""
    st, ct = math.sin(hth), math.cos(hth)
    R, D = cfg["R"], cfg["D"]
    x0 = lerp(0.0, cfg.get("x0_side", -3.0), st)
    fp = head_proj(hth, R, D, x0)
    blink, narrow = P["blink"], P["narrow"] + cfg.get("lid", 0.0)
    lx, ly = P["look"]
    ey0 = cfg["eye_y"]
    for side in (-1, 1):
        c, z = fp(side * cfg["eye_sep"], ey0)
        if z < 4:
            continue
        fsh = clamp(z / D) ** 0.7
        ew = cfg["eye_w"] * fsh
        open_ = (1 - blink) * (1 - min(narrow, 0.9) * 0.6)
        eh = cfg["eye_h"] * open_
        ex, ey = c
        if eh > 0.4:
            eye = np.vstack([ellipse(ex, ey, ew, eh, 14, math.pi, 2 * math.pi), ellipse(ex, ey, ew, eh * 0.8, 12, 0, math.pi)])
            fill(canvas, X(eye), cfg.get("white", "#f3eee4"), do_boil=False)
            px = ex + lx * ew * 0.35 + st * 1.2
            pr = cfg.get("pupil", 2.4)
            fill(canvas, X(ellipse(px, ey + ly + 0.3, pr * fsh + 0.4, min(pr * 1.05, eh * 0.95), 10)), cfg["eye_col"], do_boil=False)
            fill(canvas, X(ellipse(px - 0.8, ey - 0.9, 0.75, 0.75, 6)), "#ffffff", alpha=0.9, do_boil=False)
        lid_y = ey - eh * 0.95
        ink_line(canvas, X(np.array([(ex - ew * 1.15, ey + 0.6), (ex - ew * 0.3, lid_y - 0.4), (ex + ew * 0.5, lid_y - 0.2),
                                     (ex + ew * 1.2, ey + 0.3)])), lw * cfg.get("lid_w", 0.85), seed=820 + side, taper=0.3)
        if cfg.get("lash"):
            ink_line(canvas, X(np.array([(ex + side * ew * 1.0, ey - eh * 0.4), (ex + side * ew * 1.5, ey - eh * 0.9)])), lw * 0.5, seed=823 + side)
    # brows
    for side in (-1, 1):
        c, z = fp(side * cfg["eye_sep"], cfg["brow_y"])
        if z < 4:
            continue
        fsh = clamp(z / D) ** 0.7
        bx, by = c
        r_ = P["brow"] * 3.0
        soft = cfg.get("brow_soft", 0.0)   # inner ends raised = gentle / worried
        L = cfg["brow_len"]
        pts = np.array([(bx - side * L * fsh, by - r_ - soft * 2.5 + P.get("cold", 0) * 2), (bx, by - 2 - r_), (bx + side * L * 1.05 * fsh, by - r_ * 0.6 + soft)])
        ink_line(canvas, X(spline(pts, n=5)), lw * cfg.get("brow_w", 1.0), color=cfg["brow_col"], seed=830 + side, taper=0.35)
    # nose
    kind = cfg["nose"]
    b, _ = fp(0, cfg["nose_top"])
    nt = cfg["nose_tip"]
    if kind == "broad":
        tipx = b[0] + 8 * st
        fill(canvas, X(np.array([(b[0], cfg["nose_top"]), (tipx + 2 * st, nt), (b[0] + 2 * st, nt + 3), (b[0] - 1, nt + 2)])), cfg["skin"], do_boil=False)
        if st > 0.2:
            ink_line(canvas, X(spline(np.array([(b[0] + 1, cfg["nose_top"]), (tipx + 3, nt - 2), (tipx, nt + 2.5), (b[0] + 1, nt + 3)]), n=4)), lw * 0.85, seed=840)
        else:
            ink_line(canvas, X(np.array([(b[0] - 6, nt + 1), (b[0] - 3, nt + 3.5), (b[0] + 3, nt + 3.5), (b[0] + 6, nt + 1)])), lw * 0.7, seed=841)
            ink_line(canvas, X(np.array([(b[0] - 2.5, cfg["nose_top"] + 2), (b[0] - 3.5, nt - 3)])), lw * 0.5, seed=842, alpha=0.6)
    elif kind == "small":
        tipx = b[0] + 7 * st
        if st > 0.2:
            fill(canvas, X(np.array([(b[0], cfg["nose_top"]), (tipx + 1, nt), (b[0] + 1, nt + 2)])), cfg["skin"], do_boil=False)
            ink_line(canvas, X(spline(np.array([(b[0] + 0.5, cfg["nose_top"]), (tipx + 1, nt - 1), (tipx - 1, nt + 1.5), (b[0] + 1, nt + 2)]), n=4)), lw * 0.75, seed=843)
        else:
            ink_line(canvas, X(np.array([(b[0] - 1.8, nt + 0.5), (b[0], nt + 1.8), (b[0] + 1.8, nt + 0.5)])), lw * 0.6, seed=844)
    elif kind == "clown":
        cx = b[0] + 7 * st
        cfgc = cfg["nose_col"]
        shape(canvas, X(ellipse(cx, nt, 6.5, 6.0, 18)), cfgc, lw * 0.8, seed=845, shade_depth=2.5)
        fill(canvas, X(ellipse(cx - 2, nt - 2.2, 1.6, 1.3, 8)), "#ffffff", alpha=0.6, do_boil=False)
    # mouth (the character's real mouth)
    sm, op = P["smile"], P["open"]
    mw = cfg["mouth_w"]
    us = np.linspace(-mw, mw, 9)
    pts, zs = [], []
    for u in us:
        k = u / mw
        p, z = fp(u, cfg["mouth_y"] - sm * 3.5 * k * k + sm * 1.2 * (1 - k * k))
        pts.append(p); zs.append(z)
    pts = np.array(pts); okm = np.array(zs) > 0
    if okm.sum() >= 3:
        top = pts[okm]
        if op > 0.05:
            bottom = top.copy()
            kk = np.linspace(-1, 1, len(bottom))
            bottom[:, 1] += op * 9 * (1 - kk ** 2) ** 0.8
            fill(canvas, X(np.vstack([top, bottom[::-1]])), "#3a1418")
            ink_line(canvas, X(bottom), lw * 0.6, seed=852, taper=0.3)
        ink_line(canvas, X(top), lw * 0.85, seed=850, taper=0.3)
        if cfg.get("lip_col"):
            mid = top[len(top) // 2]
            fill(canvas, X(ellipse(mid[0], mid[1] + 2.6, mw * 0.45, 1.8, 10)), cfg["lip_col"], alpha=0.75, do_boil=False)
    return fp


# ============================================================================ hands

def hand_shape(kind, flip=1.0):
    """Hand outline in hand-local coords: origin at wrist, +x along the hand.
    Returns list of (points, is_main) and detail lines."""
    f = flip
    if kind in ("grip", "fist"):
        body = spline([(0, -8 * f), (10, -10 * f), (20, -9 * f), (25, -3 * f), (24, 6 * f), (16, 10 * f),
                       (6, 9 * f), (0, 7 * f)], closed=True, n=6)
        lines = [spline([(19, -8 * f), (21, -1 * f), (18, 7 * f)], n=5),
                 bez((6, -9 * f), (11, -4 * f), (14, 0), (13, 4 * f), 6)]
        thumb = spline([(8, -9 * f), (15, -13 * f), (21, -12 * f), (23, -8 * f), (16, -6 * f)], n=4)
        return body, lines, thumb
    if kind == "open":
        body = spline([(0, -8 * f), (9, -11 * f), (16, -10 * f), (30, -9 * f), (33, -5 * f), (34, 0),
                       (33, 5 * f), (28, 8 * f), (16, 9 * f), (6, 8 * f), (0, 7 * f)], closed=True, n=5)
        lines = [spline([(18, -3 * f), (31, -2 * f)], n=3), spline([(18, 3 * f), (30, 4 * f)], n=3)]
        thumb = spline([(6, -8 * f), (14, -16 * f), (21, -18 * f), (22, -14 * f), (14, -7 * f)], n=4)
        return body, lines, thumb
    if kind == "pinch":   # holding a ticket / card between thumb and fingers
        body = spline([(0, -8 * f), (10, -10 * f), (22, -9 * f), (28, -5 * f), (27, 3 * f), (18, 9 * f),
                       (6, 9 * f), (0, 7 * f)], closed=True, n=5)
        lines = [spline([(16, -6 * f), (24, -2 * f)], n=3)]
        thumb = spline([(8, -9 * f), (17, -14 * f), (27, -11 * f), (28, -7 * f), (18, -6 * f)], n=4)
        return body, lines, thumb
    if kind == "point":
        body = spline([(0, -8 * f), (12, -10 * f), (36, -8 * f), (38, -5 * f), (24, -3 * f), (22, 6 * f),
                       (12, 9 * f), (0, 7 * f)], closed=True, n=5)
        lines = [spline([(18, 0), (20, 6 * f)], n=3)]
        thumb = spline([(8, -9 * f), (16, -14 * f), (22, -12 * f), (16, -7 * f)], n=4)
        return body, lines, thumb
    # relax
    body = spline([(0, -8 * f), (10, -9 * f), (22, -8 * f), (29, -4 * f), (30, 2 * f), (25, 7 * f),
                   (12, 9 * f), (0, 7 * f)], closed=True, n=5)
    lines = [spline([(17, -2 * f), (27, 0)], n=3)]
    thumb = spline([(7, -8 * f), (14, -13 * f), (19, -12 * f), (15, -7 * f)], n=4)
    return body, lines, thumb


def draw_hand(canvas, xf, kind, color, lw, seed, glove=True, size=1.0, thumb_front=True):
    body, lines, thumb = hand_shape(kind)
    X = xf.s(size)
    if not thumb_front:
        shape(canvas, X(thumb), color, lw * 0.9, seed=seed + 2, shade_depth=2.5)
    shape(canvas, X(body), color, lw, seed=seed, shade_depth=3.0)
    for i, l in enumerate(lines):
        ink_line(canvas, X(l), lw * 0.55, seed=seed + 10 + i, taper=0.4)
    if thumb_front:
        shape(canvas, X(thumb), color, lw * 0.9, seed=seed + 2, shade_depth=2.5)
    if glove and kind in ("relax", "open"):
        for k in range(3):
            y = -3.5 + k * 3.5
            ink_line(canvas, X(np.array([[8, y], [15, y]])), lw * 0.35, seed=seed + 30 + k, alpha=0.6)
