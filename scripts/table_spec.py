"""Geometry and palette for the Lost World Pinball table.

This module is the single source of truth for the table.  Both the background
artwork (scripts/gen-assets.py) and the runtime collision data are derived from
the shapes defined here, so the picture the player sees and the surface the ball
bounces off can never drift apart.

Coordinates are screen pixels on the CoCo 3's 320x200 display.  The playfield
occupies the left PLAYFIELD_W columns; the score/scene panel takes the rest.
"""

# ---------------------------------------------------------------------------
# Screen geometry
# ---------------------------------------------------------------------------

SCREEN_W = 320
SCREEN_H = 200

# The tilemap must be a whole number of 16x16 tiles, so the canvas is 8 rows
# taller than the visible screen.  Rows 200..207 are never displayed.
CANVAS_H = 208

PLAYFIELD_W = 192
PANEL_X = PLAYFIELD_W
PANEL_W = SCREEN_W - PANEL_X

# Vertical bands of the playfield
WALL = 6  # thickness of the outer magenta wall

# Launch lane, on the right-hand edge of the playfield
LANE_X0 = 174  # first playable column of the lane
LANE_X1 = 185  # last playable column of the lane
LANE_TOP = 40  # lane divider ends here; above this the ball rolls free
DIVIDER_X0 = 168
DIVIDER_X1 = 173

# Ball
BALL_R = 3  # radius in pixels (6x6 sprite)

# ---------------------------------------------------------------------------
# Palette.  Channel values are 0..3 (the CoCo 3's native 2 bits per channel),
# expanded to 8-bit as 0/85/170/255 so the build pipeline finds exact matches.
# Index 0 must be the background colour.
# ---------------------------------------------------------------------------

PALETTE_444 = [
    (0, 0, 0),  # 0  black       background / void
    (3, 3, 3),  # 1  white       playfield surface
    (2, 2, 2),  # 2  grey        surface shading
    (1, 1, 1),  # 3  dark grey   outlines and shadow
    (3, 1, 3),  # 4  magenta     table walls
    (2, 0, 2),  # 5  dark magenta wall shading
    (3, 2, 0),  # 6  orange      live scoring targets ("red" in the manual)
    (3, 0, 0),  # 7  red         hot / flashing
    (0, 2, 2),  # 8  teal        dinosaurs, plunger bodies
    (0, 1, 1),  # 9  dark teal   dinosaur shading
    (0, 2, 0),  # 10 green       plunger already hit this ball
    (3, 3, 0),  # 11 yellow      ball, flashing highlights
    (2, 1, 0),  # 12 brown       rock and lava
    (0, 0, 2),  # 13 blue        panel sky
    (3, 2, 2),  # 14 pink        light accents
    (0, 0, 1),  # 15 deep blue   night shadow
]

(
    BLACK,
    WHITE,
    GREY,
    DGREY,
    MAGENTA,
    DMAGENTA,
    ORANGE,
    RED,
    TEAL,
    DTEAL,
    GREEN,
    YELLOW,
    BROWN,
    BLUE,
    PINK,
    DBLUE,
) = range(16)


def palette_bytes():
    """768-byte PIL palette for the 16 colours above."""
    pal = []
    for r, g, b in PALETTE_444:
        pal += [r * 85, g * 85, b * 85]
    pal += [0] * (768 - len(pal))
    return pal


# ---------------------------------------------------------------------------
# Playfield outline
#
# The interior of the table is a "barrel": narrow at the top where the ball
# enters, bulging through the middle, then funnelling down to the drain.  It is
# described by the left and right boundary at a series of heights and linearly
# interpolated between them.
# ---------------------------------------------------------------------------

# The left edge of the playable interior, as (y, x) knots.
LEFT_PROFILE = [
    (8, 48),
    (12, 34),
    (18, 24),
    (26, 16),
    (38, 10),
    (60, 6),
    (110, 6),
    (132, 8),
    (148, 14),
    (164, 22),
    (176, 34),
    (188, 52),
    (200, 72),
]

# The right edge.  Above the lane divider the interior runs the full width of
# the table, so the ball shot up the lane curls over the top and comes back
# down into play; below it, the divider walls the lane off.
# The top of the lane has to lean in hard enough to turn a rising ball back
# into the table; a gentler curve just lets it come straight down again.
RIGHT_PROFILE_TOP = [
    (8, 150),
    (12, 163),
    (18, 174),
    (24, 181),
    (30, 185),
    (LANE_TOP, 185),
]
RIGHT_PROFILE_MAIN = [
    (LANE_TOP, 167),
    (110, 167),
    (132, 165),
    (148, 159),
    (164, 151),
    (176, 139),
    (188, 121),
    (200, 101),
]

