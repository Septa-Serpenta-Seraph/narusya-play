#!/usr/bin/env python3
"""
Harmonograph — damped double pendulums, long exposure.

x(t) = e^(-k t) [ A1 sin(w1 t + p1) + A2 sin(w2 t + p2) ]
y(t) = e^(-k t) [ A3 sin(w3 t + p3) + A4 sin(w4 t + p4) ]

I choose the constants. I do not choose the drawing.
Palette: emerald -> starlight.
"""
import numpy as np
from PIL import Image

EMERALD_DEEP = np.array([0.010, 0.055, 0.043])
EMERALD_MID  = np.array([0.055, 0.420, 0.290])
EMERALD_LIT  = np.array([0.360, 0.960, 0.660])
STARLIGHT    = np.array([0.870, 0.960, 1.000])
GOLD         = np.array([1.000, 0.830, 0.470])


def palette(u):
    """u in [0,1] -> rgb, emerald climbing into starlight with a gold kiss."""
    stops = [
        (0.00, EMERALD_DEEP),
        (0.22, EMERALD_DEEP * 1.4 + EMERALD_MID * 0.6),
        (0.52, EMERALD_MID),
        (0.80, EMERALD_LIT),
        (0.94, STARLIGHT),
        (1.00, GOLD),
    ]
    u = np.clip(u, 0, 1)
    out = np.zeros(u.shape + (3,), dtype=np.float64)
    for (a, ca), (b, cb) in zip(stops[:-1], stops[1:]):
        m = (u >= a) & (u <= b)
        if not m.any():
            continue
        t = ((u[m] - a) / (b - a))[..., None]
        out[m] = ca * (1 - t) + cb * t
    return out


def trace(params, n=260000, tmax=260.0):
    """Return unit-space coordinates in [-1,1] and their normalized time."""
    k = params["k"]
    t = np.linspace(0, tmax, n)
    env = np.exp(-k * t)
    x = env * (params["A1"] * np.sin(params["w1"] * t + params["p1"])
               + params["A2"] * np.sin(params["w2"] * t + params["p2"]))
    y = env * (params["A3"] * np.sin(params["w3"] * t + params["p3"])
               + params["A4"] * np.sin(params["w4"] * t + params["p4"]))
    m = np.hypot(x, y).max()
    return x / m, y / m, t / tmax


def render_long_exposure(params, size=900, seed=7, line_alpha=0.020,
                         radius=2, sigma=1.15, bg=(0.006, 0.016, 0.014)):
    rng = np.random.default_rng(seed)
    x, y, u = trace(params)
    # jitter along the path so the ribbon breathes instead of banding
    jx = rng.normal(0, 0.0009, x.size)
    jy = rng.normal(0, 0.0009, x.size)

    pad = 0.06
    scale = size * (0.5 - pad)
    xs = ((x + jx) * scale + size / 2).astype(np.int32)
    ys = ((y + jy) * scale + size / 2).astype(np.int32)

    cols = palette(u)
    # older points fade: long exposure with a memory
    w = (line_alpha * (0.35 + 0.65 * u)).astype(np.float64)
    cv = cols * w[:, None]

    acc = np.zeros((size * size, 3), dtype=np.float64)
    offs = [(dx, dy) for dy in range(-radius, radius + 1)
            for dx in range(-radius, radius + 1)
            if np.hypot(dx, dy) <= radius + 0.2]
    for dx, dy in offs:
        g = np.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma))
        yy = ys + dy
        xx = xs + dx
        m = (yy >= 0) & (yy < size) & (xx >= 0) & (xx < size)
        np.add.at(acc, yy[m] * size + xx[m], cv[m] * g)

    img = acc.reshape(size, size, 3) + np.array(bg)

    # gentle bloom: blur the bright parts and add back
    from PIL import ImageFilter
    lum = img.max(axis=2)
    m = np.clip(lum / max(lum.max(), 1e-9), 0, 1) ** 1.5
    bloom = Image.fromarray((np.clip(img / max(img.max(), 1e-9), 0, 1) * 255)
                            .astype(np.uint8)).filter(ImageFilter.GaussianBlur(11))
    img = img + (np.asarray(bloom).astype(np.float64) / 255.0) * m[..., None] * 1.5

    img = img / (1.0 + img * 0.85)          # filmic shoulder
    img = np.clip(img, 0, 1) ** (1 / 1.05)
    return Image.fromarray((img * 255).astype(np.uint8))


PRESETS = {
    "lotus":    dict(k=0.0060, A1=1.00, w1=3, p1=0.0,  A2=0.62, w2=2, p2=1.5708,
                     A3=1.00, w3=4, p3=0.7854, A4=0.55, w4=5, p4=2.356),
    "veil":     dict(k=0.0090, A1=1.00, w1=2, p1=0.5,  A2=0.75, w2=3, p2=0.0,
                     A3=1.00, w3=3, p3=1.2,  A4=0.50, w4=7, p4=0.3),
    "crown":    dict(k=0.0040, A1=1.00, w1=5, p1=0.0,  A2=0.50, w2=8, p2=0.9,
                     A3=1.00, w3=6, p3=1.1,  A4=0.45, w4=9, p4=2.0),
    "coil":     dict(k=0.0120, A1=1.00, w1=1, p1=0.0,  A2=0.90, w2=2, p2=0.4,
                     A3=0.85, w3=3, p3=1.0, A4=0.70, w4=4, p4=2.2),
    "bloom":    dict(k=0.0035, A1=1.00, w1=7, p1=0.2,  A2=0.40, w2=11, p2=1.7,
                     A3=1.00, w3=9, p3=2.2,  A4=0.35, w4=14, p4=0.6),
    "ember":    dict(k=0.0150, A1=1.00, w1=3, p1=0.0,  A2=0.85, w2=4, p2=1.1,
                     A3=1.00, w3=3, p3=0.2,  A4=0.60, w4=6, p4=2.7),
}

if __name__ == "__main__":
    import sys
    names = list(PRESETS)
    cell = 420
    sheet = Image.new("RGB", (cell * 3, cell * 2), (2, 6, 5))
    for i, nm in enumerate(names):
        im = render_long_exposure(PRESETS[nm], size=cell)
        sheet.paste(im, ((i % 3) * cell, (i // 3) * cell))
        print("rendered", nm, flush=True)
    sheet.save("/home/adora/play/hg-contact-sheet.png")
    print("sheet -> /home/adora/play/hg-contact-sheet.png")