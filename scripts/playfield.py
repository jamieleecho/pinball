#!/usr/bin/env python3
"""The playfield, traced from artwork instead of drawn from parameters.

The table is `art/pinball.png` -- the original machine's screen, in four
colours -- and `art/pinball2.png` carries nothing but the nine feet, which is
how we know which orange is a foot and which is a permanent bumper.  Both are
read here; everything the ball collides with is derived from the pixels, so
the picture and the physics cannot disagree.

    scripts/playfield.py          # report the geometry and write previews

The world is larger than the screen.  The CoCo 3's 320x200 is fixed, so the
tilemap is 336x224 -- exactly 21x14 tiles -- with the artwork centred in it and
white all round the outside.  That leaves 8 pixels of slack on each side and 12
top and bottom for the camera to jiggle into when the volcano goes off, without
a black edge ever showing.
"""

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from table_spec import (  # noqa: F403
    BLACK, WHITE, MAGENTA, TEAL, ORANGE, palette_bytes,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "art")
BUILD = os.path.join(ROOT, "build")

# The world, and where the 320x200 artwork sits inside it.
WORLD_W, WORLD_H = 336, 224
ORIGIN_X, ORIGIN_Y = (WORLD_W - 320) // 2, (WORLD_H - 200) // 2

# What the scan's four colours mean, and which palette entry each becomes.
SRC_WHITE = (239, 239, 239)
SRC_MAGENTA = (200, 106, 239)
SRC_CYAN = (114, 164, 165)
SRC_ORANGE = (205, 140, 71)
PALETTE = {
    SRC_WHITE: WHITE,
    SRC_MAGENTA: MAGENTA,
    SRC_CYAN: TEAL,
    SRC_ORANGE: ORANGE,
}

# The table, in source-image columns.  Everything right of this is the panel.
TABLE_X0, TABLE_X1 = 35, 186

# Orange that must not score.  The drain mouth would otherwise pay out on the
# way past, and the flippers would pay out on every save.
DRAIN_BOX = (93, 185, 112, 194)
FLIPPER_BOXES = ((55, 157, 84, 172), (121, 157, 150, 172))

# The launch lane: a 9-pixel white channel running the full height of the
# table down its right-hand side, walled off from the playfield by the divider.
LANE_X0, LANE_X1 = 176, 184
LANE_TOP = 34  # above this the lane opens into the table

# The stopper.  The lane and the table are joined by one gap, between the
# bottom of the curved top border and the top of the divider below it.  A shot
# on its way up goes through that gap into the table; the stopper then fills it
# so the ball cannot come back.  It is a sprite rather than artwork because it
# is only there once the ball is in play.
#
# The ball is stopped by a horizontal normal, so the bar only has to be a bar:
# two columns are as good a wall as seven, and thin is what the original looks
# like.  It sits on the divider's own tip, x 169..170, carrying that line
# straight up to the border.
#
# The open stopper saves no background -- it is what rubs the shut one out --
# so it is drawn from the artwork rather than filled with white.  That is what
# lets the bar run right into the border above and the divider below instead of
# stopping a row short of whichever column reaches further: white would take a
# bite out of the wall the first time the gate opened, and nothing puts it
# back.  So the height is the whole gap, y 13..34, and _check_gate() checks the
# one thing that still matters -- that both ends are sealed.
GATE_BOX = (169, 13, 170, 34)  # source x0, y0, x1, y1, inclusive
GATE_W = GATE_BOX[2] - GATE_BOX[0] + 1
GATE_H = GATE_BOX[3] - GATE_BOX[1] + 1

