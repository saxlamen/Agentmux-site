#!/usr/bin/env python3
"""Refresh the pixel dimensions in guide-src/images.json.

og:image:width/height are published on every guide page, so they must match the
files in resource/ rather than someone's memory. Dimensions are read from disk;
the alt text stays hand-written (it describes the screenshot, not the file).

Needs sips, which ships with macOS: python3 guide-src/refresh_images.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
WEB_ROOT = SRC.parent
IMAGES = SRC / "images.json"


def dimensions(file: Path) -> tuple:
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(file)],
                         capture_output=True, text=True).stdout
    width = re.search(r"pixelWidth: (\d+)", out)
    height = re.search(r"pixelHeight: (\d+)", out)
    if not width or not height:
        raise SystemExit("sips could not read %s" % file)
    return int(width.group(1)), int(height.group(1))


def main() -> int:
    if not IMAGES.exists():
        raise SystemExit("%s is missing; it holds the alt text, do not regenerate it blindly" % IMAGES)
    data = json.loads(IMAGES.read_text(encoding="utf-8"))
    changed, missing = [], []
    for path, entry in data.items():
        file = WEB_ROOT / path.lstrip("/")
        if not file.exists():
            missing.append(path)
            continue
        width, height = dimensions(file)
        if (entry.get("width"), entry.get("height")) != (width, height):
            changed.append("%s %sx%s -> %sx%s" % (path, entry.get("width"), entry.get("height"), width, height))
            entry["width"], entry["height"] = width, height
    new_files = ["/resource/" + f.name for f in (WEB_ROOT / "resource").iterdir()
                 if f.suffix == ".webp" and "/resource/" + f.name not in data]
    IMAGES.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for line in changed:
        print("updated", line)
    for path in missing:
        print("WARNING: %s is published in images.json but not on disk" % path)
    for path in sorted(new_files):
        print("note: %s has no entry (add width, height, alt)" % path)
    if not changed and not missing and not new_files:
        print("images.json already matches resource/")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
