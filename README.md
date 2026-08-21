# Lost World Pinball — CoCo 3

A remake of Tandy's 1983 TRS-80 MC-10 game *Lost World Pinball* (cat. no.
26-3363) for the Tandy Color Computer 3, built on the
[DynoSprite](https://github.com/richard42/dynosprite) engine.

![Lost World Pinball on the CoCo 3: the ball in play beside a target, both flippers raised, and Vally on the panel with her tongue out after the fly](doc/screenshot.png)

The original squeezed a whole pinball table into the MC-10's 32x16 block
graphics. This version keeps that table's layout and its rules, and gives it a
320x200 16-colour playfield, a ball with real velocity and reflection physics,
and flippers that swing.

The strip beside the table is the original's too, stacked the same way: Vally's
name in script, Vally herself with her head down at the water hole, the fern
desert on the near shore, the barren ground, and then the high score above the
score — orange frame and teal frame, unlabelled, as the original had them.

## Building

The toolchain (lwasm, CMOC, ToolShed, ffmpeg) lives in a Docker image:

```sh
./coco-dev make all               # build/PBAL6809.DSK
./coco-dev make all CPU=6309      # build/PBAL6309.DSK
./coco-dev make all RELEASE=1     # no bounds checks, no SWI traps
```

Assets — the table artwork, its collision data, the sprites, the level
descriptor, the splash screens and the sound effects — are all generated:

```sh
scripts/gen-assets.py --preview   # also writes build/table-preview.png
```

Nothing in `game/` is hand-drawn, so the table is edited by editing
`scripts/table_spec.py` and re-running the generator.

## The Mac version

The same game code also builds as a Mac app, on the Objective-C/SpriteKit
reimplementation of DynoSprite that lives in `mac/dynosprite/` (taken from the
space-bandits project). `game/objects/*.c` and `game/levels/*.c` are compiled
verbatim for both targets; only the engine underneath differs.

```sh
scripts/gen-xcode.py                      # regenerate mac/Pinball.xcodeproj
open mac/Pinball.xcodeproj                # or build from the command line:
xcodebuild -project mac/Pinball.xcodeproj -scheme "Lost World Pinball" \
  -destination 'platform=macOS,variant=Mac Catalyst' build
```

It is a Mac Catalyst app, so it also builds for iPad. Controls are the same
except that the CoCo's CONTROL and SHIFT arrive as F3 and F4; the arrow keys
are usually easier.

## Playing

Boot the disk and type:

```
LOADM"PINBALL"
EXEC
```

then press SPACE at the title screen. The title and loading screens are the
1983 cassette cover, dithered down to sixteen of the CoCo's colours. A dithered
photograph hardly compresses, so the backdrop is nearly 16KB and takes about
twelve seconds to come off the floppy: expect a black screen for that long
after `EXEC` before the menu appears.

| Key | |
|---|---|
| `CONTROL` (or `←`, `Z`) | left flipper |
| `SHIFT` (or `→`, `/`) | right flipper |
| `ENTER` | hold to draw the launcher back, release to fire |
| `BREAK` | abandon the game |
| `SPACE` | start a new game |

Hold `ENTER` too long and the launcher springs back to the top, exactly as the
manual describes — let go and start again.

## The rules, as printed in 1983

Three balls. Points come from hitting anything red — everything except the end
hole and the flipper hubs.

| | |
|---|---|
| bumpers | 10 |
| red power strips | 10 |
| plungers | 20 |
| red marks | 30 |

A plunger turns green when hit and cannot score again until it resets. Hit
every plunger during one ball and they all reset with scoring doubled: `2X`
appears beside the playfield. Do it again and it goes to `3X`. Each new ball
starts back at 1X.

Hit the red marks under the top pods twelve times and Vally's tongue reaches
far enough to catch the prehistoric fly. The volcano erupts and the rest of
that ball scores `10X`. Tongue length accumulates across the whole game, not
just one ball.

An extra ball arrives with every 10,000 points. When the last ball drains the
high score board flashes.

## Testing

MAME can be driven headlessly, which is how the table gets checked:

```sh
scripts/playtest.sh 240            # boots, plays three balls, saves screenshots
scripts/shot.py build/playtest/coco3/0100.png out.png 2
```

`scripts/playtest.lua` walks the menus, works the launcher, flaps the flippers
and prints the game's own globals every few frames, so a run reports what the
ball actually did rather than just whether the build succeeded.

## Continuous integration

`.github/workflows/build.yml` runs on every push and pull request:

- **build-dsk-images** — checks every generated asset still matches
  `scripts/gen-assets.py`, then builds both CPU targets.
- **playtest** — boots the disk in headless MAME and plays a whole three-ball
  game, then checks the game's own state to see that the ball launched, scored,
  drained and the game ended. Screenshots and the state trace are uploaded, so
  a failure is diagnosable from the pull request.
- **build-macos** — regenerates the Xcode project and builds the Mac app.

`make-release.yml` builds both disk images and the Mac app and attaches them to
a draft release; `bump-version.yml` bumps `package.json` and triggers it. The
version lives only in `package.json` — the Xcode project reads it when
regenerated.

## Layout

```
engine/     DynoSprite engine (6809/6309 assembly); only menu.asm differs
mac/        the same engine reimplemented in Objective-C, plus the Xcode app
game/
  levels/   the table: descriptor plus its per-frame hook
  objects/  ball physics and rules, flippers, score digits, lamps, panel
  sprites/  generated sheets and their descriptors
  tiles/    generated tileset: the playfield and the panel beside it
  images/   splash screens, generated from art/
  sounds/   generated effects
scripts/    asset generator, table spec, build tools, playtest harness
art/        the 1983 cassette cover, source for both splash screens
```

## Credits

*Lost World Pinball*, and the cover art in `art/`, © 1983 Tandy Corporation.

DynoSprite © 2013–2014 Richard Goedeken,
<https://github.com/richard42/dynosprite>.
