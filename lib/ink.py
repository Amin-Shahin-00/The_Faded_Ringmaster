"""Hand-drawn ink rendering.

Shapes are numpy point arrays (N,2) in screen space. Every drawn shape gets:
  * line boil  - a low-frequency wobble re-seeded 12x a second (subtle, <1px)
  * uneven ink - stroke width varies with pressure noise and stroke direction
  * painted shading - a soft shadow crescent opposite the key light and an
    optional rim-light crescent, built with path boolean ops
"""
import math
import numpy as np
import skia
from .core import vnoise, snoise, c4, hexc, paint, clamp
from config.palettes import INK


class Style:
    """Per-frame drawing state (set by the renderer each frame)."""
    boil = 0            # drawing index (12 per second)
    boil_amp = 0.75     # px
    line_scale = 1.0
    ink = INK
    # lighting (screen space unit vectors)
    key = (-0.55, -0.83)       # direction TOWARD the key light
    shadow_col = "#2a1a2a"
    shadow_a = 0.32
    rim = None                 # direction toward rim light, or None
    rim_col = "#cfe8ea"
    rim_a = 0.0
    shade_blur = 2.2


S = Style


# ----------------------------------------------------------------------------- primitives

def ellipse(cx, cy, rx, ry, n=40, a0=0.0, a1=math.tau, rot=0.0):
    t = np.linspace(a0, a1, n, endpoint=(a1 - a0) < math.tau - 1e-6)
    x, y = rx * np.cos(t), ry * np.sin(t)
    if rot:
        c, s = math.cos(rot), math.sin(rot)
        x, y = c * x - s * y, s * x + c * y
    return np.stack([cx + x, cy + y], 1)


