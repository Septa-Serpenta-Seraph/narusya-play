"""Probe 7: extract the placement math, run it in isolation for the mid-body
sample, print the actual cross-flank spacing. Are the stars spread across the
flank, or clustered?
"""
import math
import numpy as np

# extract the placement logic for the mid-body sample at (585, 725)
# body width at u~0.3 from the render
w = 35.0  # approximate mid-body half-width
sag = 1.6 + w * 0.10
across = max(2, int(w / 10.5))

print(f"mid-body w={w}, sag={sag:.1f}, across={across}")
print(f"stars across the flank: {across}")
print(f"spacing between adjacent stars: {2.0 * w / across:.1f}px")
print(f"sag (row bow): {sag:.1f}px")

# simulate: if across=2, stars at a=-0.5, +0.5 → positions ±0.5*w*0.97 = ±17px
# if across=3, stars at a=-0.67, 0, 0.67 → positions ±23px, 0
# what does w/10.5=3.33 actually give?
for ac in [2, 3, 4, 5]:
    positions = [((j + 0.5) / ac) * 2.0 - 1.0 for j in range(ac)]
    px = [p * w * 0.97 for p in positions]
    print(f"  across={ac}: positions={[f'{p:.1f}' for p in px]}, gaps={[f'{px[i+1]-px[i]:.1f}' for i in range(len(px)-1)]}")
