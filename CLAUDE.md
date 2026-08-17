# Lost World Pinball — Development Guide

## What this is

A CoCo 3 remake of Tandy's 1983 MC-10 game *Lost World Pinball*, built on a
copy of the [DynoSprite](https://github.com/richard42/dynosprite) engine (taken
from the `space-bandits` fork of it, which is the sibling project next door).

The original manual is the specification for the rules; the archived screenshot
of the real table is the specification for the layout. Both are summarised in
`README.md`.

## Hardware budget

- **CPU:** 6809 at 1.79 MHz (6309 build is ~29% faster)
- **Screen:** 320x200, 16 colours from 64, double buffered
- **Frame rate:** the game runs at a steady 30 Hz (two video fields per tick).
  Physics constants are tuned for that rate, so a change to the object count
  that drops it to 20 Hz will visibly slow the ball down.
- **Sound:** CPU-driven 6-bit DAC at 2 kHz

## Build

```sh
./coco-dev make all [RELEASE=1] [CPU=6309]
scripts/gen-assets.py --preview      # regenerate every asset
scripts/playtest.sh 240              # headless MAME run with screenshots
```

`./coco-dev` runs a command inside the `jamieleecho/coco-dev` image with the
project mounted at `/work`. It adds a TTY only when stdin really is one, so it
works from a script.

## The table is generated, not drawn

`scripts/table_spec.py` is the single source of truth: palette, playfield
outline, every target's bounding box, the flipper pivots, the drain, and the
layout of the right-hand panel. From it, `scripts/gen-assets.py` produces

- `game/tiles/01-table.png` — the tileset image, which *is* the artwork; the
  build extracts unique 16x16 tiles from it and derives the tilemap
- `game/objects/table_data.h` — the collision grid and lookup tables, plus the
  panel positions (`SCORE_DIGIT_Y`, `PANEL_TONGUE_X`, …). The read-outs are
  sprites drawn over artwork drawn from the same constants, so placing them
  from anywhere else is how a digit ends up sitting off its board
- `game/levels/01-table.json` — the level descriptor and its object list
- `game/sprites/*` — every sprite sheet and descriptor
- `game/images/*`, `game/sounds/*` — splash screens and effects

Never hand-edit anything under `game/` except the `.c`/`.h` files. Change the
spec and regenerate, so the picture and the physics cannot drift apart.

### The splash screens

The menu backdrop and the level loading screen are both `art/boxart.jpg`, the
1983 cassette cover, reduced by `coco_reduce()` to sixteen of the CoCo 3's
sixty-four colours and Floyd-Steinberg dithered. Three things about that are
worth keeping in mind:

- **The palette is chosen before the dither.** Maximum-coverage quantisation
  picks a spread of colours, each is snapped into the hardware's gamut, and
  only then is the picture dithered onto what survives. Quantising to arbitrary
  RGB and snapping afterwards moves every colour after its error has already
  been diffused, and the banding shows.
- **Splash images carry their own palette**, so they are not limited to the
  table's sixteen. `build-images.py` also picks the loader's text and progress
  bar colours out of that palette, which is why black and two bright inks are
  reserved before the picture gets a say.
- **A dithered photograph is expensive to load.** It barely compresses: the
  320x200 backdrop is about 16KB and comes off the emulated floppy at roughly a
  kilobyte a second, so the screen is black for some thirteen seconds before
  the menu appears. Ordered dithering compresses about a third better and looks
  markedly worse; fading more of the picture to true black is the cheaper
  lever, since flat black costs almost nothing.

### The collision grid

The playfield is diced into 4x4 pixel cells, one byte each: the top three bits
are the kind of surface (wall, power strip, plunger, mark, bumper, scenery,
slingshot) and the low five bits index a table of 32 unit normals. Normals are
computed at generation time from the *free space* around each solid cell, so
curved walls get sensible normals without anyone writing them down.

The ball therefore needs one array lookup to know both how to bounce and what
to score. Which *instance* was hit is resolved afterwards by scanning a short
table of bounding boxes, which only happens on a scoring hit.