def bez(p0, p1, p2, p3, n=16):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, float) for p in (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def spline(ctrl, closed=False, n=8, tension=0.5):
    """Catmull-Rom spline through control points."""
    P = np.asarray(ctrl, float)
    if len(P) < 3:
        return P
    if closed:
        P = np.vstack([P[-1:], P, P[:2]])
    else:
        P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    t = np.linspace(0, 1, n, endpoint=False)[:, None]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        m1 = (p2 - p0) * tension
        m2 = (p3 - p1) * tension
        t2, t3 = t * t, t * t * t
        seg = (2 * t3 - 3 * t2 + 1) * p1 + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * p2 + (t3 - t2) * m2
        out.append(seg)
    if not closed:
        out.append(P[-2][None])
    return np.vstack(out)


def arclen(p):
    d = np.hypot(*np.diff(p, axis=0).T)
    return np.concatenate([[0], np.cumsum(d)])


def resample(p, step=6.0, closed=False):
    if closed:
        p = np.vstack([p, p[:1]])
    s = arclen(p)
    L = s[-1]
    if L < 1e-6:
        return p
    n = max(int(L / step), 4)
    u = np.linspace(0, L, n, endpoint=not closed)
    return np.stack([np.interp(u, s, p[:, 0]), np.interp(u, s, p[:, 1])], 1)


# ----------------------------------------------------------------------------- boil

def boil(pts, seed=0, amp=None, freq=0.018):
    """Gentle hand-redrawn wobble: smooth noise displacement along arc length."""
    amp = S.boil_amp if amp is None else amp
    if amp <= 0 or len(pts) < 2:
        return pts
    s = arclen(pts) * freq
    b = S.boil * 13.37 + seed * 3.1
    dx = snoise(s + b, seed * 2 + 1) * amp
    dy = snoise(s + b + 41.7, seed * 2 + 2) * amp
    return pts + np.stack([dx, dy], 1)


# ----------------------------------------------------------------------------- paths

def path_of(pts, closed=True):
    pts = np.asarray(pts, float)
    path = skia.Path()
    if len(pts) == 0:
        return path
    path.addPoly([skia.Point(float(x), float(y)) for x, y in pts], closed)
    return path


def _ribbon(pts, widths):
    t = np.gradient(pts, axis=0)
    n = np.hypot(t[:, 0], t[:, 1])[:, None] + 1e-9
    t = t / n
    nrm = np.stack([-t[:, 1], t[:, 0]], 1)
    w = widths[:, None] * 0.5
    left, right = pts + nrm * w, pts - nrm * w
    return np.vstack([left, right[::-1]])


def ink_line(canvas, pts, width=3.0, color=None, closed=False, seed=0, taper=0.22,
             var=0.38, alpha=1.0, do_boil=True, nib=0.35):
    """Variable-width ink stroke along pts."""
    pts = np.asarray(pts, float)
    if len(pts) < 2:
        return
    if do_boil:
        pts = boil(pts, seed)
    if closed:
        pts = np.vstack([pts, pts[:3]])
    pts = resample(pts, step=max(2.0, width * 0.9))
    if len(pts) < 3:
        return
    width *= S.line_scale
    s = arclen(pts)
    L = s[-1] + 1e-9
    u = s / L
    w = width * (1 + var * snoise(s * 0.02 + seed * 1.7, seed + 99))
    d = np.gradient(pts, axis=0)
    ang = np.arctan2(d[:, 1], d[:, 0])
    w *= (1 - nib) + nib * np.abs(np.sin(ang + 0.6)) * 1.35          # calligraphic nib
    if not closed and taper > 0:
        w *= np.clip(np.minimum(u, 1 - u) / taper, 0.12, 1.0) ** 0.6
    poly = _ribbon(pts, np.maximum(w, 0.35))
    canvas.drawPath(path_of(poly), paint(color or S.ink, alpha))


def fill(canvas, pts, color, alpha=1.0, blend=None, blur=0.0, do_boil=True, seed=0):
    if do_boil:
        pts = boil(np.asarray(pts, float), seed)
    canvas.drawPath(path_of(pts), paint(color, alpha, blend=blend, blur=blur))


def _crescent(path, d, dist):
    shifted = skia.Path(path)
    shifted.offset(d[0] * dist, d[1] * dist)
    try:
        return skia.Op(path, shifted, skia.PathOp.kDifference_PathOp)
    except Exception:
        return None


def shape(canvas, pts, color, line=3.0, seed=0, shadow=True, shade_depth=None, rim=True,
          outline=True, alpha=1.0, shadow_col=None, line_col=None, closed=True, light_scale=1.0):
    """Filled, painterly-shaded, ink-outlined shape. Returns the boiled points."""
    pts = boil(np.asarray(pts, float), seed)
    path = path_of(pts, closed)
    canvas.drawPath(path, paint(color, alpha))
    size = float(np.ptp(pts[:, 0]) + np.ptp(pts[:, 1])) * 0.5
    depth = (shade_depth if shade_depth is not None else max(3.0, size * 0.16)) * light_scale
    if shadow and S.shadow_a > 0:
        cres = _crescent(path, (S.key[0], S.key[1]), depth)
        if cres is not None:
            canvas.save()
            canvas.clipPath(path, skia.ClipOp.kIntersect, True)
            canvas.drawPath(cres, paint(shadow_col or S.shadow_col, S.shadow_a * alpha,
                                        blend=skia.BlendMode.kMultiply, blur=S.shade_blur))
            canvas.restore()
    if rim and S.rim is not None and S.rim_a > 0:
        cres = _crescent(path, (-S.rim[0], -S.rim[1]), max(2.0, depth * 0.35))
        if cres is not None:
            canvas.save()
            canvas.clipPath(path, skia.ClipOp.kIntersect, True)
            canvas.drawPath(cres, paint(S.rim_col, S.rim_a * alpha, blur=0.8))
            canvas.restore()
    if outline and line > 0:
        ink_line(canvas, pts, line, color=line_col, closed=closed, seed=seed + 5, do_boil=False, alpha=alpha)
    return pts


def strokes(canvas, lines, width=2.0, seed=0, color=None, alpha=1.0):
    for i, l in enumerate(lines):
        ink_line(canvas, l, width, color=color, seed=seed + i * 7, alpha=alpha)
