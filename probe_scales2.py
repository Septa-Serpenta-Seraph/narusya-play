"""Probe v2: flank strips taken ALONG the body (rotated to the local tangent),
so a horizontal x-window doesn't mismeasure a curling tail."""
import math
import numpy as np
from PIL import Image

im = np.asarray(Image.open("/home/adora/narusya-play/scales-of-starlight.png").convert("RGB")).astype(np.float32) / 255
lum = im @ np.array([0.299, 0.587, 0.114])
print("overall mean lum: %.4f  p99.9: %.3f  frac>0.5: %.4f" %
      (lum.mean(), np.percentile(lum, 99.9), (lum > 0.5).mean()))


def count_peaks(v, thresh=0.30, mind=2):
    n = len(v); peaks = 0; last = -99
    for i in range(n):
        if v[i] < thresh:
            continue
        left = v[i - 1] if i > 0 else 0
        right = v[i + 1] if i < n - 1 else 0
        if v[i] >= left and v[i] >= right and i - last >= mind:
            peaks += 1; last = i
    return peaks


# body control polyline (same as the render); local tangent at each probe point
control = [
    (300, 1730), (360, 1580), (490, 1470), (570, 1330),
    (530, 1190), (425, 1090), (335, 990), (355, 865),
    (455, 770), (585, 725), (705, 705),
    (835, 645), (945, 565), (1005, 455),
    (1000, 385),
]
# probe at arc-length fractions along the whole body
for frac in (0.15, 0.35, 0.55, 0.75, 0.92):
    k = frac * (len(control) - 1)
    i0 = int(k)
    p0 = np.array(control[i0], float)
    p1 = np.array(control[min(i0 + 1, len(control) - 1)], float)
    t = p1 - p0
    t = t / (np.hypot(*t) + 1e-9)
    nrmv = np.array([-t[1], t[0]])
    # walk 220px along the tangent through the probe point, sampling both flanks
    pts = []
    for s in np.linspace(-110, 110, 221):
        c = p0 + t * s
        for off in (-30, 0, 30):
            q = c + nrmv * off
            if 0 <= int(q[1]) < lum.shape[0] and 0 <= int(q[0]) < lum.shape[1]:
                pts.append(lum[int(q[1]), int(q[0])])
    v = np.array(pts)
    s = "".join("#" if x > 0.65 else "+" if x > 0.45 else "." if x > 0.28 else " " for x in v)
    print("along-body at arc %.0f%% (tangent %.2f,%.2f):" % (frac * 100, t[0], t[1]))
    print("  " + s)
    print("  local maxima: %d  mean %.3f" % (count_peaks(v), v.mean()))
