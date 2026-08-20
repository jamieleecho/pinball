#!/usr/bin/env python3
"""Generate the Lost World Pinball table artwork and collision data.

Everything the table is made of is described once, in table_spec.py.  This
script draws it (background tileset image) and rasterises it (collision grid
consumed by the ball object), so the ball always bounces off exactly what the
player can see.

    scripts/gen-assets.py            # write game assets
    scripts/gen-assets.py --preview  # also write a 2x preview PNG to build/
"""

import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from table_spec import *  # noqa: F403
import playfield  # the table, traced from art/ rather than drawn here

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILE_DIR = os.path.join(ROOT, "game", "tiles")
LEVEL_DIR = os.path.join(ROOT, "game", "levels")
OBJ_DIR = os.path.join(ROOT, "game", "objects")
BUILD_DIR = os.path.join(ROOT, "build")

PAL_ROWS = 16  # palette block at the top of the tileset image
ART_Y = PAL_ROWS  # artwork starts here


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------


def interp(profile, y):
    """Linearly interpolate an (y, x) profile at row y."""
    if y <= profile[0][0]:
        return profile[0][1]
    if y >= profile[-1][0]:
        return profile[-1][1]
    for i in range(len(profile) - 1):
        y0, x0 = profile[i]
        y1, x1 = profile[i + 1]
        if y0 <= y <= y1:
            if y1 == y0:
                return x0
            return x0 + (x1 - x0) * (y - y0) / (y1 - y0)
    return profile[-1][1]


def left_edge(y):
    return int(round(interp(LEFT_PROFILE, y)))


def right_edge(y):
    if y < LANE_TOP:
        return int(round(interp(RIGHT_PROFILE_TOP, y)))
    return int(round(interp(RIGHT_PROFILE_MAIN, y)))


def interior_rows():
    """Yield (y, x_left, x_right) for every row of the playfield interior."""
    for y in range(CANVAS_H):
        if y < 8 or y > 200:
            continue
        yield y, left_edge(y), right_edge(y)


# ---------------------------------------------------------------------------
# Shape drawing.  Each routine takes a "painter" so the same geometry can be
# rendered into the colour image and into the collision kind-map.
# ---------------------------------------------------------------------------


class Painter:
    """Draws into an indexed image with a fixed palette translation."""

    def __init__(self, img, colours):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.c = colours  # maps a semantic name to a fill value

    def rect(self, box, name):
        v = self.c.get(name)
        if v is None:
            return
        self.d.rectangle(box, fill=v)

    def rrect(self, box, name, radius=4):
        v = self.c.get(name)
        if v is None:
            return
        self.d.rounded_rectangle(box, radius=radius, fill=v)

    def ellipse(self, box, name):
        v = self.c.get(name)
        if v is None:
            return
        self.d.ellipse(box, fill=v)

    def polygon(self, pts, name):
        v = self.c.get(name)
        if v is None:
            return
        self.d.polygon(pts, fill=v)

    def line(self, pts, name, width=1):
        v = self.c.get(name)
        if v is None:
            return
        self.d.line(pts, fill=v, width=width)


