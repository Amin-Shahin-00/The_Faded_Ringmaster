"""CROWD - simple stylized silhouettes and faces.

Each person is a seeded random record (size, colors, hat, kid/adult); drawing is
cheap (no boil on tiny figures) so hundreds fit in a frame. Moods:
  cheer  - bouncing, clapping, laughing mouths (Act 1)
  idle   - small breathing and head turns
  still  - circus owners in the finale: rigid, tiny breathing, eye glints only
"""
import math
import numpy as np
import skia
from lib.core import paint, mix, hexc, rng, clamp, twos
from lib.ink import S, ink_line, ellipse, spline, path_of, fill, shape

CROWD_COLS = {
    1: ["#c8443a", "#e0a03a", "#3a6ab0", "#6a9a4a", "#9a4a8a", "#e0c08a", "#4a8a9a", "#b06a3a", "#d06a7a", "#5a5a8a"],
    2: ["#6e4a44", "#8a7a5a", "#4d5a6a", "#5a6a4a", "#6a4a5a", "#8a8070", "#4a6066", "#7a5a44", "#7a5a5e", "#4e4e5e"],
    3: ["#2a2a30", "#33302e", "#262e33", "#2e332c", "#302a30", "#3a3632", "#242c2e", "#34302c", "#2e2a2c", "#28282e"],
}
SKINS = ["#f0c49a", "#e1a97c", "#c98f6a", "#a8704e", "#f3d2b5", "#8a5a3e"]


def make_people(seed, n, kid_ratio=0.25):
    r = rng(seed)
    P = []
    for i in range(n):
        P.append(dict(
            col=int(r.integers(0, 10)), skin=int(r.integers(0, len(SKINS))), hat=int(r.integers(0, 6)),
            kid=r.random() < kid_ratio, ph=r.random() * 10, sz=0.9 + 0.2 * r.random(), hair=int(r.integers(0, 4)),
            present=r.random(), lean=(r.random() - 0.5) * 0.15, look=(r.random() - 0.5)))
    return P


def person(c, x, y, size, p, t, mood="cheer", act=1, light=1.0, face=True, back=False):
    """Draw one seated audience member. (x, y) = seat point; size = head radius px."""
    tq = twos(t)
    k = 0.72 if p["kid"] else 1.0
    s = size * p["sz"] * k
    col = CROWD_COLS[act][p["col"]]
    skin = SKINS[p["skin"]]
    if act == 3:
        skin = mix(skin, "#2a3236", 0.72)
    elif act == 2:
        skin = mix(skin, "#8a8a88", 0.45)
    bob = 0.0
    clap = 0.0
    laugh = 0.0
    if mood == "cheer":
        f = 2.2 + (p["ph"] % 1.0) * 1.2
        bob = abs(math.sin(math.tau * f * tq * 0.5 + p["ph"])) * s * 0.35
        clap = 0.5 + 0.5 * math.sin(math.tau * f * tq + p["ph"] * 3)
        laugh = 0.5 + 0.5 * math.sin(math.tau * 1.7 * tq + p["ph"])
    elif mood == "idle":
        bob = math.sin(math.tau * 0.3 * tq + p["ph"]) * s * 0.05
    elif mood == "still":
        bob = math.sin(math.tau * 0.22 * tq + p["ph"]) * s * 0.03
    lean = p["lean"]
    hx = x + lean * s * 2
    hy = y - s * 2.6 - bob
    dark = mix(col, "#000000", 0.35)
    # body: rounded shoulders
    body = np.array([(x - s * 1.55, y + s * 0.4), (x - s * 1.4, y - s * 1.2 - bob * 0.6), (x - s * 0.6, y - s * 1.75 - bob),
                     (x + s * 0.6, y - s * 1.75 - bob), (x + s * 1.4, y - s * 1.2 - bob * 0.6), (x + s * 1.55, y + s * 0.4)])
    c.drawPath(path_of(spline(body, closed=True, n=3)), paint(col))
    lw = max(0.8, s * 0.12)
    # clapping arms (cheer) - hands meet above the lap or overhead
    if mood == "cheer" and clap > 0.0:
        up = (p["ph"] % 1.0) > 0.6
        for sd in (-1, 1):
            sx, sy = x + sd * s * 1.2, y - s * 1.3 - bob
            if up:
                hx2, hy2 = x + sd * s * (0.35 + 0.5 * clap), y - s * 4.2 - bob
            else:
                hx2, hy2 = x + sd * s * (0.25 + 0.55 * clap), y - s * 0.9 - bob
            c.drawLine(sx, sy, hx2, hy2, paint(dark, stroke=s * 0.55))
            c.drawCircle(hx2, hy2, s * 0.32, paint(skin))
    # head
    c.drawCircle(hx, hy, s, paint(skin))
    # hair / hats
    hc = ["#2a1a14", "#5a3a20", "#b08040", "#1a1a1a"][p["hair"]]
    if act == 3:
        hc = "#141618"
    if p["hat"] == 1 and not p["kid"]:   # bowler
        c.drawPath(path_of(ellipse(hx, hy - s * 0.55, s * 1.25, s * 0.25, 14)), paint("#1e1a1a"))
        c.drawPath(path_of(ellipse(hx, hy - s * 0.85, s * 0.8, s * 0.65, 14, math.pi, 2 * math.pi)), paint("#1e1a1a"))
    elif p["hat"] == 2 and not p["kid"]:  # top hat (finale owners mostly)
        c.drawRect(skia.Rect.MakeLTRB(hx - s * 0.75, hy - s * 2.3, hx + s * 0.75, hy - s * 0.6), paint("#16141a"))
        c.drawPath(path_of(ellipse(hx, hy - s * 0.6, s * 1.25, s * 0.22, 14)), paint("#16141a"))
    elif p["hat"] == 3 and p["kid"]:     # kid cap
        c.drawPath(path_of(ellipse(hx, hy - s * 0.35, s * 1.0, s * 0.8, 14, math.pi, 2 * math.pi)), paint(CROWD_COLS[act][(p["col"] + 3) % 10]))
    else:
        c.drawPath(path_of(ellipse(hx, hy - s * 0.25, s * 1.02, s * 0.85, 14, math.pi * 1.05, 1.95 * math.pi)), paint(hc))
    if back:
        return
    # face: dot eyes + mouth
    if face and s > 5:
        ex = hx + p["look"] * s * 0.3
        blink = ((t * 0.37 + p["ph"]) % 4.0) < 0.12
        ec = "#1a1210" if act != 3 else "#0a0a0a"
        if not blink:
            c.drawCircle(ex - s * 0.33, hy - s * 0.05, max(0.6, s * 0.11), paint(ec))
            c.drawCircle(ex + s * 0.33, hy - s * 0.05, max(0.6, s * 0.11), paint(ec))
        else:
            c.drawLine(ex - s * 0.45, hy - s * 0.05, ex - s * 0.2, hy - s * 0.05, paint(ec, stroke=max(0.6, s * 0.08)))
            c.drawLine(ex + s * 0.2, hy - s * 0.05, ex + s * 0.45, hy - s * 0.05, paint(ec, stroke=max(0.6, s * 0.08)))
        if mood == "cheer":
            mo = 0.2 + 0.5 * laugh
            c.drawPath(path_of(ellipse(ex, hy + s * 0.42, s * 0.36, s * 0.3 * mo + 0.4, 10, 0, math.pi)), paint("#5a1a1a"))
        elif mood == "still":
            c.drawLine(ex - s * 0.25, hy + s * 0.45, ex + s * 0.25, hy + s * 0.45, paint(ec, stroke=max(0.5, s * 0.07)))
        else:
            c.drawLine(ex - s * 0.25, hy + s * 0.42, ex + s * 0.25, hy + s * 0.45, paint(ec, stroke=max(0.5, s * 0.07)))
    if light < 1.0:
        pass


