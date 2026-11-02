"""Probe 2: do the scale-stars have dark valleys between them, at several points along the body?

The Oct 2 lesson (on-texture-that-exists-but-does-not-read) said generating a feature
and producing a perception of it are different acts. Tonight's hypothesis: the
scale-stars failed for a second, deeper reason - the additive bloom fuses stars whose
spacing is smaller than the glow radius, so there are no dark valleys between them,
and a row of stars without valleys is not a row of stars. It's a ribbon.
"""
import numpy as np
from PIL import Image

im = np.asarray(Image.open("/home/adora/narusya-play/scales-of-starlight.png").convert("RGB")).astype(np.float32) / 255
H, W, _ = im.shape
lum = im @ np.array([0.299, 0.587, 0.114])

# flank cross-sections (x, y) from the render's control polyline
samples = [(300, 1730), (490, 1470), (335, 990), (585, 725), (945, 565), (1000, 385)]

print("flank cross-sections: min valley between peaks, and spacing of local maxima")
for x0, y0 in samples:
    strip = lum[y0 - 12:y0 + 12, x0 - 110:x0 + 110]
    rowmax = strip.max(axis=0)
    # local maxima above 0.5
    peaks = [i for i in range(1, len(rowmax) - 1)
             if rowmax[i] >= rowmax[i - 1] and rowmax[i] >= rowmax[i + 1] and rowmax[i] > 0.5]
    if not peaks:
        print(f"  ({x0},{y0}): no bright peaks")
        continue
    spacings = np.diff(peaks)
    # valleys between consecutive peaks
    valleys = [rowmax[peaks[k]:peaks[k + 1] + 1].min() for k in range(len(peaks) - 1)]
    vmed = np.median(valleys) if valleys else float("nan")
    pmed = np.median(rowmax[peaks])
    print(f"  ({x0:>4},{y0:>4}): {len(peaks):2d} peaks, median spacing {np.median(spacings) if len(spacings) else float('nan'):5.1f}px, "
          f"peak lum {pmed:.2f}, median valley lum {vmed:.2f}, valley/peak ratio {vmed / max(pmed, 1e-6):.2f}")
