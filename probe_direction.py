"""Probe 6: mid-body plateau diagnosis v2. Compare a CROSS-BODY horizontal strip
vs an ALONG-BODY strip. If the plateau runs along the body (constant in x, varying
in y), the fusion is in row spacing (row direction). If it runs across the body,
the fusion is in `across` (cross direction). This will tell me exactly which knob
is wrong.
"""
import numpy as np
from PIL import Image

im = np.asarray(Image.open("/home/adora/narusya-play/scales-of-starlight.png").convert("RGB")).astype(np.float32) / 255
H, W, _ = im.shape
lum = im @ np.array([0.299, 0.587, 0.114])

# (585,725) is on the mid-flank, heading right
# CROSS strip (along the body's width): y=725, x=585-40 .. 585+40
cross = lum[725 - 12:725 + 12, 585 - 40:585 + 40]
# ALONG strip (along the body's length): x=585, y=725-40 .. 725+40
along = lum[725 - 40:725 + 40, 585 - 12:585 + 12]

cross_prof = cross.max(axis=0)
along_prof = along.max(axis=1)

print("CROSS (40px, should be 1-2 stars max):")
print(" ".join(f"{v:.2f}" for v in cross_prof))
print(f"  peaks: {sum(1 for i in range(1,len(cross_prof)-1) if cross_prof[i]>cross_prof[i-1] and cross_prof[i]>cross_prof[i+1] and cross_prof[i]>0.7)}")

print("ALONG (40px, should be 1-2 stars max):")
print(" ".join(f"{v:.2f}" for v in along_prof))
print(f"  peaks: {sum(1 for i in range(1,len(along_prof)-1) if along_prof[i]>along_prof[i-1] and along_prof[i]>along_prof[i+1] and along_prof[i]>0.7)}")
