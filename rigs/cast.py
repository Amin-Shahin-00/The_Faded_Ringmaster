"""BRUNO (strongman), LENA (knife thrower), PIP (clown).

Model sheet constants:
  BRUNO  height ~470 to crown, shoulder half-span 80, bald, gentle eyes, horizontally
         striped one-piece suit to mid-shin, wide belt, brown laced boots, bare arms
         with leather wrist cuffs.
  LENA   height ~410, slim; short black bob with bangs; long dark coat to below the knee
         (high collar, 4 dark buttons, belt); calm half-lidded eyes; dark trousers, boots.
  PIP    height ~300, small and wiry, big head; orange hair tufts, white face paint with a
         big drooping painted smile around a small real mouth, red clown nose; baggy
         patched suit, suspenders, ruffled collar, big shoes.
"""
import math
import numpy as np
import skia
from lib.core import Xf, clamp, lerp, mix, mul, paint, smooth, rot
from lib.ink import shape, ink_line, fill, ellipse, spline, bez, S, path_of
from rigs.figure import Figure, proj, ext, draw_hand, draw_face, head_proj
from config.palettes import BRUNO, LENA, PIP


def stripes(canvas, clip_pts, col, y0, y1, period, width, xf, xmin=-200, xmax=200, angle=0.0):
    canvas.save()
    canvas.clipPath(path_of(clip_pts), skia.ClipOp.kIntersect, True)
    y = y0
    while y < y1:
        band = np.array([(xmin, y), (xmax, y + angle), (xmax, y + width + angle), (xmin, y + width)])
        canvas.drawPath(path_of(xf(band)), paint(col))
        y += period
    canvas.restore()


class CastFigure(Figure):
    """Shared drawing for the supporting cast."""
    FRONT = None
    SIDE = None
    face_cfg = {}

    def pose_defaults(self):
        return dict(smile=0.25)

    def head_outline(self, hth):
        w = math.sin(hth)
        return spline(self.FRONT * (1 - w) + self.SIDE * w, closed=True, n=5)

    def draw_ears(self, canvas, X, hth, R, D, x0, y0, y1, behind):
        lw = self.lw()
        for side in (1, -1):
            x, z = proj(side * math.pi / 2, R + 1, D, hth)
            if z < -12:
                continue
            is_behind = z < 2
            if is_behind != behind:
                continue
            ex = x0 + x
            o = (1 if x >= 0 else -1) if behind else -1
            ear = spline(np.array([(ex - o * 2, y0), (ex + o * 5, y0 - 1), (ex + o * 7, (y0 + y1) / 2), (ex + o * 4, y1), (ex - o * 2, y1 + 1)]), n=4)
            shape(canvas, X(ear), self.C["skin"], lw * 0.8, seed=870 + side, shadow_col=self.C["skin_shade"])

    def limb(self, canvas, M, a, b, c, w, col, seed, shadow_col=None, bulge=1.5):
        pts = self.limb_poly(a, b, c, w, bulge=bulge)
        return shape(canvas, M(pts), col, self.lw(), seed=seed, shadow_col=shadow_col)

    def hand_xf(self, J, M, k):
        e, h = J["elbow_" + k], J["hand_" + k]
        a = math.atan2(h[1] - e[1], h[0] - e[0]) + self.P["wrist_" + k]
        return M.t(*h).r(a)

    def foot(self, canvas, J, M, k, col, flen, hgt, seed, front_w=9.0):
        th = J["th"]
        ank = J["ankle_" + k]
        L = flen * lerp(0.42, 1.0, math.sin(th))
        X = M.t(*ank)
        toe = self.P["toe_" + k]
        if toe:
            X = M.t(ank[0] + L * 0.7, ank[1] + 6).r(-toe).t(-L * 0.7, -6)
        if th >= 0.35:
            pts = np.array([(-9, -hgt * 0.6), (-10, hgt * 0.4), (-8, hgt), (L * 0.6, hgt), (L + 2, hgt - 1), (L + 3, hgt * 0.3),
                            (L * 0.7, -hgt * 0.4), (L * 0.3, -hgt * 0.8), (0, -hgt)], float)
        else:
            pts = np.array([(-front_w, -hgt), (-front_w - 1.5, 0), (-front_w, hgt), (0, hgt + 2), (front_w, hgt), (front_w + 1.5, 0), (front_w, -hgt)], float)
        shape(canvas, X(spline(pts, closed=True, n=4)), col, self.lw(), seed=seed, shade_depth=4)

    def draw_arm_generic(self, canvas, J, M, k, sleeve, sleeve_shade, skin, sid, hand_col=None, cuff=None, bare_from=None):
        P = self.P
        sh, el, hd = J["sh_" + k], J["elbow_" + k], J["hand_" + k]
        lw = self.lw()
        before = P.get("arm_prop_before")
        self.limb(canvas, M, sh, el, hd, self.arm_w, sleeve, sid, shadow_col=sleeve_shade)
        if cuff:
            d = hd - el
            n = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-9)
            a, b = el + d * 0.80, el + d * 0.97
            w = self.arm_w[2] + 1.5
            shape(canvas, M(np.array([a + n * w, b + n * w, b - n * w, a - n * w])), cuff, lw * 0.7, seed=sid + 5, shade_depth=2)
        X = self.hand_xf(J, M, k)
        prop = P.get("prop_" + k)
        if prop:
            prop(canvas, self, X)
        draw_hand(canvas, X, P["hand_" + k], hand_col or skin, lw * 0.85, seed=sid + 10, glove=False,
                  size=self.hand_size)

    hand_size = 1.0