def draw_table(p, oy):
    """Draw the whole playfield.  oy is the vertical offset of the artwork."""

    # Solid wall everywhere, then carve out the playable interior.
    p.rect((0, oy, PLAYFIELD_W - 1, oy + CANVAS_H - 1), "wall")
    for y, xl, xr in interior_rows():
        p.rect((xl, oy + y, xr, oy + y), "floor")

    # Launch lane and the divider that separates it from the table.
    p.rect((LANE_X0, oy + LANE_TOP, LANE_X1, oy + 200), "floor")
    p.polygon(
        [
            (DIVIDER_X0, oy + LANE_TOP + 4),
            ((DIVIDER_X0 + DIVIDER_X1) // 2, oy + LANE_TOP - 3),
            (DIVIDER_X1, oy + LANE_TOP + 4),
        ],
        "wall",
    )

    # Drain funnel at the bottom: two walls converging on the centre gap.
    p.polygon(
        [(34, oy + 176), (70, oy + 199), (34, oy + 199)],
        "wall",
    )
    p.polygon(
        [(139, oy + 176), (103, oy + 199), (139, oy + 199)],
        "wall",
    )

    # The drain chute, cut straight through the bottom of the table.
    p.rect((DRAIN_X0, oy + DRAIN_MOUTH_Y, DRAIN_X1, oy + CANVAS_H - 1), "drain")

    # Slingshot wedges above the flippers.
    for pts in SLINGSHOTS:
        p.polygon([(x, oy + y) for x, y in pts], "sling")

    # Red power strips set into the side walls.
    for x0, y0, x1, y1 in POWER_STRIPS:
        p.rect((x0, oy + y0, x1, oy + y1), "strip")

    # Vally's crest in the middle of the table.
    p.polygon(
        [
            (CREST_APEX[0], oy + CREST_APEX[1]),
            (CREST_APEX[0] - CREST_HALF_W, oy + CREST_BASE_Y),
            (CREST_APEX[0] + CREST_HALF_W, oy + CREST_BASE_Y),
        ],
        "scenery",
    )

    # Vally's head against the right wall.
    hx0, hy0, hx1, hy1 = HEAD_BOX
    p.polygon(
        [
            (hx0, oy + hy0 + 6),
            (hx1, oy + hy0),
            (hx1, oy + hy1),
            (hx0, oy + hy1 - 4),
        ],
        "scenery",
    )

    # Bumpers.
    for cx, cy, r in BUMPERS:
        p.polygon(
            [
                (cx, oy + cy - r),
                (cx + r, oy + cy),
                (cx, oy + cy + r),
                (cx - r, oy + cy),
            ],
            "bumper",
        )

    # Plungers: the two pods and the three capsules.  Everything the ball can
    # land on top of is rounded, so it always rolls off instead of perching.
    for x0, y0, x1, y1 in PODS:
        p.rrect((x0, oy + y0, x1, oy + y1), "plunger", radius=6)
    for x0, y0, x1, y1 in CAPSULES:
        p.ellipse((x0, oy + y0, x1, oy + y1), "plunger")

    # Red marks.
    for x0, y0, x1, y1 in TOP_MARKS + CREST_MARKS + HEAD_MARKS:
        p.rrect((x0, oy + y0, x1, oy + y1), "mark", radius=2)


# ---------------------------------------------------------------------------
# Colour artwork
# ---------------------------------------------------------------------------

ART_COLOURS = {
    "drain": BLACK,
    "wall": MAGENTA,
    "floor": WHITE,
    "sling": MAGENTA,
    "strip": ORANGE,
    "scenery": TEAL,
    "bumper": ORANGE,
    "plunger": ORANGE,
    "mark": ORANGE,
}


def shade_table(img, oy):
    """Add the shading pass that makes the flat shapes read as a table."""
    d = ImageDraw.Draw(img)

    # A dark line just inside the wall, all the way round the interior.
    for y, xl, xr in interior_rows():
        d.point((xl, oy + y), fill=DMAGENTA)
        d.point((xr, oy + y), fill=DMAGENTA)
    # ... and along the lane.
    for y in range(LANE_TOP, 201):
        d.point((LANE_X0, oy + y), fill=DMAGENTA)
        d.point((LANE_X1, oy + y), fill=DMAGENTA)

    # Highlight the top-left of each bumper, shade the bottom-right.
    for cx, cy, r in BUMPERS:
        d.line(
            [(cx - r + 2, oy + cy - 1), (cx - 1, oy + cy - r + 2)],
            fill=YELLOW,
        )
        d.line(
            [(cx + 1, oy + cy + r - 2), (cx + r - 2, oy + cy + 1)],
            fill=RED,
        )
        d.point((cx, oy + cy), fill=WHITE)

    # Plunger bodies get a teal core so they read as pinosaurus shells.
    for x0, y0, x1, y1 in PODS:
        d.rectangle((x0 + 3, oy + y0 + 3, x1 - 3, oy + y1 - 3), fill=TEAL)
        d.rectangle((x0 + 6, oy + y0 + 6, x1 - 6, oy + y1 - 8), fill=DTEAL)
    for x0, y0, x1, y1 in CAPSULES:
        d.ellipse((x0 + 2, oy + y0 + 3, x1 - 2, oy + y1 - 3), fill=TEAL)

    # The crest gets a shaded underside and a spine.
    ax, ay = CREST_APEX
    d.polygon(
        [
            (ax, oy + ay + 4),
            (ax - CREST_HALF_W + 6, oy + CREST_BASE_Y - 1),
            (ax + CREST_HALF_W - 6, oy + CREST_BASE_Y - 1),
        ],
        fill=DTEAL,
    )

    # Vally's eye.
    hx0, hy0, hx1, hy1 = HEAD_BOX
    d.rectangle((hx1 - 5, oy + hy0 + 5, hx1 - 3, oy + hy0 + 7), fill=WHITE)

    # Give each slingshot a bright rubber along its face.
    for pts in SLINGSHOTS:
        d.line(
            [(pts[0][0], oy + pts[0][1]), (pts[1][0], oy + pts[1][1])],
            fill=YELLOW,
            width=2,
        )

    # A lip around the drain so the hole reads as part of the table.
    d.rectangle(
        (DRAIN_X0, oy + DRAIN_MOUTH_Y, DRAIN_X1, oy + DRAIN_MOUTH_Y + 1),
        fill=ORANGE,
    )

    # Power strips get a bright core.
    for x0, y0, x1, y1 in POWER_STRIPS:
        d.rectangle((x0 + 1, oy + y0 + 2, x1 - 1, oy + y1 - 2), fill=RED)


def draw_panel(img, oy):
    """The valley and the score boards down the right-hand side.

    Stacked the way the original stacked them: Vally's name in script, Vally
    herself with her head down at the water hole, the fern desert beyond it,
    the barren ground, then the high score above the score.  The background is
    the same white as the playfield, because on the original the whole screen
    was one light field with the picture inked onto it.

    Everything that changes -- the digits, the multiplier, the ball count and
    Vally's tongue -- is a sprite drawn on top.  Those sprites are placed from
    the same table_spec constants used here, so the read-outs cannot drift off
    the artwork they belong to.
    """
    d = ImageDraw.Draw(img)
    x0 = PANEL_X
    cx = x0 + PANEL_W // 2

    d.rectangle((x0, oy, SCREEN_W - 1, oy + CANVAS_H - 1), fill=WHITE)

    draw_script_name(d, cx, oy + NAME_Y)
    draw_water_hole(d, x0 + 2, oy + SCENE_Y, PANEL_W - 4, SCENE_H)
    draw_vally_drinking(d, VALLY_X, oy + VALLY_Y)
    draw_desert(d, x0 + 2, oy + DESERT_Y, PANEL_W - 4, DESERT_H)
    draw_barren(img, x0 + 2, oy + BARREN_Y, PANEL_W - 4, BARREN_H)

    # Score boards.  The frames are drawn here; the digits are objects.  The
    # original labelled neither and told them apart by the colour of the frame:
    # the high score on top in orange, the score below it in teal.
    for y, colour in ((HIGH_DIGIT_Y, ORANGE), (SCORE_DIGIT_Y, TEAL)):
        d.rectangle(
            (
                BOARD_X0,
                oy + y - BOARD_PAD,
                BOARD_X1,
                oy + y + SCORE_DIGIT_H + BOARD_PAD - 1,
            ),
            outline=colour,
            width=2,
        )

    draw_text(d, BALLS_LABEL[0], oy + BALLS_LABEL[1], "BALLS", DMAGENTA)



# ---------------------------------------------------------------------------
# Collision grid
# ---------------------------------------------------------------------------

def build_world_grid():
    """Encode playfield's kind map, one byte per cell: kind and facing.

    The kinds come from the artwork (scripts/playfield.py); the facing is
    worked out here from the free space around each solid cell, so a curved
    wall gets a sensible normal without anyone writing one down.
    """
    kinds, (x0, y0, gw, gh) = playfield.collision_grid()
    solid = [[k != playfield.K_EMPTY for k in row] for row in kinds]

    R = 3
    grid = [[0] * gw for _ in range(gh)]
    for gy in range(gh):
        for gx in range(gw):
            if not solid[gy][gx]:
                continue
            sx = sy = 0.0
            for dy in range(-R, R + 1):
                for dx in range(-R, R + 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < gw and 0 <= ny < gh:
                        free = not solid[ny][nx]
                    else:
                        free = False  # off-table counts as solid
                    if free:
                        dist = math.hypot(dx, dy)
                        sx += dx / (dist * dist)
                        sy += dy / (dist * dist)
            mag = math.hypot(sx, sy)
            if mag < 1e-6:
                dir_idx = NUM_DIRS // 4  # buried: face straight down
            else:
                ang = math.atan2(sy / mag, sx / mag)
                dir_idx = int(round(ang / (2 * math.pi) * NUM_DIRS)) % NUM_DIRS
            grid[gy][gx] = (kinds[gy][gx] << 5) | dir_idx
    return grid, x0, y0, gw, gh


# ---------------------------------------------------------------------------
# Emitters
# ---------------------------------------------------------------------------


def write_tileset(preview=False):
    """The background: a palette strip, then the 336x224 world.

    The world is bigger than the 320x200 screen on purpose -- see
    scripts/playfield.py -- so the camera has somewhere to jiggle into.
    """
    W, H = playfield.WORLD_W, playfield.WORLD_H
    img = Image.new("P", (W, PAL_ROWS + H), BLACK)
    img.putpalette(palette_bytes())

    d = ImageDraw.Draw(img)
    swatch = W // 16
    for i in range(16):
        d.rectangle((i * swatch, 0, (i + 1) * swatch - 1, PAL_ROWS - 1), fill=i)

    img.paste(playfield.world_image(), (0, ART_Y))

    path = os.path.join(TILE_DIR, "01-table.png")
    img.save(path)

    if preview:
        os.makedirs(BUILD_DIR, exist_ok=True)
        prev = img.crop((0, ART_Y, W, ART_Y + H)).convert("RGB")
        prev = prev.resize((W * 2, H * 2), Image.NEAREST)
        prev.save(os.path.join(BUILD_DIR, "table-preview.png"))

    return count_tiles(img)


def count_tiles(img):
    """How many unique 16x16 background tiles the artwork needs."""
    px = img.load()
    seen = set()
    for ty in range(ART_Y, ART_Y + playfield.WORLD_H, 16):
        for tx in range(0, playfield.WORLD_W, 16):
            tile = tuple(
                px[tx + x, ty + y] for y in range(16) for x in range(16)
            )
            seen.add(tile)
    return len(seen)


def c_table(name, values, per_line=16, typ="const unsigned char"):
    out = [f"{typ} {name}[] = {{"]
    for i in range(0, len(values), per_line):
        out.append("    " + ", ".join(str(v) for v in values[i : i + per_line]) + ",")
    out.append("};")
    return "\n".join(out)


def write_collision_header(grid, gx0, gy0, gw, gh):
    dirs_x, dirs_y = [], []
    for i in range(NUM_DIRS):
        ang = i * 2 * math.pi / NUM_DIRS
        dirs_x.append(int(round(math.cos(ang) * 32)))
        dirs_y.append(int(round(math.sin(ang) * 32)))

    flat = [grid[y][x] for y in range(gh) for x in range(gw)]

    _, feet = playfield.source()
    diamonds = playfield.diamond_boxes()
    diamond_vals = []
    for x0, y0, x1, y1 in diamonds:
        diamond_vals += list(playfield.world(x0, y0)) + list(playfield.world(x1, y1))
    feet_world = [
        playfield.world(x0, y0) + playfield.world(x1, y1)
        for x0, y0, x1, y1 in playfield.foot_boxes(feet)
    ]
    foot_vals = []
    for x0, y0, x1, y1 in feet_world:
        foot_vals += [x0, y0, x1, y1]

    fly = [playfield.world(x, y) for x, y in playfield.fly_path()]
    fly_x = [p[0] for p in fly]
    fly_y = [p[1] for p in fly]
    fly_catch = min(range(len(fly)), key=lambda i: fly[i][0])

    plunger_vals = []
    for x0, y0, x1, y1 in playfield.plunger_boxes():
        plunger_vals += list(playfield.world(x0, y0)) + list(playfield.world(x1, y1))

    # Each tongue's root block, in world pixels, and the box the sprites are
    # drawn into -- the one the longest tongue needs.
    tongue_l = playfield.world(*playfield.DINO_TONGUE_ROOTS[0])
    tongue_r = playfield.world(*playfield.DINO_TONGUE_ROOTS[1])
    tongue_box_l, tongue_box_r = (
        playfield.world(
            min(q[0] for q in playfield.tongue_pixels(i, playfield.DINO_TONGUE_BLOCKS)),
            min(q[1] for q in playfield.tongue_pixels(i, playfield.DINO_TONGUE_BLOCKS)),
        )
        for i in range(2)
    )

    # Flipper geometry, one entry per side per animation frame.  "dir" runs
    # from the pivot to the tip; "nrm" is the outward normal of the face the
    # ball is meant to be launched from.
    fdx, fdy, fnx, fny = [], [], [], []
    frames = playfield.FLIPPER_FRAMES
    # Entries for the left flipper first.  Its tail sweeps to the right, away
    # from the pivot, so it is the unmirrored one.
    for mirror in (False, True):
        for f in range(frames):
            deg = playfield.FLIPPER_REST_DEG + (
                playfield.FLIPPER_UP_DEG - playfield.FLIPPER_REST_DEG
            ) * f / (frames - 1)
            a = math.radians(deg)
            sgn = -1 if mirror else 1
            fdx.append(int(round(sgn * math.cos(a) * 32)))
            fdy.append(int(round(math.sin(a) * 32)))
            fnx.append(int(round(sgn * math.sin(a) * 32)))
            fny.append(int(round(-math.cos(a) * 32)))

    lx, ly = playfield.world(*playfield.FLIPPER_PIVOTS[0])
    rx, ry = playfield.world(*playfield.FLIPPER_PIVOTS[1])
    tl, _ = playfield.world(playfield.TABLE_X0, 0)
    tr, _ = playfield.world(playfield.TABLE_X1, 0)
    lane0, _ = playfield.world(playfield.LANE_X0, 0)
    lane1, _ = playfield.world(playfield.LANE_X1, 0)
    _, lane_top = playfield.world(0, playfield.LANE_TOP)
    _, drain_y = playfield.world(0, playfield.DRAIN_BOX[3])

    body = f"""#ifndef _table_data_h
#define _table_data_h

/* Generated by scripts/gen-assets.py from scripts/playfield.py -- do not edit.
 *
 * The table is traced from art/pinball.png; the nine feet come from
 * art/pinball2.png.  It is diced into {gw}x{gh} cells of {playfield.CELL}x{playfield.CELL} pixels, covering the
 * table only -- the ball never leaves it, and a cell for the whole world would
 * cost three times as much.  A zero cell is open floor.  Any other cell packs
 * the kind of surface in the top 3 bits and the direction it faces in the low
 * 5, so one lookup tells the ball both how to bounce and what to score.
 *
 * Cell (0,0) is at world pixel (TBL_ORIGIN_X, TBL_ORIGIN_Y).
 */

#define TBL_CELL        {playfield.CELL}
#define TBL_CELL_SHIFT  {int(math.log2(playfield.CELL))}
#define TBL_GRID_W      {gw}
#define TBL_GRID_H      {gh}
#define TBL_ORIGIN_X    {gx0}
#define TBL_ORIGIN_Y    {gy0}
#define TBL_NUM_DIRS    {NUM_DIRS}

#define TBL_KIND(c)     ((c) >> 5)
#define TBL_DIR(c)      ((c) & 31)

#define K_EMPTY   {playfield.K_EMPTY}
#define K_WALL    {playfield.K_WALL}
#define K_BUMPER  {playfield.K_BUMPER}
#define K_FOOT    {playfield.K_FOOT}
#define K_SCENERY {playfield.K_SCENERY}
#define K_DRAIN   {playfield.K_DRAIN}

/* The world is bigger than the screen so the camera has room to move; the
 * artwork is centred in it and CAMERA_X/Y is where the view sits at rest. */
#define WORLD_W          {playfield.WORLD_W}
#define WORLD_H          {playfield.WORLD_H}
#define CAMERA_X         {playfield.ORIGIN_X}
#define CAMERA_Y         {playfield.ORIGIN_Y}
#define CAMERA_MAX_X     {playfield.WORLD_W - 320}
#define CAMERA_MAX_Y     {playfield.WORLD_H - 200}

/* All of these are world pixels. */
#define PLAYFIELD_LEFT   {tl}
#define PLAYFIELD_RIGHT  {tr}
#define LANE_X0          {lane0}
#define LANE_X1          {lane1}
#define LANE_TOP         {lane_top}
#define DRAIN_Y          {drain_y}
#define BALL_R           {playfield.BALL_R}

#define NUM_FEET         {len(feet_world)}
/* The first NUM_TOP_FEET are the ones under the pods -- the marks the manual
 * says feed Vally's tongue.  foot_boxes() returns them top row first. */
#define NUM_TOP_FEET     {sum(1 for f in feet_world if f[1] == feet_world[0][1])}
#define NUM_DIAMONDS     {len(diamonds)}
#define DIAMOND_MID_OFF  {playfield.DIAMOND_MID_OFF}

/* The three big bumpers, as x0, y0, x1, y1.  Striking one flashes its middle;
 * the strips and the small wall diamonds score but do not flash. */
{c_table("tblDiamondBox", diamond_vals, per_line=16)}

/* The panel read-outs, placed from the boards drawn in the artwork. */
#define SCORE_DIGITS      {playfield.SCORE_DIGITS}
#define SCORE_DIGIT_X0    {playfield.SCORE_DIGIT_X0 + playfield.ORIGIN_X}
#define SCORE_DIGIT_PITCH {playfield.SCORE_DIGIT_PITCH}
#define SCORE_GROUP_GAP   {playfield.SCORE_GROUP_GAP}
#define HIGH_DIGIT_Y      {playfield.HIGH_BOX[1] + playfield.SCORE_DIGIT_DY + playfield.ORIGIN_Y}
#define SCORE_DIGIT_Y     {playfield.SCORE_BOX[1] + playfield.SCORE_DIGIT_DY + playfield.ORIGIN_Y}
#define MULT_DIGIT_X      {playfield.MULT_XY[0] + playfield.ORIGIN_X}
#define MULT_DIGIT_Y      {playfield.MULT_XY[1] + playfield.ORIGIN_Y}
#define BALLS_DIGIT_X     {playfield.BALLS_XY[0] + playfield.ORIGIN_X}
#define BALLS_DIGIT_Y     {playfield.BALLS_XY[1] + playfield.ORIGIN_Y}
#define BALLS_PITCH       {playfield.BALLS_PITCH}
#define PANEL_TONGUE_X    {playfield.TONGUE_XY[0] + playfield.ORIGIN_X}
#define PANEL_TONGUE_Y    {playfield.TONGUE_XY[1] + playfield.ORIGIN_Y}

/* The volcano, and the two slopes the lava runs down. */
#define VOLCANO_X         {playfield.VOLCANO_APEX[0] + playfield.ORIGIN_X}
#define VOLCANO_Y         {playfield.VOLCANO_APEX[1] + playfield.ORIGIN_Y}
/* Distances from the apex to the foot of each slope, as magnitudes: the left
 * one runs left, the right one right, and both run down.  Keeping them
 * positive keeps the shifts in 06-lava.c off negative numbers. */
#define LAVA_L_DX         {abs(playfield.VOLCANO_LEFT_FOOT[0] - playfield.VOLCANO_APEX[0])}
#define LAVA_L_DY         {abs(playfield.VOLCANO_LEFT_FOOT[1] - playfield.VOLCANO_APEX[1])}
#define LAVA_R_DX         {abs(playfield.VOLCANO_RIGHT_FOOT[0] - playfield.VOLCANO_APEX[0])}
#define LAVA_R_DY         {abs(playfield.VOLCANO_RIGHT_FOOT[1] - playfield.VOLCANO_APEX[1])}
#define LAVA_FRAMES       {playfield.LAVA_FRAMES}
#define GATE_X0           {playfield.GATE_BOX[0] + playfield.ORIGIN_X}
#define GATE_Y0           {playfield.GATE_BOX[1] + playfield.ORIGIN_Y}
#define GATE_X1           {playfield.GATE_BOX[2] + playfield.ORIGIN_X}
#define GATE_Y1           {playfield.GATE_BOX[3] + playfield.ORIGIN_Y}

/* The dinosaurs' tongues.  Like the gate these come and go, so they cannot be
 * cells in the grid; unlike the gate they lie at 45 degrees, so the ball tests
 * its distance from a line rather than its place in a box.  X is the root
 * block's outer edge -- the left tongue grows towards smaller x and the right
 * towards larger -- and Y is the root block's bottom. */
#define TONGUE_L_X        {tongue_l[0]}
#define TONGUE_R_X        {tongue_r[0]}
#define TONGUE_Y          {tongue_l[1]}
#define TONGUE_BOX_L_X    {tongue_box_l[0]}
#define TONGUE_BOX_R_X    {tongue_box_r[0]}
#define TONGUE_BOX_Y      {tongue_box_l[1]}
#define TONGUE_MAX        {playfield.DINO_TONGUE_BLOCKS}
#define TONGUE_PERIOD     {playfield.DINO_TONGUE_PERIOD}

/* How far out a tongue is on each tick of its cycle.  The two run half a
 * period apart, so one is always further out than the other. */
{c_table("tblTongueLen", playfield.tongue_lengths(), per_line=16)}

/* The nine feet, as x0, y0, x1, y1.  Hitting one turns it cyan and takes it
 * out of play until the ball drains. */
{c_table("tblFootBox", foot_vals, per_line=16)}

/* Where the fly is on each tick of its cycle.  It is a table because the 6809
 * has no sine and no multiply worth the name, and 128 bytes is cheaper than
 * either; the loop is closed, so an index that wraps is the whole of it. */
#define FLY_PERIOD        {playfield.FLY_PERIOD}
/* The tick at which it is furthest left, which is where it can be caught. */
#define FLY_CATCH_TICK    {fly_catch}
/* How many ticks the tongue takes to reach full stretch, and so how far ahead
 * of the catch it has to start. */
#define TONGUE_REACH_STAGES {playfield.TONGUE_REACH_STAGES}
{c_table("tblFlyX", fly_x, per_line=16)}

{c_table("tblFlyY", fly_y, per_line=16)}

/* The four plunger lines along the top, as x0, y0, x1, y1, in the same order
 * as the four top feet: the leftmost foot lights the leftmost line.  A ball
 * through a lit line is sped on its way and grows Vally's tongue. */
#define NUM_PLUNGERS      {len(plunger_vals) // 4}
{c_table("tblPlungerBox", plunger_vals, per_line=16)}

/* Unit normals, scaled by 32. */
{c_table("tblDirX", dirs_x, typ="const signed char")}

{c_table("tblDirY", dirs_y, typ="const signed char")}

/* Flippers.  Entries 0..{frames - 1} are the left flipper from rest to fully
 * raised; the next {frames} are the right. */
#define FLIPPER_FRAMES   {frames}
#define FLIPPER_LEN      {playfield.FLIPPER_LEN}
#define FLIPPER_HALF_THICK {playfield.FLIPPER_HALF_THICK}
#define FLIP_L_X         {lx}
#define FLIP_L_Y         {ly}
#define FLIP_R_X         {rx}
#define FLIP_R_Y         {ry}

{c_table("tblFlipDirX", fdx, typ="const signed char")}

{c_table("tblFlipDirY", fdy, typ="const signed char")}

{c_table("tblFlipNrmX", fnx, typ="const signed char")}

{c_table("tblFlipNrmY", fny, typ="const signed char")}

/* The grid itself is {len(flat)} bytes, which is a large slice of an 8K object code
 * page, so only the ball object -- the one thing that collides with the table
 * -- asks for it, by defining TBL_WANT_GRID before including this header. */
#ifdef TBL_WANT_GRID
{c_table("tblGrid", flat, per_line=24)}
#endif

#endif /* _table_data_h */
"""
    with open(os.path.join(OBJ_DIR, "table_data.h"), "w") as f:
        f.write(body)


# ---------------------------------------------------------------------------
# Sprites
#
# Sprite sheets are laid out on a transparent field and each sprite is found by
# flood fill from its anchor point, so every sprite must be one connected blob
# with clear space around it.  The anchor is also the point that lands on the
# object's globalX/globalY, which is why the flipper anchors sit on the pivot.
# ---------------------------------------------------------------------------

TRANSPARENT = 16
SPRITE_DIR = os.path.join(ROOT, "game", "sprites")


def sprite_palette():
    pal = palette_bytes()
    pal[TRANSPARENT * 3 : TRANSPARENT * 3 + 3] = [255, 0, 255]
    return pal


def new_sheet(w, h):
    img = Image.new("P", (w, h), TRANSPARENT)
    img.putpalette(sprite_palette())
    return img


def write_sprite_group(idx, name, size, draw_fn, chunk=None):
    """Draw a sheet and emit its JSON descriptor.

    draw_fn is handed an ImageDraw and returns [(name, anchor_x, anchor_y,
    single_pixel), ...] or [(name, x, y, single_pixel, save_background), ...].

    save_background=False drops the erase code entirely, which is a large
    saving in both compiled size and per-frame work.  It is only safe for a
    sprite that is opaque over its whole footprint and drawn in the same place
    every single frame, so that redrawing it wipes the previous image: nothing
    ever erases it.

    chunk sets ChunkHint, which caps how many store operations the sprite
    compiler permutes at once.  Large byte-aligned blocks otherwise send that
    search exponential -- a single 66x22 plate took over twenty minutes.
    """
    img = new_sheet(*size)
    d = ImageDraw.Draw(img)
    sprites = draw_fn(d, img)
    img.save(os.path.join(SPRITE_DIR, f"{idx:02d}-{name}.png"))

    desc = {
        "Main": {
            "Group": idx,
            "Image": f"{idx:02d}-{name}.png",
            "Transparent": [255, 0, 255],
            "Palette": 1,
        },
        "Sprites": [
            spec
            for spec in (
                {
                    "Name": item[0],
                    "Location": [item[1], item[2]],
                    "SinglePixelPosition": item[3],
                    **({} if chunk is None else {"ChunkHint": chunk}),
                    **({} if len(item) < 5 else {"SaveBackground": item[4]}),
                }
                for item in sprites
            )
        ],
    }
    import json

    with open(os.path.join(SPRITE_DIR, f"{idx:02d}-{name}.json"), "w") as f:
        json.dump(desc, f, indent=2)
        f.write("\n")
    return len(sprites)


def draw_ball_sheet(d, img):
    """A 7x7 ball with a highlight, plus the launcher plunger head.

    The playfield is white, so the ball needs a dark rim or it vanishes into
    the table.
    """
    cx, cy = 8, 8
    d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=DGREY)
    d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=WHITE)
    d.ellipse((cx, cy, cx + 2, cy + 2), fill=GREY)
    d.point((cx - 1, cy - 1), fill=YELLOW)

    # Launcher head: a small orange block that rides up and down the lane.
    lx, ly = 30, 8
    d.rectangle((lx - 4, ly - 3, lx + 4, ly + 3), fill=ORANGE)
    d.rectangle((lx - 4, ly - 3, lx + 4, ly - 2), fill=YELLOW)
    d.rectangle((lx - 4, ly + 2, lx + 4, ly + 3), fill=BROWN)

    # The ball goes anywhere, so it needs both the byte-aligned draw and the
    # shifted one.  The launcher only ever sits at LANE_CX, which is even, so
    # it gets the aligned half alone -- SinglePixelPosition emits two draw
    # routines instead of one, and the second is dead weight here.
    return [("Ball", cx, cy, True), ("Launcher", lx, ly, False)]