# Drain.  The chute is cut clean through the bottom of the table so a ball that
# gets past the flippers falls out of the world rather than settling on the
# funnel; DRAIN_Y is where it counts as lost.
DRAIN_X0 = 72
DRAIN_X1 = 101
DRAIN_MOUTH_Y = 192
DRAIN_Y = 199

# ---------------------------------------------------------------------------
# Flippers
# ---------------------------------------------------------------------------

FLIPPER_LEN = 32
FLIPPER_REST_DEG = 28  # below horizontal, at rest
FLIPPER_UP_DEG = -30  # above horizontal, fully raised
FLIPPER_FRAMES = 6  # animation frames between rest and up
FLIPPER_HALF_THICK = 3

LEFT_FLIPPER_PIVOT = (54, 174)
RIGHT_FLIPPER_PIVOT = (120, 174)

# ---------------------------------------------------------------------------
# Scoring elements
#
# Every entry carries the element kind, which fixes both how it is drawn and
# what it is worth.  Positions are the bounding box (x0, y0, x1, y1) inclusive.
# ---------------------------------------------------------------------------

# Plungers: hitting one turns it green until every plunger has been hit, at
# which point they all reset and the score multiplier steps up.  20 points.
PODS = [  # the two big "pinosaurus" boxes at the top corners
    (30, 26, 51, 45),
    (122, 26, 143, 45),
]
CAPSULES = [  # the three upright plungers across the top
    (64, 24, 73, 45),
    (82, 24, 91, 45),
    (100, 24, 109, 45),
]

# Red marks: 30 points.  The four beneath the top pods are the ones that feed
# Vally's tongue; twelve hits on those makes the volcano erupt.
TOP_MARKS = [
    (32, 48, 39, 52),
    (42, 48, 49, 52),
    (124, 48, 131, 52),
    (134, 48, 141, 52),
]
CREST_MARKS = [
    (66, 140, 73, 144),
    (82, 140, 89, 144),
    (98, 140, 105, 144),
]
HEAD_MARKS = [
    (156, 126, 163, 130),
    (156, 134, 163, 138),
]

# Bumpers: 10 points, and they kick the ball away.  (cx, cy, r)
BUMPERS = [
    (86, 78, 12),
    (60, 104, 12),
    (114, 104, 12),
]

# Red power strips on the side walls: 10 points.  (x0, y0, x1, y1)
POWER_STRIPS = [
    (6, 72, 9, 104),
    (164, 72, 167, 104),
    (8, 118, 11, 138),
    (162, 118, 165, 138),
]

# Vally's crest: solid scenery in the middle of the table, no score.
CREST_APEX = (87, 114)
CREST_BASE_Y = 138
CREST_HALF_W = 24

# Vally's head, tucked against the right wall.  Scenery; the marks beside it
# are what scores.
HEAD_BOX = (142, 120, 156, 144)

# Slingshots: wedges set into the side walls above each flipper.  They are
# drawn as triangles so they merge into the wall instead of floating in the
# middle of the table, and they give the ball a kick on the way past.
SLINGSHOTS = [
    [(10, 144), (46, 174), (10, 174)],
    [(163, 144), (127, 174), (163, 174)],
]

# ---------------------------------------------------------------------------
# Collision grid
# ---------------------------------------------------------------------------

CELL = 4  # collision cells are CELL x CELL pixels
GRID_W = PLAYFIELD_W // CELL
GRID_H = CANVAS_H // CELL
NUM_DIRS = 32  # normals are quantised to this many directions

# Sprite overlays are drawn byte-aligned, which on the CoCo 3 means every
# overlay position must be an even pixel column.  The element boxes above are
# laid out to keep that true; this is asserted at generation time.

# Cell encoding: 0 means empty, otherwise (kind << 5) | direction.
K_EMPTY = 0
K_WALL = 1
K_STRIP = 2  # red power strip, 10
K_PLUNGER = 3  # pod or capsule, 20
K_MARK = 4  # red mark, 30
K_BUMPER = 5  # bumper, 10, plus a kick
K_SCENERY = 6  # crest and head: solid, no score
K_SLING = 7  # slingshot: solid, no score, bigger kick

KIND_NAMES = {
    K_WALL: "WALL",
    K_STRIP: "STRIP",
    K_PLUNGER: "PLUNGER",
    K_MARK: "MARK",
    K_BUMPER: "BUMPER",
    K_SCENERY: "SCENERY",
    K_SLING: "SLING",
}
