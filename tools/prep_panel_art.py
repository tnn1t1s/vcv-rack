#!/usr/bin/env python3
"""
Crop and upscale the Attenuate background art.

Input:  plugin/AgentRack/res/Attenuate-bg.jpg  (452x1600, full deck)
Output: plugin/AgentRack/res/Attenuate-bg.jpg  (overwritten with crop+upscale)

Crop: rectangular section of pure flower background, avoiding the rounded
deck ends where white corners bleed in.
Upscale: 2x with LANCZOS for crisp rendering on Retina displays.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
import numpy as np

SRC = "plugin/AgentRack/res/Attenuate-bg.jpg"
DST = "plugin/AgentRack/res/Attenuate-bg.jpg"
SCALE = 2

img = Image.open(SRC)
arr = np.array(img)
W, H = img.size
print(f"Original: {W}x{H}")

# Detect white corner regions (outside the deck oval shape)
is_white = (arr[:,:,0] > 200) & (arr[:,:,1] > 200) & (arr[:,:,2] > 200)

# Profile: leftmost/rightmost non-white per row
left_of_row  = np.full(H, W, dtype=int)
right_of_row = np.zeros(H, dtype=int)
for y in range(H):
    nw = np.where(~is_white[y])[0]
    if len(nw):
        left_of_row[y]  = int(nw[0])
        right_of_row[y] = int(nw[-1])

row_width = right_of_row - left_of_row

# Find rows where deck width is >= 95% of max width (fully interior)
max_width  = int(row_width.max())
threshold  = int(max_width * 0.95)
wide_rows  = np.where(row_width >= threshold)[0]

crop_top    = int(wide_rows[0])
crop_bottom = int(wide_rows[-1])
# Use the most conservative (widest inset) left/right within that span
crop_left   = int(left_of_row[crop_top:crop_bottom].max()) + 4
crop_right  = int(right_of_row[crop_top:crop_bottom].min()) - 4

print(f"Crop:     ({crop_left}, {crop_top}) -> ({crop_right}, {crop_bottom})")
print(f"Crop size: {crop_right-crop_left} x {crop_bottom-crop_top}")

cropped = img.crop((crop_left, crop_top, crop_right, crop_bottom))

# Upscale 2x with high-quality LANCZOS
new_w = cropped.width  * SCALE
new_h = cropped.height * SCALE
upscaled = cropped.resize((new_w, new_h), Image.LANCZOS)
print(f"Upscaled: {new_w}x{new_h}")

upscaled.save(DST, "JPEG", quality=95, optimize=True)
print(f"Saved:    {DST}")
