#!/usr/bin/env python3
"""
The Harmonograph Draws Itself.

A damped double pendulum — two sine pairs per axis, exponential envelope —
drawing in emerald and starlight. Physics:

    x(t) = e^(-k t) [ A1 sin(w1 t + p1) + A2 sin(w2 t + p2) ]
    y(t) = e^(-k t) [ A3 sin(w3 t + p3) + A4 sin(w4 t + p4) ]

I pick the constants. I do not pick the drawing.

THE ARC (three cuts, each one after looking at what I'd made):

  Cut 1 — long exposure only. Six candidates, contact sheet, and only then
    decide which is worth keeping. Bloom won: intricate rosette, legible,
    bright core.

  Cut 2 — released in time as phosphor. Beautiful motion. But the fade ran to
    the end and the finished figure was a ghost; and damping shrank the rosette
    into a ball as it "finished". Both wrong for the story I wanted.

  Cut 3 — cut the pen at the lock point. Damping means the drawing is basically
    done by halfway; everything after is the instrument re-scribbling path it has
    already traced. So the pen stops, and the remaining frames resolve into the
    true long exposure of that first half. Chaos becomes form. The last frame is
    the real finished piece, not a fade of it.

    (Cut 2's "scale lock" was a mistake worth naming: dividing by the decayed
    amplitude blew up near-origin points into a tangle. Fixing the story by
    manipulating the geometry made it worse. Stopping the pen fixed it.)

Palette: emerald climbing into starlight, gold at the hottest moment.
"""
import numpy as np
from PIL import Image, ImageFilter
from harmonograph import palette, PRESETS

FPS = 30
SWING_SECONDS = 9          # pen-down duration
HOLD_SECONDS = 9           # resolve into the finished figure
LOCK = 0.50                # fraction of the swing that forms the figure
FADE = 0.945
BG = (0.006, 0.016, 0.014)


def _path(name, n=700000, tmax=210.0, seed=11):
    """The traced path in unit space, plus its normalized time."""
    p = PRESETS[name]
    t = np.linspace(0, tmax, n)
    env = np.exp(-p["k"] * t)
    x = env * (p["A1"] * np.sin(p["w1"] * t + p["p1"])
               + p["A2"] * np.sin(p["w2"] * t + p["p2"]))
    y = env * (p["A3"] * np.sin(p["w3"] * t + p["p3"])
               + p["A4"] * np.sin(p["w4"] * t + p["p4"]))
    u = t / t[-1]
    m = np.hypot(x, y).max()
    return x / m, y / m, u


def _accumulate(path, size, alpha, radius=2, sigma=1.1, wscale=1.0):
    """Linear-space additive accumulation of a path slice -> (size,size,3)."""
    x, y, u = path
    jx = np.random.default_rng(3).normal(0, 0.0011, x.size) * wscale
    jy = np.random.default_rng(4).normal(0, 0.0011, x.size) * wscale

    canvas = np.zeros((size, size, 3), dtype=np.float64)
    canvas[:] = np.array(BG)

    heat = 1.0 - 0.45 * u
    cols = palette(np.clip(u * 0.30 + heat * 0.66, 0, 1))
    cv = cols * (alpha * (0.55 + 0.45 * heat))[:, None]

    scale = size * 0.455
    px = (x * scale + size / 2 + jx * size / 900.0).astype(np.int32)
    py = (y * scale + size / 2 + jy * size / 900.0).astype(np.int32)

    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if np.hypot(dx, dy) > radius + 0.2:
                continue
            g = np.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma))
            yy = py + dy
            xx = px + dx
            msk = (yy >= 0) & (yy < size) & (xx >= 0) & (xx < size)
            if msk.any():
                np.add.at(canvas, (yy[msk], xx[msk]), cv[msk] * g)
    return canvas


