"""Motion helpers.

Walk: footstep-planned walking. Feet are planted at explicit positions and only
move during their swing phase, so a planted foot can never slide. The pelvis
travels between the midpoints of the feet with slow-in/slow-out at the start
and end of the walk. Everything is a pure function of time (no state), which
lets frames render in any order.

follow(): damped-spring follow-through computed by integrating a short history
window - also a pure function of time.
"""
import math
import numpy as np
from .core import clamp, lerp, smooth, ease_io, remap


class Walk:
    def __init__(self, t0, n_steps, step_len, step_dur, start_u=0.0, stance=14.0, bob=4.0, lift=14.0,
                 swing_frac=0.72, toe=0.45, first="n", squash=0.0):
        """Positions are in the character's local units along its facing direction.
        start_u: pelvis position at the start (feet straddle it by +-stance/2)."""
        self.t0, self.n, self.L, self.sd = t0, n_steps, step_len, step_dur
        self.bob, self.lift, self.swing_frac, self.toe, self.squash = bob, lift, swing_frac, toe, squash
        # footfall plan
        xn, xf = start_u + stance / 2, start_u - stance / 2
        if first == "f":
            xn, xf = start_u - stance / 2, start_u + stance / 2
        self.plan = []          # (t_lift, t_land, foot, x_from, x_to)
        pos = {"n": xn, "f": xf}
        foot = first
        for i in range(n_steps):
            other = "f" if foot == "n" else "n"
            if i == n_steps - 1:
                target = pos[other] + (stance if False else 0.0) + stance * 0.0 + 0.0
                target = pos[other] + stance * 0.6          # close up next to the other foot
            elif i == 0:
                target = pos[other] + step_len
            else:
                target = pos[other] + step_len
            ts = t0 + i * step_dur
            self.plan.append((ts, ts + step_dur * swing_frac, foot, pos[foot], target))
            pos[foot] = target
            foot = other
        self.final = dict(pos)
        self.start = {"n": xn, "f": xf}
        self.t1 = t0 + n_steps * step_dur

    def feet(self, t):
        res = {}
        for f in ("n", "f"):
            x, lift, toe = self.start[f], 0.0, 0.0
            for (ta, tb, foot, xa, xb) in self.plan:
                if foot != f:
                    continue
                if t >= tb:
                    x = xb
                elif t >= ta:
                    u = (t - ta) / (tb - ta)
                    x = lerp(xa, xb, ease_io(u, 2.0))
                    lift = self.lift * math.sin(math.pi * u) ** 0.9 * (0.6 + 0.4 * min(1.0, abs(xb - xa) / max(self.L, 1)))
                    toe = self.toe * math.sin(math.pi * min(1.0, u / 0.45)) if u < 0.45 else 0.0
                    break
                else:
                    break
            res[f] = (x, lift, toe)
        return res

    def pelvis(self, t):
        """Pelvis position (u), bob (y offset), progress info."""
        mids = [(self.t0, (self.start["n"] + self.start["f"]) / 2)]
        pos = dict(self.start)
        for (ta, tb, foot, xa, xb) in self.plan:
            pos[foot] = xb
            mids.append((ta + self.sd, (pos["n"] + pos["f"]) / 2))
        if t <= mids[0][0]:
            return mids[0][1], 0.0
        if t >= mids[-1][0]:
            return mids[-1][1], 0.0
        # piecewise-linear through midpoints with eased first and last segments
        for i in range(1, len(mids)):
            if t <= mids[i][0]:
                u = (t - mids[i - 1][0]) / (mids[i][0] - mids[i - 1][0])
                if i == 1:
                    u = u * u * (1.5 - 0.5 * u) if len(mids) > 2 else ease_io(u)
                elif i == len(mids) - 1:
                    u = 1 - (1 - u) ** 2 * (1.5 - 0.5 * (1 - u))
                x = lerp(mids[i - 1][1], mids[i][1], u)
                raw = (t - mids[i - 1][0]) / (mids[i][0] - mids[i - 1][0])
                bob = self.bob * math.cos(2 * math.pi * raw)
                return x, bob
        return mids[-1][1], 0.0

    def swing(self, t):
        f = self.feet(t)
        return clamp((f["n"][0] - f["f"][0]) / max(self.L, 1.0), -1, 1)

    def pose(self, t, s=1.0, face=1, origin_x=0.0, ground_y=0.0):
        """Returns pose fields (x, y, pelvis, feet, toes) for Figure.pose()."""
        pu, bob = self.pelvis(t)
        f = self.feet(t)
        active = self.t0 <= t <= self.t1
        b = bob if active else 0.0
        return dict(x=origin_x + face * s * pu, y=ground_y, face=face, s=s,
                    pelvis=(0.0, b), foot_n=(f["n"][0] - pu, f["n"][1]), foot_f=(f["f"][0] - pu, f["f"][1]),
                    toe_n=f["n"][2], toe_f=f["f"][2])


def arm_swing_fk(swing, amp=0.45, bend=0.25, side="n"):
    """FK arm angles for walking: arms swing opposite to the legs."""
    k = -swing if side == "n" else swing
    return ("fk", amp * k, bend + 0.15 * max(0.0, k))


def follow(fn, t, k=40.0, zeta=0.35, window=1.2, dt=1 / 120.0):
    """Damped spring y'' = k(x - y) - 2 zeta sqrt(k) y' driven by x = fn(t).
    Returns y(t) - x(t): the lag/overshoot to add to a secondary element."""
    n = int(window / dt)
    t0 = t - n * dt
    x = fn(t0)
    y, v = x, 0.0
    c = 2 * zeta * math.sqrt(k)
    for i in range(1, n + 1):
        x = fn(t0 + i * dt)
        a = k * (x - y) - c * v
        v += a * dt
        y += v * dt
    return y - x
