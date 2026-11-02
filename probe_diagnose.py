"""Probe 8: the REAL diagnosis. The CROSS strip at (585,725) has 9 peaks and
valleys of 0.5-0.8 — meaning 9 stars are sitting within 80px across the flank,
not 2. That's impossible with across=2 at ±17px. So the probe is sampling a
DIFFERENT row than the one I think. The strip at y=725±12 crosses multiple body
widths as the body curves, OR the sample point is off the control polyline.
Print the actual body half-width at several points along the body near (585,725).
"""
import math
import numpy as np
from PIL import Image

# reconstruct the body spine near (585,725) from the control polyline
# (the render uses this exact sequence)
control = [
    (300, 1730), (360, 1580), (490, 1470), (570, 1330),
    (530, 1190), (425, 1090), (335, 990), (355, 865),
    (455, 770), (585, 725), (705, 705),
    (835, 645), (945, 565), (1005, 455),
    (1000, 385),
]

def catmull(pts, n=2400):
    p = np.asarray(pts, np.float32)
    p = np.vstack([p[0] + (p[0] - p[1]), p, p[-1] + (p[-1] - p[-2])])
    t = np.linspace(0, len(p) - 3, n)
    i = np.clip(t.astype(int), 0, len(p) - 4)
    f = (t - i)[:, None]
    p0, p1, p2, p3 = p[i], p[i + 1], p[i + 2], p[i + 3]
    return 0.5 * ((2 * p1) + (-p0 + p2) * f +
                  (2 * p0 - 5 * p1 + 4 * p2 - p3) * f ** 2 +
                  (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)

def resample(pts, n):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    return np.column_stack([np.interp(np.linspace(0, d[-1], n), d, pts[:, 0]),
                            np.interp(np.linspace(0, d[-1], n), d, pts[:, 1])])

sp = resample(catmull(control, 3000), 3000)
u = np.linspace(0, 1, len(sp))
width = 15.0 + 52.0 * np.exp(-((u / 0.10) ** 2)) \
        + 44.0 * np.exp(-(((u - 0.22) / 0.13) ** 2)) \
        + 13.0 * (1 - u) ** 1.5

# find the spine point nearest to (585, 725)
dists = np.hypot(sp[:, 0] - 585, sp[:, 1] - 725)
idx = int(np.argmin(dists))
print(f"nearest spine point to (585,725): ({sp[idx,0]:.0f}, {sp[idx,1]:.0f}), u={u[idx]:.3f}")
print(f"body half-width at that point: w={width[idx]*0.5:.1f}px")
print(f"with across=2, stars at ±{width[idx]*0.5*0.97:.1f}px from centerline")
print(f"the probe strip spans x=485..685, i.e. ±100px from center")
print(f"so it captures {2*width[idx]*0.5:.0f}px of body width")
print(f"expected peaks from THIS row: 2")
print(f"actual peaks found: 9")
print()
print("if 9 peaks, they're from ADJACENT rows (NROWS=80 over ~1500px = ~19px row spacing)")
print("the probe strip is 24px tall (y=713..737) — captures 1-2 rows, not 9")
print()
print("CONCLUSION: the probe is measuring sky-stars + noise on the body, not scale-stars.")
