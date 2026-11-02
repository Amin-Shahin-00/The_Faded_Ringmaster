"""Silas choreography shared between scenes.

THE BOW is defined once here. Scene 2 plays it at Act 1 timing (bouncy, overshoot,
humble head-down) and Scene 7 plays the SAME key poses at Act 3 timing (1.7x slower,
no overshoot, longer holds, eyes up on the audience) in the SAME framing (BOW_FRAME).
"""
import math
import numpy as np
from lib.core import Xf, keys, clamp, lerp, twos
from lib.motion import follow
from rigs.silas import Silas

# framing shared by Scene 2 "bow" and Scene 7 "bow_final"
BOW_FRAME = dict(x=900.0, y=1032.0, s=1.55, face=1, turn=0.3)
BOW_CAM = dict(x=960.0, y=690.0, zoom=2.25)


def _inv(xf):
    return Xf(np.linalg.inv(xf.m))


def bow_channels(u, act):
    """Key poses of the bow on a normalized Act-1 time axis u (seconds at Act 1 speed)."""
    over = act == 1
    lean = keys(u, [(0, 0.0), (0.6, -0.05), (1.6, -0.06), (2.3, 0.84, "back" if over else "io"), (3.3, 0.8),
                    (4.0, 0.0, "io"), (4.3, -0.03), (4.6, 0.0)])
    chest = keys(u, [(0, 0.0), (1.6, 0.0), (2.3, 0.2), (3.3, 0.2), (4.0, 0.0)])
    pel_y = keys(u, [(0, 0.0), (0.6, -4.0 if over else -1.0), (1.0, 0.0), (2.3, 7.0), (3.3, 7.0), (4.0, 0.0)])
    far = keys(u, [(0, (-0.45, 0.35)), (1.6, (-0.85, 0.25)), (2.3, (-1.25, 0.2)), (3.3, (-1.25, 0.2)), (4.4, (-0.45, 0.35))])
    head_rot = keys(u, [(0, 0.0), (1.6, -0.05), (2.3, 0.12 if act == 1 else -0.5), (3.3, 0.12 if act == 1 else -0.5), (4.0, 0.0)])
    return lean, chest, pel_y, far, head_rot


def bow_pose(fig, u, act, extra=None):
    """Full pose for the bow at Act-1 time u. Hat grab/release are continuous: the
    hat's offset in the hand is measured from the real head position at grab time."""
    lean, chest, pel_y, far, head_rot = bow_channels(u, act)
    base = dict(BOW_FRAME)
    base.update(lean=lean, chest=chest, pelvis=(-22.0 * max(lean, 0.0), pel_y), foot_n=(26.0, 0.0), foot_f=(-16.0, 0.0),
                arm_f=("fk", far[0], far[1]), hand_f="grip", cane=("hand_f", 0.25, "front"), head_rot=head_rot)
    if act == 1:
        base.update(smile=0.85, open=keys(u, [(1.4, 0.0), (1.8, 0.35), (2.4, 0.0)]), crow=1.0)
    else:
        base.update(smile=0.3, cold=1.0, narrow=0.25, brow=-0.3)
    if extra:
        base.update(extra)
    brim = brim_point(fig, act)
    hand = keys(u, [(0, (96.0, -296.0)), (0.55, (96.0, -300.0)), (1.0, brim), (1.45, (78.0, -478.0) if act == 1 else (70.0, -455.0)),
                    (1.65, (72.0, -468.0) if act == 1 else (70.0, -455.0)), (2.3, (150.0, -248.0)), (3.3, (150.0, -248.0)),
                    (4.0, brim), (4.6, (96.0, -300.0))])
    base.update(arm_n=tuple(hand), hand_n="pinch" if 1.0 <= u <= 4.0 else "open", wrist_n=keys(u, [(1.0, 0.0), (1.6, -0.6), (2.3, 0.5), (3.3, 0.5), (4.0, 0.0)]))
    P = fig.pose(**base)
    # tails follow-through driven by the lean
    P["tail_swing"] = -follow(lambda tt: bow_channels(tt, act)[0], u, k=55, zeta=0.32) * 0.9
    P["tail_flare"] = 0.75 * clamp(lean / 0.8)
    # hat: on head -> hand (1.0 .. 4.0) -> head
    if 1.0 <= u <= 4.0:
        off = hat_offset(fig, act)
        J = fig.solve(P); fig.P = P
        M = fig.root_xf(P)
        hx = fig.hand_xf(J, M, "n") @ off
        P["hat"] = ("hand_n", None)
        P["hat_xf"] = hx
    return P


_cache = {}


def _pose_at(fig, u, act):
    lean, chest, pel_y, far, head_rot = bow_channels(u, act)
    base = dict(BOW_FRAME)
    base.update(lean=lean, chest=chest, pelvis=(-22.0 * max(lean, 0.0), pel_y), foot_n=(26.0, 0.0), foot_f=(-16.0, 0.0), head_rot=head_rot,
                arm_f=("fk", far[0], far[1]))
    return fig.pose(**base)


def brim_point(fig, act):
    key = ("brim", act)
    if key not in _cache:
        P = _pose_at(fig, 1.0, act)
        fig.P = P
        J = fig.solve(P)
        M = fig.root_xf(P)
        hat = fig.hat_xf_head(J, M)
        # front-right edge of the brim, back in root-local units
        w = hat(np.array([33.0, 3.0]))
        loc = _inv(M)(w)
        _cache[key] = (float(loc[0]) - 14.0, float(loc[1]) + 4.0)
    return _cache[key]


def hat_offset(fig, act):
    key = ("off", act)
    if key not in _cache:
        P = _pose_at(fig, 1.0, act)
        P.update(arm_n=brim_point(fig, act), hand_n="pinch", wrist_n=0.0)
        fig.P = P
        J = fig.solve(P)
        M = fig.root_xf(P)
        _cache[key] = _inv(fig.hand_xf(J, M, "n")) @ fig.hat_xf_head(J, M)
    return _cache[key]


def breathing(t, rate=0.25):
    return math.sin(math.tau * rate * t)


def blink_at(t, times, dur=0.16):
    for b in times:
        if b <= t < b + dur:
            return 1.0 - abs((t - b) / dur * 2 - 1)
    return 0.0


def auto_blinks(t, seed=0, every=3.4):
    """Natural blinks every ~3.4 s with jitter. Returns 0..1."""
    k = math.floor(t / every)
    for kk in (k - 1, k):
        off = ((kk * 7919 + seed * 104729) % 1000) / 1000.0
        b = kk * every + off * (every - 0.4)
        if b <= t < b + 0.18:
            return 1.0 - abs((t - b) / 0.18 * 2 - 1)
    return 0.0
