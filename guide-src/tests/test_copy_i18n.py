#!/usr/bin/env python3
"""Guard the four-locale copy surfaces the guide tests do not reach.

`test_language.py` covers the guide: its zh-Hant sources, its strings, and its
wizard copy, and it deliberately skips `index.source.html` because that file
also carries zh-Hans and ja blocks. That left the homepage and the privacy
policy with no test at all: nobody checked that all four locales are actually
filled in, that the Simplified Chinese blocks stayed Simplified, that the
Japanese blocks are Japanese, or that each generated homepage paints its own
language before JavaScript runs.

This file covers those. It reads the sources (and the generated homepages) and
says which locale drifted, not just that something failed.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_language import MAINLAND_TERMS, SIMPLIFIED_ONLY  # noqa: E402

SRC = Path(__file__).resolve().parent.parent.parent

HOME_SOURCE = SRC / "index.source.html"
PRIVACY = SRC / "privacy.html"
CONFIG = SRC / "guide-src" / "config.json"

SITE_LANGS = ("en", "zh-TW", "zh-Hans", "ja")
GENERATED_HOMES = {
    "en": SRC / "index.html",
    "zh-TW": SRC / "zh-TW" / "index.html",
    "zh-Hans": SRC / "zh-Hans" / "index.html",
    "ja": SRC / "ja" / "index.html",
}

CJK = re.compile(r"[\u4e00-\u9fff]")
KANA = re.compile(r"[\u3040-\u30ff]")

# A block that is mostly Latin letters is a block somebody never translated:
# the CJK locales carry their own script for about half of what they show,
# because technical words (SSH, tmux, agent, App) stay in Latin on purpose.
MIN_NATIVE_SHARE = 0.40
# How much shorter the shortest locale may run than the longest one. CJK is
# denser than English, so 4x is generous and still catches a dropped section.
MAX_LENGTH_RATIO = 4.0
MIN_LOCALE_CHARS = 200

# Characters that only exist in Traditional orthography, limited to the ones a
# zh-Hans page could plausibly inherit from a zh-TW original. Homographs that
# Simplified also uses (面, 台, 于 …) are absent on purpose.
TRADITIONAL_ONLY = set(
    "網務軟碼圖憶鎖儲載盤電腦資蓋設連線斷顯發應銀據級統總運遠進義產親從眾無"
    "術機權條來標檢沒測濟滅災熱愛現視覺覽計認讓論證評詞譯誤說敗賬購責車輕"
    "輯遷違遞遺釋鐘鑰鏈問隊難頂順預頻額風館駛顧類緊紀純約細織終紹結給絡絕"
    "繼績維綠緩編縮聯艱節藥獲營慮補規筆簡時東書寫語會見並於廣"
)
# Traditional house terms that would read as foreign in a Simplified page.
TRADITIONAL_TERMS = (
    "網路", "伺服器", "使用者", "軟體", "硬體", "程式碼", "記憶體", "螢幕", "儲存",
    "載入", "硬碟", "滑鼠", "電腦", "資訊", "應用程式", "回饋", "快取", "內部網路",
    "區域網路", "鎖定螢幕",
)
# Mainland terms that Japanese would never write: if one shows up, a Chinese
# block was pasted into the ja slot instead of written in Japanese.
CHINESE_ONLY_IN_JA = (
    "伺服器", "軟體", "硬體", "記憶體", "電腦", "滑鼠", "網路", "硬碟", "使用者",
    "程式碼", "螢幕", "介面",
)

# The homepage offers the guide in every locale, but the guide itself is built
# for two. The gap is a known product decision, not an oversight: shrinking
# this set is what "the guide supports one more language" looks like, and the
# test fails until someone deletes the language it just learned to allow.
# The homepage nav calls the guide 指南 and ガイド, but build_home.py rewrites
# that link to a guide locale that exists, so a zh-Hans reader lands in
# Traditional Chinese and a Japanese reader lands in English. This is a ratchet:
# when the guide gains a language, fix the fallback map and KNOWN_GUIDE_GAP in
# the same commit that adds the locale to guide-src/config.json.
KNOWN_GUIDE_GAP = {"zh-Hans", "ja"}
GUIDE_FALLBACK = {"zh-Hans": "zh-TW", "ja": "en"}

# The homepage's search snippet is written in two places that have to agree:
# build_home.py's LANG_CONFIG paints each generated page, and LANG_META inside
# index.source.html repaints it when a visitor switches language in the browser.
# A SERP clips English around 60 title characters and 160 description
# characters; CJK glyphs are about twice as wide, so those caps halve for CJK.
META_CAPS = {"en": (60, 160), "zh-TW": (60, 100), "zh-Hans": (60, 100), "ja": (60, 100)}


class LocaleTextParser(HTMLParser):
    """Collect visible text, attributed to the innermost data-lang ancestor."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.by_locale = {}
        self.inert = 0

    def handle_starttag(self, tag, attrs):
        locale = dict(attrs).get("data-lang")
        if tag in ("script", "style"):
            self.inert += 1
        self.stack.append(locale or (self.stack[-1] if self.stack else None))

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.inert:
            self.inert -= 1
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.inert or not data.strip():
            return
        locale = self.stack[-1] if self.stack else None
        if locale:
            joined = " ".join(data.split())
            self.by_locale[locale] = self.by_locale.get(locale, "") + " " + joined