def flipper_points(pivot, deg):
    """Outline of a flipper rotated deg degrees below horizontal."""
    px, py = pivot
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)

    def at(along, across):
        return (px + along * ca - across * sa, py + along * sa + across * ca)

    base = float(playfield.FLIPPER_HALF_THICK)
    tip = base / 2.0
    return [
        at(0, -base),
        at(playfield.FLIPPER_LEN, -tip),
        at(playfield.FLIPPER_LEN, tip),
        at(0, base),
    ]


def draw_flipper_sheet(d, img):
    """Six frames of the right flipper; the left is those pixels mirrored.

    Only one side is ever drawn.  Reflecting the outline and rasterising it
    again rounds differently on each side and leaves the two a handful of
    pixels apart -- enough to see, and enough to make one flipper hit sooner
    than the other.  Mirroring the finished pixels makes them identical by
    construction.

    Side 0 is the left flipper.  It pivots on its dinosaur's tail, which is the
    inboard end, so its tip points outward; the collision tables in
    table_data.h are built in the same order and must agree.
    """
    cell = 40
    pivot_x, pivot_y = 6, 20
    left, right = [], []

    for f in range(playfield.FLIPPER_FRAMES):
        deg = playfield.FLIPPER_REST_DEG + (
            playfield.FLIPPER_UP_DEG - playfield.FLIPPER_REST_DEG
        ) * f / (playfield.FLIPPER_FRAMES - 1)

        one = Image.new("P", (cell, cell), TRANSPARENT)
        one.putpalette(sprite_palette())
        od = ImageDraw.Draw(one)
        od.polygon(flipper_points((pivot_x, pivot_y), deg), fill=TEAL, outline=DTEAL)
        # Hub, drawn last so the anchor pixel is always opaque.
        od.ellipse(
            (pivot_x - 3, pivot_y - 3, pivot_x + 3, pivot_y + 3), fill=ORANGE)
        od.point((pivot_x, pivot_y), fill=RED)

        img.paste(one, (f * cell, 0))
        left.append((f"LeftFlip{f}", f * cell + pivot_x, pivot_y, False))

        img.paste(one.transpose(Image.FLIP_LEFT_RIGHT), (f * cell, cell))
        right.append(
            (f"RightFlip{f}", f * cell + cell - 1 - pivot_x, cell + pivot_y, False))

    # Both pivots sit on even pixel columns, so these never need the
    # single-pixel-position variant -- which would double the code.
    return left + right


