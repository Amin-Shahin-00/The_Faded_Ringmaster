"""THE FADED RINGMASTER - master timeline.

Every timing in the film lives here: scene boundaries, shot boundaries, voiceover
chunk start times and sound-effect cue times. Scenes read their shot windows from
SHOTS, the audio mixer reads VO and SFX, and tools/check_timeline.py validates
that every VO chunk starts and ends inside its scene.

All times are in seconds from the start of the film.
"""
FPS = 24
W, H = 1920, 1080

# --------------------------------------------------------------------------
# Scenes  (id, start, end, act)
# --------------------------------------------------------------------------
SCENES = [
    ("s1", 0.0, 18.0, 2),     # cold open (present day, Act 2 palette)
    ("s2", 18.0, 48.0, 1),    # golden days flashback
    ("s3", 48.0, 78.0, 2),    # the fall (drains from Act 1 to Act 2 palette)
    ("s4", 78.0, 105.0, 2),   # the change
    ("s5", 105.0, 140.0, 3),  # the recruitment
    ("s6", 140.0, 170.0, 3),  # the rise
    ("s7", 170.0, 191.0, 3),  # the finale + title card (title 185-190, black tail)
]
DURATION = 191.0

# --------------------------------------------------------------------------
# Shots (scene, shot id, start, end). Scene modules dispatch on these.
# --------------------------------------------------------------------------
SHOTS = [
    ("s1", "ext_tent",     0.0,  7.5),
    ("s1", "ring_alone",   7.5, 18.0),
    ("s2", "wide_full",   18.0, 24.5),
    ("s2", "bow",         24.5, 29.5),
    ("s2", "bruno",       29.5, 33.5),
    ("s2", "lena",        33.5, 38.0),
    ("s2", "pip",         38.0, 42.5),
    ("s2", "peanut",      42.5, 46.5),
    ("s2", "wide_cheer",  46.5, 48.0),
    ("s3", "nights",      48.0, 56.0),
    ("s3", "poster",      56.0, 61.0),
    ("s3", "notice",      61.0, 65.0),
    ("s3", "leaving",     65.0, 71.0),
    ("s3", "storm",       71.0, 78.0),
    ("s4", "trailer",     78.0, 83.0),
    ("s4", "wipe",        83.0, 89.0),
    ("s4", "coat",        89.0, 95.0),
    ("s4", "cane",        95.0, 99.5),
    ("s4", "smile",       99.5, 105.0),
    ("s5", "docks",      105.0, 114.0),
    ("s5", "bar",        114.0, 122.5),
    ("s5", "corner",     122.5, 131.0),
    ("s5", "walk",       131.0, 140.0),
    ("s6", "table",      140.0, 144.286),     # montage cuts on beats of the 84 BPM theme
    ("s6", "lowangle",   144.286, 148.571),
    ("s6", "paint",      148.571, 157.143),
    ("s6", "papers",     157.143, 163.571),
    ("s6", "map",        163.571, 170.0),
    ("s7", "wide_final", 170.0, 175.0),
    ("s7", "bow_final",  175.0, 184.0),
    ("s7", "title",      184.0, 191.0),
]

# Transitions at shot boundaries: (cut time, duration, kind). Kinds:
#   "dissolve" - cross-dissolve centred on the cut
#   "black"    - dip to black (fade out, fade in)
# Any boundary not listed is a straight cut (used for beat cuts in the montage).
TRANSITIONS = [
    (7.5, 1.4, "dissolve"),     # exterior -> interior push
    (18.0, 1.6, "dissolve"),    # cold open -> golden flashback (warm bloom)
    (24.5, 0.5, "dissolve"),
    (48.0, 0.8, "dissolve"),    # SAME ANGLE: full house -> the fall
    (56.0, 0.6, "dissolve"),
    (65.0, 0.6, "dissolve"),
    (71.0, 0.6, "dissolve"),
    (78.0, 1.6, "black"),       # storm -> trailer
    (83.0, 0.5, "dissolve"),
    (105.0, 1.4, "black"),      # laugh -> recruitment
    (114.0, 0.8, "dissolve"),
    (122.5, 0.8, "dissolve"),
    (131.0, 1.0, "dissolve"),
    (170.0, 1.4, "dissolve"),   # montage -> finale
    (175.0, 0.8, "dissolve"),
]

