import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image
from lib.frame import new_surface, to_array
from lib.core import paint
from lib.ink import S
import importlib

name = sys.argv[1] if len(sys.argv) > 1 else "silas"
mod = importlib.import_module("rigs.silas" if name == "silas" else "rigs.cast")
cls = getattr(mod, name.capitalize())
surf = new_surface(1920, 1080)
c = surf.getCanvas()
c.clear(0xFFEDE4D2)
for row, act in enumerate((1, 2)):
    fig = cls(act)
    for i, turn in enumerate((0.0, 0.5, 1.0)):
        x = 260 + i * 330 + row * 990 * 0
        P = fig.pose(x=170 + i * 300 + (act - 1) * 960, y=1000, s=1.55, turn=turn, face=1)
        if name == "silas" and turn > 0.3:
            P.update(cane=("hand_n", -0.15, "front"), hand_n="grip", arm_n=(52, -205))
        fig.draw(c, P)
out = ROOT / "build" / f"test_{name}.png"
Image.fromarray(to_array(surf)[:, :, :3]).save(out)
print(out)