# A compact 5x7 digit font: one string of five characters per row.
DIGIT_FONT = {
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
}

# One definition, in table_spec, because the score board frames are sized from
# it as well as the digits that go inside them.
DIGIT_W = SCORE_DIGIT_W
DIGIT_H = SCORE_DIGIT_H


def draw_digit_sheet(d, img):
    sprites = []
    for i in range(10):
        x0 = 2 + i * (DIGIT_W + 4)
        y0 = 2
        # An opaque tile in the panel's own white, so drawing a digit also
        # wipes the one before it and every digit is exactly the same size.
        d.rectangle((x0, y0, x0 + DIGIT_W - 1, y0 + DIGIT_H - 1), fill=WHITE)
        rows = DIGIT_FONT[str(i)]
        for ry, row in enumerate(rows):
            for rx, ch in enumerate(row):
                if ch == "#":
                    d.point((x0 + 1 + rx, y0 + 2 + ry), fill=MAGENTA)
        sprites.append((f"Digit{i}", x0, y0, False, False))

    # A blank cell.  Read-outs that switch off (the flashing high score, the
    # multiplier at 1X) draw this instead of going inactive, because a sprite
    # with no erase code would otherwise stay on screen for ever.
    x0 = 2 + 10 * (DIGIT_W + 4)
    d.rectangle((x0, 2, x0 + DIGIT_W - 1, 2 + DIGIT_H - 1), fill=WHITE)
    sprites.append(("DigitBlank", x0, 2, False, False))

    # The balls still to play, drawn one per ball beside the score boards.
    # Both of these are opaque 8x8 blocks and carry no erase code either, so
    # the blank is what takes a used ball off the panel.
    for name, ink in (("BallLive", DGREY), ("BallBlank", None)):
        x0 += DIGIT_W + 4
        d.rectangle((x0, 2, x0 + 7, 9), fill=WHITE)
        if ink is not None:
            d.ellipse((x0 + 1, 3, x0 + 6, 8), fill=ink)
            d.point((x0 + 3, 4), fill=WHITE)
        sprites.append((name, x0, 2, False, False))
    return sprites


