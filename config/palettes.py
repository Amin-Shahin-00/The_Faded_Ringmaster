"""Color script. Change colors here; every rig, model sheet and scene reads them.

ACT 1  (Scene 2)        warm reds, golds, cream - high saturation, soft glow
ACT 2  (Scenes 1, 3, 4) dusty brick red, olive, gray-blue - low saturation, cold light
ACT 3  (Scenes 5-7)     deep shadow, dark teal, black, faded red, hard rim light.
                        Only the coat lining stays fully saturated red.
"""

INK = "#1b1412"          # line color (warm near-black ink)

SILAS = {
    1: dict(coat="#c8202a", coat_shade="#8e1220", trim="#e8b23a", button="#f4c84a",
            lining="#a3101e", hat="#1d1a1c", hat_shade="#0c0a0b", band="#c8202a",
            glove="#fbf6ea", skin="#f0c49a", skin_shade="#c98f6a", breeches="#efe3c8",
            breeches_shade="#c9b994", boot="#1a1416", mustache="#2a1a14", cane="#151214",
            silver="#e8ecf0", eye="#20140f"),
    2: dict(coat="#8a4a3e", coat_shade="#5e3029", trim="#9b8657", button="#8d7a52",
            lining="#6e2a26", hat="#232022", hat_shade="#121011", band="#7c4038",
            glove="#d6d0c2", skin="#c9a88e", skin_shade="#957661", breeches="#b9b09c",
            breeches_shade="#8e8676", boot="#1e1a1b", mustache="#2b221e", cane="#1a1718",
            silver="#b9bec2", eye="#1b1512"),
    3: dict(coat="#7a4038", coat_shade="#45231f", trim="#86754f", button="#7b6c4b",
            lining="#e3132b",   # <- the one fully saturated color in the finale
            hat="#18181a", hat_shade="#0a0a0b", band="#6e3832",
            glove="#c9c6bc", skin="#b39a88", skin_shade="#7c675a", breeches="#a29b8b",
            breeches_shade="#6f695e", boot="#151314", mustache="#221c19", cane="#141314",
            silver="#c4ccd2", eye="#15110f"),
}
SILAS_MAKEUP = dict(base="#f3e6dc", cheek="#d9697a", liner="#2a1a20")   # stage makeup (Scene 4)

BRUNO = {
    1: dict(suit_a="#c8202a", suit_b="#f5ead0", skin="#e1a97c", skin_shade="#b47852",
            boot="#3a2418", belt="#e8b23a", eye="#2a1a12", brow="#5a3a26"),
    2: dict(suit_a="#7d4a40", suit_b="#b7ad98", skin="#b9937a", skin_shade="#8a6a56",
            boot="#2c2220", belt="#8d7a52", eye="#221713", brow="#4a3a30"),
    3: dict(suit_a="#4c3a38", suit_b="#8c8a80", skin="#9f8a7c", skin_shade="#655449",
            boot="#1c1818", belt="#6b604a", eye="#1a1412", brow="#3a302a"),
}
LENA = {
    1: dict(coat="#2a2236", coat_shade="#17121f", trim="#e8b23a", hair="#121014",
            skin="#f2cfb2", skin_shade="#c8987a", boot="#151214", shirt="#c8202a",
            knife="#e8ecf0", eye="#18120f", lip="#b23a48"),
    2: dict(coat="#2b2a30", coat_shade="#18171c", trim="#8d7a52", hair="#141315",
            skin="#cdb4a2", skin_shade="#9a8273", boot="#18161a", shirt="#7d4a40",
            knife="#b9bec2", eye="#16120f", lip="#8a4a50"),
    3: dict(coat="#1f2427", coat_shade="#0f1315", trim="#6b604a", hair="#0e0e10",
            skin="#a9988c", skin_shade="#6c5f57", boot="#121214", shirt="#5e3430",
            knife="#c4ccd2", eye="#121010", lip="#7a4248"),
}
PIP = {
    1: dict(suit="#2f6fbf", suit_shade="#1f4c86", patch="#f2c14a", patch2="#c8202a",
            paint="#fbf6ea", paint_mouth="#d7262f", nose="#e02a2a", hair="#f08a24", skin_shade="#c98f6a",
            skin="#f0c49a", shoe="#c8202a", collar="#f5ead0", eye="#20140f"),
    2: dict(suit="#4d5a6a", suit_shade="#343e4a", patch="#a69563", patch2="#7d4a40",
            paint="#d8d2c4", paint_mouth="#9a4a48", nose="#9a4442", hair="#a0704a", skin_shade="#957661",
            skin="#c9a88e", shoe="#6e3a34", collar="#b7ad98", eye="#1b1512"),
    3: dict(suit="#38424c", suit_shade="#232a31", patch="#7c7356", patch2="#5e3430",
            paint="#bfbab0", paint_mouth="#874240", nose="#7e3a38", hair="#7c5a40", skin_shade="#7c675a",
            skin="#a9988c", shoe="#4e2e2a", collar="#8c8a80", eye="#15110f"),
}

# Scene-level grade targets (applied in post): saturation, warmth tint, lift.
GRADE = {
    1: dict(sat=1.12, tint=(1.05, 1.0, 0.90), lift=(0.02, 0.012, 0.0), gamma=0.98, glow=0.35),
    2: dict(sat=0.62, tint=(0.94, 0.98, 1.04), lift=(0.01, 0.015, 0.025), gamma=1.04, glow=0.12),
    3: dict(sat=0.78, tint=(0.88, 1.0, 1.04), lift=(0.0, 0.012, 0.016), gamma=1.08, glow=0.15),
}

# Environment colors per act
ENV = {
    1: dict(tent_a="#d42a2e", tent_b="#f6e7c4", pole="#7a4a2a", sky="#2a1630", ring="#c8202a",
            ring_floor="#d9a066", seat="#7a3a24", spot="#fff1c4", bunting=["#e8b23a", "#c8202a", "#2f6fbf"]),
    2: dict(tent_a="#7e4c44", tent_b="#a9a593", pole="#4c4038", sky="#1e2630", ring="#6e3c36",
            ring_floor="#6f6656", seat="#3e3430", spot="#c8d2d6", bunting=["#8d7a52", "#7d4a40", "#4d5a6a"]),
    3: dict(tent_a="#4a2e2c", tent_b="#3d4a4c", pole="#22292b", sky="#0b1517", ring="#5a2e2a",
            ring_floor="#2c3433", seat="#1a2224", spot="#e8f0f0", bunting=["#6b604a", "#5e3430", "#2f4446"]),
}
