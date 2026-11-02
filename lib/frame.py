"""Frame surface, camera with parallax, text, and the film post-process
(grade, bloom, paper + brush texture, film grain, vignette)."""
import math
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import numpy as np
import skia
from scipy import ndimage
from .core import W, H, c4, hexc, paint, clamp, lerp

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "build" / "textures"
FONTS = ROOT / "assets" / "fonts"


# ----------------------------------------------------------------------------- surfaces

def new_surface(w=W, h=H):
    info = skia.ImageInfo.Make(w, h, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
    return skia.Surface.MakeRaster(info)


def snapshot(surface):
    return surface.makeImageSnapshot()


def to_array(surface):
    return surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)


def from_array(arr):
    arr = np.ascontiguousarray(arr)
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)])
    return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)


# ----------------------------------------------------------------------------- camera

class Cam:
    """Camera for parallax. Layers are authored in 'home' screen coordinates
    (zoom 1, centered). depth 0 = infinitely far (static), 1 = subject plane,
    >1 = foreground (moves and zooms more than the subject)."""

    def __init__(self, x=W / 2, y=H / 2, zoom=1.0, rot=0.0):
        self.x, self.y, self.zoom, self.rot = x, y, zoom, rot

    def xf(self, depth=1.0):
        zd = self.zoom ** depth
        ox, oy = (self.x - W / 2) * depth, (self.y - H / 2) * depth
        m = skia.Matrix()
        m.preTranslate(W / 2, H / 2)
        if self.rot:
            m.preRotate(math.degrees(self.rot) * depth)
        m.preScale(zd, zd)
        m.preTranslate(-(W / 2 + ox), -(H / 2 + oy))
        return m

    @contextmanager
    def layer(self, canvas, depth=1.0):
        canvas.save()
        canvas.concat(self.xf(depth))
        try:
            yield
        finally:
            canvas.restore()

    def to_screen(self, p, depth=1.0):
        m = self.xf(depth)
        q = m.mapXY(float(p[0]), float(p[1]))
        return np.array([q.x(), q.y()])


# ----------------------------------------------------------------------------- text

_FONT_FILES = {
    "rye": "Rye-Regular.ttf", "ultra": "Ultra-Regular.ttf", "abril": "AbrilFatface-Regular.ttf",
    "oldstd": "OldStandard-Regular.ttf", "oldstd_b": "OldStandard-Bold.ttf",
    "elite": "SpecialElite-Regular.ttf", "bebas": "BebasNeue-Regular.ttf",
}


@lru_cache(None)
def typeface(name):
    return skia.Typeface.MakeFromFile(str(FONTS / _FONT_FILES[name]))