def draw_lite_sheet(d, img):
    """The nine feet, live and spent.

    Both states are opaque across the whole box, so they can be drawn without
    saving the background: there is no erase code, and it is the orange that
    puts a foot back when the ball drains rather than any erase.  The shapes
    are lifted straight out of the artwork, so an overlay lands exactly on the
    foot painted underneath it.

    The feet do not all sit on even columns, so these are the one place we pay
    for SinglePixelPosition.  At 6x4 pixels that is a few hundred bytes, which
    is cheaper than nudging the artwork to suit the sprite compiler.
    """
    sprites = []
    _, feet = playfield.source()
    shapes = {}
    for x0, y0, x1, y1 in playfield.foot_boxes(feet):
        shapes.setdefault((x1 - x0 + 1, y1 - y0 + 1), (x0, y0))

    # The bumper middles, hot and cool.  Both are lifted straight out of the
    # artwork so the ring of orange around the hole matches the bumper exactly;
    # the hot one just has magenta where the hole is.
    src, _ = playfield.source()
    sp = src.load()
    dx0, dy0 = playfield.diamond_boxes()[0][:2]
    mid = playfield.DIAMOND_MID
    for i, hole in enumerate((MAGENTA, WHITE)):
        x0 = 2 + i * (mid + 4)
        for j in range(mid):
            for k in range(mid):
                c = sp[dx0 + playfield.DIAMOND_MID_OFF + k,
                       dy0 + playfield.DIAMOND_MID_OFF + j]
                d.point((x0 + k, 2 + j),
                        fill=ORANGE if c == playfield.SRC_ORANGE else hole)
        sprites.append((f'Diamond{"Hot" if i == 0 else "Cool"}', x0, 2, False, False))

    x = 2 + 2 * (mid + 4) + 4
    for (w, h), (sx, sy) in sorted(shapes.items()):
        for ink, tag in ((ORANGE, "Live"), (TEAL, "Spent")):
            d.rectangle((x, 2, x + w - 1, 2 + h - 1), fill=WHITE)
            for j in range(h):
                for i in range(w):
                    if (sx + i, sy + j) in feet:
                        d.point((x + i, 2 + j), fill=ink)
            sprites.append((
                f'Foot{"Wide" if w > h else "Tall"}{tag}', x, 2, True, False))
            x += w + 4

    # The plunger lines, lit and unlit.  Both are opaque over the same box and
    # always drawn in the same place, so neither needs to save the background;
    # the unlit one is plain playfield, which is all that is behind them.
    pw, ph = playfield.PLUNGER_W, playfield.PLUNGER_H
    for ink, tag in ((ORANGE, "On"), (WHITE, "Off")):
        d.rectangle((x, 2, x + pw - 1, 2 + ph - 1), fill=ink)
        sprites.append((f"Plunger{tag}", x, 2, True, False))
        x += pw + 4
    return sprites


# Panel read-outs.  The multiplier and ball count are drawn with the ordinary
# score digits, because the sprite compiler unrolls every sprite into straight
# line code and a big block of text costs kilobytes of it.  Only the two things
# digits cannot express -- Vally's tongue and the end-of-game plate -- are
# sprites here.
TONGUE_STAGES = 6
TONGUE_REACH_STAGES = 6
TONGUE_ROW_Y = 62  # the tongue stages sit below the rest of the panel sheet
GAMEOVER_W, GAMEOVER_H = 66, 18


