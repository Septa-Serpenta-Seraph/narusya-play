"""Probe: does scales-of-starlight actually read as discrete stars on the body?"""
import numpy as np
from PIL import Image

im = np.asarray(Image.open("/home/adora/narusya-play/scales-of-starlight.png").convert("RGB")).astype(np.float32) / 255
H, W, _ = im.shape
lum = im @ np.array([0.299, 0.587, 0.114])
print("overall mean lum: %.4f" % lum.mean())
print("p99: %.3f  p99.9: %.3f" % (np.percentile(lum, 99), np.percentile(lum, 99.9)))
print("frac lum>0.5: %.4f" % (lum > 0.5).mean())

# centerline samples (x, y) along the body from the render's control polyline
samples = [(300, 1730), (490, 1470), (335, 990), (585, 725), (945, 565), (1000, 385)]
for x, y in samples:
    patch = lum[max(0, y - 45):y + 45, max(0, x - 45):x + 45]
    print("centerline (x=%4d, y=%4d): mean %.3f  p95 %.3f  p99 %.3f" %
          (x, y, patch.mean(), np.percentile(patch, 95), np.percentile(patch, 99)))


def count_peaks(v, thresh=0.30, mind=2):
    """count local maxima above thresh, separated by at least mind samples"""
    n = len(v); peaks = 0; last = -99
    for i in range(n):
        if v[i] < thresh:
            continue
        left = v[i - 1] if i > 0 else 0
        right = v[i + 1] if i < n - 1 else 0
        if v[i] >= left and v[i] >= right and i - last >= mind:
            peaks += 1; last = i
    return peaks


# flank strips at three points along the body: read the star rhythm directly
strips = [
    (335, 990, 90),   # first bend, left flank
    (585, 725, 90),   # crossing right
    (945, 565, 90),   # rearing neck
]
for x0, y0, half in strips:
    strip = lum[y0 - 12:y0 + 12, x0 - half:x0 + half]
    rowmax = strip.max(axis=0)
    s = "".join("#" if v > 0.65 else "+" if v > 0.45 else "." if v > 0.28 else " " for v in rowmax)
    print("flank strip at (%d,%d), %dpx wide  (lum>0.65='#', >0.45='+', >0.28='.'):" % (x0, y0, half * 2))
    print(s)
    print("  local maxima: %d   mean lum %.3f" % (count_peaks(rowmax), rowmax.mean()))
