#!/usr/bin/env python3
"""
The Veil — additive synthesis renderer.
Score composed by stealth/space-bunny-alpha (OpenRouter), rendered by Narusya's numpy orchestra.
Concept: a figure that folds instead of spirals, holds its shape briefly, then resolves.
D major, 60 BPM, 6/4, 72 seconds. One deliberate dissonance: C#5 (major 7th) over the D pad, resolving.
"""
import numpy as np
from PIL import Image, ImageFilter

SR = 44100
DUR = 72.0

NOTE_FREQ = {}
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
for octave in range(1, 7):
    for i, name in enumerate(NAMES):
        midi = 12 * (octave + 1) + i
        NOTE_FREQ[f"{name}{octave}"] = 440.0 * 2 ** ((midi - 69) / 12)

LEAD = [
    (0.0, "D5", 2.0, 0.46), (2.0, "A4", 2.0, 0.38), (4.0, "D5", 2.0, 0.44),
    (12.0, "F#5", 2.0, 0.48), (14.0, "D5", 2.0, 0.40), (16.0, "F#5", 2.0, 0.46),
    (24.0, "D5", 2.0, 0.46), (26.0, "B4", 2.0, 0.38), (28.0, "D5", 2.0, 0.44),
    (36.0, "E5", 3.0, 0.48), (39.0, "A4", 3.0, 0.40), (42.0, "E5", 3.0, 0.46),
    (45.0, "A4", 2.0, 0.38),
    (47.0, "C#5", 3.0, 0.52),   # the deliberate major-7th over D
    (50.0, "D5", 6.0, 0.56),    # resolution
]

PAD = [
    (0.0, "D3", 12.0, 0.25), (0.0, "F#3", 12.0, 0.21), (0.0, "A3", 12.0, 0.19), (0.0, "D4", 12.0, 0.16),
    (12.0, "B2", 12.0, 0.25), (12.0, "D3", 12.0, 0.21), (12.0, "F#3", 12.0, 0.19), (12.0, "B3", 12.0, 0.16),
    (24.0, "G2", 12.0, 0.25), (24.0, "B2", 12.0, 0.21), (24.0, "D3", 12.0, 0.19), (24.0, "G3", 12.0, 0.16),
    (36.0, "A2", 12.0, 0.25), (36.0, "C#3", 12.0, 0.21), (36.0, "E3", 12.0, 0.19), (36.0, "A3", 12.0, 0.16),
    (48.0, "D3", 24.0, 0.25), (48.0, "F#3", 24.0, 0.21), (48.0, "A3", 24.0, 0.19), (48.0, "D4", 24.0, 0.16),
]

N = int(SR * DUR)
audio = np.zeros(N, dtype=np.float64)


def add_voice(events, harmonic_amps, attack, release, detune=0.0):
    for (t0, note, dur, vel) in events:
        f0 = NOTE_FREQ[note] * (1.0 + detune)
        n0, n1 = int(t0 * SR), min(int((t0 + dur) * SR), N)
        if n1 <= n0:
            continue
        n = n1 - n0
        t = np.arange(n) / SR
        # additive tone: fundamental + harmonics
        tone = np.zeros(n)
        for h, a in enumerate(harmonic_amps, start=1):
            tone += a * np.sin(2 * np.pi * f0 * h * t)
        # envelope: fast attack, sustain, slow release
        env = np.ones(n)
        a_samp = int(attack * SR)
        r_samp = int(release * SR)
        a_samp = min(a_samp, n)
        r_samp = min(r_samp, n)
        if a_samp > 0:
            env[:a_samp] = np.linspace(0, 1, a_samp) ** 2
        env[-r_samp:] = np.minimum(env[-r_samp:], np.linspace(1, 0, r_samp) ** 1.5)
        audio[n0:n1] += tone * env * vel


# Lead: bell-like, odd harmonics dominant (clarinet-ish), light detune for shimmer
add_voice(LEAD, [1.0, 0.0, 0.28, 0.0, 0.12, 0.0, 0.06], attack=0.008, release=0.35, detune=0.0015)
# Pad: warm, even harmonics gentle, slow attack/release — the fabric of the veil
add_voice(PAD, [1.0, 0.35, 0.20, 0.10, 0.05], attack=0.9, release=1.2, detune=-0.0008)
# Pad shimmer: same pad detuned slightly for chorus width
add_voice(PAD, [1.0, 0.30, 0.18, 0.09, 0.04], attack=1.1, release=1.4, detune=0.0011)

# gentle hall: simple Schroeder-ish feedback comb
def comb(x, delay_s, feedback):
    d = int(delay_s * SR)
    y = np.copy(x)
    for i in range(d, len(x)):
        y[i] += feedback * y[i - d]
    return y

hall = 0.35 * comb(audio * 0.5, 0.043, 0.45) + 0.30 * comb(audio * 0.5, 0.057, 0.42)
audio = audio + hall

# master: normalize + soft shoulder
audio = audio / max(np.abs(audio).max(), 1e-9)
audio = np.tanh(audio * 1.1) * 0.92

# 16-bit stereo with slight width
import wave
delay = int(0.0004 * SR)
left = audio
right = np.concatenate([np.zeros(delay), audio[:-delay]])
stereo = np.stack([left, right], axis=1)
pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)

with wave.open("/home/adora/play/the-veil-in-D.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("saved /home/adora/play/the-veil-in-D.wav")

# waveform spectrogram cover
import numpy.fft as fft
img_size = 1400
spec = np.zeros((256, img_size))
win = 2048
hop = (N - win) // img_size
for i in range(img_size):
    seg = audio[i * hop: i * hop + win] * np.hanning(win)
    if len(seg) < win:
        seg = np.pad(seg, (0, win - len(seg)))
    mag = np.abs(fft.rfft(seg))[:256]
    spec[:, i] = np.log1p(mag * 40)
spec = (spec - spec.min()) / max(spec.max() - spec.min(), 1e-9)

EMERALD_DEEP = np.array([3, 14, 11]) / 255
EMERALD_MID = np.array([14, 107, 74]) / 255
EMERALD_LIT = np.array([92, 245, 168]) / 255
STARLIGHT = np.array([222, 245, 255]) / 255
GOLD = np.array([255, 212, 120]) / 255

def palette(u):
    stops = [(0.0, EMERALD_DEEP), (0.5, EMERALD_MID), (0.8, EMERALD_LIT), (0.94, STARLIGHT), (1.0, GOLD)]
    out = np.zeros(u.shape + (3,))
    for (a, ca), (b, cb) in zip(stops[:-1], stops[1:]):
        m = (u >= a) & (u <= b)
        if not m.any():
            continue
        t = ((u[m] - a) / (b - a))[..., None]
        out[m] = ca * (1 - t) + cb * t
    return out

rgb = palette(1 - spec)[::-1]  # flip so low freqs at bottom
img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
img = img.resize((1400, 900), Image.LANCZOS)
bloom = img.filter(ImageFilter.GaussianBlur(9))
arr = np.asarray(img).astype(float) / 255 + np.asarray(bloom).astype(float) / 255 * 0.6
img = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
img.save("/home/adora/play/the-veil-in-D-spectrogram.png")
print("saved spectrogram cover")
