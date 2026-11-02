"""Shared scene elements: props, crowd, weather, light effects, painted backgrounds."""
import math
from functools import lru_cache
import numpy as np
import skia
from lib.core import (W, H, Xf, clamp, lerp, remap, smooth, ease_io, hexc, mix, mul, paint, c4, rng, vnoise, snoise,
                      desat, keys)
from lib.ink import S, shape, ink_line, fill, ellipse, spline, bez, path_of, boil
from lib.frame import text, font, new_surface, text_width


# ============================================================================ props

def draw_ticket(c, x, y, scale=1.0, angle=0.0, aged=1.0, alpha=1.0):
    """Old circus ticket stamped ADMIT ONE. (x, y) = ticket center."""
    c.save()
    c.translate(x, y)
    c.rotate(math.degrees(angle))
    c.scale(scale, scale)
    w, h = 64, 30
    # scalloped / perforated outline
    pts = []
    for i in range(41):
        pts.append((-w + 2 * w * i / 40, -h + (1.2 if i % 2 else 0)))
    for i in range(41):
        pts.append((w - (1.2 if i % 2 else 0), -h + 2 * h * i / 40))
    for i in range(41):
        pts.append((w - 2 * w * i / 40, h - (1.2 if i % 2 else 0)))
    for i in range(41):
        pts.append((-w + (1.2 if i % 2 else 0), h - 2 * h * i / 40))
    pts = np.array(pts)
    paper = mix("#f1e3bd", "#cdbf9a", 0.5 * aged)
    shape(c, pts, paper, 1.6, seed=900, shade_depth=4, alpha=alpha)
    red = mix("#b8242c", "#8a3a36", 0.5 * aged)
    c.drawRect(skia.Rect.MakeLTRB(-w + 6, -h + 6, w - 6, h - 6), paint(red, alpha, stroke=1.6))
    c.drawRect(skia.Rect.MakeLTRB(-w + 9, -h + 9, w - 9, h - 9), paint(red, 0.7 * alpha, stroke=0.8))
    text(c, "MARLOWE'S MARVELOUS CIRCUS", 0, -h + 17, "oldstd_b", 6.4, red, alpha)
    text(c, "ADMIT ONE", 0, 8, "rye", 17, "#2a1a14", alpha)
    text(c, "No. 0001", 0, h - 11, "oldstd", 6.0, red, alpha)
    # stub perforation line
    for i in range(9):
        c.drawCircle(-w + 20, -h + 6 + i * 6.2, 0.8, paint("#5a4a3a", 0.6 * alpha))
    # ink stamp ring overlapping the corner
    c.drawCircle(w - 22, h - 15, 9, paint(red, 0.45 * alpha, stroke=1.4))
    c.restore()


def draw_lit(c, fig, P, lit=1.0, dark="#03070a", props=None):
    """Draw a figure, darkened toward a silhouette when lit < 1 (stepping out of shadow)."""
    if lit >= 0.999:
        return fig.draw(c, P, props=props)
    c.saveLayer(None, None)
    J = fig.draw(c, P, props=props)
    p = paint(dark, 0.94 * (1 - lit))
    p.setBlendMode(skia.BlendMode.kSrcATop)
    c.drawPaint(p)
    c.restore()
    return J