# The flippers.  Each is one of the little dinosaurs, 30x16, pivoting on its
# outer end so the tips meet over the drain.
# The paddles are the dinosaurs' tails.  Each tail is the chunky orange block
# at the inboard lower end of its dinosaur, and it pivots where it joins the
# body -- source x 78 and 126, either side of the drain's centre line at 102.5.
#
# The left tail sweeps from 315 degrees at rest to 45 when pressed, the right
# from 225 to 135; in this file's convention, which measures downwards from
# horizontal, that is +45 to -45 with the right one mirrored.  A length of 19
# puts the resting tips at x 91 and 113, leaving 21 pixels between them -- the
# width of three balls -- directly over the drain mouth at x 93..112.
FLIPPER_PIVOTS = ((78, 169), (126, 169))
FLIPPER_LEN = 19
FLIPPER_HALF_THICK = 4
FLIPPER_REST_DEG = 45   # below horizontal, at rest
FLIPPER_UP_DEG = -45    # above horizontal, fully raised
FLIPPER_FRAMES = 6

BALL_R = 3

# The launcher, and the spring beneath it.
#
# The head is a small block that rides down the lane as the plunger is drawn
# back.  On its own that reads as a block sliding about; what makes it read as
# a plunger is the spring below, which fills whatever room is left between the
# head and the floor of the lane and so squashes as the head comes down.
#
# The head's travel therefore has to stop short of the floor, or at full pull
# there is no spring left to see.  Two rows is enough to read as a coil, and
# the spring gets one frame per two rows of travel, so the pull is even.
LAUNCHER_REST_Y = 168   # the head's centre, at rest
LAUNCHER_HALF_W = 4
LAUNCHER_HALF_H = 3
SPRING_FLOOR = 189      # the last lane row the spring stands on
SPRING_W = 5
SPRING_COILS = 4
SPRING_MIN_H = 2
SPRING_TOP = LAUNCHER_REST_Y + LAUNCHER_HALF_H + 1
SPRING_H = SPRING_FLOOR - SPRING_TOP + 1
LAUNCHER_MAX_PULL = SPRING_H - SPRING_MIN_H
SPRING_FRAMES = LAUNCHER_MAX_PULL // 2 + 1

# The two score boards in the panel, measured off the artwork.  Seven digits
# each, grouped "0 000 000" as the original showed them: at pitch 8 with a
# 2-pixel gap before digits 1 and 4 they fill the frame exactly, and every
# column stays even, which byte-aligned sprites require.
HIGH_BOX = (201, 155, 266, 172)
SCORE_BOX = (201, 177, 266, 194)
SCORE_DIGITS = 7
SCORE_DIGIT_X0 = 204
SCORE_DIGIT_PITCH = 8
SCORE_GROUP_GAP = 2
SCORE_DIGIT_DY = 3  # down from the top of the frame

# The multiplier goes right of the boards, where there is width to spare.
MULT_XY = (272, 158)

# The balls still to play stack up the clear strip between the table's right
# edge and the boards.  That strip is source x 187..194 -- exactly eight
# pixels, one ball wide -- so they can only go vertically.  The first is at the
# bottom and the rest pile upwards, which is why the pitch is subtracted.
BALLS_XY = (188, 186)
BALLS_PITCH = 10

# The volcano: the left peak in the panel.  Measured off the artwork -- the
# apex, and the point on each slope where the mountain meets the ground.  Lava
# runs from the apex down both slopes, which is the upside-down V the original
# drew, so these three points are all the path needs.
# Inset from the edges the measurement gives: the lava is five pixels across,
# and a path drawn along the mountain's own outline hangs half of it out over
# the white behind.
VOLCANO_APEX = (220, 52)
VOLCANO_LEFT_FOOT = (205, 67)
VOLCANO_RIGHT_FOOT = (231, 63)
LAVA_FRAMES = 8   # frames of the flow animation
LAVA_BULGES = 4   # gobbets riding each stream

# Vally lies on the pond in the panel (cyan, x 221..266, y 63..78); her head is
# at the right-hand end, which is where the tongue reaches from.
TONGUE_XY = (262, 79)  # Vally's mouth, down at the pond she is drinking from

CELL = 4  # collision cells, as before: 4x4 pixels, one byte each

