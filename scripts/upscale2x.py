#!/usr/bin/env python3
"""Double the size of a pixel-art image without inventing colours.

    scripts/upscale2x.py in.png out.png [passes]

Each source pixel is looked at through a 3x3 window and becomes four output
pixels, one per corner.  A corner is filled from its neighbours only when the
two that meet there agree with each other and disagree with the two across the
way -- the signature of a staircase edge -- so diagonal boundaries come out
rounded and everything else is copied through:

    A B C          E0 E1        E0 = D  if D == B and D != H and B != F
    D E F   ->     E2 E3        E1 = F  if B == F and B != D and F != H
    G H I                       E2 = D  if D == H and D != B and H != F
                                E3 = F  if H == F and H != D and F != B

That much is the Scale2x/EPX rule.  It never mixes colours -- every output
pixel is one of the nine it looked at -- so a four-colour picture stays a
four-colour picture and can still be used as a CoCo image.  A filter that
averaged would have to be re-quantised afterwards, and re-quantising a
smoothed edge just puts the staircase back.

Where it needs help
-------------------

Every one of those tests is the ambiguous case of marching squares: two
diagonally opposite cells of one colour, two of another, and no local way to
know which pair is the connected one.  Scale2x always joins the pair named in
the rule, and on this artwork that is sometimes wrong.

The dinosaur eyes are the case that matters.  An eye is a single white pixel
with four teal neighbours -- but white is also the background colour, so where
an eye happens to sit diagonally opposite a scrap of background, the rule
cheerfully joins the two and the eye leaks out of the head.  Meanwhile the
same rule on the dotted lanes by the flippers is exactly what is wanted: it
threads the separate dots into one clean diagonal.

So a pixel is *protected* when it is a hole -- its four neighbours are all one
colour, and that colour is not its own -- and it is not part of a diagonal
chain of holes of its own colour.  A corner is not filled from a protected
pixel.  The chain clause is what tells the two cases apart: an eye stands
alone, whereas each dot of a dotted line has another dot cornering it, and so
does every square of a dithered band.

On the 125x95 original screen that comes to 303 holes, of which about thirty
are protected: the four eyes, the gaps inside the cycads, and the counters of
the "Vally" script.  The dither and the dotted lanes are left to smooth.

Repeat passes give 4x, 8x and so on; the rounding compounds, which looks
better than one big jump.
"""

import sys

from PIL import Image


def _sampler(img):
    w, h = img.size
    px = img.load()

    def at(x, y):
        # Clamp at the border, so edge pixels see themselves rather than a
        # colour that is not in the picture.
        return px[min(max(x, 0), w - 1), min(max(y, 0), h - 1)]

    return at


def protected_mask(img):
    """Which pixels must not be smeared into their neighbours.

    See the module docstring: a hole that is not part of a diagonal chain of
    holes of the same colour.
    """
    w, h = img.size
    at = _sampler(img)

    holes = {}
    for y in range(h):
        for x in range(w):
            c = at(x, y)
            up, down = at(x, y - 1), at(x, y + 1)
            if up == down == at(x - 1, y) == at(x + 1, y) != c:
                holes[(x, y)] = c

    return {
        (x, y)
        for (x, y), c in holes.items()
        if not any(
            holes.get((x + dx, y + dy)) == c for dx in (-1, 1) for dy in (-1, 1)
        )
    }


def scale2x(img):
    """One pass: w x h -> 2w x 2h."""
    w, h = img.size
    at = _sampler(img)
    keep = protected_mask(img)
    out = Image.new(img.mode, (w * 2, h * 2))
    dst = out.load()

    def free(x, y):
        """A neighbour may only be smeared into a corner if it is not one of
        the single-pixel features we are holding on to."""
        return (min(max(x, 0), w - 1), min(max(y, 0), h - 1)) not in keep

    for y in range(h):
        for x in range(w):
            e = at(x, y)
            b, d, f, g = at(x, y - 1), at(x - 1, y), at(x + 1, y), at(x, y + 1)
            bok, dok, fok, gok = (
                free(x, y - 1), free(x - 1, y), free(x + 1, y), free(x, y + 1)
            )

            e0 = d if (dok and bok and d == b and d != g and b != f) else e
            e1 = f if (bok and fok and b == f and b != d and f != g) else e
            e2 = d if (dok and gok and d == g and d != b and g != f) else e
            e3 = f if (gok and fok and g == f and g != d and f != b) else e

            dst[x * 2, y * 2] = e0
            dst[x * 2 + 1, y * 2] = e1
            dst[x * 2, y * 2 + 1] = e2
            dst[x * 2 + 1, y * 2 + 1] = e3

    if img.mode == "P":
        out.putpalette(img.getpalette())
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    img = Image.open(sys.argv[1])
    passes = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    for _ in range(passes):
        img = scale2x(img)
    img.save(sys.argv[2])
    print(f"{sys.argv[1]} -> {sys.argv[2]}  {img.size[0]}x{img.size[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