def cracked_hat(c, x, y, size=1.0, progress=1.0, col="#141012", crack_col=None, alpha=1.0, drips=True, seed=0):
    """The empire's symbol: a top hat split by a jagged crack, painted with a brush.
    progress 0..1 reveals it along the brush path (left-to-right sweeps)."""
    if progress <= 0:
        return
    s = size
    crown = np.array([(-34, 0), (-36, -86), (-40, -108), (40, -108), (36, -86), (34, 0)]) * s
    brim = ellipse(0, 0, 66 * s, 13 * s, 30)
    band = np.array([(-35, -6), (-35.5, -24), (35.5, -24), (35, -6)]) * s
    crack = np.array([(-4, -112), (6, -88), (-6, -66), (8, -44), (-5, -22), (5, 6)]) * s
    c.save()
    c.translate(x, y)
    if progress < 1.0:
        # brush sweeps: reveal three horizontal bands one after the other
        clip = skia.Path()
        bands = [(-120, -70), (-70, -25), (-25, 20)]
        for i, (y0, y1) in enumerate(bands):
            u = clamp(progress * 3 - i)
            if u > 0:
                clip.addRect(skia.Rect.MakeLTRB(-80 * s, y0 * s, (-80 + 160 * u) * s, y1 * s))
        c.clipPath(clip, skia.ClipOp.kIntersect, True)
    rough = lambda p, k: boil(p, seed + k, amp=1.6 * s)
    c.drawPath(path_of(rough(crown, 1)), paint(col, alpha))
    c.drawPath(path_of(rough(brim, 2)), paint(col, alpha))
    c.drawPath(path_of(rough(band, 3)), paint(crack_col or "#5a1a1a", alpha))
    # the crack shows what is underneath (a gap in the paint)
    wide = np.vstack([crack + (-4 * s, 0), (crack + (4 * s, 0))[::-1]])
    p = paint("#000000", 1.0)
    p.setBlendMode(skia.BlendMode.kClear)
    c.restore()
    c.save()
    c.translate(x, y)
    ink_line(c, crack, 7 * s, color="#d8d0c0", alpha=0.9 * alpha * clamp(progress * 3 - 0.3), do_boil=False, taper=0.3)
    if drips and progress > 0.5:
        r = rng(seed + 40)
        for i in range(5):
            dx = (-30 + 60 * r.random()) * s
            L = (10 + 30 * r.random()) * s * clamp((progress - 0.5) * 2)
            c.drawLine(dx, 10 * s, dx, 10 * s + L, paint(col, alpha, stroke=3.5 * s))
            c.drawCircle(dx, 10 * s + L, 2.6 * s, paint(col, alpha))
    c.restore()


# ============================================================================ light & weather

def radial(c, x, y, r, col, a=1.0, blend=None, inner=0.0):
    p = skia.Paint(AntiAlias=True)
    cc = hexc(col)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(x, y), max(r, 1), [skia.Color4f(*cc, a), skia.Color4f(*cc, a * 0.35), skia.Color4f(*cc, 0)],
                                               [inner, 0.45, 1.0]))
    if blend is not None:
        p.setBlendMode(blend)
    c.drawCircle(x, y, r, p)


def cone(c, apex, base_c, base_w, col, a=0.35, blend=skia.BlendMode.kScreen, soft=18):
    """Spotlight beam: a soft triangle from apex to an elliptic base."""
    ax, ay = apex
    bx, by = base_c
    d = np.array([bx - ax, by - ay]); L = np.hypot(*d) + 1e-6
    n = np.array([-d[1], d[0]]) / L
    pts = np.array([apex + n * 6, (bx, by) + n * base_w, (bx, by) - n * base_w, apex - n * 6])
    p = skia.Paint(AntiAlias=True)
    cc = hexc(col)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(ax, ay), skia.Point(bx, by)],
                                               [skia.Color4f(*cc, a), skia.Color4f(*cc, a * 0.55)], None))
    p.setBlendMode(blend)
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, soft))
    c.drawPath(path_of(pts), p)


def rain(c, t, seed=1, n=420, speed=1900.0, angle=0.16, length=46, col="#cfdde3", a=0.35, width=1.4, area=None, slow=1.0, depth_layers=3):
    """Rain streaks, smooth 24 fps motion. Deterministic per seed."""
    x0, y0, x1, y1 = area or (-100, -100, W + 100, H + 100)
    r = rng(seed)
    base = r.random((n, 3))
    dx = math.sin(angle); dy = math.cos(angle)
    hgt = (y1 - y0) + 200
    for layer in range(depth_layers):
        k = (layer + 1) / depth_layers
        sel = base[layer::depth_layers]
        sp = speed * (0.55 + 0.45 * k) * slow
        ln = length * (0.5 + 0.5 * k) * (0.6 + 0.4 * slow)
        p = paint(col, a * (0.35 + 0.65 * k), stroke=width * (0.6 + 0.6 * k))
        path = skia.Path()
        for (u, v, w_) in sel:
            yy = (v * hgt + t * sp * (0.9 + 0.2 * w_)) % hgt + y0 - 100
            xx = x0 + u * (x1 - x0) + (yy - y0) * dx
            path.moveTo(xx, yy)
            path.lineTo(xx + dx * ln, yy + dy * ln)
        c.drawPath(path, p)


