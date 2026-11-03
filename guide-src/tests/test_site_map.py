#!/usr/bin/env python3
"""Geometry and encoding guards for SITE_MAP.svg.

The diagram first shipped with curved fan-in edges that were emitted after the
cards, so the lines painted over the titles ("Cla e Code on iPhone"). Nothing
was wrong with the text; the layout covered it. These checks keep connectors out
of the card column and keep the file readable by any viewer's encoding guess.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import site_map  # noqa: E402


def path_coordinates(svg: str) -> list:
    """Every (x, y) pair written into a <path> element."""
    points = []
    for d in re.findall(r'<path d="([^"]+)"', svg):
        numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", d)]
        points += list(zip(numbers[0::2], numbers[1::2]))
    return points


class SiteMapDiagramTest(unittest.TestCase):
    def setUp(self):
        self.config = site_map.load()
        self.svg = site_map.svg(self.config)

    def test_connectors_stay_out_of_the_card_column(self):
        inside = [(x, y) for x, y in path_coordinates(self.svg) if x >= site_map.CARD_X]
        self.assertEqual(inside, [], "connector entered the card column: %s" % inside[:6])

    def test_ascii_only_so_no_viewer_can_misread_the_encoding(self):
        self.assertTrue(self.svg.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"),
                        "missing XML declaration: viewers may guess Big5")
        self.assertTrue(self.svg.isascii(),
                        "non-ASCII in SVG: %s" % sorted({c for c in self.svg if ord(c) > 127}))

    def test_every_article_label_is_drawn_whole(self):
        # A label may also appear in the legend, but it must appear as a complete
        # card text element, never split across drawing layers.
        for slug, label in site_map.LABEL.items():
            if slug in self.config["slugs"]:
                self.assertIn('>%s</text>' % html_escape(label), self.svg,
                              "label missing from the diagram: %s" % label)

    def test_sizes_are_measured_not_hardcoded(self):
        # The diagram must reflect the files on disk, otherwise it goes stale
        # silently the way the hand-written one did.
        for slug in self.config["slugs"]:
            self.assertIn(site_map.size(slug), self.svg, "size for %s missing" % slug)


def html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


if __name__ == "__main__":
    unittest.main(verbosity=2)
