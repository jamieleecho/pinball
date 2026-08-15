#!/usr/bin/env python3
"""Turn a MAME snapshot into a clean view of the 320x200 screen.

MAME writes 640x239 frames with a border round the picture.  This crops the
border off, undoes the 2x horizontal stretch, and optionally magnifies a
region so pixel-level problems are actually visible.

    scripts/shot.py build/playtest/coco3/0030.png out.png [scale] [x0 y0 x1 y1]
"""

import sys

from PIL import Image

SCREEN_W = 320
SCREEN_H = 200


def load_screen(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    # The picture is a 2x-wide 320x200 window centred in the frame.
    x0 = (w - SCREEN_W * 2) // 2
    y0 = (h - SCREEN_H) // 2
    im = im.crop((x0, y0, x0 + SCREEN_W * 2, y0 + SCREEN_H))
    return im.resize((SCREEN_W, SCREEN_H), Image.NEAREST)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    im = load_screen(sys.argv[1])
    out = sys.argv[2]
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    if len(sys.argv) >= 8:
        box = tuple(int(v) for v in sys.argv[4:8])
        im = im.crop(box)
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
