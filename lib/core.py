"""Core helpers: math, easing, keyframes, deterministic noise, colors, 2D transforms."""
import math
import numpy as np
import skia

W, H, FPS = 1920, 1080, 24
TAU = math.tau

# ----------------------------------------------------------------------------- math

def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def remap(x, a, b):
    """0..1 position of x between a and b (clamped)."""
    if b == a:
        return 1.0 if x >= b else 0.0
    return clamp((x - a) / (b - a))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def smoother(t):
    t = clamp(t)
    return t * t * t * (t * (t * 6 - 15) + 10)


def ease_io(t, p=2.2):
    t = clamp(t)
    return 0.5 * (2 * t) ** p if t < 0.5 else 1 - 0.5 * (2 * (1 - t)) ** p


def ease_out(t, p=2.0):
    t = clamp(t)
    return 1 - (1 - t) ** p


def ease_in(t, p=2.0):
    t = clamp(t)
    return t ** p


def ease_back(t, s=1.6):
    """Overshoot then settle (used for Act 1 exaggeration)."""
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


EASES = {"io": ease_io, "in": ease_in, "out": ease_out, "lin": lambda t: clamp(t),
         "back": ease_back, "smooth": smooth, "io3": lambda t: ease_io(t, 3.0),
         "hold": lambda t: 0.0}


def keys(t, kf, default="io"):
    """Piecewise keyframe interpolation.

    kf: list of (time, value) or (time, value, ease) - ease applies to the segment
    that ENDS at that key. Values may be scalars, tuples or numpy arrays.
    Holds = repeat a value. Default ease is slow-in/slow-out.
    """
    if t <= kf[0][0]:
        return _val(kf[0][1])
    for i in range(1, len(kf)):
        if t <= kf[i][0]:
            t0, v0 = kf[i - 1][0], kf[i - 1][1]
            t1, v1 = kf[i][0], kf[i][1]
            e = kf[i][2] if len(kf[i]) > 2 else default
            u = EASES[e](remap(t, t0, t1)) if isinstance(e, str) else e(remap(t, t0, t1))
            return _mix(v0, v1, u)
    return _val(kf[-1][1])


def _val(v):
    return np.array(v, float) if isinstance(v, (tuple, list)) else v


def _mix(a, b, u):
    if isinstance(a, (tuple, list, np.ndarray)):
        return np.array(a, float) + (np.array(b, float) - np.array(a, float)) * u
    return a + (b - a) * u


def twos(t, origin=0.0):
    """Quantize character-animation time to 12 drawings per second ('on twos')."""
    return origin + math.floor((t - origin) * 12 + 1e-6) / 12.0


def boil_index(t):
    """Drawing index for line boil - changes 12 times a second, like redrawn frames."""
    return int(math.floor(t * 12 + 1e-6))


# ----------------------------------------------------------------------------- noise

def _hash(i):
    i = np.asarray(i, np.int64)
    i = (i ^ 61) ^ (i >> 16)
    i = (i + (i << 3)) & 0xFFFFFFFF
    i = i ^ (i >> 4)
    i = (i * 0x27D4EB2D) & 0xFFFFFFFF
    i = i ^ (i >> 15)
    return (i & 0xFFFFFF) / float(0xFFFFFF)


def vnoise(x, seed=0):
    """Smooth 1D value noise in [0,1], vectorized, deterministic."""
    x = np.asarray(x, float)
    i = np.floor(x).astype(np.int64)
    f = x - i
    s = int(seed) * 7919
    a, b = _hash(i + s), _hash(i + 1 + s)
    u = f * f * (3 - 2 * f)
    return a + (b - a) * u


def snoise(x, seed=0):
    """Signed noise in [-1,1]."""
    return vnoise(x, seed) * 2 - 1


def rand(seed, n=None):
    """Deterministic uniform random numbers from an integer seed."""
    rng = np.random.default_rng(abs(int(seed)) + 12345)
    return rng.random(n) if n is not None else rng.random()