K_EMPTY, K_WALL, K_BUMPER, K_FOOT, K_SCENERY, K_FLIPPER, K_DRAIN = range(7)
KIND_NAMES = {
    K_EMPTY: "empty", K_WALL: "wall", K_BUMPER: "bumper", K_FOOT: "foot",
    K_SCENERY: "scenery", K_FLIPPER: "flipper", K_DRAIN: "drain",
}
# When a cell holds more than one kind, the first of these wins.  The drain
# outranks everything so a ball on its way out is never saved by a wall cell,
# and feet outrank bumpers so a foot is never mistaken for one.
KIND_PRIORITY = (K_DRAIN, K_FLIPPER, K_FOOT, K_BUMPER, K_WALL, K_SCENERY, K_EMPTY)


def world(x, y):
    """Source-image coordinates to world coordinates."""
    return x + ORIGIN_X, y + ORIGIN_Y


def _load(name):
    return Image.open(os.path.join(ART, name))


def in_box(x, y, box):
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


# The three big bumpers.  Their middles flash when the ball strikes them, and
# the middle is a 6x6 box inset five pixels from the corner: that covers the
# white hole plus a ring of the bumper's own orange, and lands on an even
# column, which byte-aligned sprites need.
DIAMOND_SIZE = 16
DIAMOND_MID_OFF = 5
DIAMOND_MID = 6


def diamond_boxes():
    """The bumpers that flash, found by their size rather than written down.

    Only the three big ones qualify; the strips and the small wall diamonds are
    the same colour but a different shape, and they do not flash.
    """
    src, _ = source()
    p = src.load()
    seen, boxes = set(), []
    for y in range(src.height):
        for x in range(TABLE_X0, TABLE_X1 + 1):
            if p[x, y] != SRC_ORANGE or (x, y) in seen:
                continue
            stack, blob = [(x, y)], []
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                blob.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (cx + dx, cy + dy)
                    if (TABLE_X0 <= n[0] <= TABLE_X1 and 0 <= n[1] < src.height
                            and n not in seen and p[n] == SRC_ORANGE):
                        seen.add(n)
                        stack.append(n)
            xs = [b[0] for b in blob]
            ys = [b[1] for b in blob]
            if (max(xs) - min(xs) + 1 == DIAMOND_SIZE
                    and max(ys) - min(ys) + 1 == DIAMOND_SIZE):
                boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return sorted(boxes, key=lambda b: (b[1], b[0]))


# The dinosaurs at the bottom flick their tongues out of their heads towards
# the wall beside them.  Each is a chain of 2x2 blocks stepping outwards at 45
# degrees -- up and out, so 135 degrees on the left and 45 on the right -- and
# at full stretch the tip reaches the magenta border.  That is the whole point
# of them: an extended tongue bridges the outlane, and the ball cannot get down
# the side past it.
DINO_TONGUE_ROOTS = ((56, 157), (148, 157))  # top-left of the block at the head
DINO_TONGUE_BLOCKS = 4                       # blocks at full stretch
DINO_TONGUE_PERIOD = 64                      # ticks for a full in-and-out


def tongue_pixels(side, blocks):
    """One tongue at a given extension, in source coordinates.

    Blocks that step diagonally touch only at their corners, and a sprite is
    found by flood fill, for which diagonal contact does not count.  Each joint
    therefore carries one extra pixel: without it the fill would take the block
    under the anchor and leave the rest of the tongue behind, silently.
    """
    step = -1 if side == 0 else 1
    rx, ry = DINO_TONGUE_ROOTS[side]
    px = set()
    prev_y = None
    for k in range(blocks):
        bx, by = rx + 2 * k * step, ry - 2 * k
        px |= {(bx + i, by + j) for i in range(2) for j in range(2)}
        if prev_y is not None:
            px.add((bx + (1 if step < 0 else 0), prev_y))
        prev_y = by
    return px


