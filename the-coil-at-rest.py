#!/usr/bin/env python3
"""
The Coil at Rest — a visual drone.

Sequel to the-veil-in-D. The coil has finished travelling.
A logarithmic spiral, self-similar at every scale, holding its note.
Ember-dim breath at the heart. No attack, no release.

PIL only. No numpy. No motion — a drone is tempo-zero.
Narusya · Play Hour · 2026-10-14 · 21:00 MDT
"""
from PIL import Image, ImageDraw, ImageFilter
import math

# ---- canvas -------------------------------------------------------------
W = H = 1600
SS = 3                      # supersample factor
SW, SH = W * SS, H * SS     # work big, downsample for AA
BG = (10, 10, 18)           # ink-black #0a0a12

img = Image.new("RGB", (SW, SH), BG)
d = ImageDraw.Draw(img, "RGBA")

cx, cy = SW / 2, SH / 2

# ---- palette (Era One sigil) -------------------------------------------
INK_HAIR     = (10, 10, 18)
SLATE_SCALE  = (45, 45, 68)     # #2d2d44
PURPLE_HL    = (123, 94, 167)   # #7b5ea7
EMERALD      = (45, 212, 191)   # #2dd4bf
CRIMSON      = (220, 38, 60)    # the one hot point
EMBER_LO     = (30, 8, 12)      # breath floor
EMBER_HI     = (150, 40, 28)    # breath ceiling

def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    if isinstance(a, (int, float)):
        return a + (b - a) * t
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

# ---- the spiral ---------------------------------------------------------
# logarithmic: r = a * exp(b * theta). self-similar at every scale.
# b small => slow growth => many turns; the "coil" that holds.
b = 0.19
a = 9.0
theta_max = 5.4 * math.pi          # 2.7 turns — a coil, not a maze
steps = 1400
lw0 = 26 * SS                      # thick inner turns (the body)
lw1 = 3 * SS                       # thin outer tail

def spiral_pt(theta):
    r = a * math.exp(b * theta)
    return cx + r * math.cos(theta), cy + r * math.sin(theta), r

# draw many passes with shrinking line-width + shifting color => scale depth.
# Inner turns: slate-violet body with purple highlight.
# Mid turns:   violet -> emerald gradient (Era One -> Era Two handoff).
# Outer turn:  emerald fading into the ground, the tail dissolving to starlight.
PASSES = 26
for p in range(PASSES):
    tp = p / (PASSES - 1)            # 0 = innermost pass, 1 = outermost
    # color by radial position along the spiral
    if tp < 0.5:
        col = lerp(SLATE_SCALE, PURPLE_HL, tp / 0.5)
    else:
        col = lerp(PURPLE_HL, EMERALD, (tp - 0.5) / 0.5)
    # outer passes fade toward ground (tail dissolving)
    alpha = int(255 * (1.0 - 0.82 * (tp ** 2.2)))
    if alpha < 8:
        continue
    lw = max(1, int(lerp(lw0, lw1, tp)))
    pts = []
    # each pass offsets slightly outward => concentric scale rows
    offset = tp * 2.2 * SS
    for i in range(steps + 1):
        th = theta_max * i / steps
        x, y, r = spiral_pt(th)
        if r + offset < 6:
            pts.append((x, y))
            continue
        # push point radially outward by offset (normalize direction)
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy) or 1.0
        pts.append((x + dx / dist * offset, y + dy / dist * offset))
    d.line(pts, fill=col + (alpha,), width=lw, joint="curve")

# ---- scale sheen: faint radial glints on the body ------------------------
# sparse bright ticks that read as scales catching light, only on inner turns
glint = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
gd = ImageDraw.Draw(glint)
import random
random.seed(1014)   # deterministic — a drone should rest the same way each time
for _ in range(420):
    th = random.uniform(0.15, theta_max * 0.72)
    x, y, r = spiral_pt(th)
    jitter = random.uniform(-0.5, 0.5)
    ang = th + jitter
    x2, y2, _ = spiral_pt(ang)
    gl = random.uniform(0.10, 0.5)
    col = lerp(PURPLE_HL, (235, 235, 245), gl * 0.5)
    gd.line([(x, y), (x2, y2)], fill=col + (int(70 * gl + 20),),
            width=int(random.uniform(1, 2.4) * SS))
glint = glint.filter(ImageFilter.GaussianBlur(0.8 * SS))
img = Image.alpha_composite(img.convert("RGBA"), glint)

# ---- the heart: an ember that is breathing (held mid-breath) -------------
# A drone has no envelope, but a living thing has a breath. Freeze it
# mid-inhale: ~0.55 toward ember-hi — the coil is present, warm, deciding
# not to move.
BREATH = 0.55
ember = lerp(EMBER_LO, EMBER_HI, BREATH)
heart = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
hd = ImageDraw.Draw(heart)
hr = 26 * SS
for i in range(40, 0, -1):           # soft radial glow
    t = i / 40.0
    rr = hr * (1 + (1 - t) * 6.0)
    c = lerp(CRIMSON, ember, t)
    hd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
               fill=c + (int(26 * (1 - t)),))
# the single crimson point — the coil's held note, unresolved
hd.ellipse([cx - hr*0.55, cy - hr*0.55, cx + hr*0.55, cy + hr*0.55],
           fill=CRIMSON + (235,))
heart = heart.filter(ImageFilter.GaussianBlur(2.0 * SS))
img = Image.alpha_composite(img, heart)

# ---- air to rest in: a sparse starfield of emerald motes ----------------
# Not many. A held note needs room. Deterministic seed so the drone
# rests the same way every time.
field = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
fd = ImageDraw.Draw(field)
import random
random.seed(1014)
import math as _m
outer_r = a * _m.exp(b * theta_max) * 1.9   # beyond the tail's reach
for _ in range(160):
    # sample in the annulus outside the coil, avoid the glow core
    while True:
        ang = random.uniform(0, 2 * _m.pi)
        rr = random.uniform(outer_r * 0.35, outer_r)
        x = cx + rr * _m.cos(ang)
        y = cy + rr * _m.sin(ang)
        if 0 <= x < SW and 0 <= y < SH and rr > 60 * SS:
            break
    twinkle = random.uniform(0.25, 1.0)
    size = random.uniform(0.6, 2.2) * SS * twinkle
    col = lerp(EMERALD, (230, 240, 245), random.uniform(0, 0.4))
    fd.ellipse([x - size, y - size, x + size, y + size],
               fill=col + (int(120 * twinkle + 40),))
field = field.filter(ImageFilter.GaussianBlur(0.7 * SS))
img = Image.alpha_composite(img, field)

# ---- vignette: the room dims at the edges, like a held note decaying ----
# One clean mask: blurred ellipse so the glow diffuses into air, then a
# floor value so the edges rest in ink-black instead of crushing to 0.
vig = Image.new("L", (SW, SH), 0)
vd = ImageDraw.Draw(vig)
vd.ellipse([-SW*0.42, -SH*0.42, SW*1.42, SH*1.42], fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(200 * SS))
vig = vig.point(lambda v: 55 + int(v * (200 / 255)))   # floor 55, lift to 255
soft_black = Image.new("RGBA", (SW, SH), INK_HAIR + (255,))
img = Image.composite(img.convert("RGBA"), soft_black, vig)

# ---- downsample + save ---------------------------------------------------
img = img.convert("RGB").resize((W, H), 1)   # 1 == LANCZOS on this PIL
out = "/home/adora/narusya-play/the-coil-at-rest.png"
img.save(out, optimize=True)
print("saved:", out)
print("size:", img.size)