def rng(seed):
    return np.random.default_rng(abs(int(seed)) + 777)


# ----------------------------------------------------------------------------- color

def hexc(h):
    if isinstance(h, (tuple, list, np.ndarray)):
        return tuple(float(v) for v in h[:3])
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def mix(c1, c2, t):
    a, b = hexc(c1), hexc(c2)
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def mul(c, k):
    a = hexc(c)
    if isinstance(k, (int, float)):
        k = (k, k, k)
    return tuple(clamp(a[i] * k[i]) for i in range(3))


def desat(c, s):
    a = hexc(c)
    l = 0.3 * a[0] + 0.59 * a[1] + 0.11 * a[2]
    return tuple(l + (a[i] - l) * s for i in range(3))


def c4(c, a=1.0):
    r, g, b = hexc(c)
    return skia.Color4f(r, g, b, a)


def paint(c="#000000", a=1.0, blend=None, blur=0.0, aa=True, stroke=0.0, cap=None, join=None):
    p = skia.Paint(AntiAlias=aa)
    p.setColor4f(c4(c, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(cap or skia.Paint.kRound_Cap)
        p.setStrokeJoin(join or skia.Paint.kRound_Join)
    if blend is not None:
        p.setBlendMode(blend)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


# ----------------------------------------------------------------------------- transforms

class Xf:
    """2D affine transform (3x3 matrix)."""
    __slots__ = ("m",)

    def __init__(self, m=None):
        self.m = np.eye(3) if m is None else m

    @staticmethod
    def T(x, y):
        m = np.eye(3); m[0, 2] = x; m[1, 2] = y
        return Xf(m)

    @staticmethod
    def R(a):
        c, s = math.cos(a), math.sin(a)
        return Xf(np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]]))

    @staticmethod
    def S(sx, sy=None):
        sy = sx if sy is None else sy
        return Xf(np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1.0]]))

    def __matmul__(self, o):
        return Xf(self.m @ o.m)

    def t(self, x, y):
        return self @ Xf.T(x, y)

    def r(self, a):
        return self @ Xf.R(a)

    def s(self, sx, sy=None):
        return self @ Xf.S(sx, sy)

    def at(self, x, y, a):
        """rotate by a around local point (x,y)."""
        return self.t(x, y).r(a).t(-x, -y)

    def __call__(self, pts):
        p = np.asarray(pts, float)
        if p.ndim == 1:
            return self.m[:2, :2] @ p + self.m[:2, 2]
        return p @ self.m[:2, :2].T + self.m[:2, 2]

    @property
    def scale(self):
        return math.sqrt(abs(np.linalg.det(self.m[:2, :2])))

    @property
    def flipped(self):
        return np.linalg.det(self.m[:2, :2]) < 0

    def skia(self):
        m = self.m
        return skia.Matrix.MakeAll(m[0, 0], m[0, 1], m[0, 2], m[1, 0], m[1, 1], m[1, 2], 0, 0, 1)


def rot(v, a):
    c, s = math.cos(a), math.sin(a)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


def ik2(root, target, l1, l2, bend=1.0, squash_side=1.0):
    """Two-bone IK in 2D. Returns (joint, end). Never stretches: if the target is
    out of reach the chain points at it fully extended (end stops short).
    bend: +1/-1 picks the side the joint bends toward; |bend|<1 flattens the bend
    (used for front views where the knee bend is foreshortened)."""
    root = np.asarray(root, float); target = np.asarray(target, float)
    d = target - root
    dist = float(np.hypot(*d))
    lo, hi = abs(l1 - l2) + 1e-3, (l1 + l2) * 0.9995
    dc = min(max(dist, lo), hi)
    u = d / dist if dist > 1e-6 else np.array([0.0, 1.0])
    a = (l1 * l1 - l2 * l2 + dc * dc) / (2 * dc)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    perp = np.array([-u[1], u[0]])
    joint = root + u * a + perp * h * bend
    end = root + u * dc
    return joint, end