def tongue_lengths():
    """How far each tongue is out, one entry per tick of the cycle."""
    half = DINO_TONGUE_PERIOD // 2
    out = []
    for i in range(DINO_TONGUE_PERIOD):
        q = i if i < half else DINO_TONGUE_PERIOD - 1 - i
        out.append(1 + (q * DINO_TONGUE_BLOCKS) // half)
    return out


# The four plunger lines along the top of the table.  The manual calls them
# plungers and the marks they set up red; they appear when the foot below the
# pod they belong to is hit, and a ball through one grows Vally's tongue.
PLUNGER_W, PLUNGER_H = 6, 2
PLUNGER_Y = 31


def plunger_boxes():
    """The four lines, one to a gap along the top row.

    They are found rather than written down.  The two pods and the three
    targets between them leave exactly four gaps, and a line sits in the middle
    of each -- which is where the original put the one it shows.  Ordering
    across the table is what makes the mapping to the feet work: the leftmost
    foot lights the leftmost line.
    """
    src, _ = source()
    sp = src.load()
    cols = {
        x
        for x in range(TABLE_X0, TABLE_X1 + 1)
        for y in range(20, 55)
        if sp[x, y] == SRC_CYAN
    }
    runs, start = [], None
    for x in range(TABLE_X0, TABLE_X1 + 2):
        if x in cols and start is None:
            start = x
        elif x not in cols and start is not None:
            runs.append((start, x - 1))
            start = None
    boxes = []
    for a, b in zip(runs, runs[1:]):
        mid = (a[1] + 1 + b[0] - 1) // 2
        x0 = mid - PLUNGER_W // 2 + 1
        boxes.append((x0, PLUNGER_Y, x0 + PLUNGER_W - 1, PLUNGER_Y + PLUNGER_H - 1))
    return boxes


# The prehistoric fly, which Vally has to catch for the volcano to erupt.  It
# beats back and forth across the desert on the panel in a sinusoid, three
# peaks to a crossing, between the rightmost bush and the leftmost cactus --
# which is what sets both the length of its flight and how high it flies.
FLY_W, FLY_H = 12, 6
FLY_LEFT_X, FLY_RIGHT_X = 211, 267
FLY_MID_Y, FLY_AMP = 97, 5
FLY_PEAKS = 3
FLY_PERIOD = 128  # ticks for a there-and-back: a crossing takes about two seconds


def fly_path():
    """Where the fly's top-left corner is on each tick of its cycle.

    A table rather than arithmetic: the 6809 has no multiply worth the name and
    certainly no sine, and 128 bytes is cheaper than either.  The path is a
    closed loop, so the object needs nothing but an index that wraps.
    """
    import math

    half = FLY_PERIOD // 2
    out = []
    for t in range(FLY_PERIOD):
        # Out on the first half, back on the second.
        u = t / half if t < half else (FLY_PERIOD - t) / half
        x = FLY_RIGHT_X + (FLY_LEFT_X - FLY_RIGHT_X) * u
        y = FLY_MID_Y + FLY_AMP * math.sin(2 * math.pi * FLY_PEAKS * u)
        out.append((int(round(x)), int(round(y))))
    return out


# Vally's tongue goes for the fly at the far left of its beat, and the manual
# has it get there by going down, then left, then down again rather than
# straight across.  The corners are what make it read as a tongue flicking out
# rather than a ruler being extended.
TONGUE_REACH_STAGES = 6


def vally_tongue_path():
    """The corners of the tongue's reach, in source coordinates.

    It starts at Vally's mouth and finishes on the fly's body at the far left
    of the flight, so the last stage is exactly long enough to catch it.
    """
    mx, my = TONGUE_XY
    fx, fy = fly_path()[FLY_PERIOD // 2]
    # Land on the fly's body, on an even column: the sprite is drawn
    # byte-aligned, and at four bits a pixel a byte is two pixels, so an odd
    # left edge would put the whole tongue a pixel off its mouth.
    tip_x = (fx + FLY_W // 2) & ~1
    tip_y = fy + FLY_H // 2
    corner_y = my + 10
    return [(mx, my), (mx, corner_y), (tip_x, corner_y), (tip_x, tip_y)]


VALLY_TONGUE_THICK = 2


def vally_tongue_pixels(stage):
    """The tongue drawn out to one of its stages, in source coordinates.

    Two pixels across rather than one.  A single-pixel line at this size reads
    as a scratch on the panel rather than as a tongue, and Vally is the one
    dinosaur whose tongue the player is meant to be watching.
    """
    pts = vally_tongue_path()
    legs = [
        (a, b, abs(b[0] - a[0]) + abs(b[1] - a[1]))
        for a, b in zip(pts, pts[1:])
    ]
    total = sum(leg[2] for leg in legs)
    want = total * stage // TONGUE_REACH_STAGES
    out, done = [], 0
    for (ax, ay), (bx, by), n in legs:
        sx = (bx > ax) - (bx < ax)
        sy = (by > ay) - (by < ay)
        for i in range(n + 1):
            if done + i > want:
                return out
            x, y = ax + sx * i, ay + sy * i
            # Thickened towards the bottom right, which leaves the left edge --
            # the one the sprite is byte-aligned on -- where it was.
            for tx in range(VALLY_TONGUE_THICK):
                for ty in range(VALLY_TONGUE_THICK):
                    out.append((x + tx, y + ty))
        done += n
    return out


def in_sweep(x, y):
    """Inside the quarter-disc one of the tails sweeps through."""
    reach = FLIPPER_LEN + FLIPPER_HALF_THICK + 2
    for (px, py), outward in zip(FLIPPER_PIVOTS, (1, -1)):
        dx = (x - px) * outward
        dy = y - py
        if 0 <= dx and dx * dx + dy * dy <= reach * reach and abs(dy) <= dx + 1:
            return True
    return False


def _check_lane(src):
    """The lane and the stopper are the two things still measured by hand.

    Everything else the ball touches comes out of the pixels, but these two are
    written down, so a redrawn table can move the artwork out from under them
    without anything complaining -- which is exactly what a one-pixel tidy-up
    of the divider did.  Read them back and insist they still agree.
    """
    p = src.load()
    mid = (LANE_X0 + LANE_X1) // 2
    # Below the divider's taper (5 rows) and above the bottom corner, where the
    # lane is a plain vertical channel.
    for y in range(LANE_TOP + 6, 190):
        assert p[mid, y] == SRC_WHITE, f"the launch lane is blocked at row {y}"
        x0 = x1 = mid
        while p[x0 - 1, y] == SRC_WHITE:
            x0 -= 1
        while p[x1 + 1, y] == SRC_WHITE:
            x1 += 1
        assert (x0, x1) == (LANE_X0, LANE_X1), (
            f"the lane is x {x0}..{x1} at row {y}, "
            f"not LANE_X0..LANE_X1 = {LANE_X0}..{LANE_X1}")


def _check_gate(src):
    """The stopper has to seal its gap at both ends.

    Anything left over is a hole the ball can drop through, and a hole one
    pixel wide still looks like a mistake even when it is too narrow to fall
    into.  The open stopper is a copy of the artwork, so overlapping the walls
    costs nothing and there is no reason to stop short of them.
    """
    p = src.load()
    x0, y0, x1, y1 = GATE_BOX
    for x in range(x0, x1 + 1):
        assert p[x, y0 - 1] != SRC_WHITE, (
            f"the stopper leaves column {x} open above it, at row {y0 - 1}")
        assert p[x, y1 + 1] != SRC_WHITE, (
            f"the stopper leaves column {x} open below it, at row {y1 + 1}")


def source():
    """The table artwork and the set of pixels belonging to the nine feet."""
    src = _load("pinball.png").convert("RGB")
    _check_lane(src)
    _check_gate(src)
    marks = _load("pinball2.png").convert("RGBA")
    mp = marks.load()
    feet = {
        (x, y)
        for y in range(marks.height)
        for x in range(marks.width)
        if mp[x, y][3] and mp[x, y][:3] == SRC_ORANGE
    }
    return src, feet


def foot_boxes(feet):
    """The nine feet as bounding boxes, in source-image coordinates."""
    seen, boxes = set(), []
    for y, x in sorted((p[1], p[0]) for p in feet):
        if (x, y) in seen:
            continue
        stack, blob = [(x, y)], []
        seen.add((x, y))
        while stack:
            cx, cy = stack.pop()
            blob.append((cx, cy))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (cx + dx, cy + dy)
                if n in feet and n not in seen:
                    seen.add(n)
                    stack.append(n)
        xs = [b[0] for b in blob]
        ys = [b[1] for b in blob]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


def kind_at(src_px, feet, x, y):
    """What the ball would meet at this pixel of the source image."""
    if not TABLE_X0 <= x <= TABLE_X1:
        # Off the table altogether.  This has to read as wall, not as floor:
        # the artwork's right-hand border is only a couple of pixels inside the
        # last cell, and calling the rest of that cell empty opened a hole the
        # ball ran straight out of.
        return K_WALL
    if in_box(x, y, DRAIN_BOX):
        # The drain.  This box is the orange pyramid at the bottom of the
        # table, and it used to be cut out of the grid entirely -- a hole, so
        # that a ball reaching it fell through and out of the world, where the
        # ball object noticed it by its crossing DRAIN_Y.  That worked, but the
        # ball visibly sank through the one solid-looking thing down there.
        #
        # The pyramid is solid now, and it is its own kind rather than a wall:
        # touching it is what loses the ball, so the ball settles on top of it
        # instead of falling off the bottom of the table.  DRAIN_Y stays as a
        # backstop for anything that gets past it.  The white either side of
        # the pyramid inside the box is only table.
        if src_px[x, y] == SRC_ORANGE:
            return K_DRAIN
        return K_EMPTY
    if in_sweep(x, y):
        # The arc the tails sweep through cannot live in a grid that never
        # moves.  The paddles are objects and the ball meets them analytically
        # from the pivot and the current angle, so the arc is a hole; the rest
        # of each dinosaur stays solid, or the ball would sail through the one
        # thing on the table that visibly is not a gap.
        return K_EMPTY
    if (x, y) in feet:
        return K_FOOT
    c = src_px[x, y]
    if c == SRC_MAGENTA:
        return K_WALL
    if c == SRC_ORANGE:
        return K_BUMPER
    if c == SRC_CYAN:
        return K_SCENERY
    return K_EMPTY


def world_image():
    """The 336x224 background, in the game's palette, artwork centred."""
    src, _ = source()
    img = Image.new("P", (WORLD_W, WORLD_H), WHITE)
    img.putpalette(palette_bytes())
    sp, dp = src.load(), img.load()
    for y in range(src.height):
        for x in range(src.width):
            dp[x + ORIGIN_X, y + ORIGIN_Y] = PALETTE.get(sp[x, y], BLACK)
    return img


def grid_bounds():
    """The collision grid covers the table only, aligned to the cell size.

    Storing a cell for the whole 336x224 world would be 4704 bytes; the table
    alone is a third of that, and the ball never leaves it.
    """
    x0 = ((TABLE_X0 + ORIGIN_X) // CELL) * CELL
    x1 = -(-(TABLE_X1 + 1 + ORIGIN_X) // CELL) * CELL
    y0 = (ORIGIN_Y // CELL) * CELL
    y1 = -(-(200 + ORIGIN_Y) // CELL) * CELL
    return x0, y0, x1, y1


def collision_grid():
    """One byte per 4x4 cell of the table, in world coordinates."""
    src, feet = source()
    sp = src.load()
    x0, y0, x1, y1 = grid_bounds()
    gw, gh = (x1 - x0) // CELL, (y1 - y0) // CELL
    grid = []
    for gy in range(gh):
        row = []
        for gx in range(gw):
            kinds, solid = set(), 0
            for j in range(CELL):
                for i in range(CELL):
                    sx = x0 + gx * CELL + i - ORIGIN_X
                    sy = y0 + gy * CELL + j - ORIGIN_Y
                    if 0 <= sx < src.width and 0 <= sy < src.height:
                        k = kind_at(sp, feet, sx, sy)
                        kinds.add(k)
                        if k != K_EMPTY:
                            solid += 1
            # A cell is solid only if most of it is.  Taking any solid pixel at
            # all would fatten every wall by up to three pixels and so narrow
            # every channel by six: the launch lane is eight pixels wide, and
            # that rule left a four-pixel gap for a seven-pixel ball.
            # A tie goes to solid.  Half a cell of wall is still wall, and
            # rounding the other way costs a border its last pixel.
            if solid * 2 < CELL * CELL:
                row.append(K_EMPTY)
            else:
                row.append(next(k for k in KIND_PRIORITY if k in kinds))
        grid.append(row)

    seal(grid, gw, gh, x0, y0)
    return grid, (x0, y0, gw, gh)


def seal(grid, gw, gh, x0, y0):
    """Wall off everything the ball cannot legitimately reach.

    The majority rule that keeps channels wide also thins the table's outer
    border, and a border one cell thick with a single majority-white cell in it
    is a hole the ball will eventually find.  Rather than thicken the border by
    guesswork, flood the open space from inside the table and turn every other
    empty cell into wall.  The playable area is then enclosed by construction,
    however thin the artwork's border happens to be, and the surface normals
    computed afterwards face inwards on their own.

    The drain is the one way out, so the fill is stopped at the row it starts
    on -- otherwise it would pour through the hole and seal nothing.
    """
    seeds = [
        ((LANE_X0 + LANE_X1) // 2 + ORIGIN_X, 60 + ORIGIN_Y),   # the launch lane
        (110 + ORIGIN_X, 70 + ORIGIN_Y),                        # mid table
    ]
    drain_row = (DRAIN_BOX[1] + ORIGIN_Y - y0) // CELL

    inside = set()
    stack = []
    for wx, wy in seeds:
        cell = ((wx - x0) // CELL, (wy - y0) // CELL)
        if grid[cell[1]][cell[0]] == K_EMPTY:
            inside.add(cell)
            stack.append(cell)
    while stack:
        cx, cy = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < gw and 0 <= ny < gh) or ny >= drain_row:
                continue
            if (nx, ny) in inside or grid[ny][nx] != K_EMPTY:
                continue
            inside.add((nx, ny))
            stack.append((nx, ny))

    sealed = 0
    for gy in range(gh):
        for gx in range(gw):
            if grid[gy][gx] == K_EMPTY and (gx, gy) not in inside and gy < drain_row:
                grid[gy][gx] = K_WALL
                sealed += 1
    return sealed


def main():
    os.makedirs(BUILD, exist_ok=True)
    src, feet = source()
    boxes = foot_boxes(feet)
    print(f"world {WORLD_W}x{WORLD_H} = {WORLD_W // 16}x{WORLD_H // 16} tiles, "
          f"artwork centred at +{ORIGIN_X},+{ORIGIN_Y}")
    print(f"{len(boxes)} feet:")
    for x0, y0, x1, y1 in boxes:
        print(f"   x {x0:3d}..{x1:3d}  y {y0:3d}..{y1:3d}   "
              f"world x {x0 + ORIGIN_X:3d}  y {y0 + ORIGIN_Y:3d}")

    img = world_image()
    img.save(os.path.join(BUILD, "world.png"))
    px = img.load()
    seen = set()
    for ty in range(0, WORLD_H, 16):
        for tx in range(0, WORLD_W, 16):
            seen.add(tuple(px[tx + x, ty + y] for y in range(16) for x in range(16)))
    print(f"tileset: {len(seen)} unique 16x16 tiles (max 254)")

    grid, (gx0, gy0, gw, gh) = collision_grid()
    counts = {}
    for row in grid:
        for k in row:
            counts[k] = counts.get(k, 0) + 1
    print(f"collision grid {gw}x{gh} = {gw * gh} bytes at world +{gx0},+{gy0}")
    for k in sorted(counts):
        print(f"   {KIND_NAMES[k]:8s} {counts[k]:5d}")

    shade = {K_EMPTY: WHITE, K_WALL: MAGENTA, K_BUMPER: ORANGE, K_FOOT: 11,
             K_SCENERY: TEAL, K_FLIPPER: 13, K_DRAIN: BLACK}
    vis = Image.new("P", (gw, gh))
    vis.putpalette(palette_bytes())
    vp = vis.load()
    for gy in range(gh):
        for gx in range(gw):
            vp[gx, gy] = shade[grid[gy][gx]]
    vis.resize((gw * 8, gh * 8), Image.NEAREST).save(
        os.path.join(BUILD, "world-grid.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
