#!/usr/bin/env python3
"""Fail if the committed assets are not what the generator produces.

Everything under game/ except the .c and .h files comes out of
scripts/gen-assets.py.  This regenerates them and compares against what is
committed, so a hand-edit to a generated file -- or a generator that is not
deterministic -- shows up as a red build rather than as a mystery weeks later.

PNGs are compared by their pixels rather than their bytes: a different Pillow
version can re-encode the same image differently, and that is not a defect.

    scripts/check-assets.py
"""

import io
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


def committed_bytes(path):
    out = subprocess.run(
        ["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, check=False
    )
    return out.stdout if out.returncode == 0 else None


def same_pixels(path):
    """True if only the PNG encoding changed, not the picture."""
    old = committed_bytes(path)
    if old is None:
        return False
    try:
        a = Image.open(io.BytesIO(old))
        b = Image.open(os.path.join(ROOT, path))
        return (
            a.size == b.size
            and a.mode == b.mode
            and a.tobytes() == b.tobytes()
            and a.getpalette() == b.getpalette()
        )
    except Exception:
        return False


def main():
    gen = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "gen-assets.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if gen.returncode != 0:
        print("FAIL: the asset generator itself failed")
        print(gen.stdout + gen.stderr)
        return 1
    print(gen.stdout.strip())

    changed = [
        line for line in git("diff", "--name-only", "--", "game").stdout.split() if line
    ]
    real = []
    for path in changed:
        if path.endswith(".png") and same_pixels(path):
            continue  # same picture, different encoder
        real.append(path)

    if real:
        print("FAIL: these generated files do not match scripts/gen-assets.py:")
        for path in real:
            print(f"  {path}")
        print("\nRegenerate with scripts/gen-assets.py and commit the result.")
        print(git("diff", "--stat", "--", "game").stdout)
        return 1

    print("PASS: every generated asset matches the generator.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