# ============================================================================ BRUNO

class Bruno(CastFigure):
    hip_h, hip_w = 206.0, 21.0
    thigh, shin, ankle = 101.0, 99.0, 6.0
    sh_y, sh_w = -136.0, 80.0
    upper, fore = 88.0, 84.0
    neck_y, neck_len = -150.0, 4.0
    head_scale = 1.0
    leg_w = (25.0, 17.5, 12.5)
    arm_w = (20.0, 16.0, 12.0)
    hand_size = 1.45
    line = 3.2
    torso_levels = [(-153, 30, 24, 26), (-147, 68, 34, 38), (-135, 88, 44, 40), (-113, 78, 54, 40), (-82, 60, 50, 34),
                    (-52, 46, 44, 30), (-22, 43, 38, 34), (6, 41, 32, 38)]
    FRONT = np.array([(0, -97), (20, -94), (31, -83), (35, -65), (35.5, -47), (33.5, -29), (28, -13), (16, -2), (0, 0),
                      (-16, -2), (-28, -13), (-33.5, -29), (-35.5, -47), (-35, -65), (-31, -83), (-20, -94)], float)
    SIDE = np.array([(2, -98), (24, -93), (34, -79), (37, -62), (35.5, -48), (34.5, -32), (33.5, -18), (29.5, -6), (14, -1),
                     (-6, -4), (-20, -14), (-31, -32), (-38, -52), (-38.5, -72), (-31, -88), (-16, -96)], float)

    def __init__(self, act=1):
        super().__init__(act)
        self.C = dict(BRUNO[act])
        self.face_cfg = dict(R=33, D=34, eye_y=-52, eye_sep=13.5, eye_w=6.0, eye_h=4.5, pupil=2.9, eye_col=self.C["eye"],
                             brow_y=-63, brow_len=8.5, brow_soft=1.0, brow_w=1.5, brow_col=self.C["brow"], nose="broad",
                             nose_top=-55, nose_tip=-35, mouth_y=-23, mouth_w=9.5, skin=self.C["skin"])

    def pose_defaults(self):
        return dict(smile=0.3)

    def draw_leg(self, canvas, J, M, k):
        C = self.C
        hip, knee, ank = J["hip_" + k], J["knee_" + k], J["ankle_" + k]
        sid = 1100 if k == "n" else 1120
        pts = self.limb(canvas, M, hip + np.array([0, -10]), knee, ank, self.leg_w, C["suit_b"], sid)
        stripes(canvas, pts, C["suit_a"], -260, 40, 22, 11, M @ Xf.T(0, 0))
        ink_line(canvas, pts, self.lw(), closed=True, seed=sid + 1, do_boil=False)
        # boot
        top = knee + (ank - knee) * 0.55
        d = ank - knee
        n = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-9)
        w0, w1 = self.leg_w[2] + 4, self.leg_w[2] + 2
        boot = np.array([top + n * w0, ank + n * w1, ank - n * w1, top - n * w0])
        shape(canvas, M(boot), C["boot"], self.lw(), seed=sid + 3, shade_depth=4)
        for j in range(3):
            q = top + (ank - top) * (0.2 + j * 0.25)
            ink_line(canvas, M(np.array([q + n * w0 * 0.6, q - n * w0 * 0.6])), self.lw(0.4), seed=sid + 6 + j, alpha=0.7)
        self.foot(canvas, J, M, k, C["boot"], 44, 12, sid + 9, front_w=13)

    def draw_torso(self, canvas, J, M):
        C, th = self.C, J["th"]
        T = M @ J["chest"]
        lw = self.lw()
        nb = J["neck_base"]
        top = J["head_xf"](np.array([-2.0, -6.0]))
        neck = np.array([nb + (-22, 8), top + (-20, 0), top + (20, 0), nb + (22, 8)])
        shape(canvas, M(neck), C["skin"], lw, seed=1200, shadow_col=C["skin_shade"])
        outline = self.torso_outline(J, th)
        body = shape(canvas, T(outline), C["skin"], lw, seed=1201, shadow_col=C["skin_shade"], shade_depth=16)
        # suit: covers torso below the chest, straps over the shoulders
        suit_lv = [(y, hw, df, db) for (y, hw, df, db) in self.torso_levels if y >= -118]
        suit = self.torso_outline(J, th, levels=[(-118, 74, 39, 33)] + suit_lv[1:])
        neckline = []
        for ph in np.linspace(-0.9, 0.9, 9):
            x, z = proj(ph, 70, 38, th)
            if z > 0:
                neckline.append((x, -112 + 10 * math.cos(ph * 1.6)))
        sp = shape(canvas, T(suit), C["suit_b"], lw, seed=1202, shadow=False)
        stripes(canvas, sp, C["suit_a"], -125, 20, 22, 11, T)
        canvas.save()
        canvas.clipPath(path_of(sp), skia.ClipOp.kIntersect, True)
        canvas.drawPath(path_of(sp), paint("#2a1a2a", 0.0))
        canvas.restore()
        ink_line(canvas, sp, lw, closed=True, seed=1203, do_boil=False)
        for side in (-1, 1):   # straps
            x1, z1 = proj(side * 0.75, 74, 36, th)
            x2, z2 = proj(side * 0.5, 80, 34, th)
            if z1 > -5:
                strap = np.array([(x1 - 7, -114), (x1 + 7, -114), (x2 + 6, -146), (x2 - 6, -146)])
                shape(canvas, T(strap), C["suit_a"], lw * 0.8, seed=1205 + side, shade_depth=3)
        # belt with buckle
        belt = self.torso_outline(J, th, levels=[(-56, 47, 36, 28), (-38, 45, 34, 29)])
        shape(canvas, T(belt), "#3a2418" if self.act == 1 else "#2a201c", lw, seed=1210, shade_depth=4)
        bx, bz = proj(0.0, 46, 36, th)
        if bz > 4:
            shape(canvas, T(np.array([(bx - 9, -58), (bx + 9, -58), (bx + 9, -36), (bx - 9, -36)])), C["belt"], lw * 0.7, seed=1212, shade_depth=3)
        # chest line (pecs)
        if math.cos(th) > 0.6:
            for side in (-1, 1):
                x, z = proj(side * 0.45, 70, 40, th)
                ink_line(canvas, T(np.array([(x - side * 16, -126), (x, -121), (x + side * 14, -125)])), lw * 0.45, seed=1215 + side, alpha=0.5)

    def draw_arm(self, canvas, J, M, k):
        C = self.C
        sh, el = J["sh_" + k], J["elbow_" + k]
        d = el - sh
        a = math.atan2(d[1], d[0])
        cap = ellipse(sh[0] + d[0] * 0.16, sh[1] + d[1] * 0.16 - 2, 25, 21, 20, rot=a)
        shape(canvas, M(cap), C["skin"], self.lw(), seed=1290 + (k == "f"), shadow_col=C["skin_shade"])
        self.draw_arm_generic(canvas, J, M, k, C["skin"], C["skin_shade"], C["skin"], 1300 if k == "n" else 1340,
                              cuff="#5a3a26" if self.act == 1 else "#3a2c26")
        # deltoid over the top of the arm
        cap2 = ellipse(sh[0] + d[0] * 0.2, sh[1] + d[1] * 0.2, 22, 18, 18, a0=math.pi * 0.95, a1=math.pi * 2.05, rot=a)
        shape(canvas, M(cap2), C["skin"], self.lw(), seed=1295 + (k == "f"), shadow_col=C["skin_shade"], closed=False)

    def draw_head(self, canvas, J, M):
        P, C, hth = self.P, self.C, J["hth"]
        X = M @ J["head_xf"]
        lw = self.lw()
        st = math.sin(hth)
        x0 = lerp(0, -3, st)
        self.draw_ears(canvas, X, hth, 33, 34, x0, -58, -40, True)
        outline = self.head_outline(hth)
        shape(canvas, X(outline), C["skin"], lw, seed=1400, shadow_col=C["skin_shade"], shade_depth=11)
        self.draw_ears(canvas, X, hth, 33, 34, x0, -58, -40, False)
        # bald head shine
        fill(canvas, X(ellipse(x0 - 10 + st * 10, -84, 9, 4.5, 14, rot=-0.3)), "#ffffff", alpha=0.25, blur=2.5, do_boil=False)
        draw_face(self, canvas, X, hth, self.face_cfg, P, lw)
        # jaw/chin dimple
        fp = head_proj(hth, 33, 34, x0)
        c, z = fp(0, -8)
        if z > 5:
            ink_line(canvas, X(np.array([c + (-4, 0), c + (0, 1.2), c + (4, 0)])), lw * 0.4, seed=1410, alpha=0.55)


