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

KIND_COLOURS = {
    "drain": 0,
    "wall": K_WALL,
    "floor": 0,
    "sling": K_SLING,
    "strip": K_STRIP,
    "scenery": K_SCENERY,
    "bumper": K_BUMPER,
    "plunger": K_PLUNGER,
    "mark": K_MARK,
}


def build_kind_map():
    """Pixel-resolution map of what occupies each point of the playfield."""
    img = Image.new("L", (PLAYFIELD_W, CANVAS_H), 0)
    draw_table(Painter(img, KIND_COLOURS), 0)
    return img


def build_grid(kind_img):
    """Reduce the kind map to one byte per CELL x CELL cell.

    Each solid cell stores its kind and the direction the surface faces, so the
    ball object needs a single table lookup to know both how to bounce and what
    to score.
    """
    px = kind_img.load()
    solid = [[False] * GRID_W for _ in range(GRID_H)]
    kind = [[0] * GRID_W for _ in range(GRID_H)]

    for gy in range(GRID_H):
        for gx in range(GRID_W):
            counts = {}
            for y in range(gy * CELL, gy * CELL + CELL):
                for x in range(gx * CELL, gx * CELL + CELL):
                    v = px[x, y]
                    if v:
                        counts[v] = counts.get(v, 0) + 1
            if counts:
                solid[gy][gx] = True
                # Scoring surfaces win ties: a mark set into a wall should
                # score when the ball reaches it.
                kind[gy][gx] = max(counts, key=lambda k: (counts[k], k))

    # Normal of each solid cell: the direction of the free space around it.
    R = 3
    grid = [[0] * GRID_W for _ in range(GRID_H)]
    for gy in range(GRID_H):
        for gx in range(GRID_W):
            if not solid[gy][gx]:
                continue
            sx = sy = 0.0
            for dy in range(-R, R + 1):
                for dx in range(-R, R + 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = gx + dx, gy + dy
                    free = True
                    if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
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
            grid[gy][gx] = (kind[gy][gx] << 5) | dir_idx
    return grid


# ---------------------------------------------------------------------------
# Emitters
# ---------------------------------------------------------------------------


def write_tileset(preview=False):
    img = Image.new("P", (SCREEN_W, PAL_ROWS + CANVAS_H), BLACK)
    img.putpalette(palette_bytes())

    d = ImageDraw.Draw(img)
    swatch = SCREEN_W // 16
    for i in range(16):
        d.rectangle((i * swatch, 0, (i + 1) * swatch - 1, PAL_ROWS - 1), fill=i)

    draw_table(Painter(img, ART_COLOURS), ART_Y)
    shade_table(img, ART_Y)
    draw_panel(img, ART_Y)

    path = os.path.join(TILE_DIR, "01-table.png")
    img.save(path)

    if preview:
        os.makedirs(BUILD_DIR, exist_ok=True)
        prev = img.crop((0, ART_Y, SCREEN_W, ART_Y + SCREEN_H)).convert("RGB")
        prev = prev.resize((SCREEN_W * 2, SCREEN_H * 2), Image.NEAREST)
        prev.save(os.path.join(BUILD_DIR, "table-preview.png"))

    return count_tiles(img)


def count_tiles(img):
    """How many unique 16x16 background tiles the artwork needs."""
    px = img.load()
    seen = set()
    for ty in range(ART_Y, ART_Y + CANVAS_H, 16):
        for tx in range(0, SCREEN_W, 16):
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


def write_collision_header(grid):
    dirs_x, dirs_y = [], []
    for i in range(NUM_DIRS):
        ang = i * 2 * math.pi / NUM_DIRS
        dirs_x.append(int(round(math.cos(ang) * 32)))
        dirs_y.append(int(round(math.sin(ang) * 32)))

    flat = [grid[gy][gx] for gy in range(GRID_H) for gx in range(GRID_W)]

    def boxes(name, items):
        vals = []
        for x0, y0, x1, y1 in items:
            vals += [x0, y0, x1, y1]
        return c_table(name, vals, per_line=16)

    # Flipper geometry, one entry per side per animation frame.  "dir" runs
    # from the pivot to the tip; "nrm" is the outward normal of the face the
    # ball is meant to be launched from.
    fdx, fdy, fnx, fny = [], [], [], []
    for mirror in (False, True):
        for f in range(FLIPPER_FRAMES):
            deg = FLIPPER_REST_DEG + (FLIPPER_UP_DEG - FLIPPER_REST_DEG) * f / (
                FLIPPER_FRAMES - 1
            )
            a = math.radians(deg)
            sgn = -1 if mirror else 1
            fdx.append(int(round(sgn * math.cos(a) * 32)))
            fdy.append(int(round(math.sin(a) * 32)))
            fnx.append(int(round(sgn * math.sin(a) * 32)))
            fny.append(int(round(-math.cos(a) * 32)))

    cell_shift = int(math.log2(CELL))

    body = f"""#ifndef _table_data_h
#define _table_data_h

/* Generated by scripts/gen-assets.py from scripts/table_spec.py -- do not edit.
 *
 * The playfield is diced into {GRID_W}x{GRID_H} cells of {CELL}x{CELL} pixels.  A zero cell is
 * open floor.  Any other cell packs the kind of surface in the top 3 bits and
 * the direction the surface faces in the low 5 bits, so one lookup tells the
 * ball both how to bounce and what to score.
 */

#define TBL_CELL        {CELL}
#define TBL_CELL_SHIFT  {cell_shift}
#define TBL_GRID_W      {GRID_W}
#define TBL_GRID_H      {GRID_H}
#define TBL_NUM_DIRS    {NUM_DIRS}

#define TBL_KIND(c)     ((c) >> 5)
#define TBL_DIR(c)      ((c) & 31)

#define K_EMPTY   {K_EMPTY}
#define K_WALL    {K_WALL}
#define K_STRIP   {K_STRIP}
#define K_PLUNGER {K_PLUNGER}
#define K_MARK    {K_MARK}
#define K_BUMPER  {K_BUMPER}
#define K_SCENERY {K_SCENERY}
#define K_SLING   {K_SLING}

#define PLAYFIELD_LEFT   0
#define PLAYFIELD_RIGHT  {PLAYFIELD_W - 1}
#define DRAIN_Y          {DRAIN_Y}
#define LANE_X0          {LANE_X0}
#define LANE_X1          {LANE_X1}
#define LANE_TOP         {LANE_TOP}
#define BALL_R           {BALL_R}

/* The right-hand panel.  These are the same constants that placed the artwork
 * underneath, so a read-out cannot end up off the board it belongs to. */
#define PANEL_X           {PANEL_X}
#define SCORE_DIGITS      {SCORE_DIGITS}
#define SCORE_DIGIT_X0    {SCORE_DIGIT_X0}
#define SCORE_DIGIT_PITCH {SCORE_DIGIT_PITCH}
#define SCORE_GROUP_GAP   {SCORE_GROUP_GAP}
#define HIGH_DIGIT_Y      {HIGH_DIGIT_Y}
#define SCORE_DIGIT_Y     {SCORE_DIGIT_Y}
#define BALLS_DIGIT_X     {BALLS_DIGIT_X}
#define BALLS_DIGIT_Y     {BALLS_DIGIT_Y}
#define MULT_DIGIT_X      {MULT_DIGIT_X}
#define MULT_DIGIT_Y      {MULT_DIGIT_Y}
#define PANEL_TONGUE_X    {VALLY_MOUTH[0]}
#define PANEL_TONGUE_Y    {VALLY_MOUTH[1]}

#define BUMPER_R         {BUMPERS[0][2]}
#define NUM_PLUNGERS     {len(PODS) + len(CAPSULES)}
#define NUM_MARKS        {len(TOP_MARKS) + len(CREST_MARKS) + len(HEAD_MARKS)}
#define NUM_TOP_MARKS    {len(TOP_MARKS)}
#define NUM_BUMPERS      {len(BUMPERS)}

/* Unit normals, scaled by 32. */
{c_table("tblDirX", dirs_x, typ="const signed char")}

{c_table("tblDirY", dirs_y, typ="const signed char")}

/* Bounding boxes as x0, y0, x1, y1.  The first NUM_TOP_MARKS marks are the
 * ones under the top pods -- the ones that feed Vally's tongue. */
{boxes("tblPlungerBox", PODS + CAPSULES)}

{boxes("tblMarkBox", TOP_MARKS + CREST_MARKS + HEAD_MARKS)}

{c_table("tblBumperX", [b[0] for b in BUMPERS])}

{c_table("tblBumperY", [b[1] for b in BUMPERS])}

/* Flippers.  Entries 0..{FLIPPER_FRAMES - 1} are the left flipper from rest to fully
 * raised; the next {FLIPPER_FRAMES} are the right. */
#define FLIPPER_FRAMES   {FLIPPER_FRAMES}
#define FLIPPER_LEN      {FLIPPER_LEN}
#define FLIPPER_HALF_THICK {FLIPPER_HALF_THICK}
#define FLIP_L_X         {LEFT_FLIPPER_PIVOT[0]}
#define FLIP_L_Y         {LEFT_FLIPPER_PIVOT[1]}
#define FLIP_R_X         {RIGHT_FLIPPER_PIVOT[0]}
#define FLIP_R_Y         {RIGHT_FLIPPER_PIVOT[1]}

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

    return [("Ball", cx, cy, True), ("Launcher", lx, ly, True)]


def flipper_points(pivot, deg, mirror):
    """Outline of a flipper rotated deg degrees below horizontal."""
    px, py = pivot
    a = math.radians(deg)
    sgn = -1 if mirror else 1
    ca, sa = math.cos(a), math.sin(a)

    def at(along, across):
        x = px + sgn * (along * ca) - across * sa * sgn * sgn
        y = py + along * sa + across * ca
        return (x, y)

    base = 4.0
    tip = 2.0
    return [
        at(0, -base),
        at(FLIPPER_LEN, -tip),
        at(FLIPPER_LEN, tip),
        at(0, base),
    ]


def draw_flipper_sheet(d, img):
    sprites = []
    cell_w = 40
    cell_h = 40
    for mirror in (False, True):
        for f in range(FLIPPER_FRAMES):
            col = f
            row = 1 if mirror else 0
            # Anchor (the pivot) sits where the flipper's hub is.
            ax = col * cell_w + (34 if mirror else 6)
            ay = row * cell_h + 20
            deg = FLIPPER_REST_DEG + (FLIPPER_UP_DEG - FLIPPER_REST_DEG) * f / (
                FLIPPER_FRAMES - 1
            )
            pts = flipper_points((ax, ay), deg, mirror)
            d.polygon(pts, fill=TEAL, outline=DTEAL)
            # Hub, drawn last so the anchor pixel is always opaque.
            d.ellipse((ax - 3, ay - 3, ax + 3, ay + 3), fill=ORANGE)
            d.point((ax, ay), fill=RED)
            name = ("Right" if mirror else "Left") + f"Flip{f}"
            # Both pivots sit on even pixel columns, so these never need the
            # single-pixel-position variant -- which would double the code.
            sprites.append((name, ax, ay, False))
    return sprites


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
    return sprites


def draw_lite_sheet(d, img):
    """Overlays that show an element's state without redrawing the tilemap."""
    sprites = []

    # A hit plunger turns green.  These are opaque and exactly cover the shape
    # drawn into the background.
    pod_w = PODS[0][2] - PODS[0][0] + 1
    pod_h = PODS[0][3] - PODS[0][1] + 1
    x0, y0 = 2, 2
    d.rounded_rectangle(
        (x0, y0, x0 + pod_w - 1, y0 + pod_h - 1), radius=6, fill=GREEN
    )
    d.rectangle((x0 + 4, y0 + 4, x0 + pod_w - 5, y0 + pod_h - 5), fill=DTEAL)
    sprites.append(("PodHit", x0, y0, False))

    cap_w = CAPSULES[0][2] - CAPSULES[0][0] + 1
    cap_h = CAPSULES[0][3] - CAPSULES[0][1] + 1
    x0, y0 = 40, 2
    d.ellipse((x0, y0, x0 + cap_w - 1, y0 + cap_h - 1), fill=GREEN)
    d.ellipse((x0 + 2, y0 + 3, x0 + cap_w - 3, y0 + cap_h - 4), fill=DTEAL)
    sprites.append(("CapHit", x0, y0, False))

    # A struck bumper flashes for a few frames.
    r = BUMPERS[0][2]
    cx, cy = 70 + r, 2 + r
    d.polygon(
        [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
        fill=YELLOW,
    )
    d.polygon(
        [(cx, cy - r + 4), (cx + r - 4, cy), (cx, cy + r - 4), (cx - r + 4, cy)],
        fill=WHITE,
    )
    sprites.append(("BumperHit", cx - r, cy - r, False))

    # A struck mark flashes yellow.
    mw = TOP_MARKS[0][2] - TOP_MARKS[0][0] + 1
    mh = TOP_MARKS[0][3] - TOP_MARKS[0][1] + 1
    x0, y0 = 100, 2
    d.rounded_rectangle((x0, y0, x0 + mw - 1, y0 + mh - 1), radius=2, fill=YELLOW)
    sprites.append(("MarkHit", x0, y0, False))

    return sprites


# Panel read-outs.  The multiplier and ball count are drawn with the ordinary
# score digits, because the sprite compiler unrolls every sprite into straight
# line code and a big block of text costs kilobytes of it.  Only the two things
# digits cannot express -- Vally's tongue and the end-of-game plate -- are
# sprites here.
TONGUE_STAGES = 6
TONGUE_STEP = 4  # pixels of tongue per stage
GAMEOVER_W, GAMEOVER_H = 66, 18


def draw_panel_sheet(d, img):
    sprites = []

    # Vally's tongue, reaching further with every pair of top marks hit.
    for stage in range(1, TONGUE_STAGES + 1):
        x0 = 2 + (stage - 1) * 34
        y0 = 2 + TONGUE_STAGES * TONGUE_STEP
        length = stage * TONGUE_STEP
        d.line([(x0, y0), (x0 + length, y0 - length)], fill=ORANGE)
        if stage == TONGUE_STAGES:
            # The prehistoric fly, finally within reach.
            d.rectangle(
                (x0 + length, y0 - length - 2, x0 + length + 2, y0 - length),
                fill=DGREY,
            )
        sprites.append((f"Tongue{stage}", x0, y0, False))

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

    return sprites


def write_sprites():
    os.makedirs(SPRITE_DIR, exist_ok=True)
    total = 0
    total += write_sprite_group(1, "ball", (48, 20), draw_ball_sheet)
    total += write_sprite_group(2, "flipper", (240, 80), draw_flipper_sheet, chunk=8)
    total += write_sprite_group(3, "digit", (144, 16), draw_digit_sheet)
    total += write_sprite_group(4, "lite", (160, 40), draw_lite_sheet, chunk=8)
    total += write_sprite_group(5, "panel", (216, 60), draw_panel_sheet, chunk=8)
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


def box_art(w, h, top_trim=0, fade=None):
    """The cover, cropped to what will look undistorted at w x h, and reduced.

    top_trim is how much of the source to lose off the top; the rest of the
    crop comes off the bottom, which on this cover is the least interesting
    part of the picture.
    """
    src = Image.open(BOX_ART).convert("RGB")
    keep = int(round(src.width * PIXEL_TALL * h / w))
    img = src.crop(
        (0, top_trim, src.width, min(src.height, top_trim + keep))
    ).resize((w, h), Image.LANCZOS)
    if fade:
        fade_below(img, *fade)
    return coco_reduce(img)


def write_images():
    os.makedirs(IMAGE_DIR, exist_ok=True)

    # The menu draws its four option lines and its prompt over rows 99 to 192
    # of the backdrop (engine/menu.asm), so the lower half is faded down far
    # enough for that text to read over it.
    box_art(SCREEN_W, SCREEN_H, top_trim=6, fade=(92, 124, 0.45)).save(
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


def write_descriptors():
    import json

    with open(os.path.join(TILE_DIR, "01-table.json"), "w") as f:
        json.dump(
            {
                "Image": "01-table.png",
                "TileSetStart": [0, ART_Y],
                "TileSetSize": [SCREEN_W, CANVAS_H],
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
    obj("ball", 1, 3, LANE_X0 + 6, 190, [0])
    obj("launcher", 1, 3, LANE_X0 + 6, 192, [1])
    obj("left flipper", 2, 3, *LEFT_FLIPPER_PIVOT, [0])
    obj("right flipper", 2, 3, *RIGHT_FLIPPER_PIVOT, [1])

    for board in (0, 1):
        for column in range(7):
            obj(f"{'high ' if board else ''}score digit {column}", 3, 3, 0, 0,
                [board, column])
    obj("ball count", 3, 3, 0, 0, [2, 0])
    obj("multiplier tens", 3, 1, 0, 0, [3, 0])
    obj("multiplier units", 3, 1, 0, 0, [4, 0])

    for i in range(len(PODS) + len(CAPSULES)):
        obj(f"plunger lamp {i}", 4, 1, 0, 0, [0, i])
    for i in range(len(BUMPERS)):
        obj(f"bumper lamp {i}", 4, 1, 0, 0, [1, i])
    for i in range(len(TOP_MARKS) + len(CREST_MARKS) + len(HEAD_MARKS)):
        obj(f"mark lamp {i}", 4, 1, 0, 0, [2, i])

    for i, what in enumerate(("tongue", "game over", "multiplier X")):
        obj(what, 5, 1, 0, 0, [i])

    level = {
        "Level": {
            "Name": "Lost World Pinball",
            "Description": "Three balls. Hit anything red.",
            "ObjectGroups": [1, 2, 3, 4, 5],
            "MaxObjectTableSize": len(objects) + 2,
            "Tileset": 1,
            "TilemapImage": "../tiles/01-table.png",
            "TilemapStart": [0, ART_Y],
            "TilemapSize": [SCREEN_W, CANVAS_H],
            "BkgrndStartX": 0,
            "BkgrndStartY": 0,
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
    grid = build_grid(build_kind_map())
    write_collision_header(grid)
    nobjects = write_descriptors()
    nsprites = write_sprites()
    write_images()
    write_sounds()

    solid_cells = sum(1 for row in grid for c in row if c)
    print(f"sprites: {nsprites}, level objects: {nobjects}")
    print(f"table artwork: {tiles} unique tiles ({tiles * 256} bytes of tileset)")
    print(f"collision grid: {GRID_W}x{GRID_H} = {GRID_W * GRID_H} bytes, {solid_cells} solid")
    if tiles > 254:
        print("****Error: too many unique tiles (max 254)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
