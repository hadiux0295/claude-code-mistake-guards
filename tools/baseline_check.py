#!/usr/bin/env python3
"""Prop footing check. Takes the bottom row of the pixels a prop actually draws (its alpha bounding box, not its canvas)
as the baseline, and checks that every opaque pixel in that row stands on the scene's 'walkable ground' mask.
If any pixel misses, the render stops (exit 1).
  python3 baseline_check.py <ground_mask.png> <prop.png> <x> <y>    (x, y = top-left of the prop canvas in the scene)
Ground mask = same size as the scene, walkable = white, water / air = black.
"""
import sys

from PIL import Image


def check(mask_path, prop_path, x, y):
    ground = Image.open(mask_path).convert("L")
    prop = Image.open(prop_path).convert("RGBA")
    box = prop.getchannel("A").getbbox()  # what is actually drawn, not the canvas
    if not box:
        return ["the prop is fully transparent"]
    left, top, right, bottom = box
    foot = bottom - 1
    bad = []
    for px in range(left, right):
        if prop.getpixel((px, foot))[3] == 0:
            continue
        gx, gy = x + px, y + foot + 1  # the pixel right below the foot
        inside = 0 <= gx < ground.width and 0 <= gy < ground.height
        if not inside or ground.getpixel((gx, gy)) < 128:
            bad.append((gx, gy))
    return [f"not standing on ground: {len(bad)} pixels, first at {bad[0]}"] if bad else []


if __name__ == "__main__":
    errs = check(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    print("FAIL " + errs[0] if errs else "PASS")
    sys.exit(1 if errs else 0)