# ============================================================================ LENA

class Lena(CastFigure):
    hip_h, hip_w = 186.0, 12.0
    thigh, shin, ankle = 93.0, 91.0, 5.0
    sh_y, sh_w = -106.0, 37.0
    upper, fore = 74.0, 68.0
    neck_y, neck_len = -118.0, 10.0
    head_scale = 0.94
    leg_w = (14.0, 9.5, 7.0)
    arm_w = (8.5, 7.0, 5.6)
    hand_size = 0.92
    line = 2.9
    torso_levels = [(-120, 14, 10, 11), (-114, 33, 14, 17), (-105, 39, 18, 19), (-90, 36, 22, 18), (-66, 30, 19, 16),
                    (-44, 26, 16, 15), (-22, 30, 18, 21), (6, 33, 19, 23)]
    FRONT = np.array([(0, -92), (14, -90), (23, -81), (27, -66), (27.5, -51), (25, -36), (19.5, -21), (11, -8), (0, -2),
                      (-11, -8), (-19.5, -21), (-25, -36), (-27.5, -51), (-27, -66), (-23, -81), (-14, -90)], float)
    SIDE = np.array([(2, -93), (20, -87), (28, -73), (30, -60), (28.5, -47), (28, -34), (26, -20), (21, -8), (10, -3),
                     (-4, -6), (-14, -16), (-25, -33), (-32, -50), (-33, -68), (-27, -84), (-14, -91)], float)

    def __init__(self, act=1):
        super().__init__(act)
        self.C = dict(LENA[act])
        self.face_cfg = dict(R=26, D=29, eye_y=-53, eye_sep=10.5, eye_w=5.4, eye_h=3.3, pupil=2.3, eye_col=self.C["eye"],
                             lid=0.35, lash=True, brow_y=-62, brow_len=7.0, brow_soft=-0.3, brow_w=1.0, brow_col=self.C["hair"],
                             nose="small", nose_top=-55, nose_tip=-38, mouth_y=-25, mouth_w=5.8, skin=self.C["skin"],
                             lip_col=self.C["lip"])

    def pose_defaults(self):
        return dict(smile=0.0)

    def draw_leg(self, canvas, J, M, k):
        C = self.C
        hip, knee, ank = J["hip_" + k], J["knee_" + k], J["ankle_" + k]
        sid = 2100 if k == "n" else 2120
        trousers = "#1c1a20" if self.act == 1 else "#18181c"
        self.limb(canvas, M, hip + np.array([0, -8]), knee, ank, self.leg_w, trousers, sid)
        top = knee + (ank - knee) * 0.3
        d = ank - knee
        n = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-9)
        w0, w1 = self.leg_w[1] + 1.5, self.leg_w[2] + 1.2
        shape(canvas, M(np.array([top + n * w0, ank + n * w1, ank - n * w1, top - n * w0])), C["boot"], self.lw(), seed=sid + 3, shade_depth=3)
        self.foot(canvas, J, M, k, C["boot"], 31, 8, sid + 9, front_w=8)

    def draw_torso(self, canvas, J, M):
        C, th, P = self.C, J["th"], self.P
        T = M @ J["chest"]
        T0 = M @ J["torso"]
        lw = self.lw()
        nb = J["neck_base"]
        top = J["head_xf"](np.array([-2.0, -6.0]))
        neck = np.array([nb + (-8, 4), top + (-7, 0), top + (7, 0), nb + (8, 4)])
        shape(canvas, M(neck), C["skin"], lw, seed=2200, shadow_col=C["skin_shade"])
        # long skirt of the coat - follows the knees so walking opens it
        kn, kf = J["knee_n"], J["knee_f"]
        an, af = J["ankle_n"], J["ankle_f"]
        pel = J["pelvis"]
        fr, bk = ext(33, 19, 23, th)
        front_x = max(kn[0], kf[0]) + 15 + 6 * math.sin(th)
        back_x = min(kn[0], kf[0]) - 18 - 8 * math.sin(th)
        hem_y = (kn[1] + kf[1]) / 2 + 32 + P.get("coat_flare", 0) * 0
        sk = np.array([pel + (bk, -34), pel + (fr, -34), pel + (fr + 2, 0),
                       (front_x, hem_y - 4), (front_x - 4, hem_y + 2), ((front_x + back_x) / 2, hem_y + 4),
                       (back_x + 2, hem_y + 2), (back_x - 2, hem_y - 4), pel + (bk - 3, 0)])
        if th < 0.35:   # front view: straight-hanging panels
            sk = np.array([pel + (-31, -34), pel + (31, -34), pel + (33, 0), pel + (39, 150), pel + (2, 155), pel + (-2, 155),
                           pel + (-39, 150), pel + (-33, 0)])
        skirt = spline(sk, closed=True, n=3)
        shape(canvas, M(skirt), C["coat"], lw, seed=2205, shadow_col=C["coat_shade"], shade_depth=12)
        # front opening line + hem trim
        if th < 0.35:
            ink_line(canvas, M(np.array([pel + (0, -30), pel + (1, 154)])), lw * 0.8, seed=2206)
        else:
            ink_line(canvas, M(np.array([pel + (fr - 5, -30), (front_x - 8, hem_y)])), lw * 0.6, seed=2206, alpha=0.7)
        outline = self.torso_outline(J, th)
        shape(canvas, T(outline), C["coat"], lw, seed=2210, shadow_col=C["coat_shade"], shade_depth=10)
        # high collar
        col = []
        for ph in np.linspace(-1.3, 1.3, 9):
            x, z = proj(ph, 16, 13, th)
            col.append((x, -132 + 3 * abs(ph)))
        for ph in np.linspace(1.3, -1.3, 9):
            x, z = proj(ph, 18, 15, th)
            col.append((x, -114))
        shape(canvas, T(np.array(col)), C["coat"], lw * 0.9, seed=2212, shadow_col=C["coat_shade"])
        # buttons (4, single column) + belt
        for i, y in enumerate((-100, -84, -68, -52)):
            x, z = proj(0.12, 32, 20, th)
            if z > 2:
                shape(canvas, T(ellipse(x, y, 2.8, 2.8, 10)), C["trim"], lw * 0.4, seed=2220 + i, shadow=False)
        belt = self.torso_outline(J, th, levels=[(-42, 27, 17, 16), (-33, 28, 17, 18)])
        shape(canvas, T(belt), C["coat_shade"], lw * 0.8, seed=2230, shadow=False)

    def draw_arm(self, canvas, J, M, k):
        C = self.C
        self.draw_arm_generic(canvas, J, M, k, C["coat"], C["coat_shade"], C["skin"], 2300 if k == "n" else 2340,
                              cuff=C["coat_shade"])

    def draw_head(self, canvas, J, M):
        P, C, hth = self.P, self.C, J["hth"]
        X = M @ J["head_xf"]
        lw = self.lw()
        st, ct = math.sin(hth), math.cos(hth)
        x0 = lerp(0, -3, st)
        # bob: back hair (behind head)
        back_f = np.array([(0, -100), (22, -96), (31, -80), (33, -60), (32, -40), (30, -24), (20, -22), (-20, -22), (-30, -24),
                           (-32, -40), (-33, -60), (-31, -80), (-22, -96)], float)
        back_s = np.array([(2, -100), (22, -95), (31, -80), (31, -66), (20, -60), (8, -52), (-10, -20), (-28, -20), (-38, -30),
                           (-41, -52), (-40, -72), (-33, -90), (-18, -99)], float)
        back = spline(back_f * (1 - st) + back_s * st, closed=True, n=4)
        shape(canvas, X(back), C["hair"], lw, seed=2400, shade_depth=6, shadow=False)
        outline = self.head_outline(hth)
        shape(canvas, X(outline), C["skin"], lw, seed=2401, shadow_col=C["skin_shade"], shade_depth=9)
        draw_face(self, canvas, X, hth, self.face_cfg, P, lw)
        # bangs + side locks over the face edge
        # hair cap: everything above the bang line, clipped to the head outline
        fp = head_proj(hth, 27, 30, x0)
        bang = []
        for u in np.linspace(-34, 34, 15):
            p, z = fp(u, -67 + 2.5 * math.sin(u * 0.5))
            bang.append(p)
        bang = np.array(bang)
        # behind the near ear the bob covers the head down to the jaw
        xe = x0 + proj(-math.pi / 2 * 0.92, 28, 30, hth)[0] - 3
        front = bang[bang[:, 0] > xe + 2]
        capp = np.vstack([[(xe, -22), (xe, front[0][1] if len(front) else -66)], front, [(60, -66), (60, -130), (-60, -130), (-60, -22)]])
        canvas.save()
        canvas.clipPath(path_of(X(outline)), skia.ClipOp.kIntersect, True)
        fill(canvas, X(capp), C["hair"], seed=2405)
        canvas.restore()
        if len(front) > 2:
            ink_line(canvas, X(front), lw * 0.7, seed=2406, taper=0.3)
        # side locks hang at the ears; only the visible (near) side is drawn over the face edge
        for side in (-1, 1):
            x, z = proj(side * math.pi / 2 * 0.92, 28, 30, hth)
            if z < 1:
                continue
            px = x0 + x
            o = -1 if x < x0 else 1
            lock = np.array([(px - o * 2, -70), (px + o * 7, -66), (px + o * 7, -40), (px + o * 4, -24), (px - o * 4, -27), (px - o * 5, -48)])
            shape(canvas, X(spline(lock, closed=True, n=3)), C["hair"], lw * 0.7, seed=2408 + side, shadow=False)
        # hair sheen strand
        ink_line(canvas, X(np.array([(x0 - 14, -92), (x0 - 4, -95), (x0 + 8, -93)])), lw * 0.6, color="#4a4650", seed=2410, alpha=0.6)