class ActiveTextParser(HTMLParser):
    """Collect the text of elements marked class="active", i.e. what a
    visitor sees before any JavaScript has run."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.inert = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.inert += 1
        classes = dict(attrs).get("class", "").split()
        self.active = "active" in classes

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.inert:
            self.inert -= 1
        self.active = False

    def handle_data(self, data):
        if self.inert or not data.strip() or not self.active:
            return
        self.parts.append(" ".join(data.split()))


def locale_text(path: Path) -> dict:
    parser = LocaleTextParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.by_locale


def native_share(text: str) -> float:
    letters = len(CJK.findall(text)) + len(KANA.findall(text))
    return letters / max(len(text), 1)


class CopyLocaleSurfaceTest(unittest.TestCase):
    def setUp(self):
        self.home = locale_text(HOME_SOURCE)
        self.privacy = locale_text(PRIVACY)

    def test_every_locale_has_real_copy_in_both_surfaces(self):
        offenders = []
        for surface, text_by_locale in (("index.source.html", self.home), ("privacy.html", self.privacy)):
            for code in SITE_LANGS:
                text = text_by_locale.get(code, "")
                if len(text) < MIN_LOCALE_CHARS:
                    offenders.append("%s %s: %d characters" % (surface, code, len(text)))
        self.assertEqual(offenders, [], "a locale is missing or stubbed:\n" + "\n".join(offenders))

    def test_cjk_locales_are_written_in_their_own_script(self):
        offenders = []
        for surface, text_by_locale in (("index.source.html", self.home), ("privacy.html", self.privacy)):
            for code in ("zh-TW", "zh-Hans", "ja"):
                share = native_share(text_by_locale.get(code, ""))
                if share < MIN_NATIVE_SHARE:
                    offenders.append(
                        "%s %s: only %.0f%% native script, so part of it is still English"
                        % (surface, code, share * 100)
                    )
        self.assertEqual(offenders, [], "untranslated copy inside a CJK locale:\n" + "\n".join(offenders))

    def test_no_locale_is_much_shorter_than_the_others(self):
        offenders = []
        for surface, text_by_locale in (("index.source.html", self.home), ("privacy.html", self.privacy)):
            lengths = {code: len(text_by_locale.get(code, "")) for code in SITE_LANGS}
            longest, shortest = max(lengths.values()), min(lengths.values())
            if longest > shortest * MAX_LENGTH_RATIO:
                offenders.append("%s: longest %d vs shortest %d %s" % (surface, longest, shortest, lengths))
        self.assertEqual(offenders, [], "one locale lost a section:\n" + "\n".join(offenders))


class HomeLanguagePurityTest(unittest.TestCase):
    def setUp(self):
        self.home = locale_text(HOME_SOURCE)
        self.privacy = locale_text(PRIVACY)

    def test_zh_tw_surfaces_use_taiwan_terms(self):
        offenders = []
        for surface, text_by_locale in (("index.source.html", self.home), ("privacy.html", self.privacy)):
            text = text_by_locale.get("zh-TW", "")
            for term in MAINLAND_TERMS:
                if term in text:
                    offenders.append("%s: %s" % (surface, term))
        self.assertEqual(offenders, [], "mainland terminology in a zh-TW surface:\n" + "\n".join(offenders))

    def test_zh_tw_surfaces_have_no_simplified_characters(self):
        offenders = []
        for surface, text_by_locale in (("index.source.html", self.home), ("privacy.html", self.privacy)):
            leak = sorted(set(text_by_locale.get("zh-TW", "")) & SIMPLIFIED_ONLY)
            if leak:
                offenders.append("%s: %s" % (surface, " ".join(leak)))
        self.assertEqual(offenders, [], "simplified characters in a zh-TW surface:\n" + "\n".join(offenders))

    def test_zh_hans_surfaces_do_not_carry_traditional_forms(self):
        offenders = []
        for surface, text_by_locale in (("index.source.html", self.home), ("privacy.html", self.privacy)):
            text = text_by_locale.get("zh-Hans", "")
            chars = sorted(set(text) & TRADITIONAL_ONLY)
            terms = [term for term in TRADITIONAL_TERMS if term in text]
            if chars or terms:
                offenders.append("%s: chars %s terms %s" % (surface, " ".join(chars), " ".join(terms)))
        self.assertEqual(offenders, [], "Traditional forms in a zh-Hans surface:\n" + "\n".join(offenders))

    def test_japanese_surfaces_are_actually_japanese(self):
        offenders = []
        for surface, text_by_locale in (("index.source.html", self.home), ("privacy.html", self.privacy)):
            text = text_by_locale.get("ja", "")
            if not KANA.search(text):
                offenders.append("%s: no kana, so the ja slot holds non-Japanese text" % surface)
            for term in CHINESE_ONLY_IN_JA:
                if term in text:
                    offenders.append("%s: %s" % (surface, term))
        self.assertEqual(offenders, [], "Chinese left in a Japanese surface:\n" + "\n".join(offenders))


class GeneratedHomeTest(unittest.TestCase):
    """The four generated homepages must paint their own language with no JS."""

    def test_each_home_page_declares_and_shows_its_own_locale(self):
        offenders = []
        for code, path in GENERATED_HOMES.items():
            if not path.exists():
                offenders.append("%s: missing" % code)
                continue
            html = path.read_text(encoding="utf-8")
            declared = re.search(r'<html lang="([^"]+)"', html)
            if not declared or declared.group(1) != code:
                offenders.append("%s: <html lang> is %r" % (code, declared and declared.group(1)))
            parser = ActiveTextParser()
            parser.feed(html)
            shown = " ".join(parser.parts)
            if not shown.strip():
                offenders.append("%s: nothing is marked active, so the no-JS page is blank" % code)
                continue
            if code == "en":
                if native_share(shown) > 0.20:
                    offenders.append("en: the no-JS page paints mostly CJK text")
            elif native_share(shown) < MIN_NATIVE_SHARE:
                offenders.append(
                    "%s: the no-JS page is only %.0f%% native script" % (code, native_share(shown) * 100)
                )
        self.assertEqual(offenders, [], "a generated homepage shows the wrong language:\n" + "\n".join(offenders))

    def test_every_home_page_links_every_locale(self):
        offenders = []
        wanted = {'hreflang="%s"' % code for code in SITE_LANGS} | {'hreflang="x-default"'}
        for code, path in GENERATED_HOMES.items():
            if not path.exists():
                continue
            found = set(re.findall(r'hreflang="[^"]+"', path.read_text(encoding="utf-8")))
            if found != wanted:
                offenders.append("%s: %s" % (code, sorted(wanted - found) or sorted(found - wanted)))
        self.assertEqual(offenders, [], "hreflang alternates are incomplete:\n" + "\n".join(offenders))


class HomeMetaTest(unittest.TestCase):
    """The title and description a reader sees in a search result or share card.

    They live in two places that drift silently: `build_home.py` paints the
    generated page, `LANG_META` repaints it on an in-page language switch.
    """

    def setUp(self):
        sys.path.insert(0, str(SRC))
        import build_home  # the module owns the copy it paints with

        self.lang_config = build_home.LANG_CONFIG
        self.meta = self._lang_meta()

    def _lang_meta(self):
        source = HOME_SOURCE.read_text(encoding="utf-8")
        block = re.search(r"const LANG_META = \{(.*?)\n        \};", source, re.S)
        entries = {}
        pattern = r"(en|'zh-TW'|'zh-Hans'|ja): \{\s*title: '([^']*)',\s*description: '([^']*)'\s*\}"
        for match in re.finditer(pattern, block.group(1), re.S):
            entries[match.group(1).strip("'")] = (match.group(2), match.group(3))
        return entries

    def test_both_copies_cover_every_site_locale(self):
        offenders = []
        for name, keys in (("build_home.LANG_CONFIG", set(self.lang_config)), ("LANG_META", set(self.meta))):
            if keys != set(SITE_LANGS):
                offenders.append("%s covers %s" % (name, sorted(keys)))
        self.assertEqual(offenders, [], "a locale has no search metadata:\n" + "\n".join(offenders))

    def test_the_two_copies_of_home_metadata_say_the_same_thing(self):
        offenders = []
        for code in SITE_LANGS:
            if code not in self.meta or code not in self.lang_config:
                continue
            painted = (self.lang_config[code]["title"], self.lang_config[code]["description"])
            if painted != self.meta[code]:
                offenders.append(
                    "%s: LANG_CONFIG says %r while LANG_META says %r" % (code, painted[0], self.meta[code][0])
                )
        self.assertEqual(offenders, [], "the page and the language switcher disagree:\n" + "\n".join(offenders))

    def test_home_metadata_fits_a_search_result(self):
        offenders = []
        for code, (title_cap, desc_cap) in META_CAPS.items():
            painted = self.lang_config.get(code)
            painted = (painted["title"], painted["description"]) if painted else None
            for source, pair in (("LANG_CONFIG", painted), ("LANG_META", self.meta.get(code))):
                if not pair:
                    continue
                if len(pair[0]) > title_cap:
                    offenders.append("%s %s title %d > %d" % (code, source, len(pair[0]), title_cap))
                if len(pair[1]) > desc_cap:
                    offenders.append("%s %s description %d > %d" % (code, source, len(pair[1]), desc_cap))
        self.assertEqual(offenders, [], "the snippet gets cut off in the SERP:\n" + "\n".join(offenders))

    def test_guide_links_point_at_a_locale_that_exists(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        guide_langs = {lang["code"] for lang in config["languages"]}
        offenders = []
        for code, cfg in self.lang_config.items():
            href = cfg.get("guide_href", "")
            target = re.search(r"/guide/([A-Za-z-]+)/", href)
            want = GUIDE_FALLBACK.get(code, code)
            if not target:
                offenders.append("%s: guide_href %r is not a localized guide" % (code, href))
            elif target.group(1) != want:
                offenders.append(
                    "%s points at %s, expected %s (update GUIDE_FALLBACK if the guide gained a language)"
                    % (code, target.group(1), want)
                )
            elif target.group(1) not in guide_langs:
                offenders.append("%s points at %s, which the guide does not build" % (code, target.group(1)))
        self.assertEqual(offenders, [], "a homepage links to a guide that is not there:\n" + "\n".join(offenders))


class PrivacyMetaTest(unittest.TestCase):
    """`privacy.html` is one file for four languages, so its search metadata
    exists twice in different ways: a static English `<head>` (what a crawler
    without JavaScript gets, in any locale) and `LANG_META`, which repaints it
    per language. The English pair has to agree, and every language has to fit
    a search result.
    """

    def setUp(self):
        self.source = PRIVACY.read_text(encoding="utf-8")
        self.meta = self._lang_meta()

    def _lang_meta(self):
        block = re.search(r"const LANG_META = \{(.*?)\n        \};", self.source, re.S)
        entries = {}
        pattern = r"(en|'zh-TW'|'zh-Hans'|ja): \{\s*title: '([^']*)',\s*description: '([^']*)'\s*\}"
        for match in re.finditer(pattern, block.group(1), re.S):
            entries[match.group(1).strip("'")] = (match.group(2), match.group(3))
        return entries

    def test_privacy_metadata_covers_every_site_locale(self):
        self.assertEqual(set(self.meta), set(SITE_LANGS), "privacy.html cannot describe a locale in its own language")

    def test_the_english_head_matches_the_switcher(self):
        head_title = re.search(r"<title>([^<]*)</title>", self.source).group(1)
        head_description = re.search(r'name="description" content="([^"]*)"', self.source).group(1)
        self.assertEqual((head_title, head_description), self.meta["en"], "privacy.html's own head disagrees with its language switcher")

    def test_privacy_metadata_fits_a_search_result(self):
        offenders = []
        for code, (title_cap, desc_cap) in META_CAPS.items():
            title, description = self.meta[code]
            if len(title) > title_cap:
                offenders.append("%s title %d > %d" % (code, len(title), title_cap))
            if len(description) > desc_cap:
                offenders.append("%s description %d > %d" % (code, len(description), desc_cap))
        self.assertEqual(offenders, [], "the snippet gets cut off in the SERP:\n" + "\n".join(offenders))


class GuideLanguageGapTest(unittest.TestCase):
    """The homepage nav calls the guide 指南/ガイド in every locale, while the
    guide is only built for two, and build_home.py sends the other two readers
    to somebody else's language. This test is a ratchet, not a complaint."""

    def setUp(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.guide_langs = {lang["code"] for lang in config["languages"]}

    def test_the_gap_between_site_locales_and_guide_locales_is_the_documented_one(self):
        gap = set(SITE_LANGS) - self.guide_langs
        self.assertEqual(
            gap,
            KNOWN_GUIDE_GAP,
            "the guide locale set changed: %s. If one more language shipped, delete it "
            "from KNOWN_GUIDE_GAP and from GUIDE_FALLBACK in this test; if one shrank, the "
            "homepage nav labels a guide in a language that is not there." % sorted(gap),
        )


class AppLabelTest(unittest.TestCase):
    """`privacy.html` names app switches, in four languages, and those names live
    one repo over in the iOS app's `Localizable.strings`. Nothing linked them, so
    the policy spent a while telling readers to look for a "Background Activity
    Chime" that the app never showed. Skipped when the app is not checked out
    beside the site.
    """

    APP = SRC.parent / "Agentmux"
    LPROJ = {"en": "en", "zh-TW": "zh-Hant", "zh-Hans": "zh-Hans", "ja": "ja"}
    # Taken from Agentmux/Resources/*.lproj/Localizable.strings on 2026-10-30:
    # `share_usage_statistics` and `background_activity_alerts`.
    POLICY_LABELS = {
        "en": ["Share Anonymous Usage Statistics", "Background Activity Alerts"],
        "zh-TW": ["分享匿名使用統計", "背景任務警報"],
        "zh-Hans": ["分享匿名使用统计", "背景任务提醒"],
        "ja": ["匿名の利用統計を共有", "バックグラウンド活動アラート"],
    }

    def setUp(self):
        self.strings = {}
        for lang, folder in self.LPROJ.items():
            path = self.APP / "Resources" / ("%s.lproj" % folder) / "Localizable.strings"
            if not path.exists():
                self.skipTest("the app is not checked out beside the site (%s missing)" % path)
            self.strings[lang] = path.read_text(encoding="utf-8")
        self.privacy = locale_text(PRIVACY)

    def test_the_policy_quotes_labels_the_app_actually_shows(self):
        offenders = []
        for lang, labels in self.POLICY_LABELS.items():
            for label in labels:
                if label not in self.strings[lang]:
                    offenders.append("%s: the policy points at %r, which the settings screen does not show" % (lang, label))
        self.assertEqual(offenders, [], "the app renamed a switch:\n" + "\n".join(offenders))

    def test_the_policy_still_names_them(self):
        offenders = []
        for lang, labels in self.POLICY_LABELS.items():
            text = self.privacy.get(lang, "")
            for label in labels:
                if label not in text:
                    offenders.append("%s: the app calls it %r, the policy stopped saying so" % (lang, label))
        self.assertEqual(offenders, [], "the policy drifted from the app:\n" + "\n".join(offenders))


if __name__ == "__main__":
    unittest.main(verbosity=2)