# --------------------------------------------------------------------------
# Voiceover. Each line of the script is split at "..." and at sentence breaks
# so each chunk can be placed by hand; the pauses come from the gaps.
# (scene, chunk id, start time, text)
# --------------------------------------------------------------------------
VO = [
    ("s1", "s1a",   1.6, "They used to call me the happiest man alive."),
    ("s1", "s1b",   7.9, "Funny thing about happiness..."),
    ("s1", "s1c",  11.4, "it never sends a warning before it leaves."),

    ("s2", "s2a",  19.4, "Marlowe's Marvelous Circus."),
    ("s2", "s2b",  23.2, "Every night, a full house."),
    ("s2", "s2c",  27.4, "Every night, I was the king of a little world made of canvas and light."),

    ("s3", "s3a",  49.2, "Then the crowds moved on."),
    ("s3", "s3b",  61.4, "The bank came."),
    ("s3", "s3c",  65.8, "My people left."),
    ("s3", "s3d",  71.2, "One by one, the lights went out..."),
    ("s3", "s3e",  74.6, "and nobody came to turn them back on."),

    ("s4", "s4a",  89.2, "I could have taken off the coat."),
    ("s4", "s4b",  92.3, "I could have walked away."),
    ("s4", "s4c",  95.3, "But a man who has lost everything..."),
    ("s4", "s4d",  98.7, "has nothing left to be afraid of."),

    ("s5", "s5a", 105.8, "The world had forgotten them too."),
    ("s5", "s5b", 109.8, "So I made them an offer."),
    ("s5", "s5c", 118.6, "One ticket."),
    ("s5", "s5d", 126.8, "One family."),
    ("s5", "s5e", 134.4, "One last show."),

    ("s6", "s6a", 140.6, "One circus."),
    ("s6", "s6b", 149.2, "Then ten."),
    ("s6", "s6c", 152.4, "Then all of them."),
    ("s6", "s6d", 157.6, "Every big top in the country learned my name..."),
    ("s6", "s6e", 164.2, "and learned to bow when they said it."),

    ("s7", "s7a", 171.0, "They still call me the Ringmaster."),
    ("s7", "s7b", 176.4, "But the show..."),
    ("s7", "s7c", 178.8, "is different now."),
]

# The low laugh in Scene 4 is a separate voice element (not subtitled).
LAUGH_START = 101.9
LAUGH_END = 104.8     # the laugh is faded out here so it ends inside Scene 4

# --------------------------------------------------------------------------
# Key action beats shared by picture and sound (seconds, absolute).
# Scene modules read these so the SFX land exactly on the action.
# --------------------------------------------------------------------------
MONTAGE_BPM = 84.0          # Act 3 theme tempo; the montage cuts land on its beats
MONTAGE_START = 140.0

BEATS = {
    "s1_lightning": [3.1, 13.6],
    "s2_bow_hat": 26.2,
    "s2_cannon_up": 31.2,
    "s2_knives": [35.0, 35.55, 36.1, 36.65],
    "s2_pip_slip": 40.2,
    "s2_peanut_toss": 43.3,
    "s2_laugh": 44.6,
    "s3_dissolves": [50.6, 53.2],
    "s3_paste": 57.0,
    "s3_hammer": [62.0, 62.6, 63.2],
    "s3_leave": [65.4, 67.2, 69.0],
    "s3_rip": 72.4,
    "s3_bursts": [73.3, 74.1, 74.8, 75.4, 76.0, 76.6],
    "s3_thunder": [71.6, 75.0],
    "s4_cane_snap": 97.0,
    "s5_steps_bruno": 106.6,
    "s5_take_bruno": 112.4,
    "s5_darts": [114.6, 115.7, 116.8],
    "s5_take_lena": 121.2,
    "s5_take_pip": 129.6,
    "s6_taps": [140.714, 141.429, 142.143, 142.857, 143.571],
    "s6_sign": [140.8, 142.0],
    "s7_hat": 177.0,
    "s7_spot_off": 184.0,
}


def scene_of(t):
    for sid, a, b, act in SCENES:
        if a <= t < b:
            return sid
    return SCENES[-1][0]


def shot_of(t):
    for sid, shot, a, b in SHOTS:
        if a <= t < b:
            return sid, shot, a, b
    sid, shot, a, b = SHOTS[-1]
    return sid, shot, a, b