# ============================================================================ PIP

class Pip(CastFigure):
    hip_h, hip_w = 118.0, 13.0
    thigh, shin, ankle = 58.0, 56.0, 5.0
    sh_y, sh_w = -80.0, 29.0
    upper, fore = 52.0, 47.0
    neck_y, neck_len = -90.0, 4.0
    head_scale = 1.0
    leg_w = (18.0, 15.5, 14.0)
    arm_w = (9.5, 8.5, 8.0)
    hand_size = 0.9
    line = 2.8
    torso_levels = [(-92, 12, 9, 10), (-86, 27, 14, 16), (-79, 32, 18, 18), (-58, 34, 24, 20), (-30, 36, 26, 22),
                    (-6, 37, 26, 25), (8, 35, 24, 26)]
    FRONT = np.array([(0, -88), (15, -86), (25, -77), (30, -62), (31.5, -46), (29.5, -30), (23, -15), (12, -5), (0, -2),
                      (-12, -5), (-23, -15), (-29.5, -30), (-31.5, -46), (-30, -62), (-25, -77), (-15, -86)], float)
    SIDE = np.array([(2, -89), (20, -84), (29, -71), (32, -57), (31, -43), (30, -30), (27, -17), (21, -7), (10, -3),
                     (-5, -6), (-17, -15), (-28, -31), (-34, -48), (-34, -65), (-28, -80), (-14, -88)], float)

    def __init__(self, act=1):
        super().__init__(act)
        self.C = dict(PIP[act])
        self.face_cfg = dict(R=30, D=31, eye_y=-50, eye_sep=11.5, eye_w=5.6, eye_h=4.2, pupil=2.6, eye_col=self.C["eye"],
                             brow_y=-60, brow_len=6.5, brow_soft=1.5, brow_w=0.9, brow_col="#5a4030", nose="clown",
                             nose_col=self.C["nose"], nose_top=-46, nose_tip=-37, mouth_y=-24, mouth_w=5.0, skin=self.C["paint"])

    def pose_defaults(self):
        return dict(smile=-0.4, droop=0.6, paint_run=0.0)

    def draw_leg(self, canvas, J, M, k):
        C = self.C
        hip, knee, ank = J["hip_" + k], J["knee_" + k], J["ankle_" + k]
        sid = 3100 if k == "n" else 3120
        pts = self.limb(canvas, M, hip + np.array([0, -8]), knee, ank, self.leg_w, C["suit"], sid, shadow_col=C["suit_shade"], bulge=3)
        if k == "n":   # knee patch
            shape(canvas, M(np.array([knee + (-8, -6), knee + (7, -8), knee + (8, 6), knee + (-7, 7)])), C["patch"], self.lw(0.6), seed=sid + 4, shadow=False)
            for j in range(3):
                ink_line(canvas, M(np.array([knee + (-8 + j * 7, -9), knee + (-6 + j * 7, -5)])), self.lw(0.35), seed=sid + 5 + j)
        self.foot(canvas, J, M, k, C["shoe"], 52, 13, sid + 9, front_w=16)

    def draw_torso(self, canvas, J, M):
        C, th = self.C, J["th"]
        T = M @ J["chest"]
        lw = self.lw()
        outline = self.torso_outline(J, th)
        shape(canvas, T(outline), C["suit"], lw, seed=3200, shadow_col=C["suit_shade"], shade_depth=12)
        # patch on the belly
        px, pz = proj(0.45, 34, 24, th)
        if pz > 3:
            shape(canvas, T(np.array([(px - 7, -44), (px + 8, -46), (px + 7, -31), (px - 8, -30)])), C["patch2"], lw * 0.6, seed=3203, shadow=False)
        # suspenders
        for side in (-1, 1):
            a, za = proj(side * 0.4, 30, 18, th)
            b, zb = proj(side * 0.3, 36, 26, th)
            if za > 0 and zb > 0:
                ink_line(canvas, T(np.array([(a, -84), (b, -2)])), lw * 2.2, color=C["patch2"], seed=3205 + side, taper=0.02, var=0.1)
                ink_line(canvas, T(np.array([(a - 2.5, -84), (b - 2.5, -2)])), lw * 0.4, seed=3207 + side, alpha=0.6)
        # buttons
        for i, y in enumerate((-66, -48)):
            x, z = proj(0.0, 34, 24, th)
            if z > 3:
                shape(canvas, T(ellipse(x, y, 3.2, 3.2, 10)), C["patch"], lw * 0.45, seed=3210 + i, shadow=False)
        # ruffled collar
        pts = []
        n = 14
        for i in range(n + 1):
            ph = -1.5 + 3.0 * i / n
            x, z = proj(ph, 24, 18, th)
            r = -94 + (6 if i % 2 else -1)
            pts.append((x * (1.25 if i % 2 else 1.0), r))
        for i in range(n, -1, -1):
            ph = -1.5 + 3.0 * i / n
            x, z = proj(ph, 14, 11, th)
            pts.append((x, -88))
        shape(canvas, T(np.array(pts)), C["collar"], lw * 0.7, seed=3215, shade_depth=3)

    def draw_arm(self, canvas, J, M, k):
        C = self.C
        self.draw_arm_generic(canvas, J, M, k, C["suit"], C["suit_shade"], "#f5efe2" if self.act == 1 else "#cfc9bc",
                              3300 if k == "n" else 3340, cuff=C["collar"])

    def draw_head(self, canvas, J, M):
        P, C, hth = self.P, self.C, J["hth"]
        X = M @ J["head_xf"]
        lw = self.lw()
        st, ct = math.sin(hth), math.cos(hth)
        x0 = lerp(0, -3, st)
        def tufts(front):
            for side in (1, -1):
                x, z = proj(side * math.pi / 2, 30, 31, hth)
                if z < -14 or (z > 6) != front:
                    continue
                hx = x0 + x
                o = (1 if x >= 0 else -1) if not front else -1
                k = 1.0 if not front else 0.8
                tuft = np.array([(hx - o * 4, -76), (hx + o * 10 * k, -82), (hx + o * 17 * k, -72), (hx + o * 13 * k, -64),
                                 (hx + o * 19 * k, -56), (hx + o * 9 * k, -48), (hx - o * 4, -50)])
                if front:   # near tuft seen from the side: puff around the ear
                    tuft = np.array([(hx + 8, -78), (hx - 4, -84), (hx - 16, -76), (hx - 13, -66), (hx - 19, -57), (hx - 8, -47), (hx + 6, -50)])
                shape(canvas, X(spline(tuft, closed=True, n=3)), C["hair"], lw * 0.8, seed=3400 + side, shade_depth=4)
        tufts(False)
        self.draw_ears(canvas, X, hth, 30, 31, x0, -54, -40, True)
        outline = self.head_outline(hth)
        shape(canvas, X(outline), C["skin"], lw, seed=3401, shadow_col="#9a7a66", shade_depth=9)
        fp = head_proj(hth, 30, 31, x0)
        # white face paint (faded at the edges)
        paint_pts = []
        for ang in np.linspace(0, math.tau, 28, endpoint=False):
            u, y = 31 * math.cos(ang), -42 + 27 * math.sin(ang)
            p, z = fp(u, y)
            if z > -2:
                paint_pts.append(p)
        if len(paint_pts) > 5:
            canvas.save()
            canvas.clipPath(path_of(X(outline)), skia.ClipOp.kIntersect, True)
            fill(canvas, X(np.array(paint_pts)), C["paint"], alpha=0.92, blur=1.5)
            canvas.restore()
        self.draw_ears(canvas, X, hth, 30, 31, x0, -54, -40, False)
        tufts(True)
        # painted smile: big, red, drooping at the corners (does not match his real mouth)
        droop = P["droop"]
        top, bot = [], []
        for u in np.linspace(-17, 17, 13):
            k = u / 17
            yy = -27 + 2.0 * (1 - k * k) - 9 * k * k + droop * 11 * k ** 4
            p1, z1 = fp(u, yy)
            p2, z2 = fp(u, yy + 6 * (1 - k * k) ** 0.6 + 1)
            if z1 > 0:
                top.append(p1); bot.append(p2)
        if len(top) >= 3:
            sm = np.vstack([np.array(top), np.array(bot)[::-1]])
            fill(canvas, X(sm), C["paint_mouth"], alpha=0.82, blur=0.8)
        # painted brows (high arches) + diamond marks
        for side in (-1, 1):
            c, z = fp(side * 11.5, -64)
            if z > 4:
                ink_line(canvas, X(np.array([c + (-side * 6, 2), c + (0, -5), c + (side * 6, 1)])), lw * 0.8, color="#3a2a40", seed=3410 + side, alpha=0.8)
        draw_face(self, canvas, X, hth, self.face_cfg, P, lw)
        # paint running in the rain
        if P["paint_run"] > 0:
            for i, (u, y0, ln) in enumerate([(-12, -45, 16), (-6, -22, 22), (5, -21, 26), (13, -24, 18), (16, -44, 12)]):
                c, z = fp(u, y0)
                if z > 3:
                    L = ln * P["paint_run"]
                    col = C["paint_mouth"] if abs(y0 + 22) < 4 else C["paint"]
                    ink_line(canvas, X(np.array([c, c + (0.6, L * 0.5), c + (-0.4, L)])), lw * 0.9, color=col, seed=3420 + i, alpha=0.75, taper=0.5)