def back_of_head(c, x, y, s, p, t, act=1, mood="cheer", col_override=None):
    """Foreground audience seen from behind (silhouettes along the bottom of frame)."""
    tq = twos(t)
    col = col_override or mix(CROWD_COLS[act][p["col"]], "#0a0608", 0.55)
    bob = 0.0
    arm = 0.0
    if mood == "cheer":
        f = 2.0 + (p["ph"] % 1.0)
        bob = abs(math.sin(math.tau * f * tq * 0.5 + p["ph"])) * s * 0.25
        arm = 0.5 + 0.5 * math.sin(math.tau * f * tq + p["ph"] * 2)
    else:
        bob = math.sin(math.tau * 0.25 * tq + p["ph"]) * s * 0.03
    k = 0.75 if p["kid"] else 1.0
    s = s * k
    body = np.array([(x - s * 1.8, y + s * 2), (x - s * 1.6, y - s * 0.6 - bob), (x - s * 0.7, y - s * 1.3 - bob),
                     (x + s * 0.7, y - s * 1.3 - bob), (x + s * 1.6, y - s * 0.6 - bob), (x + s * 1.8, y + s * 2)])
    c.drawPath(path_of(spline(body, closed=True, n=3)), paint(col))
    c.drawCircle(x, y - s * 2.0 - bob, s, paint(col))
    if p["hat"] == 1 and not p["kid"]:
        c.drawPath(path_of(ellipse(x, y - s * 2.6 - bob, s * 1.25, s * 0.25, 14)), paint(col))
        c.drawPath(path_of(ellipse(x, y - s * 2.9 - bob, s * 0.8, s * 0.65, 14, math.pi, 2 * math.pi)), paint(col))
    if p["hat"] == 2 and not p["kid"]:
        c.drawRect(skia.Rect.MakeLTRB(x - s * 0.72, y - s * 4.2 - bob, x + s * 0.72, y - s * 2.6 - bob), paint(col))
        c.drawPath(path_of(ellipse(x, y - s * 2.65 - bob, s * 1.2, s * 0.22, 14)), paint(col))
    if mood == "cheer" and (p["ph"] % 1.0) > 0.45:
        for sd in (-1, 1):
            sx, sy = x + sd * s * 1.3, y - s * 0.8 - bob
            hx, hy = x + sd * s * (0.7 + 0.8 * arm), y - s * (3.6 + 0.8 * arm) - bob
            c.drawLine(sx, sy, hx, hy, paint(col, stroke=s * 0.6))
            c.drawCircle(hx, hy, s * 0.36, paint(col))
