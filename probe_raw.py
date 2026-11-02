"""Probe 4: what is in the (585,725) plateau? The profile shows a long run of '#'
with tiny '+' valleys. If the 'cores' array has distinct maxima but the composited
'out' has a plateau, the difference is in the compose (sky/haze/ink/bloom terms),
not in core placement. Print both the composited profile AND a synthetic 'no glow,
no sky' profile (just cores + ink) for comparison.
"""
import numpy as np
from PIL import Image

im = np.asarray(Image.open("/home/adora/narusya-play/scales-of-starlight.png").convert("RGB")).astype(np.float32) / 255
H, W, _ = im.shape
lum = im @ np.array([0.299, 0.587, 0.114])

x0, y0 = 585, 725
strip = lum[y0 - 12:y0 + 12, x0 - 110:x0 + 110]
rowmax = strip.max(axis=0)

# Show the raw values around the deepest valley
peaks = [i for i in range(1, len(rowmax) - 1)
         if rowmax[i] >= rowmax[i - 1] and rowmax[i] >= rowmax[i + 1] and rowmax[i] > 0.5]
print(f"{len(peaks)} peaks in 220px window at (585,725)")
# print every 5th value so we can see the shape
vals = [f"{v:.2f}" for v in rowmax[::5]]
print(" ".join(vals))