def draw_panel_sheet(d, img):
    sprites = []

    # Vally's tongue, reaching further with every pair of top marks hit.  It
    # goes down, then left, then down again rather than straight at the fly,
    # and the last stage finishes on the fly's body at the far left of the
    # flight -- so a tongue that has not been fed twelve times cannot reach it,
    # and one that has cannot miss.  Laid out in two rows because a full reach
    # is over fifty pixels wide.
    pts = playfield.vally_tongue_pixels(playfield.TONGUE_REACH_STAGES)
    tw = max(q[0] for q in pts) - min(q[0] for q in pts) + 1
    th = max(q[1] for q in pts) - min(q[1] for q in pts) + 1
    mx, my = playfield.TONGUE_XY
    for stage in range(1, TONGUE_REACH_STAGES + 1):
        cx = 2 + ((stage - 1) % 3) * (tw + 4)
        cy = TONGUE_ROW_Y + ((stage - 1) // 3) * (th + 4)
        px = playfield.vally_tongue_pixels(stage)
        x0 = min(q[0] for q in px)
        for qx, qy in px:
            d.point((cx + qx - x0, cy + qy - my), fill=ORANGE)
        sprites.append((f"Tongue{stage}", cx + mx - x0, cy, False))

    # The end-of-game message, shown across the middle of the table.  It is
    # bare lettering rather than a filled plate: the sprite compiler unrolls
    # every opaque pixel into store instructions, and a solid block of a
    # thousand of them takes the optimiser into the weeds for tens of minutes.
    #
    # A sprite is found by flood filling from its anchor, so the two lines are
    # tied together by a rule underneath and the anchor sits on that rule --
    # otherwise the "sprite" would be whatever single pixel the anchor landed
    # on.
    x0, y0 = 2, 34
    draw_text(d, x0, y0, "GAME OVER", RED, scale=1)
    draw_text(d, x0, y0 + 9, "PUSH SPACE", DGREY, scale=1)
    d.line([(x0, y0 + 7), (x0 + GAMEOVER_W - 1, y0 + 7)], fill=RED)
    d.line([(x0, y0 + 16), (x0 + GAMEOVER_W - 1, y0 + 16)], fill=RED)
    d.line([(x0, y0 + 7), (x0, y0 + 16)], fill=RED)
    sprites.append(("GameOver", x0, y0, False))

    # The "X" of the score multiplier.  It is a sprite rather than part of the
    # panel artwork so it can disappear along with the digits at 1X.
    x0, y0 = 160, 34
    draw_text(d, x0, y0, "X", MAGENTA, scale=1)
    sprites.append(("MultX", x0, y0, False))

    # The gate across the mouth of the launch lane, shut and open.  Both are
    # opaque over the same footprint and save no background, so the open one is
    # what takes the bar away again -- there is no erase code to do it.
    # The stopper across the gap between the table and the launch lane, shut
    # and open.  Both are opaque over the same footprint and save no
    # background, so the open one is what takes the bar away again.
    #
    # It sits on an odd column, so this is the one sprite in the game that pays
    # for SinglePixelPosition.  Nudging it a pixel to suit the compiler would
    # leave a slot down one side of the gap and eat a pixel of the table on the
    # other.
    for i, (name, ink) in enumerate((("GateShut", MAGENTA), ("GateOpen", WHITE))):
        # Clear of the GameOver plate (x 2..67) and the tongue frames (y 2..26).
        x0 = 100 + i * (playfield.GATE_W + 8)
        y0 = 30
        d.rectangle((x0, y0, x0 + playfield.GATE_W - 1, y0 + playfield.GATE_H - 1),
                    fill=ink)
        sprites.append((name, x0, y0, True, False))

    return sprites


def draw_lava_sheet(d, img):
    """The lava, as frames of one flow rather than a swarm of moving drops.

    Thirty-six drops, each saving and restoring the background every tick, cost
    the game a third of its frame rate.  This is one sprite in one place, so
    what it costs no longer grows with how much lava is drawn.

    Each frame is two streams running from the apex down both slopes with
    gobbets riding on them, and the gobbets shift a fraction of their spacing
    between frames so the cycle reads as flow.  The streams meet at the apex on
    purpose: a sprite is found by flood fill, so a frame of separate blobs would
    come back as whichever blob the anchor landed on and the rest would
    silently vanish.
    """
    frames = playfield.LAVA_FRAMES
    ax, ay = playfield.VOLCANO_APEX
    slopes = (playfield.VOLCANO_LEFT_FOOT, playfield.VOLCANO_RIGHT_FOOT)

    x0 = min(f[0] for f in slopes)
    cell_w = max(f[0] for f in slopes) - x0 + 6
    cell_h = max(f[1] for f in slopes) - ay + 6

    sprites = []
    for f in range(frames):
        ox = (f % 4) * cell_w + 2
        oy = (f // 4) * cell_h + 2
        apex = (ox + ax - x0, oy + 2)

        for foot in slopes:
            fx, fy = ox + foot[0] - x0, oy + 2 + foot[1] - ay
            d.line([apex, (fx, fy)], fill=ORANGE, width=2)
            for k in range(playfield.LAVA_BULGES):
                t = (k + f / frames) / playfield.LAVA_BULGES
                bx = apex[0] + (fx - apex[0]) * t
                by = apex[1] + (fy - apex[1]) * t
                d.ellipse((bx - 2, by - 2, bx + 2, by + 2), fill=ORANGE)
                d.ellipse((bx - 1, by - 1, bx + 1, by + 1), fill=YELLOW)
        sprites.append((f"LavaFlow{f}", apex[0], apex[1], False))
    return sprites


def draw_tongue_sheet(d, img):
    """Each tongue at each extension, both sides.

    Every length is drawn into the same box -- the one the longest of them
    needs -- filled with the playfield that lies under it and the tongue laid
    over the top.  That costs eight times the opaque pixels of a bare chain of
    blocks, but it buys the two things that make these cheap to run: the box is
    the same size and in the same place whichever length is showing, so the
    sprites need not save the background, and a shorter tongue paints the
    playfield back over the longer one it replaces.  Drawn every tick they were
    costing more than they were worth; drawn twice per change they cost almost
    nothing.

    The box starts on an even column on both sides, so neither pays for
    SinglePixelPosition either.
    """
    world = playfield.world_image().load()
    size = playfield.DINO_TONGUE_BLOCKS * 2
    sprites = []
    for side in range(2):
        full = playfield.tongue_pixels(side, playfield.DINO_TONGUE_BLOCKS)
        bx0 = min(q[0] for q in full)
        by0 = min(q[1] for q in full)
        for n in range(1, playfield.DINO_TONGUE_BLOCKS + 1):
            cx = 2 + (side * playfield.DINO_TONGUE_BLOCKS + n - 1) * (size + 4)
            for j in range(size):
                for i in range(size):
                    wx, wy = playfield.world(bx0 + i, by0 + j)
                    ink = world[wx, wy]
                    assert ink != TRANSPARENT, "playfield under a tongue is keyed"
                    d.point((cx + i, 2 + j), fill=ink)
            for qx, qy in playfield.tongue_pixels(side, n):
                d.point((cx + qx - bx0, 2 + qy - by0), fill=TEAL)
            sprites.append((
                f'Tongue{"R" if side else "L"}{n}', cx, 2, False, False))
    return sprites


def draw_fly_sheet(d, img):
    """The prehistoric fly: an orange body between two teal wings.

    Lifted from the original's shape rather than invented.  The wings meet the
    body along a full edge on each side, which matters: a sprite is found by
    flood fill, and wings that only cornered onto the body would be left behind
    without a word.
    """
    w, h = playfield.FLY_W, playfield.FLY_H
    d.rectangle((2, 2, 2 + 3, 2 + 3), fill=TEAL)
    d.rectangle((2 + w - 4, 2, 2 + w - 1, 2 + 3), fill=TEAL)
    d.rectangle((2 + 4, 2 + 2, 2 + 7, 2 + h - 1), fill=ORANGE)
    return [("Fly", 2, 2, True)]


def write_sprites():
    os.makedirs(SPRITE_DIR, exist_ok=True)
    total = 0
    total += write_sprite_group(1, "ball", (48, 20), draw_ball_sheet)
    total += write_sprite_group(2, "flipper", (240, 80), draw_flipper_sheet, chunk=8)
    total += write_sprite_group(3, "digit", (176, 16), draw_digit_sheet)
    total += write_sprite_group(4, "lite", (160, 40), draw_lite_sheet, chunk=8)
    total += write_sprite_group(5, "panel", (216, 140), draw_panel_sheet, chunk=8)
    total += write_sprite_group(6, "lava", (192, 72), draw_lava_sheet, chunk=8)
    total += write_sprite_group(7, "tongue", (112, 16), draw_tongue_sheet,
                                chunk=8)
    total += write_sprite_group(8, "fly", (24, 16), draw_fly_sheet, chunk=8)
    return total


# ---------------------------------------------------------------------------
# A 5x7 bitmap font, shared by the score digits and the splash screens.
# ---------------------------------------------------------------------------

LETTER_FONT = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["....#", "....#", "....#", "....#", "#...#", "#...#", ".###."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".###.", "#...#", "#....", ".###.", "....#", "#...#", ".###."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#...#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".....", "..#.."],
    "'": ["..#..", "..#..", ".....", ".....", ".....", ".....", "....."],
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
}


def glyph(ch):
    if ch in LETTER_FONT:
        return LETTER_FONT[ch]
    return DIGIT_FONT.get(ch, LETTER_FONT[" "])


def draw_text(d, x, y, s, colour, scale=1, spacing=1):
    """Draws s at scale, one 5x7 cell per character."""
    for ch in s.upper():
        rows = glyph(ch)
        for ry, row in enumerate(rows):
            for rx, c in enumerate(row):
                if c == "#":
                    px = x + rx * scale
                    py = y + ry * scale
                    d.rectangle((px, py, px + scale - 1, py + scale - 1), fill=colour)
        x += (5 + spacing) * scale
    return x


# ---------------------------------------------------------------------------
# The right-hand panel.
#
# Almost everything down this strip is a curve, so it is drawn as strokes
# through control points rather than as rectangles: the 5x7 cell font cannot
# say "handwriting", and the pond and the hills read as scenery only if their
# edges wobble.
# ---------------------------------------------------------------------------


def spline(pts, steps=8):
    """Sample a Catmull-Rom curve through every one of pts."""
    p = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(len(p) - 3):
        p0, p1, p2, p3 = p[i : i + 4]
        for s in range(steps + 1):
            t = s / steps
            t2 = t * t
            t3 = t2 * t
            out.append(
                tuple(
                    0.5
                    * (
                        2 * p1[k]
                        + (-p0[k] + p2[k]) * t
                        + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                        + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3
                    )
                    for k in (0, 1)
                )
            )
    return out


def stroke(d, pts, colour, width=2):
    d.line(spline(pts), fill=colour, width=width, joint="curve")


# "Vally", as the original wrote it: joined-up script, in a box VALLY_SCRIPT_W
# wide and 31 tall, with the x-height top at y=12, the baseline at y=22 and the
# y's tail dropping to y=30.  Each entry is one pen stroke, given as the control
# points of a Catmull-Rom curve.
VALLY_SCRIPT_W = 112
VALLY_SCRIPT = [
    # The capital V: down to the point, up to the top right, then a hook that
    # hands over to the a.
    [(1, 3), (7, 13), (12, 22), (18, 12), (23, 2), (27, 6), (27, 13)],
    # "ally", written without lifting the pen.  The l's are the fiddly part:
    # their loops only read as loops if the up stroke and the down stroke are
    # about six pixels apart at the top, which is why each one leans so far.
    [
        (27, 13), (33, 12),                                          # into the a
        (28, 14), (28, 19), (33, 21), (36, 18), (36, 12),            # a, bowl
        (36, 21), (40, 21),                                          # a, stem
        (46, 13), (52, 4), (47, 2), (44, 7), (46, 14), (49, 21),     # first l
        (53, 20),
        (59, 13), (65, 4), (60, 2), (57, 7), (59, 14), (62, 21),     # second l
        (66, 20),
        (70, 12), (72, 21), (77, 17), (79, 11),                      # y, bowl
        (80, 20), (79, 26), (74, 30), (69, 29), (71, 24),            # y, tail
    ],
    # The flourish the tail runs into, sweeping back under the whole word.
    [(71, 24), (80, 29), (91, 30), (102, 26), (111, 19)],
]


def draw_script_name(d, cx, y):
    """Vally's name, centred on cx with its top at y."""
    left = cx - VALLY_SCRIPT_W // 2
    for pen in VALLY_SCRIPT:
        stroke(d, [(left + px, y + py) for px, py in pen], MAGENTA, 2)


def draw_water_hole(d, x0, y0, w, h):
    """Two peaks on the skyline and the water hole below them.

    The pond is an outline rather than a filled shape, as it was in the
    original: the water is the same white as the ground and only its rim is
    inked, which is also what lets Vally's head cross the rim and read as being
    in the water.
    """
    horizon = y0 + h // 2

    d.polygon([(x0, horizon), (x0 + 16, y0 + 5), (x0 + 34, horizon)], fill=MAGENTA)
    d.polygon(
        [(x0 + 62, horizon), (x0 + 90, y0 + 2), (x0 + w - 1, horizon)], fill=MAGENTA
    )

    d.ellipse((x0 + 2, horizon - 2, x0 + w - 3, y0 + h - 5), outline=ORANGE, width=2)

    # Ripples, to say that the outline is water and not a crater.
    for dx, dy, span in ((14, 10, 16), (44, 14, 12), (74, 11, 14)):
        d.line([(x0 + dx, horizon + dy), (x0 + dx + span, horizon + dy)], fill=TEAL)


def draw_vally_drinking(d, x, y):
    """Vally at the water hole, her neck arched over and her head in it.

    (x, y) is the top-left of her body.  Her mouth has to end up at
    VALLY_MOUTH, because that is where the tongue sprite is anchored; the two
    are checked against each other here rather than left to drift.
    """
    # Tail, drooping away over the far shore.  Laid down as circles of
    # shrinking radius along a curve: a polygon of the same shape kinks at
    # every control point and reads as a spike rather than a tail.
    path = spline(
        [(x + 4, y + 12), (x - 3, y + 17), (x - 13, y + 22), (x - 24, y + 24),
         (x - 34, y + 24)],
        steps=10,
    )
    for i, (tx, ty) in enumerate(path):
        r = 4.2 * (1.0 - i / (len(path) - 1)) ** 1.2 + 0.6
        d.ellipse((tx - r, ty - r, tx + r, ty + r), fill=TEAL)

    # Body, with a lumpy back.
    d.ellipse((x, y + 4, x + 30, y + 16), fill=TEAL)
    for hx in (3, 11, 19):
        d.ellipse((x + hx, y + 1, x + hx + 9, y + 8), fill=TEAL)

    # Legs, planted on the shore.
    for lx in (5, 20):
        d.rectangle((x + lx, y + 14, x + lx + 4, y + 22), fill=DTEAL)

    # Neck, thick as a sauropod's, coming down over the rim, and the head at
    # the end of it turned to face out of the picture with its muzzle in the
    # water: two eyes rather than one is the whole difference between a head
    # seen from the side and a head looking at you.
    stroke(
        d,
        [(x + 24, y + 6), (x + 32, y + 4), (x + 39, y + 10), (x + 42, y + 18)],
        TEAL,
        6,
    )
    d.ellipse((x + 34, y + 13, x + 50, y + 24), fill=TEAL)  # skull
    d.ellipse((x + 38, y + 20, x + 47, y + 29), fill=TEAL)  # muzzle, in the water
    for ex in (37, 45):
        d.rectangle((x + ex, y + 16, x + ex + 1, y + 17), fill=WHITE)

    mouth = (VALLY_X + 50, VALLY_Y + 22)
    assert mouth == VALLY_MOUTH, f"tongue anchor {VALLY_MOUTH} is not at {mouth}"


def draw_desert(d, x0, y0, w, h):
    """The near shore, dotted with the little teal Y's the original used for
    cycads -- about as much as block graphics can say about a plant."""
    base = y0 + h - 1
    for px, dy, s in (
        (5, 0, 6), (20, 5, 9), (37, 1, 6), (54, 6, 10), (71, 0, 7),
        (87, 5, 9), (103, 1, 6), (117, 6, 10),
    ):
        x, ty = x0 + px, base - dy
        arm = 1 + s // 3
        d.line([(x, ty), (x, ty - s)], fill=TEAL)
        d.line([(x - arm, ty - s - arm), (x, ty - s + 1)], fill=TEAL)
        d.line([(x + arm, ty - s - arm), (x, ty - s + 1)], fill=TEAL)


def draw_barren(img, x0, y0, w, h):
    """The barren ground between the desert and the score boards.

    The original hatched it, which in block graphics means a chequer.  An
    unbroken 2x2 chequer is a single unique 16x16 tile however much of it there
    is, so the band is nearly free; only its ragged edges cost anything.
    """
    mask = Image.new("1", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.polygon(
        spline([(0, 7), (w // 3, 2), (2 * w // 3, 5), (w - 1, 1)])
        + spline([(w - 1, h - 6), (2 * w // 3, h - 1), (w // 3, h - 3), (0, h - 1)]),
        fill=1,
    )
    mp = mask.load()
    px = img.load()
    for yy in range(h):
        for xx in range(w):
            if mp[xx, yy] and not (((xx >> 1) + (yy >> 1)) & 1):
                px[x0 + xx, y0 + yy] = MAGENTA


# ---------------------------------------------------------------------------
# Splash images: the main menu backdrop and the level loading screen.
#
# Both are the 1983 cassette cover, reduced to sixteen of the CoCo 3's
# sixty-four colours and dithered.  Splash images are not tied to the table's
# palette -- scripts/build-images.py stores a palette per image -- so each one
# gets the sixteen that suit it.
# ---------------------------------------------------------------------------

IMAGE_DIR = os.path.join(ROOT, "game", "images")
BOX_ART = os.path.join(ROOT, "art", "boxart.jpg")

# Two bits per channel is the whole of the CoCo 3's gamut.
COCO_LEVELS = (0, 85, 170, 255)
COCO_GAMUT = [(r, g, b) for r in COCO_LEVELS for g in COCO_LEVELS for b in COCO_LEVELS]

# A pixel in the 320x200 mode is 1.2 times taller than it is wide on a 4:3
# screen, so a picture only comes out undistorted if the source is cropped to
# the aspect it will be *displayed* at rather than to the pixel one.
PIXEL_TALL = 1.2

# The loader picks the colours for its menu text, its loading message and its
# progress bar out of the image's own palette (see images.json below), so black
# and two bright inks are reserved whether or not the picture wants them.
IMAGE_RESERVED = [(0, 0, 0), (255, 255, 0), (255, 170, 0)]


def coco_snap(rgb):
    """The nearest of the CoCo's 64 colours."""
    return tuple(COCO_LEVELS[min(3, (v + 42) // 85)] for v in rgb)


def palette_image(colours):
    """A 'P' image carrying just these colours, to quantise against."""
    p = Image.new("P", (1, 1))
    flat = [c for rgb in colours for c in rgb]
    p.putpalette(flat + [0] * (768 - len(flat)))
    return p


def coco_reduce(rgb, n=16):
    """Reduce a photograph to n of the CoCo's colours, dithered.

    The palette is settled *before* the dither: maximum-coverage quantisation
    picks a spread of colours, each is snapped into the hardware's gamut, and
    only then is the picture Floyd-Steinberg dithered onto what survives.
    Quantising to arbitrary RGB and snapping afterwards would move every colour
    after its error had already been diffused, which comes out as banding.
    """
    chosen = list(IMAGE_RESERVED)
    seed = rgb.quantize(colors=n, method=Image.Quantize.MAXCOVERAGE).getpalette()
    for i in range(n):
        c = coco_snap(tuple(seed[i * 3 : i * 3 + 3]))
        if c not in chosen and len(chosen) < n:
            chosen.append(c)

    # Snapping collapses near neighbours onto each other, so top the palette
    # back up with whatever the picture uses most and has not got yet.
    hist = rgb.quantize(
        palette=palette_image(COCO_GAMUT), dither=Image.Dither.NONE
    ).histogram()
    for i in sorted(range(len(COCO_GAMUT)), key=lambda j: -hist[j]):
        if len(chosen) >= n:
            break
        if COCO_GAMUT[i] not in chosen:
            chosen.append(COCO_GAMUT[i])

    return rgb.quantize(
        palette=palette_image(chosen), dither=Image.Dither.FLOYDSTEINBERG
    )


def fade_below(img, start, end, floor, black=40):
    """Fade the picture down from row start to row end, and flatten what is
    left very dark to true black.

    Dithering near-black into near-black is just speckle, and speckle is what
    makes text drawn on top of it unreadable.
    """
    px = img.load()
    w, h = img.size
    for y in range(start, h):
        f = floor if y >= end else 1.0 + (floor - 1.0) * (y - start) / (end - start)
        for x in range(w):
            r, g, b = (int(v * f) for v in px[x, y])
            px[x, y] = (0, 0, 0) if max(r, g, b) < black else (r, g, b)


def box_art(w, h, top_trim=0, fade=None, black_box=None):
    """The cover, cropped to what will look undistorted at w x h, and reduced.

    top_trim is how much of the source to lose off the top; the rest of the
    crop comes off the bottom, which on this cover is the least interesting
    part of the picture.

    black_box is (x, y, w, h) painted flat black before the reduction, which
    is how the menu gets a plain backdrop to draw its options over.  Doing it
    here rather than at run time costs nothing: black is a reserved palette
    entry, so it survives the dither exactly, and the loader has one less thing
    to draw.
    """
    src = Image.open(BOX_ART).convert("RGB")
    keep = int(round(src.width * PIXEL_TALL * h / w))
    img = src.crop(
        (0, top_trim, src.width, min(src.height, top_trim + keep))
    ).resize((w, h), Image.LANCZOS)
    if fade:
        fade_below(img, *fade)
    if black_box:
        bx, by, bw, bh = black_box
        ImageDraw.Draw(img).rectangle((bx, by, bx + bw - 1, by + bh - 1),
                                      fill=(0, 0, 0))
    return coco_reduce(img)


def write_images():
    os.makedirs(IMAGE_DIR, exist_ok=True)

    # The menu draws four option lines at rows 107, 123, 139 and 155, each nine
    # rows tall: the labels from x 60 and the values from x 144 (engine/menu.asm
    # draws them at 30 and 32+10*4 bytes), with the longest value reaching about
    # x 248.  Then a prompt down at row 184.  The options get a flat black box
    # to sit on; the prompt is on its own, which is why the lower half of the
    # picture is still faded down behind it.
    #
    # The box is x 58..255 by rows 105..170, which clears the text on every
    # side.  The picture is cropped harder at the top to suit.
    box_art(SCREEN_W, SCREEN_H, top_trim=12, fade=(92, 124, 0.45),
            black_box=(58, 105, 198, 66)).save(
        os.path.join(IMAGE_DIR, "00-mainmenu.png")
    )

    # The loading screen centres its picture and puts the message underneath
    # it, so this one is left alone.  The loader reserves 64 rows for that
    # message, which leaves 136 for the image.
    box_art(160, 116).save(os.path.join(IMAGE_DIR, "01-level1.png"))

    import json

    # One entry per image, in file order: the menu backdrop, then one loading
    # screen per level.  The colours are looked up in each image's palette,
    # which is why coco_reduce reserves them.
    inks = {
        "BackgroundColor": "000000",
        "ForegroundColor": "ffaa00",
        "ProgressColor": "ffff00",
    }
    with open(os.path.join(IMAGE_DIR, "images.json"), "w") as f:
        json.dump({"images": [dict(inks), dict(inks)]}, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Sound effects.  The build resamples these down to the engine's 2 kHz output,
# so nothing here goes above about 800 Hz or it would alias.
# ---------------------------------------------------------------------------

SOUND_DIR = os.path.join(ROOT, "game", "sounds")
SND_RATE = 8000


def write_wav(name, samples):
    import wave

    path = os.path.join(SOUND_DIR, name)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(SND_RATE)
        w.writeframes(bytes(samples))


# ffmpeg's resampler needs a couple of hundred milliseconds of material to
# work with; anything shorter comes out of the build as an empty file.  Short
# effects are therefore given a fast decay rather than a short duration.
SND_MIN_MS = 220

# A pentatonic scale: C, D, E, G, A, and the octave.
SND_SCALE = (262, 294, 330, 392, 440, 523)


def envelope(t, decay):
    if decay <= 0:
        return 1.0
    return math.exp(-t * decay)


def tone(freq0, freq1, ms, shape="square", decay=3.0, sweep_ms=None):
    """A swept tone.  decay is in e-folds over the whole sample."""
    n = SND_RATE * ms // 1000
    sweep = n if sweep_ms is None else SND_RATE * sweep_ms // 1000
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        st = min(1.0, i / sweep)
        f = freq0 + (freq1 - freq0) * st
        phase += f / SND_RATE
        v = phase - math.floor(phase)
        if shape == "square":
            s = 1.0 if v < 0.5 else -1.0
        elif shape == "saw":
            s = 2.0 * v - 1.0
        else:
            s = math.sin(2 * math.pi * v)
        out.append(max(0, min(255, int(128 + s * envelope(t, decay) * 100))))
    return out


def noise(ms, level=90, decay=14.0):
    n = SND_RATE * ms // 1000
    out = []
    seed = 0x1234
    for i in range(n):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        s = ((seed >> 16) & 255) - 128
        v = (s / 128.0) * level * envelope(i / n, decay)
        out.append(max(0, min(255, int(128 + v))))
    return out


def write_sounds():
    os.makedirs(SOUND_DIR, exist_ok=True)
    # Bumper: a fat low thump.
    write_wav("01-bumper.wav", tone(620, 240, SND_MIN_MS, "square", decay=6.0))
    # Target: a bright ping.
    write_wav("02-target.wav", tone(880, 700, SND_MIN_MS, "sine", decay=7.0))
    # Flipper: a mechanical clack.
    write_wav("03-flipper.wav", noise(SND_MIN_MS, 80, decay=22.0))
    # Drain: the ball is gone.
    write_wav("04-drain.wav", tone(520, 80, 420, "saw", decay=1.2))
    # Launch: the spring lets go.
    write_wav("05-launch.wav", tone(160, 780, 300, "square", decay=1.5, sweep_ms=160))
    # The lane: one low blip of the ticking the ball makes on its way up.  It
    # has to carry the resampler's 220ms of material or it comes out empty, so
    # the shortness is all in the decay.
    write_wav("06-lane.wav", tone(150, 140, SND_MIN_MS, "square", decay=26.0))

    # Notes for the scoring targets, so a good run sounds like a tune rather
    # than a series of thumps.  Plain square waves, and a pentatonic scale
    # because any two of its notes sit together -- the ball chooses the order,
    # and it has no ear.  All well under the 800Hz the 2kHz DAC can carry.
    for i, freq in enumerate(SND_SCALE):
        write_wav(f"{7 + i:02d}-note{i + 1}.wav",
                  tone(freq, freq, SND_MIN_MS, "square", decay=9.0))


def write_descriptors():
    import json

    LAUNCHER_REST_Y = 180  # near the bottom of the lane; matches object_info.h
    BALL_INDICATORS = 4

    with open(os.path.join(TILE_DIR, "01-table.json"), "w") as f:
        json.dump(
            {
                "Image": "01-table.png",
                "TileSetStart": [0, ART_Y],
                "TileSetSize": [playfield.WORLD_W, playfield.WORLD_H],
            },
            f,
            indent=2,
        )
        f.write("\n")

    # The level's object list is generated too, so adding a target to the spec
    # gives it an overlay without anyone having to remember to.
    objects = []

    def obj(comment, group, active, x, y, init):
        objects.append(
            {
                "_comment": comment,
                "GroupID": group,
                "ObjectID": 0,
                "Active": active,
                "globalX": x,
                "globalY": y,
                "InitData": init,
            }
        )

    # The ball must come first: the overlays find it with a search that stops
    # at the first object of its group.
    lane_cx = (playfield.LANE_X0 + playfield.LANE_X1) // 2 + playfield.ORIGIN_X
    obj("launcher", 1, 3, lane_cx, LAUNCHER_REST_Y, [1])
    obj("left flipper", 2, 3, *playfield.world(*playfield.FLIPPER_PIVOTS[0]), [0])
    obj("right flipper", 2, 3, *playfield.world(*playfield.FLIPPER_PIVOTS[1]), [1])

    for board in (0, 1):
        for column in range(7):
            obj(f"{'high ' if board else ''}score digit {column}", 3, 3, 0, 0,
                [board, column])
    # One indicator per ball still to play.  Four fit beside the boards; a
    # game only ever starts with three, and extra balls beyond the fourth are
    # counted but not drawn.
    for i in range(BALL_INDICATORS):
        obj(f"ball indicator {i}", 3, 3, 0, 0, [2, i])
    obj("multiplier tens", 3, 1, 0, 0, [3, 0])
    obj("multiplier units", 3, 1, 0, 0, [4, 0])

    obj("fly", 8, 3, 0, 0, [0])

    # One overlay per plunger line; it places itself from tblPlungerBox.
    for i in range(len(playfield.plunger_boxes())):
        obj(f"plunger {i}", 4, 3, 0, 0, [2, i])

    # One overlay per foot; it places itself from tblFootBox.
    _, feet = playfield.source()
    for i in range(len(playfield.foot_boxes(feet))):
        obj(f"foot {i}", 4, 3, 0, 0, [0, i])
    for i in range(len(playfield.diamond_boxes())):
        obj(f"bumper middle {i}", 4, 3, 0, 0, [1, i])

    for i, what in enumerate(("tongue", "game over", "multiplier X", "lane gate")):
        obj(what, 5, 3 if what == "lane gate" else 1, 0, 0, [i])

    # Lava, once the volcano goes off: drops running down both slopes, spread
    # around the run so they do not fall in step.  They start inactive and the
    # object switches itself on.
    # One object for the whole flow: it never moves, and only its frame
    # changes.
    obj("lava", 6, 3, 0, 0, [0])

    # The two tongues.  They place themselves from the roots in table_data.h,
    # and they update before the ball does, which is what lets the ball trust
    # the extension each one publishes.
    for i, name in enumerate(("left tongue", "right tongue")):
        obj(name, 7, 3, 0, 0, [i])

    # The ball goes last, so it is drawn over everything else.  It matters most
    # around the feet: those save no background, so when one changes colour it
    # repaints itself, and anything drawn before it would be painted over.
    obj("ball", 1, 3, lane_cx, LAUNCHER_REST_Y - 2, [0])

    level = {
        "Level": {
            "Name": "Lost World Pinball",
            "Description": "Three balls. Hit anything red.",
            # Every group an object in the list belongs to has to appear
            # here, or the loader searches the sprite group table, falls
            # off the end of it and traps.
            "ObjectGroups": sorted({o["GroupID"] for o in objects}),
            "MaxObjectTableSize": len(objects) + 2,
            "Tileset": 1,
            "TilemapImage": "../tiles/01-table.png",
            "TilemapStart": [0, ART_Y],
            "TilemapSize": [playfield.WORLD_W, playfield.WORLD_H],
            "BkgrndStartX": playfield.ORIGIN_X,
            "BkgrndStartY": playfield.ORIGIN_Y,
        },
        "Objects": objects,
    }
    with open(os.path.join(LEVEL_DIR, "01-table.json"), "w") as f:
        json.dump(level, f, indent=2)
        f.write("\n")
    return len(objects)


def check_panel_columns():
    """Every panel sprite is compiled byte-aligned only, so each of them has to
    land on an even pixel column or it will be drawn half a byte out."""
    cols = [BALLS_DIGIT_X, VALLY_MOUTH[0]]
    cols += [MULT_DIGIT_X + n * SCORE_DIGIT_PITCH for n in range(3)]
    cols += [
        SCORE_DIGIT_X0
        + c * SCORE_DIGIT_PITCH
        + (SCORE_GROUP_GAP if c >= 1 else 0)
        + (SCORE_GROUP_GAP if c >= 4 else 0)
        for c in range(SCORE_DIGITS)
    ]
    odd = [c for c in cols if c & 1]
    assert not odd, f"panel sprite columns must be even: {odd}"


def main():
    preview = "--preview" in sys.argv
    for d in (TILE_DIR, LEVEL_DIR, OBJ_DIR):
        os.makedirs(d, exist_ok=True)

    check_panel_columns()

    tiles = write_tileset(preview=preview)
    grid, gx0, gy0, gw, gh = build_world_grid()
    write_collision_header(grid, gx0, gy0, gw, gh)
    nobjects = write_descriptors()
    nsprites = write_sprites()
    write_images()
    write_sounds()

    solid_cells = sum(1 for row in grid for c in row if c)
    print(f"sprites: {nsprites}, level objects: {nobjects}")
    print(f"table artwork: {tiles} unique tiles ({tiles * 256} bytes of tileset)")
    print(f"collision grid: {gw}x{gh} = {gw * gh} bytes, {solid_cells} solid")
    if tiles > 254:
        print("****Error: too many unique tiles (max 254)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
