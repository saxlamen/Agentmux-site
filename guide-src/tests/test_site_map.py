#!/usr/bin/env python3
"""Geometry and encoding guards for SITE_MAP.svg.

The diagram first shipped with curved fan-in edges emitted after the cards, so
the lines painted over the titles ("Cla e Code on iPhone"). Then the spine was
shorter than the stubs hanging off it, leaving a connector pointing at nothing
next to "Standby is the real cost". Both were layout bugs, not text bugs, and
neither shows up when you read the SVG by eye -- so they are checked by walking
the path geometry here.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import site_map  # noqa: E402

COMMAND = re.compile(r"([MLHVCSQTAZ])([^MLHVCSQTAZ]*)", re.I)
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def segments(d: str) -> list:
    """Line segments in a path's `d` string, as ((x1, y1), (x2, y2)).

    Commands are walked in order so H and V -- which carry a single coordinate
    and inherit the other -- resolve to real points instead of shifting every
    later number by one.
    """
    out = []
    current = None
    for command, body in COMMAND.findall(d):
        values = [float(n) for n in NUMBER.findall(body)]
        kind = command.upper()
        if kind in "ML":
            for i in range(0, len(values) - 1, 2):
                point = (values[i], values[i + 1])
                if current:
                    out.append((current, point))
                current = point
        elif kind == "H":
            for value in values:
                point = (value, current[1])
                out.append((current, point))
                current = point
        elif kind == "V":
            for value in values:
                point = (current[0], value)
                out.append((current, point))
                current = point
        else:  # curves: their endpoints and control points are what matter here
            for i in range(0, len(values) - 1, 2):
                point = (values[i], values[i + 1])
                out.append((current, point))
                current = point
    return out


def all_segments(svg: str) -> list:
    return [seg for d in re.findall(r'<path d="([^"]+)"', svg) for seg in segments(d)]


class SiteMapDiagramTest(unittest.TestCase):
    def setUp(self):
        self.config = site_map.load()
        self.svg = site_map.svg(self.config)
        self.segments = all_segments(self.svg)

    def test_connectors_stay_out_of_the_card_column(self):
        inside = [p for seg in self.segments for p in seg if p[0] >= site_map.CARD_X]
        self.assertEqual(inside, [], "connector entered the card column: %s" % inside[:6])

    def test_no_connector_ends_in_mid_air(self):
        verticals = [(a, b) for a, b in self.segments if a[0] == b[0]]
        self.assertTrue(verticals, "no spine drawn")
        spine_x = max(verticals, key=lambda s: abs(s[1][1] - s[0][1]))[0][0]
        covered = [y for a, b in verticals if a[0] == spine_x for y in (a[1], b[1])]
        low, high = min(covered), max(covered)
        floating = []
        for a, b in self.segments:
            if a[1] != b[1]:
                continue  # not a horizontal stub
            if spine_x not in (a[0], b[0]):
                continue  # a box-to-box link, not a stub on the spine
            if not low <= a[1] <= high:
                floating.append((a, b))
        self.assertEqual(floating, [],
                         "stubs outside the spine span %d..%d: %s" % (low, high, floating[:4]))

    def test_ascii_only_so_no_viewer_can_misread_the_encoding(self):
        self.assertTrue(self.svg.startswith('<?xml version="1.0" encoding="UTF-8"?>'),
                        "missing XML declaration: viewers may guess Big5")
        self.assertTrue(self.svg.isascii(),
                        "non-ASCII in SVG: %s" % sorted({c for c in self.svg if ord(c) > 127}))

    def test_every_article_label_is_drawn_whole(self):
        for slug, label in site_map.LABEL.items():
            if slug in self.config["slugs"]:
                escaped = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                self.assertIn(">%s</text>" % escaped, self.svg, "label missing: %s" % label)

    def test_sizes_are_measured_not_hardcoded(self):
        for slug in self.config["slugs"]:
            self.assertIn(site_map.size(slug), self.svg, "size for %s missing" % slug)


if __name__ == "__main__":
    unittest.main(verbosity=2)
