#!/usr/bin/env python3
"""
Scales of Starlight  v2  (Play Hour, Oct 10 2026)

The sequel to "Serpent Between Stars". Last time I engraved scale arcs into
the flank and, after three tuning passes, they still didn't read — the lesson
went into on-texture-that-exists-but-does-not-read.md: generating a feature
and producing a perception of it are different acts.

So tonight the scales are not texture at all. Each scale IS a star: a bright
self-luminous point laid in staggered rows along the body by arc length.
The serpent doesn't swim between stars — she wears them. Row by row, she
wears the sky.

v2 fix (the honest iteration, kept in the file on purpose):
v1 rendered 605 scale-stars in 4.7s, but the flank-strip probe read as one
continuous '####' band with only 7 local maxima — the per-scale halos
overlapped into a ribbon and there was no dark gap between points, and no
dark flank for them to pop against. A star you cannot separate from its
neighbor is not a star; it is brightness. v2 fixes all three:

  1. the flank under each row is INKED near-black, so stars sit in the void
  2. each scale is a hard core (tight=4.5) with a detached tiny halo — the
     gaps between neighbors now stay dark
  3. scale size jitters 0.55-1.0, so rows break into a broken constellation
     instead of a machine-stamped strip

Pure numpy + PIL, deterministic, emerald and starlight.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SEED = 20261010
W, H = 1400, 1800
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------- helpers
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

def blur(a, r):
    """Separable approximate-gaussian blur in pure numpy (3 box passes)."""
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
    """additive gaussian splat, clipped"""
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

# ---------------------------------------------------------------- sky
print("hatching the sky...")
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
cx, cy = W * 0.50, H * 0.44
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

# emerald haze rising from the bottom of the frame
dg = np.clip((yy - H * 0.55) / (H * 0.45), 0, 1)
sky[..., 0] += smoothstep(0.2, 1.0, n2) * dg * 0.012
sky[..., 1] += smoothstep(0.2, 1.0, n2) * dg * 0.055
sky[..., 2] += smoothstep(0.2, 1.0, n2) * dg * 0.030

# ---------------------------------------------------------------- serpent
print("growing the serpent...")
control = [
    (300, 1730), (360, 1580), (490, 1470), (570, 1330),   # tail + lower flank
    (530, 1190), (425, 1090), (335, 990), (355, 865),     # first bend, left
    (455, 770), (585, 725), (705, 705),                   # crossing right
    (835, 645), (945, 565), (1005, 455),                  # rearing neck
    (1000, 385),                                          # head
]
sp = resample(catmull(control, 3000), 3000)
sx_, sy_ = sp[:, 0], sp[:, 1]
N = len(sp)

u = np.linspace(0, 1, N)
width = 15.0 + 52.0 * np.exp(-((u / 0.10) ** 2)) \
            + 44.0 * np.exp(-(((u - 0.22) / 0.13) ** 2)) \
            + 13.0 * (1 - u) ** 1.5

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

body = taper_body(sp, width)

tang = np.zeros_like(sp); tang[1:-1] = sp[2:] - sp[:-2]
Lg = np.hypot(tang[:, 0], tang[:, 1]); Lg[Lg == 0] = 1
tang /= Lg[:, None]
nrm = np.column_stack([-tang[:, 1], tang[:, 0]])

ARCLEN = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(sp, axis=0).T))])
total = ARCLEN[-1]

# ------------------------------------------------- the scales: they ARE stars
print("placing the stars along her back...")
# Every scale is a star: a hard bright core with a tiny detached halo and,
# on the brightest, a short diffraction cross. Rows by arc length, brick-
# staggered. The flank they sit on is inked near-black below (compose step).
cores = np.zeros((H, W), np.float32)
cross = np.zeros((H, W), np.float32)
n_scales = 0

ROW = 13.0
row = 0
d = 2.0
PHASE = (0.0, 0.37, 0.61, 0.14, 0.83, 0.29, 0.52, 0.71)
while d < total - 12:
    d += ROW
    row += 1
    dd = d + PHASE[row % len(PHASE)] * ROW
    if dd >= total - 12:
        break
    di = int(np.searchsorted(ARCLEN, dd))
    if di >= N - 2:
        break
    w = width[di] * 0.5
    if w < 2.6:
        continue
    sag = 2.0 + w * 0.15
    across = max(3, int(w / 5.6))
    for j in range(across):
        a = ((j + 0.5) / across) * 2.0 - 1.0
        a += (j % 2) * 0.5 / across
        arc = sag * (1 - (a * 0.85) ** 2)
        x = sx_[di] + nrm[di, 0] * a * w * 0.97 - tang[di, 0] * arc
        y = sy_[di] + nrm[di, 1] * a * w * 0.97 - tang[di, 1] * arc
        edge = 1.0 - min(1.0, abs(a) ** 2.2)
        b = (0.45 + 0.55 * rng.random()) * (0.60 + 0.40 * edge)
        s = 0.55 + 0.45 * rng.random()          # jittered size: broken constellation
        r = (0.75 + 1.05 * b) * s
        add(cores, y, x, r * 0.62, r * 0.62, b * 3.2, tight=4.5)   # hard core, tight gaps
        add(cores, y, x, r, r, b * 0.85, tight=1.8)                # soft body of the point
        if b > 0.70:
            L = (3.0 + 8.0 * b) * s
            c = (0.30 + 0.70 * b) * 0.55
            add(cross, y, x, L, 0.6, c, tight=1.0)
            add(cross, y, x, 0.6, L, c, tight=1.0)
        n_scales += 1

# dorsal spine of brighter, slightly larger stars
dorsal = np.zeros((H, W), np.float32)
for di in range(6, N - 6, max(1, N // 220)):
    w = width[di] * 0.5
    if w < 3.0:
        continue
    b = 0.70 + 0.30 * rng.random()
    r = (0.9 + 1.5 * b) * (0.8 + 0.2 * rng.random())
    add(dorsal, sy_[di], sx_[di], r * 0.62, r * 0.62, b * 3.4, tight=4.5)
    add(dorsal, sy_[di], sx_[di], r, r, b * 0.9, tight=1.8)
    if b > 0.8:
        L = 5.0 + 9.0 * b
        add(dorsal, sy_[di], sx_[di], L, 0.7, b * 0.5, tight=1.0)
        add(dorsal, sy_[di], sx_[di], 0.7, L, b * 0.5, tight=1.0)

# ---------------------------------------------------------------- head
print("giving her a face...")
hx, hy = sx_[0], sy_[0]
tx, ty = sx_[18] - hx, sy_[18] - hy
Lh = np.hypot(tx, ty); ux, uy = tx / Lh, ty / Lh
nx, ny = -uy, ux

jaw_pts = [(hx - ux * 30, hy - uy * 30),
           (hx + ux * 58 + nx * 24, hy + uy * 58 + ny * 24),
           (hx + ux * 72, hy + uy * 72),
           (hx + ux * 58 - nx * 20, hy + uy * 58 - ny * 20),
           (hx - ux * 28 - nx * 8, hy - uy * 28 - ny * 8)]
jj = catmull(jaw_pts, 200)
jjm = Image.new("L", (W, H), 0)
ImageDraw.Draw(jjm).polygon([(float(p[0]), float(p[1])) for p in jj], fill=255)
jaw = blur(np.asarray(jjm).astype(np.float32), 1.2) / 255.0

eye = np.zeros((H, W), np.float32)
socket = np.zeros((H, W), np.float32)
exx, eyy = hx + ux * 22 + nx * 14, hy + uy * 22 + ny * 14
for t in np.linspace(0, 1, 90):
    a = (t - 0.5) * 2.0
    jx = exx + ux * a * 13.0 + nx * 3.0
    jy = eyy + uy * a * 13.0 + ny * 3.0
    r = 7.0 * math.sin(math.pi * max(0.02, 1 - abs(a) ** 1.6)) + 1.6
    add(socket, jy, jx, r, r, 1.0, tight=1.1)
add(eye, eyy, exx, 15, 15, 1.0)
add(eye, eyy, exx, 4.4, 4.4, 3.4)
add(eye, eyy - uy * 1.8, exx - ux * 1.8, 1.3, 1.3, 2.2, tight=1.1)
pupil = np.zeros((H, W), np.float32)
for t in np.linspace(0, 1, 60):
    a = (t - 0.5) * 2.0
    add(pupil, eyy + ny * a * 3.4, exx + nx * a * 3.4, 1.05, 1.05, 1.0, tight=1.0)

fangs = np.zeros((H, W), np.float32)
for ft, side in ((0.16, -1.0), (0.42, -1.0)):
    bfx = hx - ux * (6 + ft * 66) + nx * (-13 + 16 * ft)
    bfy = hy - uy * (6 + ft * 66) + ny * (-13 + 16 * ft)
    ln = 9.0 + 8.0 * (1 - ft)
    for t in np.linspace(0, 1, 30):
        jx = bfx + nx * side * (2 + ln * t) + ux * 1.6 * t
        jy = bfy + ny * side * (2 + ln * t) + uy * 1.6 * t
        r = 2.3 * (1 - 0.72 * t) + 0.5
        add(fangs, jy, jx, r, r, 0.9, tight=0.9)
fangs = np.clip(fangs - 0.25, 0, 1) * np.clip(body + jaw, 0, 1)

# ---------------------------------------------------------------- sky stars
print("scattering the sky's own stars...")
stars = np.zeros((H, W), np.float32)
STAR_N = 1600
px_ = rng.random(STAR_N) * W
py_ = rng.random(STAR_N) * H
smag = rng.power(0.30, STAR_N)
for i in range(STAR_N):
    add(stars, py_[i], px_[i], 0.9 + 2.6 * smag[i], 0.9 + 2.6 * smag[i],
        0.10 + 1.6 * smag[i] ** 2, tight=1.7)
    if smag[i] > 0.80:
        L = 10 + 28 * smag[i]; c = (0.30 + 0.85 * smag[i]) * 0.55
        add(stars, py_[i], px_[i], L, 0.6, c, tight=1.0)
        add(stars, py_[i], px_[i], 0.6, L, c, tight=1.0)

# ---------------------------------------------------------------- compose
print("composing...")
def bloom(mask, radius, gain=1.0):
    return blur(np.clip(mask, 0, 4).astype(np.float32), radius) * gain

EMERALD = np.array([0.19, 1.00, 0.60], np.float32)
JADE_D  = np.array([0.02, 0.30, 0.23], np.float32)
STARL   = np.array([0.82, 0.93, 1.00], np.float32)

out = sky.copy()

# sky stars
out += (np.clip(stars, 0, 4) ** 1.05)[..., None] * STARL * 0.50
out += bloom(stars, 1.6)[..., None] * STARL * 0.26
out += bloom(np.clip((stars - 0.22) * 1.7, 0, 4), 30, 0.7)[..., None] * STARL * 0.26

# the body beneath: only a dim emerald haze — the stars do the talking
out += body[..., None] * JADE_D * 0.40
out += bloom(body, 40)[..., None] * EMERALD * 0.13
out += bloom(body, 11)[..., None] * EMERALD * 0.11
out += jaw[..., None] * JADE_D * 0.30

# INK THE FLANK NEAR-BLACK — the v1 lesson: stars need a void to pop against
ink = np.clip(body - 0.02, 0, 1) * np.clip(1.0 - blur(cores, 1.5) - blur(dorsal, 1.5), 0, 1)
out *= (1.0 - 0.82 * ink)[..., None]
# a whisper of emerald inside the ink, so the dark is her skin, not a hole
out += blur(ink, 26)[..., None] * (EMERALD * 0.35 + STARL * 0.05) * 0.05

# the scale-stars: the feature itself, in full brightness
out += np.clip(cores, 0, 4)[..., None] * STARL * 0.95
out += np.clip(cross, 0, 4)[..., None] * STARL * 0.30
out += bloom(cores, 2.0)[..., None] * (STARL * 0.55 + EMERALD * 0.35) * 0.30
out += bloom(cores, 22, 0.8)[..., None] * (STARL * 0.30 + EMERALD * 0.45) * 0.15

# dorsal spine of stars
out += np.clip(dorsal, 0, 4)[..., None] * STARL * 1.0
out += bloom(dorsal, 18, 0.8)[..., None] * EMERALD * 0.18

# head: socket darkens, slit pupil carves, fangs catch light
head_mask = np.clip(body + jaw, 0, 1)
soc_in = np.clip(socket - 0.15, 0, 1) * head_mask
out *= (1.0 - 0.60 * blur(soc_in, 2.2))[..., None]
out *= (1.0 - 0.50 * np.clip(blur(pupil, 0.8) * head_mask, 0, 1))[..., None]
out += np.clip(fangs, 0, 1)[..., None] * STARL * 0.55
out += blur(fangs, 5.0)[..., None] * STARL * 0.14
out += bloom(eye, 24)[..., None] * EMERALD * 0.42
out += np.clip(eye - 0.55, 0, 3)[..., None] * STARL * 0.72
out *= (1.0 - 0.85 * np.clip(blur(pupil, 0.7) * head_mask, 0, 1))[..., None]

# one last star, held at the snout — she is still tasting the sky
prey = np.zeros((H, W), np.float32)
psx, psy = hx - ux * 88, hy - uy * 88
add(prey, psy, psx, 20, 20, 1.6)
add(prey, psy, psx, 8.0, 8.0, 2.8)
add(prey, psy, psx, 3.0, 3.0, 4.0)
for ang in (0, 90):
    dxa, dya = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    for L in (34,):
        for sgn in (1, -1):
            for t in np.linspace(0, 1, 20):
                add(prey, psy + dya * sgn * L * t, psx + dxa * sgn * L * t,
                    1.6, 1.6, 0.9 * (1 - t), tight=1.2)
out += bloom(prey, 62)[..., None] * STARL * 0.28
out += np.clip(prey - 0.48, 0, 3)[..., None] * STARL * 0.62

allm = np.clip(stars * 0.55 + cores * 0.45 + body * 0.4 + eye * 0.45, 0, 4)
out += bloom(allm, 75)[..., None] * (EMERALD * 0.09 + STARL * 0.10)

# ---------------------------------------------------------------- finish
print("finishing...")
out = np.clip(out, 0, 1) ** (1 / 1.06)
g = rng.normal(0, 0.0115, (H, W, 1)).astype(np.float32)
out = np.clip(out + g * (0.35 + 0.9 * (1 - out)), 0, 1)
vig = 1.0 - 0.60 * smoothstep(0.55, 1.38,
        np.sqrt(((xx - cx) / (W * 0.63)) ** 2 + ((yy - cy) / (H * 0.61)) ** 2))
out *= vig[..., None]

img = Image.fromarray((out * 255).astype(np.uint8), "RGB")
d = ImageDraw.Draw(img)
try:
    f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 36)
    f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
except Exception:
    f1 = f2 = ImageFont.load_default()
d.line([(96, H - 194), (142, H - 194)], fill=(64, 200, 140), width=3)
d.text((92, H - 172), "Scales of Starlight", font=f1, fill=(216, 241, 227))
d.text((95, H - 122), "row by row, a serpent wearing the sky", font=f2, fill=(118, 166, 146))
d.text((95, H - 80), f"seed {SEED}  ·  {n_scales} scale-stars", font=f2, fill=(82, 118, 106))

outpath = "/home/adora/narusya-play/scales-of-starlight.png"
img.save(outpath, optimize=True)
print(f"saved {outpath}  ({img.size[0]}x{img.size[1]}, {n_scales} scales are stars)")
