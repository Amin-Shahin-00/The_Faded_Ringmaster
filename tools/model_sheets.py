"""Render character model sheets -> model_sheets/*.png

Each sheet: front / three-quarter / side views per act, color palette chips per act,
expressions and props. Every shot in the film is drawn by the same rig code, so
the sheet IS the reference the shots are built from.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image
from lib.frame import new_surface, to_array, text
from lib.core import paint, hexc, Xf
from lib.ink import S, ellipse, shape, ink_line
from rigs.silas import Silas
from rigs.cast import Bruno, Lena, Pip
from config.palettes import SILAS, BRUNO, LENA, PIP

OUT = ROOT / "model_sheets"
SW, SH = 2560, 1900
PAPER = 0xFFEFE7D6


def header(c, title, sub):
    text(c, title, 60, 92, "rye", 64, "#2a1a14", align="left")
    text(c, sub, 64, 138, "oldstd", 28, "#4a3a30", align="left")
    c.drawRect(skia_rect(40, 160, SW - 40, 163), paint("#2a1a14", 0.6))


def skia_rect(a, b, c_, d):
    import skia
    return skia.Rect.MakeLTRB(a, b, c_, d)


def chips(c, x, y, pal, label, keys):
    text(c, label, x, y - 14, "oldstd_b", 24, "#2a1a14", align="left")
    for i, k in enumerate(keys):
        cx = x + (i % 6) * 120
        cy = y + (i // 6) * 92
        c.drawRect(skia_rect(cx, cy, cx + 100, cy + 50), paint(pal[k]))
        c.drawRect(skia_rect(cx, cy, cx + 100, cy + 50), paint("#2a1a14", stroke=2))
        text(c, k, cx + 50, cy + 70, "oldstd", 17, "#2a1a14")
        text(c, pal[k].upper(), cx + 50, cy + 87, "oldstd", 14, "#5a4a40")


def views(c, fig, x0, ground, scale, label, extra=None, dx=330):
    text(c, label, x0 - 20, ground - fig_height(fig) * scale - 40, "oldstd_b", 30, "#2a1a14", align="left")
    for i, (turn, name) in enumerate(((0.0, "FRONT"), (0.5, "3/4"), (1.0, "SIDE"))):
        P = fig.pose(x=x0 + 110 + i * dx, y=ground, s=scale, turn=turn, face=1, blink=0.0, look=(0.3 * turn, 0))
        if extra:
            extra(P, turn)
        fig.draw(c, P)
        text(c, name, x0 + 110 + i * dx, ground + 44, "oldstd", 22, "#4a3a30")
    c.drawRect(skia_rect(x0 - 30, ground + 2, x0 + 3 * dx, ground + 4), paint("#2a1a14", 0.35))


def fig_height(fig):
    return {Silas: 545, Bruno: 470, Lena: 410, Pip: 300}[type(fig)]


def save(surf, name):
    OUT.mkdir(exist_ok=True)
    Image.fromarray(to_array(surf)[:, :, :3]).save(OUT / name)
    print(OUT / name)


def silas_sheet():
    surf = new_surface(SW, SH); c = surf.getCanvas(); c.clear(PAPER)
    S.boil = 0
    header(c, "SILAS MARLOWE  -  model sheet", "Ringmaster, ~45. Tall, thin, long face, sharp nose, thin curled mustache. "
           "6 gold buttons (2 x 3). Cane: black shaft, silver ball handle.")
    def act1(P, turn):
        if turn > 0.3:
            P.update(cane=("hand_n", -0.12, "front"), hand_n="grip", arm_n=(48, -205))
    def act3(P, turn):
        if turn > 0.3:
            P.update(handle=("hand_n", 0.0), hand_n="grip", arm_n=(40, -215), wrist_n=-1.2)
    views(c, Silas(1), 80, 880, 1.15, "ACT 1  -  bright, warm, open", act1)
    views(c, Silas(3), 80, 1780, 1.15, "ACT 2 / 3  -  same coat faded; torn tail, cracked band, LEFT glove missing", act3)
    # expressions
    x = 1180
    text(c, "EXPRESSIONS", x, 230, "oldstd_b", 28, "#2a1a14", align="left")
    exprs = [(1, dict(smile=0.8, open=0.0), "warm smile"), (1, dict(smile=1.0, open=0.85, narrow=0.5), "real laugh (Act 1)"),
             (2, dict(smile=0.0, cold=0.0, brim_shadow=0.0, hat_drop=0), "tired (Act 2)"),
             (3, dict(smile=0.35, cold=1.0, narrow=0.35, brow=-0.4), "cold smile (Act 3)")]
    for i, (act, kw, name) in enumerate(exprs):
        f = Silas(act)
        P = f.pose(x=x + 130 + i * 300, y=1100, s=1.75, turn=0.35, look=(0.3, 0))
        P.update(kw)
        c.save(); c.clipRect(skia_rect(x + i * 300, 250, x + i * 300 + 260, 560))
        f.draw(c, P)
        c.restore()
        text(c, name, x + 130 + i * 300, 590, "oldstd", 22, "#4a3a30")
    # props
    text(c, "PROPS", x, 660, "oldstd_b", 28, "#2a1a14", align="left")
    f = Silas(1)
    f.P = f.pose(); f._scale = 1.3
    f.draw_cane(c, None, None, X=Xf.T(x + 80, 760).s(1.3))
    text(c, "cane (Act 1-2)", x + 80, 1110, "oldstd", 20, "#4a3a30")
    f3 = Silas(3); f3.P = f3.pose(hand_n="grip"); f3._scale = 1.6
    f3.draw_ball(c, Xf.T(x + 300, 820).s(1.6))
    from lib.ink import shape as shp
    stub = np.array([(-3.4, -8), (3.4, -8), (3.2, 30), (1.0, 34), (-0.6, 29), (-2.2, 36), (-3.4, 31)])
    shp(c, Xf.T(x + 300, 820).s(1.6)(stub), f3.C["cane"], 2.5, seed=510)
    text(c, "silver handle (Act 3)", x + 300, 960, "oldstd", 20, "#4a3a30")
    fh = Silas(1); fh.P = fh.pose(); fh._scale = 1.3
    fh.draw_hat(c, None, None, X=Xf.T(x + 560, 930).s(1.3))
    text(c, "hat Act 1", x + 560, 990, "oldstd", 20, "#4a3a30")
    fh2 = Silas(3); fh2.P = fh2.pose(); fh2._scale = 1.3
    fh2.draw_hat(c, None, None, X=Xf.T(x + 760, 930).s(1.3))
    text(c, "hat Act 2-3 (cracked band, dent)", x + 780, 990, "oldstd", 20, "#4a3a30")
    from scenes.common import draw_ticket
    draw_ticket(c, x + 1080, 830, 1.3, 0.0)
    text(c, "ticket", x + 1080, 990, "oldstd", 20, "#4a3a30")
    keys = ["coat", "coat_shade", "trim", "button", "lining", "hat", "band", "glove", "skin", "breeches", "boot", "silver"]
    chips(c, x, 1250, SILAS[1], "ACT 1 palette", keys)
    chips(c, x + 0, 1530, SILAS[3], "ACT 3 palette (Act 2 is between; lining stays saturated in the finale)", keys)
    save(surf, "silas_model_sheet.png")


def cast_sheet(cls, pals, name, desc, keys, scale):
    surf = new_surface(SW, SH); c = surf.getCanvas(); c.clear(PAPER)
    S.boil = 0
    header(c, f"{name}  -  model sheet", desc)
    views(c, cls(1), 80, 880, scale, "ACT 1  (Scene 2)")
    views(c, cls(3), 80, 1780, scale, "ACT 2 / 3  (Scenes 3, 5-7)")
    x = 1300
    for i, act in enumerate((1, 2, 3)):
        chips(c, x, 300 + i * 280, pals[act], f"ACT {act} palette", keys)
    # expression heads
    text(c, "EXPRESSIONS", x, 1180, "oldstd_b", 28, "#2a1a14", align="left")
    for i, (kw, lab) in enumerate(((dict(smile=0.6), "happy"), (dict(smile=-0.2, brow=0.3), "worried"), (dict(smile=0.0, narrow=0.3), "neutral"))):
        f = cls(1 if i == 0 else 3)
        P = f.pose(x=x + 150 + i * 330, y=1260 + fig_height(f) * scale * 1.4, s=scale * 1.4, turn=0.3)
        P.update(kw)
        c.save(); c.clipRect(skia_rect(x + i * 330, 1200, x + i * 330 + 300, 1500))
        f.draw(c, P)
        c.restore()
        text(c, lab, x + 150 + i * 330, 1540, "oldstd", 22, "#4a3a30")
    save(surf, f"{name.lower()}_model_sheet.png")


def lineup():
    """All four side by side at true relative scale (Act 3)."""
    surf = new_surface(SW, 1100); c = surf.getCanvas(); c.clear(PAPER)
    header(c, "CAST LINE-UP  -  relative heights", "Act 3 palettes. Silas 440 (+hat), Bruno 470, Lena 410, Pip 300 units.")
    for i in range(0, 7):
        y = 1000 - i * 100
        c.drawRect(skia_rect(60, y, SW - 60, y + 1), paint("#2a1a14", 0.2))
    figs = [(Silas(3), 0.3), (Bruno(3), 0.4), (Lena(3), 0.35), (Pip(3), 0.4)]
    for i, (f, turn) in enumerate(figs):
        P = f.pose(x=420 + i * 560, y=1000, s=1.45, turn=turn)
        f.draw(c, P)
    save(surf, "cast_lineup.png")


if __name__ == "__main__":
    silas_sheet()
    cast_sheet(Bruno, BRUNO, "BRUNO", "The strongman. Huge shoulders, bald, gentle eyes, striped one-piece suit, wide belt, bare arms.",
               ["suit_a", "suit_b", "skin", "skin_shade", "boot", "belt"], 1.15)
    cast_sheet(Lena, LENA, "LENA", "The knife thrower. Short black bob, long dark coat, calm and silent, quick hands.",
               ["coat", "coat_shade", "trim", "hair", "skin", "lip"], 1.25)
    cast_sheet(Pip, PIP, "PIP", "The clown. Small and wiry, faded makeup, drooping painted smile that does not match his real face.",
               ["suit", "suit_shade", "patch", "patch2", "paint", "paint_mouth", "nose", "hair", "shoe", "collar"], 1.6)
    lineup()
