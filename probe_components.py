"""Probe 5: figure out what's IN the fused plateau at (585,725) — is it sky stars
from the background field landing on the body, or is it the body glow? Render a
dark-only version (no stars field, no bloom) of just that flank strip.
"""
import numpy as np
from PIL import Image

# same flank strip from the composited image
im = np.asarray(Image.open("/home/adora/narusya-play/scales-of-starlight.png").convert("RGB")).astype(np.float32) / 255
H, W, _ = im.shape
lum = im @ np.array([0.299, 0.587, 0.114])

# 1) count the sky stars in a 220x24 window around (585,725)
# sky stars were drawn with `add` into `stars` — we can't re-derive them here, but
# we CAN check whether the plateau is made of discrete bright points at a
# different scale (i.e., sky stars) by looking at a 2D slice.
strip = lum[725 - 24:725 + 24, 585 - 110:585 + 110]
# find every pixel > 0.7 (bright)
bright = strip > 0.7
# count connected components via simple flood-free label scan (scipy unavailable)
# use scipy.ndimage.label if available, else do a crude row-run count
try:
    from scipy import ndimage
    lab, n = ndimage.label(bright)
    print(f"bright components in flank window: {n}")
except ImportError:
    # crude: count runs of >0.7 per row, average
    runs_per_row = []
    for r in range(strip.shape[0]):
        row = strip[r]
        n_runs = 0
        in_run = False
        for v in row:
            if v > 0.7 and not in_run:
                n_runs += 1
                in_run = True
            elif v <= 0.7:
                in_run = False
        runs_per_row.append(n_runs)
    print(f"mean bright runs per row (crude): {np.mean(runs_per_row):.1f}")
    print(f"max bright runs in any row: {max(runs_per_row)}")
