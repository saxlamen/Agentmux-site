"""Print the size of every site copy surface, so COPY.md's numbers are
measured instead of remembered. Stdlib only.

    python3 tools/copy_stats.py

Counts are of reader-visible text: tags are dropped, whitespace collapsed.
For Chinese and Japanese the character count is the honest unit; for English
it is the word count. Guide strings and wizard strings are counted as JSON
string values, because that is what ships.
"""

import html.parser
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE_LANGS = ("en", "zh-TW", "zh-Hans", "ja")


class LangText(html.parser.HTMLParser):
    """Collect visible text, attributed to the innermost data-lang ancestor."""

    VOID = {"img", "br", "meta", "link", "input", "hr", "source", "wbr", "col"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.out = {}

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        data = dict(attrs)
        self.stack.append(data.get("data-lang", self.stack[-1] if self.stack else None))
        if tag == "script":
            pass

    def handle_endtag(self, tag):
        if tag not in self.VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        lang = self.stack[-1] if self.stack else None
        if lang:
            self.out[lang] = self.out.get(lang, "") + data


def page_text(path):
    parser = LangText()
    parser.feed(path.read_text(encoding="utf-8"))
    return {lang: clean(text) for lang, text in parser.out.items()}


def clean(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def cjk(text):
    return sum(1 for char in text if "\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff")


def size(text):
    """Word count for English, character count for Chinese and Japanese. The
    English home page carries the language switcher's 繁體中文 / 简体中文 /
    日本語, so a page is judged by which script dominates it, not by whether
    any CJK glyph appears."""
    count = cjk(text)
    if count > len(text) * 0.2:
        return "%d CJK chars" % count
    return "%d words" % len(text.split())


def visible_text(path):
    """A generated page holds one locale and does not tag it, so count
    everything the reader can see: tags, script and style all go away."""

    class Plain(html.parser.HTMLParser):
        SKIP = {"script", "style", "noscript", "template"}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.skip = 0
            self.parts = []

        def handle_starttag(self, tag, attrs):
            if tag in self.SKIP:
                self.skip += 1

        def handle_endtag(self, tag):
            if tag in self.SKIP and self.skip:
                self.skip -= 1

        def handle_data(self, data):
            if not self.skip:
                self.parts.append(data)

    parser = Plain()
    parser.feed(path.read_text(encoding="utf-8"))
    return clean(" ".join(parser.parts))


def strings_values(path):
    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                yield from walk(value)
        elif isinstance(node, list):
            for value in node:
                yield from walk(value)
        elif isinstance(node, str):
            yield node

    values = list(walk(json.loads(path.read_text(encoding="utf-8"))))
    return len(values), sum(len(value) for value in values)


def main():
    home = {lang: visible_text(ROOT / lang_dir(lang) / "index.html") for lang in SITE_LANGS}
    print("home (generated, one locale per page)")
    for lang in SITE_LANGS:
        print("  %-8s %s" % (lang, size(home[lang])))

    privacy = page_text(ROOT / "privacy.html")
    print("privacy.html (one file, four locales)")
    for lang in SITE_LANGS:
        print("  %-8s %s" % (lang, size(privacy.get(lang, ""))))

    print("guide articles (guide-src/content)")
    for lang in ("en", "zh-TW"):
        total = ""
        for path in sorted((ROOT / "guide-src" / "content").glob("*/%s.html" % lang)):
            total += " " + clean(path.read_text(encoding="utf-8"))
        print("  %-8s %s across %d articles" % (lang, size(total.strip()), len(list((ROOT / "guide-src" / "content").glob("*/%s.html" % lang)))))

    print("guide strings (JSON string values)")
    for path in (
        ROOT / "guide-src/strings/en.json",
        ROOT / "guide-src/strings/zh-TW.json",
        ROOT / "guide-src/wizard/strings/en.json",
        ROOT / "guide-src/wizard/strings/zh-TW.json",
    ):
        count, chars = strings_values(path)
        print("  %-42s %d values, %d chars" % (path.relative_to(ROOT), count, chars))


def lang_dir(lang):
    return ROOT if lang == "en" else ROOT / lang


if __name__ == "__main__":
    main()