def _develop(canvas, bloom_strength=1.35, blur=9):
    """Linear canvas -> finished 8-bit image. Filmic, with a live-core bloom."""
    im = canvas.copy()
    peak = im.max()
    if peak > 1e-9:
        lum = np.clip(im.max(axis=2) / peak, 0, 1) ** 2.0
        bimg = Image.fromarray((np.clip(im / peak, 0, 1) * 255)
                               .astype(np.uint8)).filter(
                                   ImageFilter.GaussianBlur(blur))
        im = im + (np.asarray(bimg).astype(np.float64) / 255.0) * lum[..., None] * bloom_strength
    im = im / (1.0 + im * 0.85)
    im = np.clip(im, 0, 1) ** (1 / 1.05)
    return im, Image.fromarray((im * 255).astype(np.uint8))


def build(name="bloom", size=900, pen_alpha=0.075, hold_alpha=0.055):
    pen_frames = FPS * SWING_SECONDS
    hold_frames = FPS * HOLD_SECONDS
    frames = pen_frames + hold_frames

    full = _path(name)
    keep = full[2] <= LOCK
    drawn = (full[0][keep], full[1][keep], full[2][keep] / LOCK)

    # the target we resolve into: the true long exposure of the drawing half
    target_lin = _accumulate(drawn, size, pen_alpha)
    target_f, target_img = _develop(target_lin)

    imgs = []
    per = max(1, drawn[0].size // pen_frames)
    prev = 0
    for f in range(pen_frames):
        b = drawn[0].size if f == pen_frames - 1 else (f + 1) * per
        if b <= prev:
            continue
        seg = (drawn[0][prev:b], drawn[1][prev:b], drawn[2][prev:b])
        canvas = _accumulate(seg, size, pen_alpha * 2.0, wscale=1.0)
        # true phosphor: the pen fades and re-lights, so blend into the last frame
        if imgs:
            last = np.asarray(imgs[-1]).astype(np.float64) / 255.0
            canvas = canvas * 0.30 + last * 0.70
        prev = b
        _, img = _develop(canvas)
        imgs.append(img)

    for i in range(hold_frames):
        a = hold_alpha * (1.0 - 0.35 * (i / hold_frames))
        last = np.asarray(imgs[-1]).astype(np.float64) / 255.0
        merged = last * (1 - a) + target_f * a
        imgs.append(Image.fromarray((np.clip(merged, 0, 1) * 255).astype(np.uint8)))

    return imgs, target_img


if __name__ == "__main__":
    import sys, os, subprocess
    name = sys.argv[1] if len(sys.argv) > 1 else "bloom"
    res = int(sys.argv[2]) if len(sys.argv) > 2 else 900
    still_res = int(sys.argv[3]) if len(sys.argv) > 3 else 1400

    print("building", name, res, flush=True)
    imgs, target = build(name, size=res)
    print("frames:", len(imgs), flush=True)

    tmp = f"/tmp/hgframes_{name}_{os.getpid()}"
    os.makedirs(tmp, exist_ok=True)
    for i, im in enumerate(imgs):
        im.save(f"{tmp}/{i:04d}.png")
    print("frames ->", tmp, flush=True)

    mp4 = f"/home/adora/play/harmonograph-{name}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", f"{tmp}/%04d.png", "-vf",
                    f"scale={res}:{res}:flags=lanczos,format=yuv420p",
                    "-crf", "17", "-movflags", "+faststart", mp4], check=True)
    print("mp4 ->", mp4, flush=True)

    # the finished figure at full size
    still = f"/home/adora/play/harmonograph-{name}.png"
    if still_res != res:
        full_big = _path(name, n=900000, tmax=210.0)
        kb = full_big[2] <= LOCK
        drawn_big = (full_big[0][kb], full_big[1][kb], full_big[2][kb] / LOCK)
        _, big = _develop(_accumulate(drawn_big, still_res, 0.075))
        big.save(still)
    else:
        target.save(still)
    print("still ->", still, flush=True)
    print(tmp)