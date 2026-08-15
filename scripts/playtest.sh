#!/usr/bin/env bash
#
# Run the built disk image in MAME with no window and no sound, driving it from
# scripts/playtest.lua, and leave a series of screenshots plus a trace of the
# game's own state in build/playtest/.
#
#     scripts/playtest.sh [seconds] [cpu]
#
# MAME is taken from tools/mame64 if that symlink exists, otherwise from PATH,
# so this works both on a developer machine and inside the coco-dev image.
# CoCo 3 ROMs are copyrighted and are not shipped anywhere, so point
# MAME_ROMPATH at wherever coco3.zip lives.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECONDS_TO_RUN="${1:-45}"
CPU="${2:-6809}"
SYSTEM=$([ "$CPU" = "6309" ] && echo coco3h || echo coco3)

if [ -n "${MAME:-}" ]; then
  :
elif [ -x "$ROOT/tools/mame64" ]; then
  MAME="$ROOT/tools/mame64"
else
  MAME="$(command -v mame)"
fi
ROMPATH="${MAME_ROMPATH:-$HOME/Applications/mame/roms}"

rm -rf "$ROOT/build/playtest"
mkdir -p "$ROOT/build/playtest"

"$MAME" "$SYSTEM" \
  -flop1 "$ROOT/build/PBAL$CPU.DSK" \
  -rompath "$ROMPATH" \
  -video none -sound none -nothrottle \
  -seconds_to_run "$SECONDS_TO_RUN" \
  -snapshot_directory "$ROOT/build/playtest" \
  -autoboot_script "$ROOT/scripts/playtest.lua" > "$ROOT/build/playtest/log.txt" 2>&1 || true

grep -vE "^Average speed|^$" "$ROOT/build/playtest/log.txt" || true
echo "--- $(find "$ROOT/build/playtest" -name '*.png' | wc -l | tr -d ' ') screenshots in build/playtest/coco3/"
