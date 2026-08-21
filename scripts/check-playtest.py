#!/usr/bin/env python3
"""Judge a headless playtest run: did the game actually play?

scripts/playtest.sh boots the disk in MAME and prints the game's own globals
every few frames.  This reads that trace and insists the run got all the way
through a game, so CI fails on "the ball never left the launcher" rather than
only on "the build broke".

The assertions deliberately stop at the shape of a game -- launched, scored,
ran out of balls.  Pinning an exact score would turn any MAME or timing change
into a red build for no good reason.

    scripts/check-playtest.py [build/playtest/log.txt]
"""

import re
import sys

LINE = re.compile(
    r"f=(?P<frame>\d+) state=(?P<state>\d+) balls=(?P<balls>\d+) "
    r"score=(?P<score>[0-9a-f]{8})"
)

# The driver announces each launch and how far back the plunger was.
LAUNCH = re.compile(
    r"launch (?P<n>\d+): pull=(?P<pull>\d+) after (?P<held>\d+) frames"
    r"(?P<stop> \(stop test\))?"
)

# table_data.h.  One of the driver's shots holds the key far past full stretch,
# and a plunger with a stop has to answer that at full stretch.  The counter
# used to wrap back to nothing instead, so holding the key too long quietly
# fired a weak shot -- or, at about 1.1 seconds, no shot at all.
FULL_PULL = 16

STATE_NAMES = {1: "ready", 2: "playing", 3: "drained", 4: "game over"}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "build/playtest/log.txt"
    try:
        text = open(path).read()
    except OSError as err:
        print(f"FAIL: cannot read the playtest trace: {err}")
        return 1

    samples = [m.groupdict() for m in LINE.finditer(text)]
    if not samples:
        print(f"FAIL: {path} has no game state in it -- the level never loaded.")
        print("\n".join(text.splitlines()[-15:]))
        return 1

    states = {int(s["state"]) for s in samples}
    best = max(int(s["score"], 16) for s in samples)
    lowest_balls = min(int(s["balls"]) for s in samples)

    print(f"{len(samples)} samples, states seen: "
          + ", ".join(STATE_NAMES.get(s, str(s)) for s in sorted(states)))
    print(f"best score {best:08x}, fewest balls left {lowest_balls}")

    failures = []
    if 2 not in states:
        failures.append("the ball never got into play (no 'playing' state)")
    if best == 0:
        failures.append("nothing was ever scored")
    if 3 not in states:
        failures.append("no ball ever drained")
    if 4 not in states:
        failures.append("the game never ended (run it for longer?)")

    launches = [m.groupdict() for m in LAUNCH.finditer(text)]
    if not launches:
        failures.append("the driver never reported a launch")
    else:
        held = [int(l["pull"]) for l in launches if l["stop"]]
        print(f"{len(launches)} launches, plunger reached "
              f"{max(int(l['pull']) for l in launches)} of {FULL_PULL}")
        if not held:
            failures.append("no shot was tagged as testing the plunger's stop")
        elif max(held) < FULL_PULL:
            failures.append(
                f"holding the plunger for a second or more left it at "
                f"{max(held)} of {FULL_PULL} -- it is winding past its stop "
                f"and back to nothing instead of staying put"
            )

    for f in failures:
        print(f"FAIL: {f}")
    if failures:
        return 1

    print("PASS: the game launched, scored, drained and ended.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
