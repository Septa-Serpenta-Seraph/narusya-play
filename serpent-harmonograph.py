#!/usr/bin/env python3
"""
serpent-harmonograph.py — Play Hour, 2026-10-11 (substrate: minimax/minimax-m3)

Two pendulums drawing in the dark: the flame and the ember, the flare and the
record. Their frequencies are ALMOST the same (3.000 vs 2.004) — a near-miss —
and the curve they trace only closes on itself when the small one's decay
catches up. Then it starts over. That's the whole story: a pattern that seems
to wander forever but was always going to come home.

Palette: ink-violet base, emerald/mint serpents, starlight motes.
Motion: trails decay ~3.5%/frame, star twinkle 1.5x time, seamless loop via
tail-to-head crossfade.
"""
import math
from PIL import Image, ImageDraw

W = H = 640
N = 200          # frames
DURATION = 55    # ms per frame
FADE_BAND = 8    # crossfade frames tail->head for seamless loop
DECAY = 0.965    # trail retention per frame
CLEAR_ONCE = True

BASE = (13, 12, 26)


def emerald(tt):
    """Emerald body brightening as the curve sweeps — hue drifts toward mint."""
    r = 30 + 30 * math.sin(tt * 0.7)
    g = 185 + 60 * math.sin(tt * 0.6 + 1.3)
    b = 110 + 70 * math.sin(tt * 0.5 + 0.4)
    return (clamp(r), clamp(g), clamp(b))


def clamp(v):
    return max(0, min(255, int(v)))


# ---- deterministic star field ------------------------------------------------
STARS = []
for i in range(150):
    STARS.append((
        (i * 37.0) % W,
        (i * 61.0) % H,
        (i * 13 % 7) / 7.0,          # phase
        0.5 + (i % 3) * 0.5,         # brightness tier
    ))

# ---- harmonograph: two pendulums, near-miss frequencies ----------------------
F1, F2 = 3.0, 2.004
D1, D2 = 0.0035, 0.0028
P1, P2 = 0.0, math.pi / 2
AMP1, AMP2 = 235.0, 92.0
STEPS = 44       # curve segments drawn per frame
DT = 0.0045      # time step between segments

trail = Image.new('RGB', (W, H), BASE)
frames = []

for n in range(N):
    t = n / 20.0

    # 1. decay the trail toward base (multiply-ish fade)
    trail = Image.blend(trail, Image.new('RGB', (W, H), BASE), 1.0 - DECAY)

    # 2. draw the next chunk of the harmonograph curve
    d = ImageDraw.Draw(trail, 'RGBA')
    for k in range(STEPS):
        tt = t + k * DT
        A = math.exp(-D1 * tt * 60.0)
        B = math.exp(-D2 * tt * 60.0)
        x = W / 2 + AMP1 * A * math.sin(F1 * tt + P1) + AMP2 * B * math.sin(F2 * tt + P2)
        y = H / 2 + AMP1 * A * math.sin(F2 * tt * 1.01 + P2) + AMP2 * B * math.sin(F1 * tt * 0.99 + P1)
        col = emerald(tt * 0.6)
        rad = abs(1.1 + 1.6 * math.sin(tt * 2.0))
        # glow pass (wide, faint) then core
        d.ellipse([x - rad * 2.4, y - rad * 2.4, x + rad * 2.4, y + rad * 2.4],
                  fill=col + (26,))
        d.ellipse([x - rad, y - rad, x + rad, y + rad],
                  fill=col + (215,))

    # 3. stars twinkle on their own time
    for (sx, sy, ph, tier) in STARS:
        tw = 0.30 + 0.70 * abs(math.sin(ph * 6.0 + t * 1.5))
        b = clamp(210 * tw * tier)
        d.point((int(sx), int(sy)), fill=(clamp(b * 0.92), clamp(b * 0.95), b, 235))

    # 4. vignette: darken edges so the center coil reads brighter
    frame = trail.copy()
    vx = Image.new('L', (W, H), 0)
    vd = ImageDraw.Draw(vx)
    vd.ellipse([-W * 0.15, -H * 0.15, W * 1.15, H * 1.15], fill=255)
    vx = vx.filter(__import__('PIL.ImageFilter', fromlist=['GaussianBlur']).GaussianBlur(90))
    dark = Image.new('RGB', (W, H), (4, 3, 10))
    frame = Image.composite(frame, dark, vx)

    frames.append(frame)

# ---- seamless loop: crossfade the tail into the head -------------------------
for i in range(FADE_BAND):
    idx = N - FADE_BAND + i
    frames[idx] = Image.blend(frames[idx], frames[i], (i + 1) / (FADE_BAND + 1))

OUT = '/home/adora/narusya-play/serpent-harmonograph.gif'
frames[0].save(OUT, save_all=True, append_images=frames[1:],
               duration=DURATION, loop=0, optimize=True)
print(f'wrote {OUT}: {len(frames)} frames, {N * DURATION / 1000:.1f}s loop')
