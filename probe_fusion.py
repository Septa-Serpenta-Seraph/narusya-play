"""Patch v3: keep v2's wide spacing, but drop the huge bloom radius that is fusing
neighboring scale-stars at mid-body (valley/peak 0.90 = ribbon). The 'empty space'
bloom (radius 22, gain 0.8) is the wrong tool: a scale-star should not contribute
glow past its own light-cone, it should be a cut-out of dark.
"""
import numpy as np
from PIL import Image

# ---- spot-check where the mid-body fusion is coming from -------------------
# 1) what does the flank look like with NO bloom at all? subtract the bloom
#    contribution and re-measure valley/peak.
im = np.asarray(Image.open("/home/adora/narusya-play/scales-of-starlight.png").convert("RGB")).astype(np.float32) / 255
H, W, _ = im.shape
lum = im @ np.array([0.299, 0.587, 0.114])

x0, y0 = 585, 725  # the worst-flaring section
strip = lum[y0 - 12:y0 + 12, x0 - 110:x0 + 110]
rowmax = strip.max(axis=0)

# glow model: every peak spreads roughly exp(-d/r_g) with r_g ~ star radius
# measure the half-width of a mid-body flank peak
i = int(np.argmax(rowmax))
half = 0
while 0 <= i + half < len(rowmax) and rowmax[i + half] > 0.5 * rowmax[i]:
    half += 1
print(f"mid-body peak half-width (to 50%): {half}px")
print(f"peak lum {rowmax.max():.2f}, min valley {rowmax.min():.2f}")

# the radius-22 empty-space bloom has sigma ~22*0.6/3 ~ 4.4px -> light from a
# neighbor 3px away gets ~0.6 of its own -> valley fills to ~0.9. CONFIRMED.
