"""Probe 3: diagnose WHY (585,725) and (335,990) stay fused, without guessing.

For each flank sample, print the full luminance profile across the flank so I can
see the actual shape: is there a valley (dark) between two peaks, or a plateau
(two humps)? A plateau means the cores themselves overlap. A deep valley with high
fill means the ink/glow is refilling it.
"""
import numpy as np
from PIL import Image

im = np.asarray(Image.open("/home/adora/narusya-play/scales-of-starlight.png").convert("RGB")).astype(np.float32) / 255
H, W, _ = im.shape
lum = im @ np.array([0.299, 0.587, 0.114])

samples = [(585, 725), (335, 990), (490, 1470)]

for x0, y0 in samples:
    strip = lum[y0 - 12:y0 + 12, x0 - 110:x0 + 110]
    rowmax = strip.max(axis=0)
    # downsample to 90 chars for a readable profile
    n = len(rowmax)
    step = n // 90
    prof = rowmax[::step]
    s = "".join("#" if v > 0.7 else "+" if v > 0.45 else "." if v > 0.25 else " " for v in prof)
    print(f"--- ({x0},{y0}) 90px-wide profile (>0.7=#, >0.45=+, >0.25=.)")
    print(s)
    print()
