#!/usr/bin/env python3
"""Site map diagram for the Agentmux site.

Reads guide-src/config.json and the content files, so the picture cannot drift
from the pages the guide builder actually emits. Writes SITE_MAP.svg (a
picture) and SITE_MAP.md (the same tree as Mermaid, which GitHub renders).
Standard library only, same constraint as build.py.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent
WEB_ROOT = SRC.parent
OUT_SVG = WEB_ROOT / "SITE_MAP.svg"
OUT_MD = WEB_ROOT / "SITE_MAP.md"
CARD_X = 600  # left edge of the article cards; no connector may enter from here right

HOME_PAGES = [("/", "home (en, x-default)"), ("/zh-TW/", "home zh-TW"), ("/zh-Hans/", "home zh-Hans"),
              ("/ja/", "home ja"), ("/privacy.html", "privacy policy")]
LABEL = {
    "why-remote-vibe-coding": "Standby is the real cost",
    "why-not-gui-ide": "Why not Cursor / VS Code",
    "what-is-cli": "What is a CLI agent",
    "what-is-ssh": "What is SSH",
    "what-is-tmux": "What is tmux",
    "what-is-tailscale": "What is Tailscale",
    "why-agentmux": "vs Termius / Blink",
    "setup": "Setup wizard",
    "claude-code-on-iphone": "Claude Code on iPhone",
    "permission-review": "AI Permission Review",
    "troubleshooting": "Troubleshooting (8 fixes)",
}
TRACK_BADGE = {"beginner": "B", "cliuser": "C"}


def load() -> dict:
    return json.loads((SRC / "config.json").read_text(encoding="utf-8"))


def size(slug: str) -> str:
    """English words, or Traditional Chinese characters, code blocks excluded."""
    counts = []
    for name, pattern in (("en.html", r"[A-Za-z0-9]+"), ("zh-TW.html", r"[\u4e00-\u9fff]")):
        path = SRC / "content" / slug / name
        if not path.exists():
            counts.append(0)
            continue
        body = re.sub(r"(?is)<(pre|code|table)[^>]*>.*?</\1>", " ", path.read_text(encoding="utf-8"))
        plain = html.unescape(re.sub(r"<[^>]+>", " ", body))
        counts.append(len(re.findall(pattern, plain)))
    return "%d w / %d zh" % tuple(counts)


def track_of(config: dict, slug: str) -> str:
    badges = "".join(TRACK_BADGE[name] for name, slugs in config["tracks"].items() if slug in slugs)
    return badges or "-"


def rows(config: dict) -> list:
    """(track name, ordered slugs) for the reading orders shown in the legend."""
    listed = config["slugs"]
    return [(name, [slug for slug in slugs if slug in listed]) for name, slugs in config["tracks"].items()]


def svg(config: dict) -> str:
    slugs = config["slugs"]
    card_height, gap = 58, 16
    legend_rows = rows(config)
    height = 150 + len(slugs) * (card_height + gap) + 40 + 26 * (len(legend_rows) + 2)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1230 %d"'
           ' font-family="-apple-system, Helvetica, Arial, sans-serif" font-size="13">' % height,
           '<rect width="1230" height="%d" fill="#090d0f"/>' % height,
           '<text x="26" y="34" fill="#f4fbf7" font-size="20">Agentmux site map</text>',
           '<text x="26" y="56" fill="#6f817a">B = beginner track, C = CLI-user track | '
           'sizes are English words / Traditional Chinese characters, code excluded</text>']

    def box(x, y, w, h, title, sub="", fill="#121a1d", stroke="rgba(214,255,236,0.2)", ink="#f4fbf7"):
        out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="%s" stroke="%s"/>'
                   % (x, y, w, h, fill, stroke))
        out.append('<text x="%d" y="%d" fill="%s">%s</text>' % (x + 14, y + 23, ink, html.escape(title)))
        if sub:
            out.append('<text x="%d" y="%d" fill="#8fa79d">%s</text>' % (x + 14, y + 43, html.escape(sub)))

    def curve(x1, y1, x2, y2, colour="rgba(214,255,236,0.4)"):
        if x1 >= CARD_X or x2 >= CARD_X:
            raise AssertionError("connectors must stay left of the card column (x < %d): "
                                 "a line emitted after its card cuts the title in half" % CARD_X)
        out.append('<path d="M%d %d C %d %d %d %d %d %d" fill="none" stroke="%s" stroke-width="1.4"/>'
                   % (x1, y1, x1 + 46, y1, x2 - 46, y2, x2, y2, colour))

    # left column: the pages every visitor can land on
    y = 92
    for path, label in HOME_PAGES:
        box(26, y, 200, 42, path, label, fill="#101719")
        y += 52
    guide_y = y + 12
    box(26, guide_y, 200, 42, "/guide/", "language picker", fill="#182326")

    # middle column: the two guide locales
    box(300, 130, 190, 42, "/guide/en/", "x-default", fill="#182326")
    box(300, 192, 190, 42, "/guide/zh-TW/", "same articles", fill="#182326")
    curve(226, guide_y + 21, 300, 151)
    curve(226, guide_y + 21, 300, 213)

    # right column: one card per article, in guide reading order. Every card also
    # exists under /guide/zh-TW/, so the URLs say <lang> rather than drawing the
    # same edge twice. A spine plus short stubs, not a curved fan: the fan's
    # control points pushed the lines through the card column and cut the titles
    # in half ("Cla e Code on iPhone"). Lines stop at the card edge.
    cards_top, spine, card_x = 92, 552, CARD_X
    out.append('<text x="600" y="84" fill="#6f817a">/guide/&lt;lang&gt;/... exists in en and zh-TW</text>')
    mids = [cards_top + index * (card_height + gap) + card_height // 2 for index in range(len(slugs))]
    # The spine has to span every stub, not just the level of the two locale
    # boxes. Starting it at y=151 left the first card's stub (y=121) attached to
    # nothing -- a line ending in mid-air next to "Standby is the real cost".
    entry = (151, 213)
    top, bottom = min(mids[0], *entry), max(mids[-1], *entry)
    out.append('<path d="M490 151 H%d M490 213 H%d M%d %d V%d" fill="none"'
               ' stroke="rgba(214,255,236,0.45)" stroke-width="1.4"/>' % (spine, spine, spine, top, bottom))
    for index, slug in enumerate(slugs):
        cy = cards_top + index * (card_height + gap)
        box(card_x, cy, 300, card_height, LABEL.get(slug, slug), "%s | %s" % (track_of(config, slug), size(slug)))
        out.append('<text x="920" y="%d" fill="#6f817a">/guide/&lt;lang&gt;/%s/</text>' % (cy + 34, slug))
        out.append('<path d="M%d %d H%d" fill="none" stroke="rgba(214,255,236,0.4)" stroke-width="1.3"/>'
                   % (spine, mids[index], card_x - 8))
        out.append('<circle cx="%d" cy="%d" r="2.4" fill="rgba(214,255,236,0.6)"/>' % (card_x - 8, mids[index]))

    # legend: the two reading orders, as arrows
    legend_y = cards_top + len(slugs) * (card_height + gap) + 24
    out.append('<text x="26" y="%d" fill="#f4fbf7" font-size="15">Reading orders (pager prev/next)</text>' % legend_y)
    for index, (name, slugs_in_track) in enumerate(legend_rows):
        line = "  >  ".join(LABEL.get(slug, slug) for slug in slugs_in_track)
        out.append('<text x="26" y="%d" fill="#8fa79d">%s: %s</text>'
                   % (legend_y + 26 + index * 26, name, html.escape(line)))
    extended = config.get("trackExtended", {})
    extra = "; ".join("%s also gets %s" % (name, ", ".join(LABEL.get(s, s) for s in slugs))
                      for name, slugs in extended.items())
    if extra:
        out.append('<text x="26" y="%d" fill="#6f817a">further reading: %s</text>'
                   % (legend_y + 26 + len(legend_rows) * 26, html.escape(extra)))
    out.append("</svg>")
    picture = "\n".join(out)
    if not picture.isascii():
        bad = sorted({c for c in picture if ord(c) > 127})
        raise AssertionError("SITE_MAP.svg must stay ASCII or viewers may misread it as Big5: %r" % bad)
    return picture


def markdown(config: dict) -> str:
    slugs = config["slugs"]
    lines = ["# Site map", "",
             "Generated by `guide-src/site_map.py`. Re-run it after changing `config.json`:",
             "`python3 guide-src/site_map.py`.", ""]
    lines += ["```text", "agentmux.saxcave.cc"]
    for path, label in HOME_PAGES:
        lines.append("├─ %-18s %s" % (path, label))
    lines.append("└─ /guide/            language picker (redirects by preference)")
    for lang in config["languages"]:
        lines.append("   └─ /guide/%s/  %d articles" % (lang["code"], len(slugs)))
        for position, slug in enumerate(slugs):
            branch = "└" if position == len(slugs) - 1 else "├"
            lines.append("      %s─ %-24s [%s] %s"
                         % (branch, slug + "/", track_of(config, slug), size(slug)))
    lines += ["```", "", "B = beginner track, C = CLI-user track.", "", "## Mermaid", "", "```mermaid", "graph LR"]
    lines.append('  H["/<br>home en"]:::home')
    for path, label in HOME_PAGES[1:]:
        node = re.sub(r"[^a-z]", "", label.lower()) or "n"
        lines.append('  %s["%s<br>%s"]:::home' % (node, path, label))
        lines.append("  H --- %s" % node)
    lines += ['  G["/guide/<br>language picker"]:::hub', "  H --- G",
              '  EN["/guide/en/"]:::hub', '  ZH["/guide/zh-TW/"]:::hub', "  G --> EN", "  G --> ZH"]
    for slug in slugs:
        node = re.sub(r"[^a-z]", "", slug)
        lines.append('  EN --> %s["%s<br>%s"]:::art' % (node, LABEL.get(slug, slug), size(slug)))
    for name, slugs_in_track in rows(config):
        for previous, current in zip(slugs_in_track, slugs_in_track[1:]):
            lines.append("  %s --> %s" % (re.sub(r"[^a-z]", "", previous), re.sub(r"[^a-z]", "", current)))
    lines += ["  classDef home fill:#101719,color:#f4fbf7,stroke:#6f817a;",
              "  classDef hub fill:#182326,color:#f4fbf7,stroke:#6f817a;",
              "  classDef art fill:#121a1d,color:#a7b8b2,stroke:#6f817a;",
              "```", "",
              "Locales: `/`, `/zh-TW/`, `/zh-Hans/`, `/ja/`. The guide exists in en and zh-TW only; "
              "`/en/` is a redirect to `/`."]
    return "\n".join(lines) + "\n"


def main() -> int:
    config = load()
    OUT_SVG.write_text(svg(config), encoding="utf-8")
    OUT_MD.write_text(markdown(config), encoding="utf-8")
    print("wrote %s and %s" % (OUT_SVG.relative_to(WEB_ROOT), OUT_MD.relative_to(WEB_ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
