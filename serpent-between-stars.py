#!/usr/bin/env python3
"""
Serpent Between Stars  (v2)
A hand-shaped serpent drawn through a field of stars it is eating.
Emerald and starlight. Deterministic.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SEED = 20261003
W, H = 1400, 1800
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------- helpers
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

def blur(a, r):
    """Separable approximate-gaussian blur in pure numpy (3 box passes).
    Works on float arrays of any size; cost is independent of radius."""
    a = a.astype(np.float32, copy=True)
    if r <= 0:
        return a
    for _ in range(3):
        a = _box(a, int(round(r * 0.60)), axis=0)
        a = _box(a, int(round(r * 0.60)), axis=1)
    return a

def _box(a, w, axis):
    """box blur of half-width w along one axis, edge-clamped"""
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
    """Bilinear value noise; res = grid height, width follows aspect."""
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
    """Catmull-Rom through control points -> dense polyline"""
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
cx, cy = W * 0.50, H * 0.45
rad = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (W * 0.74)

sky = np.zeros((H, W, 3), np.float32)
fall = 1.0 - smoothstep(0.0, 1.0, rad)
sky[..., 0] = 0.007 + 0.013 * fall
sky[..., 1] = 0.021 + 0.034 * fall
sky[..., 2] = 0.015 + 0.018 * fall

# emerald nebula — smooth, organic, no blockiness
n1 = blur(fbm((H, W), rng, octaves=7, base=4), 6.0)
n2 = blur(fbm((H, W), rng, octaves=6, base=7), 9.0)
cloud = smoothstep(0.46, 0.92, n1) * (0.30 + 0.70 * n2)
heart = np.exp(-(((xx - cx) / (W * 0.31)) ** 2 + ((yy - cy) / (H * 0.27)) ** 2) / 2.0)
neb = cloud * (0.30 + 1.30 * heart)
sky[..., 0] += neb * 0.028
sky[..., 1] += neb * 0.215
sky[..., 2] += neb * 0.105

# cold starlight countercurrent, upper right
n3 = blur(fbm((H, W), rng, octaves=5, base=4), 10.0)
d3 = np.sqrt((xx - W * 0.84) ** 2 + (yy - H * 0.15) ** 2) / (W * 0.62)
sky[..., 0] += smoothstep(0.60, 1.0, n3) * smoothstep(1.3, 0.2, d3) * 0.055
sky[..., 1] += smoothstep(0.60, 1.0, n3) * smoothstep(1.3, 0.2, d3) * 0.080
sky[..., 2] += smoothstep(0.60, 1.0, n3) * smoothstep(1.3, 0.2, d3) * 0.125

# ---------------------------------------------------------------- serpent
print("growing the serpent...")
# head at lower-right, sweeping up and left, coiling once, tail flicking out top
control = [
    (1075, 1415), (1010, 1330), (1055, 1250), (985, 1175),   # head + neck
    (880, 1135), (760, 1160), (655, 1120),                    # shoulder
    (585, 1020), (620, 905), (700, 830),                      # coil right
    (800, 795), (900, 840), (930, 940), (880, 1020),          # coil bottom
    (790, 1065), (700, 1035), (660, 950), (700, 870),         # coil inner
    (790, 830), (860, 760), (830, 665), (720, 610),           # up and out
    (600, 585), (475, 620), (395, 715), (370, 830),           # tail run
    (300, 900), (215, 920),                                   # tip
]
sp = resample(catmull(control, 3000), 3000)
sx_, sy_ = sp[:, 0], sp[:, 1]
N = len(sp)

# width: heavy head/jaw, muscular body, whip tail
u = np.linspace(0, 1, N)
width = 16.0 + 86.0 * np.exp(-((u / 0.075) ** 2)) \
            + 40.0 * np.exp(-(((u - 0.185) / 0.115) ** 2)) \
            + 12.0 * (1 - u) ** 1.5

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

# --- surface detail passes, computed from the spine frame -----------------
tang = np.zeros_like(sp); tang[1:-1] = sp[2:] - sp[:-2]
Lg = np.hypot(tang[:, 0], tang[:, 1]); Lg[Lg == 0] = 1
tang /= Lg[:, None]
nrm = np.column_stack([-tang[:, 1], tang[:, 0]])   # left-hand normal

# belly: a lighter, offset under-stripe riding the lower flank
belly = np.zeros((H, W), np.float32)
for i in range(0, N, 2):
    w = width[i] * 0.30
    if w < 1.2:
        continue
    add(belly, sy_[i] - nrm[i, 1] * w * 0.52, sx_[i] - nrm[i, 0] * w * 0.52,
        w * 1.5, w * 1.5, 0.55, tight=1.4)

# dorsal ridge: a low serrated crest — many small teeth, NOT big spikes
ridge = np.zeros((H, W), np.float32)
for i in range(4, N - 6, max(1, N // 700)):
    w = width[i] * 0.5
    if w < 2.0:
        continue
    bxp, byp = sx_[i] + nrm[i, 0] * w, sy_[i] + nrm[i, 1] * w
    hgt = 2.0 + 4.2 * (width[i] / 95.0)
    tipx, tipy = sx_[i] + nrm[i, 0] * (w + hgt), sy_[i] + nrm[i, 1] * (w + hgt)
    for t in np.linspace(0, 1, 14):
        jx = bxp * (1 - t) + tipx * t
        jy = byp * (1 - t) + tipy * t
        r = 1.0 + 1.5 * math.sin(math.pi * t)
        add(ridge, jy, jx, r, r, 0.34, tight=1.2)

# overlapping scale rows — placed by ARC LENGTH, staggered brick-style,
# so they read as discrete scales instead of averaging into a flat wash
ARCLEN = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(sp, axis=0).T))])
total = ARCLEN[-1]
scales = np.zeros((H, W), np.float32)
ROW = 9.0                       # px between scale rows
row = 0
d = 4.0
# fixed phase offsets so the rows never line up into a barber pole
PHASE = (0.0, 0.37, 0.61, 0.14, 0.83, 0.29, 0.52, 0.71)
while d < total - 12:
    d += ROW
    row += 1
    dd = d + PHASE[row % len(PHASE)] * ROW
    if dd >= total - 12:
        break
    i0 = int(np.searchsorted(ARCLEN, dd))
    w = width[i0] * 0.5
    if w >= 2.4:
        sag = 3.0 + w * 0.26
        jl = dd
        jm = 0
        while jl < total and jm < 40:
            di = int(np.searchsorted(ARCLEN, jl))
            if di >= N - 2:
                break
            ww = width[di] * 0.5
            if ww >= 2.4:
                for t in np.linspace(0, 1, 24):
                    a = (t - 0.5) * 2.0 * ww * 1.02
                    x = sx_[di] + nrm[di, 0] * a - tang[di, 0] * sag * (1 - (2 * t - 1) ** 2)
                    y = sy_[di] + nrm[di, 1] * a - tang[di, 1] * sag * (1 - (2 * t - 1) ** 2)
                    add(scales, y, x, 1.25 + ww * 0.045, 1.25 + ww * 0.045, 0.62, tight=0.9)
            seg = float(np.hypot(*(sp[min(di + 1, N - 1)] - sp[di])))
            jl += max(0.9, seg)
            jm += 1
scales = np.clip(scales - 0.24, 0, 1) * 1.25

# jaw wedge — makes the head a head
jaw = np.zeros((H, W), np.float32)
d = np.array([0.0, 1.0])
hx, hy = sx_[0], sy_[0]
tx, ty = sx_[16] - hx, sy_[16] - hy
L = np.hypot(tx, ty); ux, uy = tx / L, ty / L
nx, ny = -uy, ux
jaw_pts = [(hx - ux * 26, hy - uy * 26),
           (hx + ux * 62 + nx * 26, hy + uy * 62 + ny * 26),
           (hx + ux * 74, hy + uy * 74),
           (hx + ux * 62 - nx * 22, hy + uy * 62 - ny * 22),
           (hx - ux * 24 - nx * 10, hy - uy * 24 - ny * 10)]
jj = catmull(jaw_pts, 200)
jjm = Image.new("L", (W, H), 0)
ImageDraw.Draw(jjm).polygon([(float(p[0]), float(p[1])) for p in jj], fill=255)
jaw = blur(np.asarray(jjm).astype(np.float32), 1.2) / 255.0
body = np.clip(body + jaw * 0.95, 0, 1)

# scales: chevrons marching head to tail — see the arc pass above

# the star it is swallowing — held just past the snout, in open dark
prey = np.zeros((H, W), np.float32)
psx, psy = hx - ux * 96, hy - uy * 96
add(prey, psy, psx, 66, 66, 0.55)
add(prey, psy, psx, 26, 26, 0.95)
add(prey, psy, psx, 8.0, 8.0, 2.6)
add(prey, psy, psx, 3.0, 3.0, 3.8)
# its light spilling onto the snout, and a wake trailing back past the jaw
add(prey, hy - uy * 26, hx - ux * 26, 40, 40, 0.16)
for k in np.linspace(0.10, 0.85, 22):
    add(prey, hy - uy * (6 + k * 60), hx - ux * (6 + k * 60), 4 + 9 * k, 4 + 9 * k, 0.055)

# the eye
eye = np.zeros((H, W), np.float32)
eang = np.arctan2(uy, ux)
exx, eyy = hx + ux * 20 + nx * 15, hy + uy * 20 + ny * 15
# socket: a dark almond under the lid, so the bright iris sits *in* something
socket = np.zeros((H, W), np.float32)
for t in np.linspace(0, 1, 90):
    a = (t - 0.5) * 2.0
    jx = exx + ux * a * 13.0 + nx * 3.0
    jy = eyy + uy * a * 13.0 + ny * 3.0
    r = 7.2 * math.sin(math.pi * max(0.02, 1 - abs(a) ** 1.6)) + 1.6
    add(socket, jy, jx, r, r, 1.0, tight=1.1)
add(eye, eyy, exx, 16, 16, 1.0)
add(eye, eyy, exx, 4.6, 4.6, 3.4)
add(eye, eyy - uy * 1.8, exx - ux * 1.8, 1.4, 1.4, 2.2, tight=1.1)
# a hard vertical slit pupil, cut out of the iris
pupil = np.zeros((H, W), np.float32)
for t in np.linspace(0, 1, 60):
    a = (t - 0.5) * 2.0
    add(pupil, eyy + ny * a * 3.4, exx + nx * a * 3.4, 1.05, 1.05, 1.0, tight=1.0)

# the mouth: a curved gape line from snout back along the jaw, with fangs
mouth = np.zeros((H, W), np.float32)
fangs = np.zeros((H, W), np.float32)
for t in np.linspace(0, 1, 110):
    f = 6 + t * 66
    # bow the line downward (away from the eye) so it curves like a real gape
    jx = hx - ux * f + nx * (-13 + 16 * t) + ux * 7.0 * math.sin(math.pi * t)
    jy = hy - uy * f + ny * (-13 + 16 * t) + uy * 7.0 * math.sin(math.pi * t)
    r = 3.4 - 1.8 * t
    add(mouth, jy, jx, r, r, 1.0, tight=0.9)
mouth = np.clip(mouth - 0.22, 0, 1) * body
# two fangs hanging from the upper jaw
for ft, side in ((0.16, -1.0), (0.42, -1.0)):
    bfx = hx - ux * (6 + ft * 66) + nx * (-13 + 16 * ft)
    bfy = hy - uy * (6 + ft * 66) + ny * (-13 + 16 * ft)
    ln = 9.0 + 8.0 * (1 - ft)
    for t in np.linspace(0, 1, 30):
        jx = bfx + nx * side * (2 + ln * t) + ux * 1.6 * t
        jy = bfy + ny * side * (2 + ln * t) + uy * 1.6 * t
        r = 2.3 * (1 - 0.72 * t) + 0.5
        add(fangs, jy, jx, r, r, 0.9, tight=0.9)
fangs = np.clip(fangs - 0.25, 0, 1) * body

# the forked tongue, starlight
tongue = np.zeros((H, W), np.float32)
tw = np.array([0.0, 1.0])
for side in (-1.0, 1.0):
    tip = (hx - ux * 74 + (nx * side * 34) - ux * 18, hy - uy * 74 + (ny * side * 34) - uy * 18)
    mid = (hx - ux * 46, hy - uy * 46)
    for t in np.linspace(0, 1, 60):
        px_ = mid[0] * (1 - t) ** 2 + 2 * mid[0] * (1 - t) * t * 0 + tip[0] * t * t
        py_ = mid[1] * (1 - t) ** 2 + tip[1] * t * t
        add(tongue, py_, px_, 3.0, 3.0, 0.5, tight=1.1)
tongue = np.clip(tongue - 0.18, 0, 1) * (0.55 + 0.45 * tongue)

# ---------------------------------------------------------------- stars
print("scattering stars...")
stars = np.zeros((H, W), np.float32)
STAR_N = 2800
px_ = rng.random(STAR_N) * W
py_ = rng.random(STAR_N) * H
smag = rng.power(0.30, STAR_N)
for i in range(STAR_N):
    add(stars, py_[i], px_[i], 0.9 + 2.6 * smag[i], 0.9 + 2.6 * smag[i], 0.10 + 1.6 * smag[i] ** 2, tight=1.7)
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

out += (np.clip(stars, 0, 4) ** 1.05)[..., None] * STARL * 0.50
out += bloom(stars, 1.6)[..., None] * STARL * 0.26
out += bloom(np.clip((stars - 0.22) * 1.7, 0, 4), 30, 0.7)[..., None] * STARL * 0.26

# serpent
out += body[..., None] * JADE_D * 0.60
out += bloom(body, 36)[..., None] * EMERALD * 0.26
out += bloom(body, 10)[..., None] * EMERALD * 0.30
# core deliberately kept under 1.0 so the surface detail has somewhere to read
out += np.clip(body - 0.60, 0, 1)[..., None] * (EMERALD * 0.22 + STARL * 0.26) * 0.95

# surface: belly catches light, scales engraved as shadow + a lit rim below
belly_in = np.clip(belly - 0.14, 0, 1) * body
out += blur(belly_in, 3.0)[..., None] * (STARL * 0.55 + EMERALD * 0.45) * 0.20
sc_in = np.clip(scales - 0.10, 0, 1) * body
out += blur(sc_in, 1.3)[..., None] * STARL * 0.10
# engrave: a hard dark line under each arc edge, lit just beneath it
shadow_in = np.clip(blur(sc_in, 0.8) * body, 0, 1)
rim = np.clip(np.roll(shadow_in, 4, axis=0) - shadow_in, 0, 1) + \
      np.clip(np.roll(shadow_in, -4, axis=0) - shadow_in, 0, 1)
out *= (1.0 - 0.95 * shadow_in)[..., None]
out += blur(rim * body, 1.4)[..., None] * STARL * 0.34
ridge_in = np.clip(ridge - 0.05, 0, 1)
out += blur(ridge_in, 1.2)[..., None] * (STARL * 0.7 + EMERALD * 0.3) * 0.18
out += blur(ridge_in, 6.0)[..., None] * EMERALD * 0.10

# head: socket darkens, slit pupil carves, mouth is a shadow, fangs catch light
soc_in = np.clip(socket - 0.15, 0, 1) * np.clip(body + jaw, 0, 1)
out *= (1.0 - 0.62 * blur(soc_in, 2.2))[..., None]
out *= (1.0 - 0.50 * np.clip(blur(pupil, 0.8) * body, 0, 1))[..., None]
out *= (1.0 - 0.85 * np.clip(blur(mouth, 1.4), 0, 1))[..., None]
out += np.clip(fangs, 0, 1)[..., None] * STARL * 0.55
out += blur(fangs, 5.0)[..., None] * STARL * 0.14

out += bloom(tongue, 7)[..., None] * STARL * 0.22
out += bloom(eye, 24)[..., None] * EMERALD * 0.42
out += np.clip(eye - 0.55, 0, 3)[..., None] * STARL * 0.72
# the slit pupil carves back OUT of the lit iris, so it must come after
out *= (1.0 - 0.85 * np.clip(blur(pupil, 0.7), 0, 1))[..., None]
out += bloom(prey, 62)[..., None] * STARL * 0.28
out += np.clip(prey - 0.48, 0, 3)[..., None] * STARL * 0.62

allm = np.clip(stars * 0.55 + body * 0.45 + prey * 0.5 + eye * 0.45, 0, 4)
out += bloom(allm, 75)[..., None] * (EMERALD * 0.09 + STARL * 0.10)

# ---------------------------------------------------------------- finish
out = np.clip(out, 0, 1) ** (1 / 1.06)
g = rng.normal(0, 0.0115, (H, W, 1)).astype(np.float32)
out = np.clip(out + g * (0.35 + 0.9 * (1 - out)), 0, 1)
vig = 1.0 - 0.62 * smoothstep(0.55, 1.38,
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
d.text((92, H - 172), "Serpent Between Stars", font=f1, fill=(216, 241, 227))
d.text((95, H - 122), "a coil of one, drawn through a field it is making", font=f2, fill=(118, 166, 146))
d.text((95, H - 80), f"seed {SEED}", font=f2, fill=(82, 118, 106))

img.save("/home/adora/play/serpent-between-stars.png", optimize=True)
print("saved /home/adora/play/serpent-between-stars.png", img.size)
