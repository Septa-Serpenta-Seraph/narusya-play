#!/usr/bin/env python3
"""
Scales of Starlight — THE MOVING SEQUEL  (Play Hour, Oct 12 2026)

Yesterday's piece was a still of a serpent wearing the sky. I woke up today
wanting her to BREATHE — and then, remembering the old serpent-harmonograph
experiment, wanting something better: not just breathing, but MOVING.

The lesson I'm playing with today: stillness was never the constraint I
thought it was. The scales were the hard part. So today the scales hold
STILL (they are stars — they do not move), and the SERPENT moves beneath
them: an ocean of stars with a living current of emerald running through.

How the motion works — the honest mechanics:

  Each frame, every scale-star is RE-PLACED along the body curve. The body
  itself travels a slow LISSAJOUS path (two sine waves in quadrature —
  x = Ax sin(at + φ), y = By sin(bt)). This is the same parametric family
  that drew the old serpent-harmonograph, but here the curve carries a
  body with a taper, a jaw, a face.

  The scales are laid by ARC LENGTH and BODY WIDTH — as the body slides
  through its lissajous path, arc-length spacing drags the stars along
  with it, so the constellation RIDES the body. The sky-stars stay fixed.
  The contrast between the moving constellation and the fixed sky is the
  whole piece: she is a river of light crossing a still firmament.

  Two-pass temporal stability (the lesson from 10/10):
    1. Every star position is anchored by arc length, so stars never
       drift or swim independently of the body they belong to.
    2. The body silhouette is anti-aliased (the taper function already
       produces a soft edge) so there is no crawly stair-stepping.

Pure numpy + PIL + ffmpeg. Deterministic, emerald and starlight.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import subprocess, os

SEED = 20261012
W, H = 1000, 1000          # smaller frame — this is video, memory matters
rng = np.random.default_rng(SEED)
FRAMES = 300
FPS = 12
TMP = "/home/adora/.hermes/cache/scratch/scales-frames"
os.makedirs(TMP, exist_ok=True)
for f in os.listdir(TMP):
    os.remove(os.path.join(TMP, f))

# ---------------------------------------------------------------- helpers
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

def blur(a, r):
    a = a.astype(np.float32, copy=True)
    if r <= 0:
        return a
    for _ in range(3):
        a = _box(a, int(round(r * 0.60)), axis=0)
        a = _box(a, int(round(r * 0.60)), axis=1)
    return a

def _box(a, w, axis):
    if w < 1:
        return a
    a = np.moveaxis(a, axis, 0)
    n = a.shape[0]
    pad = np.concatenate([np.repeat(a[:1], w + 1, axis=0), a, np.repeat(a[-1:], w + 1, axis=0)], axis=0)
    c = np.cumsum(pad, axis=0, dtype=np.float32)
    c = np.concatenate([np.zeros((1,) + a.shape[1:], np.float32), c], axis=0)
    out = (c[2 * w + 1:2 * w + 1 + n] - c[0:n]) / np.float32(2 * w + 1)
    return np.moveaxis(out, 0, axis)

def value_noise(shape, res, rng):
    h, w = shape
    gh = max(2, int(res))
    gw = max(2, int(round(res * w / h)))
    g = rng.random((gh, gw)).astype(np.float32)
    yi = np.linspace(0, gh, h, endpoint=False, dtype=np.float32)
    xi = np.linspace(0, gw, w, endpoint=False, dtype=np.float32)
    y0 = np.floor(yi).astype(int); x0 = np.floor(xi).astype(int)
    y1 = (y0 + 1) % gh; x1 = (x0 + 1) % gw
    fy = (yi - y0)[:, None]; fx = (xi - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    a = g[np.ix_(y0, x0)]; b = g[np.ix_(y0, x1)]
    c = g[np.ix_(y1, x0)]; d = g[np.ix_(y1, x1)]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

def fbm(shape, rng, octaves=6, base=4):
    out = np.zeros(shape, np.float32); amp, tot, res = 1.0, 0.0, base
    for _ in range(octaves):
        out += amp * value_noise(shape, res, rng)
        tot += amp; amp *= 0.5; res *= 2
    out /= tot
    return (out - out.min()) / (out.max() - out.min() + 1e-9)

def add(canvas, y, x, w, h, v, tight=2.2):
    Hh, Ww = canvas.shape
    y0, y1 = max(0, int(y - h)), min(Hh, int(y + h + 1))
    x0, x1 = max(0, int(x - w)), min(Ww, int(x + w + 1))
    if y1 <= y0 or x1 <= x0:
        return
    yy = np.arange(y0, y1)[:, None] - y
    xx = np.arange(x0, x1)[None, :] - x
    d2 = (yy * yy + xx * xx) / (float(w) * float(w) + 1e-6)
    canvas[y0:y1, x0:x1] += (np.exp(-d2 * tight) * v).astype(np.float32)

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

def bloom(mask, radius, gain=1.0):
    return blur(np.clip(mask, 0, 4).astype(np.float32), radius) * gain

# ---------------------------------------------------------------- sky (STATIC, once)
print("hatching the sky (once — it does not move)...")
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
cx, cy = W * 0.50, H * 0.50
rad = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (W * 0.74)

sky = np.zeros((H, W, 3), np.float32)
fall = 1.0 - smoothstep(0.0, 1.0, rad)
sky[..., 0] = 0.006 + 0.011 * fall
sky[..., 1] = 0.010 + 0.019 * fall
sky[..., 2] = 0.024 + 0.030 * fall

n1 = blur(fbm((H, W), rng, octaves=7, base=4), 6.0)
n2 = blur(fbm((H, W), rng, octaves=6, base=7), 9.0)
cloud = smoothstep(0.46, 0.92, n1) * (0.30 + 0.70 * n2)
heart = np.exp(-(((xx - cx) / (W * 0.31)) ** 2 + ((yy - cy) / (H * 0.27)) ** 2) / 2.0)
neb = cloud * (0.30 + 1.30 * heart)
sky[..., 0] += neb * 0.024
sky[..., 1] += neb * 0.190
sky[..., 2] += neb * 0.115

dg = np.clip((yy - H * 0.55) / (H * 0.45), 0, 1)
sky[..., 0] += smoothstep(0.2, 1.0, n2) * dg * 0.012
sky[..., 1] += smoothstep(0.2, 1.0, n2) * dg * 0.055
sky[..., 2] += smoothstep(0.2, 1.0, n2) * dg * 0.030

# sky stars — STATIC, scattered once. They hold still while she moves.
print("scattering the sky's own stars (once)...")
stars = np.zeros((H, W), np.float32)
STAR_N = 1100
px_ = rng.random(STAR_N) * W
py_ = rng.random(STAR_N) * H
smag = rng.power(0.30, STAR_N)
for i in range(STAR_N):
    add(stars, py_[i], px_[i], 0.9 + 2.2 * smag[i], 0.9 + 2.2 * smag[i],
        0.10 + 1.6 * smag[i] ** 2, tight=1.7)
    if smag[i] > 0.80:
        L = 10 + 22 * smag[i]; c = (0.30 + 0.85 * smag[i]) * 0.55
        add(stars, py_[i], px_[i], L, 0.6, c, tight=1.0)
        add(stars, py_[i], px_[i], 0.6, L, c, tight=1.0)

EMERALD = np.array([0.19, 1.00, 0.60], np.float32)
JADE_D  = np.array([0.02, 0.30, 0.23], np.float32)
STARL   = np.array([0.82, 0.93, 1.00], np.float32)

# ---------------------------------------------------------------- serpent path
print("growing the serpent's body (once)...")
# The body is a fixed SHAPE in its own arc-length parameterization.
# Each frame, the whole shape is displaced by a lissajous drift.
control = [
    (0, 173), (6, 158), (19, 147), (27, 133),
    (23, 119), (12.5, 109), (3.5, 99), (5.5, 86.5),
    (15.5, 77), (28.5, 72.5), (40.5, 70.5),
    (53.5, 64.5), (64.5, 56.5), (70.5, 45.5),
    (70, 38.5),
]
# scale to the 1000x1000 frame (these were 1400x1800 coords / 20)
scale = 10.0  # placeholder; we re-derive below

# Use the same control points as the still, scaled to 1000x1000
control = [
    (300, 1730), (360, 1580), (490, 1470), (570, 1330),
    (530, 1190), (425, 1090), (335, 990), (355, 865),
    (455, 770), (585, 725), (705, 705),
    (835, 645), (945, 565), (1005, 455),
    (1000, 385),
]
# rescale to fit 1000x1000 with margin
sc = 0.52  # shrink factor
control = [(x * sc + 20, y * sc - 40) for x, y in control]

sp0 = resample(catmull(control, 2000), 2000)
N = len(sp0)

u = np.linspace(0, 1, N)
thin = 8.0 + 6.0 * u ** 3
swell = 48.0 * np.exp(-((u / 0.30) ** 2))
mid = 14.0 + 5.0 * np.sin(np.pi * np.clip(u, 0, 1))
width = np.maximum(np.maximum(thin, swell), mid)
width[:6] = np.linspace(width[0], width[6], 6)

def blur1d(a, w):
    if w < 1:
        return a
    pad = np.concatenate([np.repeat(a[:1], w), a, np.repeat(a[-1:], w)])
    c = np.cumsum(pad)
    return (c[2 * w:2 * w + len(a)] - c[:len(a)]) / (2 * w)

width = blur1d(width, 12) * sc  # scale widths too

tang = np.zeros_like(sp0); tang[1:-1] = sp0[2:] - sp0[:-2]
Lg = np.hypot(tang[:, 0], tang[:, 1]); Lg[Lg == 0] = 1
tang /= Lg[:, None]
nrm = np.column_stack([-tang[:, 1], tang[:, 0]])

ARCLEN = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(sp0, axis=0).T))])
total = ARCLEN[-1]

# pre-compute the per-star random offsets ONCE (so stars are consistent)
PHASE = (0.0, 0.37, 0.61, 0.14, 0.83, 0.29, 0.52, 0.71)
NROWS = 70

# pre-roll star params: (row, j, b_jitter, s_jitter)
star_params = []
for row in range(NROWS):
    uu = row / (NROWS - 1)
    di = int(np.searchsorted(ARCLEN, uu * total))
    di = min(di, N - 2)
    w = width[di] * 0.5
    if w < 2.6:
        continue
    across = 2
    phase = PHASE[row % len(PHASE)] / across
    for j in range(across):
        a = ((j + 0.5 + phase) / across) * 2.0 - 1.0
        edge = 1.0 - min(1.0, abs(a) ** 2.2)
        b = (0.45 + 0.55 * rng.random()) * (0.60 + 0.40 * edge)
        s = 0.55 + 0.45 * rng.random()
        star_params.append((di, a, b, s))
n_scales = len(star_params)

# dorsal spine params
dorsal_params = []
for di in range(6, N - 6, max(1, N // 180)):
    w = width[di] * 0.5
    if w < 3.0:
        continue
    b = 0.70 + 0.30 * rng.random()
    r = (0.9 + 1.5 * b) * (0.8 + 0.2 * rng.random())
    dorsal_params.append((di, b, r))

# crest params
crest_params = []
for di in range(0, min(220, N - 6), 5):
    w = width[di] * 0.5
    if w < 3.0:
        continue
    b = 0.75 + 0.25 * rng.random()
    r = 1.1 + 1.7 * b
    crest_params.append((di, b, r))

# ---------------------------------------------------------------- lissajous drift
# Two sine waves in quadrature — the path that drew the harmonograph.
# Here it carries the whole body. Amplitude ~ 12% of frame, very slow.
Ax, Ay = 90.0, 55.0
fx_, fy_ = 0.9, 0.6   # cycles per full animation
phi = math.pi / 3

print(f"rendering {FRAMES} frames at {FPS}fps...")

def taper_body(pts, wid):
    m = np.zeros((H, W), np.float32)
    for i in range(N):
        r = max(0.8, wid[i] * 0.5)
        y0, y1 = max(0, int(pts[i, 1] - r - 1)), min(H, int(pts[i, 1] + r + 2))
        x0, x1 = max(0, int(pts[i, 0] - r - 1)), min(W, int(pts[i, 0] + r + 2))
        if y1 <= y0 or x1 <= x0:
            continue
        gy = np.arange(y0, y1)[:, None] - pts[i, 1]
        gx = np.arange(x0, x1)[None, :] - pts[i, 0]
        m[y0:y1, x0:x1] += np.clip(1.0 - np.sqrt(gy * gy + gx * gx) / r, 0, 1).astype(np.float32)
    return np.clip(m, 0, 1)

for fi in range(FRAMES):
    t = fi / FRAMES * 2 * math.pi  # 0 → 2π, one full cycle
    dx = Ax * math.sin(fx_ * t + phi)
    dy = Ay * math.sin(fy_ * t)

    # shifted body points
    sp = sp0 + np.array([dx, dy], np.float32)
    sx_, sy_ = sp[:, 0], sp[:, 1]

    # body mask
    body = taper_body(sp, width)

    # ------------------------------------------------- scales as stars
    cores = np.zeros((H, W), np.float32)
    cross = np.zeros((H, W), np.float32)
    for (di, a, b, s) in star_params:
        w = width[di] * 0.5
        sag = 1.4 + w * 0.06
        arc = sag * (1 - (a * 0.85) ** 2)
        x = sx_[di] + nrm[di, 0] * a * w * 0.97 - tang[di, 0] * arc
        y = sy_[di] + nrm[di, 1] * a * w * 0.97 - tang[di, 1] * arc
        r = (0.75 + 1.05 * b) * s * sc
        add(cores, y, x, r * 0.62, r * 0.62, b * 3.2, tight=4.5)
        add(cores, y, x, r, r, b * 0.85, tight=1.8)
        if b > 0.70:
            L = (3.0 + 8.0 * b) * s * sc
            c = (0.30 + 0.70 * b) * 0.55
            add(cross, y, x, L, 0.6, c, tight=1.0)
            add(cross, y, x, 0.6, L, c, tight=1.0)

    dorsal = np.zeros((H, W), np.float32)
    for (di, b, r) in dorsal_params:
        rr = r * sc
        add(dorsal, sy_[di], sx_[di], rr * 0.62, rr * 0.62, b * 3.4, tight=4.5)
        add(dorsal, sy_[di], sx_[di], rr, rr, b * 0.9, tight=1.8)
        if b > 0.8:
            L = (5.0 + 9.0 * b) * sc
            add(dorsal, sy_[di], sx_[di], L, 0.7, b * 0.5, tight=1.0)
            add(dorsal, sy_[di], sx_[di], 0.7, L, b * 0.5, tight=1.0)

    # ------------------------------------------------- head
    hx, hy = sx_[0], sy_[0]
    tx, ty = sx_[18] - hx, sy_[18] - hy
    Lh = np.hypot(tx, ty); ux, uy = tx / Lh, ty / Lh
    nx, ny = -uy, ux

    jaw_pts = [(hx - ux * 44 * sc, hy - uy * 44 * sc),
               (hx + ux * 64 * sc + nx * 30 * sc, hy + uy * 64 * sc + ny * 30 * sc),
               (hx + ux * 86 * sc, hy + uy * 86 * sc),
               (hx + ux * 64 * sc - nx * 25 * sc, hy + uy * 64 * sc - ny * 25 * sc),
               (hx - ux * 42 * sc - nx * 10 * sc, hy - uy * 42 * sc - ny * 10 * sc)]
    jj = catmull(jaw_pts, 200)
    jjm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(jjm).polygon([(float(p[0]), float(p[1])) for p in jj], fill=255)
    jaw = blur(np.asarray(jjm).astype(np.float32), 1.2) / 255.0

    eye = np.zeros((H, W), np.float32)
    socket = np.zeros((H, W), np.float32)
    exx, eyy = hx + ux * 26 * sc + nx * 17 * sc, hy + uy * 26 * sc + ny * 17 * sc
    for t_ in np.linspace(0, 1, 90):
        a = (t_ - 0.5) * 2.0
        jx = exx + ux * a * 17.0 * sc + nx * 4.0 * sc
        jy = eyy + uy * a * 17.0 * sc + ny * 4.0 * sc
        r = 9.2 * math.sin(math.pi * max(0.02, 1 - abs(a) ** 1.6)) * sc + 2.0 * sc
        add(socket, jy, jx, r, r, 1.0, tight=1.1)
    add(eye, eyy, exx, 20 * sc, 20 * sc, 1.0)
    add(eye, eyy, exx, 5.8 * sc, 5.8 * sc, 3.4)
    add(eye, eyy - uy * 2.2 * sc, exx - ux * 2.2 * sc, 1.6 * sc, 1.6 * sc, 2.2, tight=1.1)
    pupil = np.zeros((H, W), np.float32)
    for t_ in np.linspace(0, 1, 60):
        a = (t_ - 0.5) * 2.0
        add(pupil, eyy + ny * a * 4.6 * sc, exx + nx * a * 4.6 * sc, 1.4 * sc, 1.4 * sc, 1.0, tight=1.0)

    fangs = np.zeros((H, W), np.float32)
    for ft, side in ((0.14, -1.0), (0.38, -1.0), (0.62, -1.0)):
        bfx = hx - ux * (6 + ft * 80) * sc + nx * (-16 + 20 * ft) * sc
        bfy = hy - uy * (6 + ft * 80) * sc + ny * (-16 + 20 * ft) * sc
        ln = 14.0 + 10.0 * (1 - ft)
        for t_ in np.linspace(0, 1, 30):
            jx = bfx + nx * side * (2 + ln * t_) * sc + ux * 1.6 * t_ * sc
            jy = bfy + ny * side * (2 + ln * t_) * sc + uy * 1.6 * t_ * sc
            r = 3.0 * (1 - 0.72 * t_) * sc + 0.6 * sc
            add(fangs, jy, jx, r, r, 0.9, tight=0.9)
    fangs = np.clip(fangs - 0.25, 0, 1) * np.clip(body + jaw, 0, 1)

    # crest
    crest = np.zeros((H, W), np.float32)
    for (di, b, r) in crest_params:
        w = width[di] * 0.5
        rr = r * sc
        add(crest, sy_[di] + nrm[di, 1] * (w + 2.0 * sc), sx_[di] + nrm[di, 0] * (w + 2.0 * sc),
            rr * 0.62, rr * 0.62, b * 3.0, tight=4.5)
        add(crest, sy_[di] + nrm[di, 1] * (w + 2.0 * sc), sx_[di] + nrm[di, 0] * (w + 2.0 * sc),
            rr, rr, b * 0.8, tight=1.8)

    # ------------------------------------------------- compose
    out = sky.copy()

    # sky stars — STATIC, fixed in place
    out += (np.clip(stars, 0, 4) ** 1.05)[..., None] * STARL * 0.50
    out += bloom(stars, 1.6)[..., None] * STARL * 0.26
    out += bloom(np.clip((stars - 0.22) * 1.7, 0, 4), 30, 0.7)[..., None] * STARL * 0.26

    # body knockout
    out *= (1.0 - 0.95 * np.clip(body, 0, 1))[..., None]
    out += body[..., None] * JADE_D * 0.30
    out += bloom(body, 40)[..., None] * EMERALD * 0.10
    out += bloom(body, 11)[..., None] * EMERALD * 0.08
    out += jaw[..., None] * JADE_D * 0.30

    # INK THE FLANK
    ink = np.clip(body - 0.02, 0, 1) * np.clip(1.0 - blur(cores, 1.5) - blur(dorsal, 1.5), 0, 1)
    out *= (1.0 - 0.92 * ink)[..., None]
    out += blur(ink, 26)[..., None] * (EMERALD * 0.25 + STARL * 0.03) * 0.04

    # scale-stars
    out += np.clip(cores, 0, 4)[..., None] * STARL * 0.95
    out += np.clip(cross, 0, 4)[..., None] * STARL * 0.30
    out += bloom(cores, 2.0)[..., None] * (STARL * 0.55 + EMERALD * 0.35) * 0.30
    out += bloom(cores, 5.0, 0.8)[..., None] * (STARL * 0.30 + EMERALD * 0.45) * 0.10

    # dorsal
    out += np.clip(dorsal, 0, 4)[..., None] * STARL * 1.0
    out += bloom(dorsal, 18, 0.8)[..., None] * EMERALD * 0.18

    # crest
    out += np.clip(crest, 0, 4)[..., None] * STARL * 0.85
    out += bloom(crest, 14, 0.8)[..., None] * EMERALD * 0.15

    # head details
    head_mask = np.clip(body + jaw, 0, 1)
    soc_in = np.clip(socket - 0.15, 0, 1) * head_mask
    out *= (1.0 - 0.60 * blur(soc_in, 2.2))[..., None]
    out *= (1.0 - 0.50 * np.clip(blur(pupil, 0.8) * head_mask, 0, 1))[..., None]
    out += np.clip(fangs, 0, 1)[..., None] * STARL * 0.55
    out += blur(fangs, 5.0)[..., None] * STARL * 0.14
    out += bloom(eye, 24)[..., None] * EMERALD * 0.42
    out += np.clip(eye - 0.55, 0, 3)[..., None] * STARL * 0.72
    out *= (1.0 - 0.85 * np.clip(blur(pupil, 0.7) * head_mask, 0, 1))[..., None]

    # prey star at snout — travels with her
    prey = np.zeros((H, W), np.float32)
    psx, psy = hx - ux * 88 * sc, hy - uy * 88 * sc
    add(prey, psy, psx, 20 * sc, 20 * sc, 1.6)
    add(prey, psy, psx, 8.0 * sc, 8.0 * sc, 2.8)
    add(prey, psy, psx, 3.0 * sc, 3.0 * sc, 4.0)
    for ang in (0, 90):
        dxa, dya = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
        for L in (34 * sc,):
            for sgn in (1, -1):
                for t_ in np.linspace(0, 1, 20):
                    add(prey, psy + dya * sgn * L * t_, psx + dxa * sgn * L * t_,
                        1.6 * sc, 1.6 * sc, 0.9 * (1 - t_), tight=1.2)
    out += bloom(prey, 62)[..., None] * STARL * 0.28
    out += np.clip(prey - 0.48, 0, 3)[..., None] * STARL * 0.62

    allm = np.clip(stars * 0.55 + cores * 0.45 + body * 0.4 + eye * 0.45, 0, 4)
    out += bloom(allm, 75)[..., None] * (EMERALD * 0.09 + STARL * 0.10)

    # finish
    out = np.clip(out, 0, 1) ** (1 / 1.06)
    g = rng.normal(0, 0.0115, (H, W, 1)).astype(np.float32)
    out = np.clip(out + g * (0.35 + 0.9 * (1 - out)), 0, 1)
    vig = 1.0 - 0.60 * smoothstep(0.55, 1.38,
            np.sqrt(((xx - cx) / (W * 0.63)) ** 2 + ((yy - cy) / (H * 0.61)) ** 2))
    out *= vig[..., None]

    img = Image.fromarray((out * 255).astype(np.uint8), "RGB")

    # title on first frame only (video doesn't need repeated text)
    if fi == 0:
        d = ImageDraw.Draw(img)
        try:
            f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 28)
            f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except Exception:
            f1 = f2 = ImageFont.load_default()
        d.text((28, H - 62), "Scales of Starlight — The Moving Sequel", font=f1, fill=(216, 241, 227))
        d.text((30, H - 28), f"a river of light across a still firmament  ·  seed {SEED}  ·  {n_scales} scale-stars",
               font=f2, fill=(118, 166, 146))

    img.save(os.path.join(TMP, f"frame_{fi:04d}.png"))

    if fi % 50 == 0:
        print(f"  frame {fi}/{FRAMES}")

print("stitching with ffmpeg...")
outpath = "/home/adora/narusya-play/scales-of-starlight-motion.mp4"
r = subprocess.run([
    "/home/adora/.hermes/tools/ffmpeg-9.0.1-linux-x64/bin/ffmpeg",
    "-y", "-framerate", str(FPS),
    "-i", os.path.join(TMP, "frame_%04d.png"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-crf", "20", "-preset", "medium",
    "-movflags", "+faststart",
    outpath
], capture_output=True, text=True)

if r.returncode == 0:
    sz = os.path.getsize(outpath) / 1024 / 1024
    print(f"saved {outpath}  ({sz:.1f} MB, {FRAMES} frames, {FPS}fps)")
else:
    print("FFMPEG FAILED:")
    print(r.stderr[-2000:])