**The kind field is full.** Three bits, and all eight values are spoken for
(empty plus seven surfaces). A new kind of surface means retiring one, or
stealing a bit from the direction field and halving the resolution of every
normal from 32 directions to 16. That is why the launch lane's one-way gate is
a coordinate test in `01-ball.c` rather than a cell kind: it was not worth a
bit.

The tileset is likewise on a budget. The artwork currently needs 161 unique
16x16 tiles; tilemap entries are bytes, so the hard ceiling is 255. Detail
costs tiles, and large flat areas cost none.

## Fixed point, and why the arithmetic looks odd

Velocities are 8.8 fixed point. Normals are scaled by 32. CMOC's `int` is
16-bit and there is no 32-bit intermediate, so every product has to be shifted
into range *before* it is taken:

```c
static int dotNormal(int vx, int vy, signed char nx, signed char ny) {
    return (((vx >> 2) * nx) >> 3) + (((vy >> 2) * ny) >> 3);
}
```

Positions are **not** 8.8: 208 rows x 256 overflows a signed 16-bit int. Whole
pixels live in the object's `globalX`/`globalY` (which the engine needs anyway)
and only the fraction is kept in object state — see `addPos()` in
`game/objects/01-ball.c`.

## Engine facts worth knowing

- **Object state size must not be understated.** `DynospriteObject_DataSize` in
  each object's header allocates the state block; the engine packs them back to
  back, so one byte of overrun corrupts the *next* object's state. The first
  byte of an object's state is its sprite index, which makes the symptom look
  bizarre (an object silently drawing itself as something else).