def font(name, size):
    f = skia.Font(typeface(name), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    return f


def text(canvas, s, x, y, fname, size, color="#000", alpha=1.0, align="center", spacing=0.0, blend=None):
    f = font(fname, size)
    p = paint(color, alpha, blend=blend)
    if spacing == 0:
        w = f.measureText(s)
        dx = {"center": -w / 2, "left": 0, "right": -w}[align]
        canvas.drawString(s, x + dx, y, f, p)
        return w
    widths = [f.measureText(ch) for ch in s]
    total = sum(widths) + spacing * (len(s) - 1)
    cx = x + {"center": -total / 2, "left": 0, "right": -total}[align]
    for ch, w in zip(s, widths):
        canvas.drawString(ch, cx, y, f, p)
        cx += w + spacing
    return total


def text_width(s, fname, size, spacing=0.0):
    f = font(fname, size)
    return sum(f.measureText(ch) for ch in s) + spacing * (len(s) - 1) if spacing else f.measureText(s)


# ----------------------------------------------------------------------------- textures

def _fbm_tex(shape, seed, scales=(2, 6, 18, 60), weights=(0.45, 0.3, 0.15, 0.1)):
    rng = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    for sc, w in zip(scales, weights):
        small = rng.standard_normal((shape[0] // sc + 2, shape[1] // sc + 2)).astype(np.float32)
        up = ndimage.zoom(small, sc, order=3)[:shape[0], :shape[1]]
        out += w * up / (up.std() + 1e-6)
    return out


@lru_cache(None)
def paper_tex():
    """Multiplicative paper + dry-brush texture (H,W,1), mean ~1."""
    TEX.mkdir(parents=True, exist_ok=True)
    f = TEX / "paper_v2.npy"
    if f.exists():
        return np.load(f)
    base = _fbm_tex((H, W), 11)
    rng = np.random.default_rng(5)
    fiber = rng.standard_normal((H, W)).astype(np.float32)
    fiber = ndimage.gaussian_filter(fiber, sigma=(0.6, 3.5))           # horizontal fibers
    brush = ndimage.gaussian_filter(rng.standard_normal((H // 3, W // 3)).astype(np.float32), (1.0, 6.0))
    brush = ndimage.zoom(brush, 3, order=1)[:H, :W]
    tex = 1.0 + 0.030 * base / 2 + 0.020 * fiber / (fiber.std() + 1e-6) + 0.016 * brush / (brush.std() + 1e-6)
    tex = tex.astype(np.float32)[:, :, None]
    np.save(f, tex)
    return tex


@lru_cache(None)
def grain_tiles(n=8):
    f = TEX / "grain_v1.npy"
    if f.exists():
        return np.load(f)
    TEX.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(3)
    tiles = []
    for i in range(n):
        g = rng.standard_normal((H, W)).astype(np.float32)
        g = ndimage.gaussian_filter(g, 0.7)
        tiles.append((g / g.std()).astype(np.float16))
    tiles = np.stack(tiles)
    np.save(f, tiles)
    return tiles


@lru_cache(None)
def vignette_map():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (x - W / 2) / (W / 2), (y - H / 2) / (H / 2)
    r = np.sqrt(nx * nx * 0.85 + ny * ny * 1.0)
    return np.clip(1 - 0.5 * np.clip(r - 0.45, 0, None) ** 1.6, 0, 1)[:, :, None].astype(np.float32)


# ----------------------------------------------------------------------------- post

@lru_cache(8)
def static_map(paper, vignette):
    """Paper texture x vignette multiplier, cached per setting."""
    m = np.ones((H, W, 1), np.float32)
    if paper:
        m *= 1 + (paper_tex() - 1) * paper
    if vignette:
        m *= 1 + (vignette_map() - 1) * vignette
    return m


def post(rgba, frame_idx, sat=1.0, tint=(1, 1, 1), lift=(0, 0, 0), gamma=1.0, glow=0.0,
         grain=0.035, vignette=1.0, paper=1.0, contrast=1.0, fade=0.0, fade_col=(0, 0, 0)):
    img = rgba[:, :, :3].astype(np.float32) * (1 / 255.0)
    if glow > 0:
        small = img.reshape(H // 4, 4, W // 4, 4, 3).mean((1, 3))
        lum = small.max(2, keepdims=True)
        bright = small * np.clip((lum - 0.62) / 0.38, 0, 1)
        bl = ndimage.gaussian_filter(bright, (9, 9, 0)) + 0.5 * ndimage.gaussian_filter(bright, (28, 28, 0))
        img = img + glow * np.repeat(np.repeat(bl, 4, 0), 4, 1)
    # saturation + tint (+ contrast) as one 3x3 color matrix
    lw = np.array([0.3, 0.59, 0.11], np.float32)
    Msat = np.outer(np.ones(3, np.float32), lw) * (1 - sat) + np.eye(3, dtype=np.float32) * sat
    Mx = (np.diag(np.array(tint, np.float32)) @ Msat) * contrast
    if not np.allclose(Mx, np.eye(3)):
        img = (img.reshape(-1, 3) @ Mx.T.astype(np.float32)).reshape(H, W, 3)
        if contrast != 1.0:
            img += 0.5 * (1 - contrast)
    # gamma + lift through a 1024-level per-channel lookup table
    if gamma != 1.0 or any(lift):
        idx = (np.clip(img, 0, 1) * 1023 + 0.5).astype(np.uint16)
        base = np.linspace(0, 1, 1024, dtype=np.float32) ** gamma
        out = np.empty_like(img)
        for ch in range(3):
            lut = base + lift[ch] * (1 - base)
            out[:, :, ch] = lut[idx[:, :, ch]]
        img = out
    else:
        img = np.clip(img, 0, 1)
    if paper or vignette:
        img *= static_map(round(float(paper), 3), round(float(vignette), 3))
    if grain > 0:
        tiles = grain_tiles()
        g = tiles[frame_idx % len(tiles)]
        g = np.roll(g, ((frame_idx * 397) % H, (frame_idx * 631) % W), (0, 1)).astype(np.float32)
        # grain is strongest in the midtones like real film
        l = img.mean(2)
        img = img + (grain * g * (0.35 + 2.6 * l * (1 - l)))[:, :, None]
    if fade > 0:
        img = img * (1 - fade) + np.array(fade_col, np.float32) * fade
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