def splashes(c, t, y_ground, seed=3, n=60, x0=0, x1=W, col="#cfdde3", a=0.5, rate=3.0, scale=1.0):
    """Little crown splashes on wet ground."""
    r = rng(seed)
    pars = r.random((n, 3))
    for (u, ph, k) in pars:
        life = (t * rate + ph * 10) % 1.0
        cyc = math.floor(t * rate + ph * 10)
        xx = x0 + ((u + cyc * 0.37) % 1.0) * (x1 - x0)
        yy = y_ground + k * 60 * scale
        rr = (2 + 9 * life) * scale * (0.6 + 0.6 * k)
        al = a * (1 - life) ** 1.5
        c.drawOval(skia.Rect.MakeXYWH(xx - rr, yy - rr * 0.3, rr * 2, rr * 0.6), paint(col, al, stroke=1.0 * scale))


def fog(c, t, y, height, col, a=0.25, seed=5, drift=12.0, n=7):
    r = rng(seed)
    for i in range(n):
        u = r.random()
        xx = ((u * (W + 600) + t * drift * (0.5 + r.random())) % (W + 600)) - 300
        yy = y + (r.random() - 0.5) * height
        rx = 260 + 260 * r.random()
        p = paint(col, a * (0.5 + 0.5 * r.random()), blur=60)
        c.drawOval(skia.Rect.MakeXYWH(xx - rx, yy - rx * 0.25, rx * 2, rx * 0.5), p)


def lightning_flash(t, times, dur=0.5):
    """Intensity 0..1 of lightning (double flicker, smooth ramps - no single-frame strobes)."""
    v = 0.0
    for t0 in times:
        u = t - t0
        if 0 <= u < dur:
            a = math.exp(-u * 9) * (1.0 if u < 0.12 else 0.75)
            b = 0.7 * math.exp(-max(0, u - 0.16) * 10) if u > 0.16 else 0.0
            v = max(v, a, b)
    return v


# ============================================================================ painted textures

@lru_cache(None)
def brush_tex(seed=1, size=512):
    """Tileable-ish dry brush texture image (gray, alpha) for painterly fills."""
    surf = new_surface(size, size)
    c = surf.getCanvas()
    c.clear(0x00000000)
    r = rng(seed)
    for i in range(900):
        x, y = r.random(2) * size
        ang = r.normal(0, 0.25)
        L = 20 + r.random() * 70
        w = 2 + r.random() * 9
        g = r.random()
        col = (g, g, g)
        p = paint(col, 0.05 + 0.1 * r.random(), stroke=w)
        c.drawLine(x, y, x + math.cos(ang) * L, y + math.sin(ang) * L, p)
    return surf.makeImageSnapshot()


def painterly(c, path, base, seed=0, strength=0.5, angle=0.0, scale=1.0, light=None, dark=None):
    """Fill path with base color plus layered brush-stroke texture (deterministic, static)."""
    c.drawPath(path, paint(base))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    b = path.getBounds()
    r = rng(seed)
    lt = light or mix(base, "#ffffff", 0.18)
    dk = dark or mix(base, "#000000", 0.22)
    area = (b.width() * b.height())
    n = int(min(1400, max(30, area / (900 * scale * scale)) * strength))
    pts = r.random((n, 5))
    for (u, v, k, a2, w2) in pts:
        x = b.left() + u * b.width(); y = b.top() + v * b.height()
        ang = angle + (a2 - 0.5) * 0.5
        L = (18 + 60 * w2) * scale
        col = lt if k > 0.5 else dk
        p = paint(col, 0.10 + 0.12 * abs(k - 0.5), stroke=(3 + 9 * a2) * scale)
        c.drawLine(x, y, x + math.cos(ang) * L, y + math.sin(ang) * L, p)
    c.restore()


def soft_poly(c, pts, col, a=1.0, blur=0.0):
    c.drawPath(path_of(np.asarray(pts, float)), paint(col, a, blur=blur))
