#!/usr/bin/env python3
"""Render guide content fragments as plain text for reading in a terminal.

Usage: python3 tools/dump_plain.py content/<slug>/{en,zh-TW}.html ...
Titles come from strings/<lang>.json so the dump reads like the built page.
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "guide-src"


def plain(fragment: str) -> str:
    t = fragment
    t = re.sub(r"<pre><code>(.*?)</code></pre>", lambda m: "\n```\n" + m.group(1).strip() + "\n```\n", t, flags=re.S)
    t = re.sub(r"<a href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"\2 (\1)", t, flags=re.S)
    t = re.sub(r"<code>(.*?)</code>", r"`\1`", t, flags=re.S)
    t = re.sub(r"<strong>(.*?)</strong>", r"**\1**", t, flags=re.S)
    t = re.sub(r"<em>(.*?)</em>", r"_\1_", t, flags=re.S)
    t = re.sub(r"<summary><h2>(.*?)</h2></summary>", r"## \1\n", t, flags=re.S)
    t = re.sub(r"<h2>(.*?)</h2>", r"\n## \1\n", t, flags=re.S)
    t = re.sub(r"<h3>(.*?)</h3>", r"\n### \1\n", t, flags=re.S)
    t = re.sub(r"</?(details|section|ul|table)[^>]*>", "", t)
    t = re.sub(r"<li>", "\n- ", t)
    t = re.sub(r"</(li|p|tr)>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    t = re.sub(r" +\n", "\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def main():
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.is_absolute():
            path = Path.cwd() / arg
        lang = path.stem
        slug = path.parent.name
        strings = json.loads((SRC / "strings" / f"{lang}.json").read_text(encoding="utf-8"))
        meta = strings["articles"].get(slug, {})
        print("=" * 72)
        print(f"{slug} / {lang}    title: {meta.get('title', '(no title)')}")
        print(f"description: {meta.get('description', '(none)')}")
        print("=" * 72)
        print(plain(path.read_text(encoding="utf-8")))
        print()


if __name__ == "__main__":
    main()