- **Objects initialise before the level does** (`engine/loader.asm` calls
  `Obj_Init_CurrentObjectTable` well before the level's `Init`), so game setup
  belongs in the ball's `Init`, and the level's `Init` must not undo it.
- **`UserGlobals`'s first byte is cleared by the menu** each time a level is
  launched, which is a free "new game" signal. Anything that must outlive that
  (the high score) is guarded by a magic number instead.
- **`GameGlobals` must fit in 32 bytes**, because that is all `UserGlobals` is
  (`engine/globals.asm`). It is currently about 20. Nothing checks this, and
  overflowing it would walk into the music engine's state.
- **The keyboard matrix is rescanned every frame** into `Input_KeyMatrix[8]`,
  which is what `keyDown()` reads. The joystick emulation cannot report two
  keys at once, and a pinball game needs both flippers.
- **One object type per C file.** Multiple behaviours come from instances with
  different `InitData` in the level descriptor.
- The COT is searched from the front, so the ball is listed first in the level
  descriptor and the lamp objects can find it in O(1).

## The engine is no longer pristine

`engine/` came across from space-bandits untouched, and everything else here
still is, but `engine/menu.asm` now differs: the four option rows moved from
99/115/131/147 down to 107/123/139/155, and the Sound and Music values moved
right to line up with the other two.  The menu is drawn entirely by the engine
and offers no hook, so there was nowhere else to put those changes.  Each row
appears four times -- label, value, erase and redraw -- so all sixteen have to
move together.

## When something goes wrong

Failures here surface a long way from their cause. These are the ones that have
actually happened, and what they looked like.

**Debug builds trap; release builds do not.** Without `RELEASE=1` the engine is
full of `swi` instructions on failed assertions, and one paints a register dump
across the top of the screen:

```
SWI  Error (PC=328B DP=20)
A=FF B=2F X=8300 Y=0000 U=4400 S=3FF8
```

Look the PC up in `build/list/dynosprite-pass2.lst`, which carries the source
file and line beside every address, and the assertion names itself. Always
reach for a debug build first: with `RELEASE=1` the same fault is a hang or
quiet corruption instead. That listing is the single most useful debugging
tool in the project.

**The level loading screen stops part-way and nothing else happens.** The level
is carrying more data than the loader can place; there is no message. It has
been seen with 72KB of compiled sprite code, and went away at 43KB. If a build
that loaded yesterday hangs today, look at what just grew:

```sh
ls -la build/obj/sprite*.raw    # compiled sprite code, the usual culprit
```

**A sound effect shorter than about 200ms silently becomes nothing.** ffmpeg's
resampler needs a couple of hundred milliseconds of material to produce any
output at 2kHz, so a 40ms click resamples to a zero-byte file, the build
carries on happily, and the failure appears much later as an `swi` deep inside
the *level loader's* sound loop ("we didn't read all of the data in the
stream"). Give short effects a fast decay instead of a short duration, and
check the output is not empty:

```sh
ls -la build/obj/sound*.raw
```

**A build that hangs forever with a container stuck in ffmpeg** is ffmpeg
waiting on stdin, which never closes under `docker run -i`. The makefile passes
`-nostdin -y` for this reason; do not remove them.

**An object drawing itself as something else** is almost always a state-size
overrun — see `DynospriteObject_DataSize` above.

**The whole screen comes up in the wrong colours, stretched, and frozen** is
the tileset and the tilemap disagreeing: the tilemap indexes tiles that the
tileset no longer has. The makefile's graphics rules used to depend only on the
`.json` descriptors, so regenerating the artwork — which rewrites the PNGs and
leaves the descriptors alone — did not rebuild either of them, and an
incremental build shipped whichever half happened to be stale. The rules now
depend on the images and on the generated headers as well. `make clean` is
still the way out if the two ever get out of step.

## Sprites are compiled code

`scripts/sprite2asm.py` unrolls each sprite into straight-line 6809. That has
three consequences that dominate every sprite decision:

1. **Code size scales with opaque pixels.** A 122x32 filled plate produced over
   16KB of draw code by itself. Prefer lettering to filled plates.
2. **`SinglePixelPosition: false` halves the code**, because only the
   byte-aligned variant is emitted. It requires the object's `globalX` to
   always be even — which is why every element in `table_spec.py` starts on an
   even column, asserted by the generator.
3. **`SaveBackground: false` removes the erase code entirely** and the
   background-saving work in the draw. Only safe for a sprite that is opaque
   across its whole footprint *and* drawn in the same place every single frame,
   because nothing will ever erase it. The score digits qualify; that is why a
   hidden read-out draws `DigitBlank` rather than going inactive.

Together these took the sprite code for this game from 43KB to 21KB.

Large byte-aligned blocks can also send the compiler's store-ordering search
exponential — a 66x22 plate took over twenty minutes. `ChunkHint` bounds that
search, but only on the 6309 path; on 6809 the answer is to use fewer opaque
pixels.

Each sprite is found by flood filling from its anchor. Two things go wrong
there, and they fail very differently:

- **Sprites overlapping on the sheet** — one drawn over another — fails the
  build with `****Error: sprite <name> not found within 20 pixels of location`.
  Annoying, but it tells you.
- **A sprite that is not 4-connected fails silently.** The fill takes whatever
  is joined to the anchor and leaves the rest behind, so you get a fragment on
  screen and no warning at all. Diagonal touching does not count as joined. The
  end-of-game message lost the whole "GAME OVER" line this way, arriving in the
  game as a stray letter; it is held together by a rule under each line for
  exactly that reason.

The anchor point is also the hotspot: it is the pixel that lands on the
object's `globalX`/`globalY`. It does not have to be opaque — the search
spirals outward to find the shape — but it does have to sit at the top-left of
the bounding box you intend, because the hotspot is `anchor` minus the
bounding-box minimum.

## Physics notes

- The ball sub-steps at no more than about a pixel per step, so it cannot
  tunnel through a wall at full speed.
- Every bounce gets a small pseudo-random tangential impulse (`jitter()`).
  Without it, symmetrical situations stay symmetrical: a ball dropping down a
  vertical gap onto a bumper is fired straight back up and loops for ever. The
  bumper kick is additionally skewed to alternating sides.
- A ball whose horizontal speed stays near zero for a couple of seconds gets a
  shove. This table, like the original, has no nudge button.
- The launch lane has a one-way gate at its mouth, implemented in code rather
  than in the grid: a rising ball passes through, a falling one is turned back
  into the table.
- A shot too weak to round the top returns to the launcher without costing a
  ball. The shooter lane is not a drain.

## The Mac build

`mac/` holds an Objective-C/SpriteKit reimplementation of DynoSprite (copied
from space-bandits) and a Mac Catalyst app target. It compiles the same
`game/objects/*.c` and `game/levels/*.c` as the CoCo build, against
`mac/dynosprite/include/dynosprite.h`, where `RegisterObject` becomes a
registry call rather than an object descriptor table.

```sh
scripts/gen-xcode.py
xcodebuild -project mac/Pinball.xcodeproj -scheme "Lost World Pinball" \
  -destination 'platform=macOS,variant=Mac Catalyst' build
```

The project file is generated. Assets are attached as folder references, so
`game/levels`, `game/sprites`, `game/tiles`, `game/images` and `game/sounds`
land in the bundle under exactly the names the resource controller looks for,
and regenerating an asset needs no project edit.

Things that bite:

- **The engine's `.c` files must compile as C**; the game's must compile as
  Objective-C++. `DSPoint.c` gets C++ name mangling otherwise and nothing can
  link to it. Conversely the game needs C++, because `table_data.h` defines its
  tables at file scope: in C++ those have internal linkage and may repeat in
  every translation unit, but as C they collide.
- **`DSWindowController.m` is AppKit-only** and must stay out of the Catalyst
  target, as it is in the project this came from.
- The macOS sprite parser locates each sprite with the same spiral search and
  flood fill as `scripts/gfx-process.py`, so sprite bounds and hotspots agree
  between the two builds. It ignores keys it does not know, so `ChunkHint` is
  harmless there.
- The macOS key matrix in `DSScene.m` mirrors the CoCo layout exactly, which is
  why `keyDown()` works unchanged. CONTROL and SHIFT arrive as F3 and F4.
- `images/images.json` must hold exactly one entry per level plus one for the
  title screen, or an assertion fires at launch.

The engine's own unit tests were not brought across; they live in
space-bandits and test the engine, not this game.

## CI

Three workflows, modelled on the sibling projects:

- `build.yml` — asset-integrity check plus both CPU builds, a headless MAME
  playtest of a full game, and the Mac build.
- `make-release.yml` — both disk images and the Mac app onto a draft release.
- `bump-version.yml` — bumps `package.json`, tags, and triggers the release.

Points worth remembering:

- The container image tag is pinned in both `coco-dev` and the workflows and
  the two must stay in step.
- **Never build two CPU targets in one workspace without cleaning between.**
  The intermediate sprite and object files are not named per CPU, so the 6309
  build will silently reuse 6809 sprite code. `make clean` also deletes the
  disk image it just built, so copy it aside first.
- `git` refuses to operate on the checkout inside the container until told the
  directory is safe; `check-assets.py` needs git, so that step comes first.
- CoCo 3 ROMs are copyrighted and are fetched at run time.
- The playtest asserts the *shape* of a game — launched, scored, drained,
  ended — rather than an exact score, so a MAME or timing change does not turn
  into a red build. It has been checked to give identical results under MAME
  0.286 locally and 0.287 in the image.

## Testing

`scripts/playtest.lua` drives MAME with no window: it types the load command,
presses SPACE at the menu, works the launcher on every ball, flaps the
flippers, saves screenshots, and prints `GameGlobals` and the ball's state
every few frames by reading emulated memory. Use it to check what the ball
*did*, not just that the build succeeded.

Note that the game samples input on its own 30 Hz tick, so a key held for a
single video frame can be missed entirely — the driver holds each press and
release across several frames for that reason.

The driver taps SPACE until `GameGlobals` shows the ball object's magic number,
rather than pressing it at a fixed frame, and everything after that is timed
from when the game answered. It used to press at frame 1500; growing the menu
splash from 1KB to 16KB pushed the menu past that, and the whole run failed
with the game apparently never starting. Anything keyed off how long the floppy
takes belongs on a signal from the game, not on a frame number.

`scripts/shot.py` crops MAME's 640x239 snapshot back to a clean 320x200 view
and can magnify a region.

The trace offsets in `playtest.lua` are hand-maintained against `GameGlobals`
and `BallObjectState`. Reordering a struct field silently makes the trace lie:
reading `cooldown` while believing it to be `pull` once sent a perfectly
healthy launcher to be debugged for half an hour. If a traced value looks
impossible, check the offsets before the game.

Being suspicious of the harness pays generally. Two "bugs" in this game turned
out to be the driver: the plunger that would not fire (the driver released the
key for fewer frames than the game samples) and the ball that would not launch
(same cause, different symptom). Confirm the game is really at fault by reading
its own state, not by watching what the driver thinks it did.
