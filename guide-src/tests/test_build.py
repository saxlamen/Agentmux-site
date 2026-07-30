from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build


def make_config(content=None, languages=None):
    return {
        "site": {
            "origin": "https://example.test",
            "appStoreUrl": "https://apps.apple.com/app/id6766158521",
        },
        "languages": languages
        or [{"code": "zh-TW", "htmlLang": "zh-Hant", "label": "繁體中文"}],
        "slugs": ["what-is-tmux", "setup", "troubleshooting"],
        "tracks": {
            "beginner": ["what-is-tmux", "setup"],
            "cliuser": ["what-is-tmux", "setup"],
        },
        "content": content if content is not None else {"zh-TW": ["what-is-tmux"]},
    }


class BuildFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "guide-src"
        self.out = self.tmp / "guide"
        (self.src / "templates").mkdir(parents=True)
        (self.src / "strings").mkdir(parents=True)
        (self.src / "content" / "what-is-tmux").mkdir(parents=True)
        (self.src / "templates" / "article.html").write_text(
            "<html lang={{htmlLang}}>"
            "<title>{{title}}</title>"
            "<link rel=canonical href={{canonical}}>"
            "{{hreflang}}{{content}}",
            encoding="utf-8",
        )
        (self.src / "content" / "what-is-tmux" / "zh-TW.html").write_text(
            "<p>tmux 讓 agent 繼續跑。</p>", encoding="utf-8"
        )
        # ui 必須含 build_article 會查的每一個鍵。Task 6 會讓 build_article
        # 讀 guideHome / ctaLine / ctaButton，屆時缺鍵會讓這裡所有測試 KeyError。
        (self.src / "strings" / "zh-TW.json").write_text(
            json.dumps(
                {
                    "ui": {
                        "guideHome": "指南首頁",
                        "troubleshooting": "疑難排解",
                        "prev": "上一篇",
                        "next": "下一篇",
                        "pagerTrackFormat": "{0} · {1}",
                        "listJoin": "、",
                        "labelColon": "：",
                        "tracks": {
                            "beginner": {
                                "title": "我沒開過終端機",
                                "blurb": "從頭建立整套心智模型。",
                            },
                            "cliuser": {
                                "title": "我已經在跑 CLI agent",
                                "blurb": "只缺遠端接回來那一段。",
                            },
                        },
                        "ctaLine": "14 天全功能試用，之後 Lifetime 買斷。",
                        "ctaButton": "在 App Store 下載",
                    },
                    "articles": {
                        "what-is-tmux": {
                            "title": "讓 agent 在你關掉手機後繼續跑",
                            "description": "tmux 是什麼，為什麼遠端跑 agent 需要它。",
                        },
                        "setup": {
                            "title": "15 分鐘，讓你的 agent 開始整晚工作",
                            "description": "回答三個問題，拿到只屬於你的步驟清單。",
                        },
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)


class TestRender(unittest.TestCase):
    def test_replaces_known_keys(self):
        self.assertEqual(build.render("a{{x}}b", {"x": "1"}), "a1b")

    def test_unknown_keys_become_empty(self):
        self.assertEqual(build.render("a{{missing}}b", {}), "ab")


class TestUrls(unittest.TestCase):
    def test_article_url_has_trailing_slash(self):
        self.assertEqual(
            build.article_url("https://example.test", "zh-TW", "what-is-tmux"),
            "https://example.test/guide/zh-TW/what-is-tmux/",
        )


class TestBuildArticle(BuildFixture):
    def test_writes_index_html_in_slug_directory(self):
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        page = self.out / "zh-TW" / "what-is-tmux" / "index.html"
        self.assertTrue(page.exists())

    def test_injects_title_and_content(self):
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        html = (self.out / "zh-TW" / "what-is-tmux" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("讓 agent 在你關掉手機後繼續跑", html)
        self.assertIn("tmux 讓 agent 繼續跑。", html)

    def test_canonical_points_at_self(self):
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        html = (self.out / "zh-TW" / "what-is-tmux" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("https://example.test/guide/zh-TW/what-is-tmux/", html)

    def test_uses_html_lang_not_url_code(self):
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        html = (self.out / "zh-TW" / "what-is-tmux" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("<html lang=zh-Hant>", html)


class TestHreflang(BuildFixture):
    def test_only_lists_languages_that_have_the_slug(self):
        config = make_config(
            content={"zh-TW": ["what-is-tmux"], "en": []},
            languages=[
                {"code": "zh-TW", "htmlLang": "zh-Hant", "label": "繁體中文"},
                {"code": "en", "htmlLang": "en", "label": "English"},
            ],
        )
        block = build.hreflang_block(config, "what-is-tmux")
        self.assertIn('hreflang="zh-TW"', block)
        self.assertNotIn('hreflang="en"', block)

    def test_includes_x_default_pointing_at_guide_root(self):
        block = build.hreflang_block(make_config(), "what-is-tmux")
        self.assertIn('hreflang="x-default"', block)
        self.assertIn('href="https://example.test/guide/"', block)

    def test_never_emits_link_to_nonexistent_page(self):
        config = make_config(
            content={"zh-TW": ["what-is-tmux"], "en": ["setup"]},
            languages=[
                {"code": "zh-TW", "htmlLang": "zh-Hant", "label": "繁體中文"},
                {"code": "en", "htmlLang": "en", "label": "English"},
            ],
        )
        block = build.hreflang_block(config, "what-is-tmux")
        self.assertNotIn("/guide/en/what-is-tmux/", block)


class TestVerifyContent(BuildFixture):
    def test_passes_when_all_declared_content_exists(self):
        build.verify_content(self.src, make_config())

    def test_raises_when_declared_content_is_missing(self):
        config = make_config(content={"zh-TW": ["what-is-tmux", "setup"]})
        with self.assertRaises(build.MissingContentError) as ctx:
            build.verify_content(self.src, config)
        self.assertIn("setup", str(ctx.exception))

    def test_error_lists_every_missing_file_not_just_the_first(self):
        config = make_config(content={"zh-TW": ["what-is-tmux", "setup", "troubleshooting"]})
        with self.assertRaises(build.MissingContentError) as ctx:
            build.verify_content(self.src, config)
        message = str(ctx.exception)
        self.assertIn("setup", message)
        self.assertIn("troubleshooting", message)


class TestNeighbors(unittest.TestCase):
    def setUp(self):
        self.config = {
            "tracks": {
                "beginner": ["a", "b", "c"],
                "cliuser": ["a", "c"],
            }
        }

    def test_middle_item_has_both_neighbors(self):
        self.assertEqual(build.neighbors(self.config, "beginner", "b"), ("a", "c"))

    def test_first_item_has_no_previous(self):
        self.assertEqual(build.neighbors(self.config, "beginner", "a"), (None, "b"))

    def test_last_item_has_no_next(self):
        self.assertEqual(build.neighbors(self.config, "beginner", "c"), ("b", None))

    def test_neighbors_differ_per_track(self):
        self.assertEqual(build.neighbors(self.config, "cliuser", "a"), (None, "c"))

    def test_slug_outside_track_has_no_neighbors(self):
        self.assertEqual(build.neighbors(self.config, "beginner", "zzz"), (None, None))


class TestTrackOf(unittest.TestCase):
    def test_troubleshooting_belongs_to_no_track(self):
        config = {
            "tracks": {
                "beginner": ["what-is-tmux", "setup"],
                "cliuser": ["what-is-tmux", "setup"],
            }
        }
        self.assertEqual(build.track_of(config, "troubleshooting"), [])

    def test_shared_slug_belongs_to_both_tracks(self):
        config = {
            "tracks": {
                "beginner": ["what-is-tmux", "setup"],
                "cliuser": ["what-is-tmux", "setup"],
            }
        }
        self.assertEqual(
            sorted(build.track_of(config, "what-is-tmux")), ["beginner", "cliuser"]
        )


class TestPagerTrackLabels(unittest.TestCase):
    """一篇文章屬於多條 track 時，鄰居不同會讓兩張卡撞成同一個標籤。"""

    def setUp(self):
        self.config = {
            "tracks": {
                "beginner": ["intro", "ssh", "tmux", "tailscale"],
                "cliuser": ["intro", "tmux", "tailscale"],
            },
            "content": {"zh-TW": ["intro", "ssh", "tmux", "tailscale"]},
        }
        self.strings = {
            "ui": {
                "prev": "上一篇",
                "next": "下一篇",
                "pagerTrackFormat": "{0} · {1}",
                "listJoin": "、",
                "labelColon": "：",
                "tracks": {
                    "beginner": {"title": "我沒開過終端機"},
                    "cliuser": {"title": "我已經在跑 CLI agent"},
                },
            },
            "articles": {
                "intro": {"title": "你的 AI 應該在你睡覺時工作"},
                "ssh": {"title": "一條通往另一台電腦的加密隧道"},
                "tmux": {"title": "讓 agent 繼續跑"},
                "tailscale": {"title": "不要對公網開 port"},
            },
        }

    def test_colliding_prev_labels_name_their_track(self):
        html = build._pager(self.config, self.strings, "zh-TW", "tmux")
        self.assertIn("上一篇 · 我沒開過終端機", html)
        self.assertIn("上一篇 · 我已經在跑 CLI agent", html)

    def test_colliding_next_labels_name_their_track(self):
        html = build._pager(self.config, self.strings, "zh-TW", "intro")
        self.assertIn("下一篇 · 我沒開過終端機", html)
        self.assertIn("下一篇 · 我已經在跑 CLI agent", html)

    def test_unambiguous_label_keeps_no_track_suffix(self):
        # tmux 的 next 在兩條 track 都是 tailscale，只會有一張「下一篇」。
        html = build._pager(self.config, self.strings, "zh-TW", "tmux")
        self.assertIn(">下一篇<span>不要對公網開 port</span>", html)

    def test_shared_neighbour_still_renders_one_card(self):
        html = build._pager(self.config, self.strings, "zh-TW", "tmux")
        self.assertEqual(html.count('href="/guide/zh-TW/tailscale/"'), 1)

    def test_single_track_article_has_plain_labels(self):
        html = build._pager(self.config, self.strings, "zh-TW", "ssh")
        self.assertIn(">上一篇<span>", html)
        self.assertIn(">下一篇<span>", html)
        self.assertNotIn("·", html)

    def test_all_prev_cards_come_before_all_next_cards(self):
        # 逐條 track 收集會讓順序變成 prev→next→prev，讀起來像上下顛倒。
        html = build._pager(self.config, self.strings, "zh-TW", "tmux")
        keys = re.findall(r'class="pager-(\w+)"', html)
        self.assertEqual(keys, ["prev", "prev", "next"])

    def test_order_within_a_direction_follows_track_order(self):
        html = build._pager(self.config, self.strings, "zh-TW", "tmux")
        self.assertLess(
            html.index('data-tracks="beginner"'), html.index('data-tracks="cliuser"')
        )

    def test_missing_translation_drops_the_card_before_labelling(self):
        self.config["content"] = {"zh-TW": ["intro", "tmux", "tailscale"]}
        html = build._pager(self.config, self.strings, "zh-TW", "tmux")
        # ssh 沒有譯文，beginner 的上一篇消失，剩下的單一「上一篇」不需要後綴。
        self.assertNotIn("ssh", html)
        self.assertIn(">上一篇<span>你的 AI 應該在你睡覺時工作</span>", html)


class TestPagerTrackMemory(unittest.TestCase):
    """pager 要帶足夠的資料，讓前端在讀者選過路線後收掉另一條的卡。"""

    def setUp(self):
        self.config = {
            "tracks": {
                "beginner": ["intro", "ssh", "tmux", "tailscale"],
                "cliuser": ["intro", "tmux", "tailscale"],
            },
            "content": {"zh-TW": ["intro", "ssh", "tmux", "tailscale"]},
        }
        self.strings = {
            "ui": {
                "prev": "上一篇",
                "next": "下一篇",
                "pagerTrackFormat": "{0} · {1}",
                "listJoin": "、",
                "labelColon": "：",
                "tracks": {
                    "beginner": {"title": "我沒開過終端機"},
                    "cliuser": {"title": "我已經在跑 CLI agent"},
                },
            },
            "articles": {
                "intro": {"title": "你的 AI 應該在你睡覺時工作"},
                "ssh": {"title": "一條通往另一台電腦的加密隧道"},
                "tmux": {"title": "讓 agent 繼續跑"},
                "tailscale": {"title": "不要對公網開 port"},
            },
        }

    def test_each_card_declares_its_tracks(self):
        html = build._pager(self.config, self.strings, "zh-TW", "tmux")
        self.assertIn('data-tracks="beginner"', html)
        self.assertIn('data-tracks="cliuser"', html)

    def test_shared_card_declares_both_tracks(self):
        # tailscale 在兩條 track 都是 tmux 的下一篇，不該被任何一邊收掉。
        html = build._pager(self.config, self.strings, "zh-TW", "tmux")
        self.assertIn('data-tracks="beginner cliuser"', html)

    def test_card_carries_the_plain_label_for_restoring(self):
        html = build._pager(self.config, self.strings, "zh-TW", "tmux")
        self.assertIn('data-label="上一篇"', html)
        self.assertIn('data-label="下一篇"', html)


class TestTrackChoiceWiring(unittest.TestCase):
    """選路線和用路線是兩份 inline script，共用的 storage key 必須一致。"""

    SRC = Path(__file__).resolve().parents[1]
    KEY = "agentmux-guide-track"

    def _template(self, name):
        return (self.SRC / "templates" / name).read_text(encoding="utf-8")

    def test_track_index_writes_the_shared_key(self):
        html = self._template("track-index.html")
        self.assertIn("localStorage.setItem('{0}'".format(self.KEY), html)

    def test_article_reads_the_shared_key(self):
        html = self._template("article.html")
        self.assertIn("localStorage.getItem('{0}')".format(self.KEY), html)

    def test_no_other_storage_key_is_used(self):
        both = self._template("track-index.html") + self._template("article.html")
        keys = set(re.findall(r"localStorage\.(?:get|set)Item\('([^']+)'", both))
        self.assertEqual(keys, {self.KEY})

    def test_both_scripts_guard_blocked_storage(self):
        for name in ("track-index.html", "article.html"):
            self.assertIn("try {", self._template(name), name)


class TestTrackIndexLinks(BuildFixture):
    def setUp(self):
        super().setUp()
        (self.src / "templates" / "track-index.html").write_text(
            "<html>{{tracks}}</html>", encoding="utf-8"
        )
        strings = json.loads(
            (self.src / "strings" / "zh-TW.json").read_text(encoding="utf-8")
        )
        strings["ui"]["trackIndexTitle"] = "Agentmux 指南"
        strings["ui"]["trackIndexDescription"] = "從零開始。"
        strings["ui"]["extendedReading"] = "延伸閱讀"
        (self.src / "strings" / "zh-TW.json").write_text(
            json.dumps(strings, ensure_ascii=False), encoding="utf-8"
        )

    def test_article_links_record_their_track(self):
        config = make_config()
        build.build_track_index(self.src, self.out, config, "zh-TW")
        html = (self.out / "zh-TW" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<a data-track="beginner" href="/guide/zh-TW/what-is-tmux/">', html)
        self.assertIn('<a data-track="cliuser" href="/guide/zh-TW/what-is-tmux/">', html)

    def test_extended_reading_links_record_their_track(self):
        config = make_config()
        config["trackExtended"] = {"cliuser": ["setup"]}
        config["content"] = {"zh-TW": ["what-is-tmux", "setup"]}
        (self.src / "content" / "setup").mkdir(parents=True, exist_ok=True)
        (self.src / "content" / "setup" / "zh-TW.html").write_text("<p>x</p>", encoding="utf-8")
        build.build_track_index(self.src, self.out, config, "zh-TW")
        html = (self.out / "zh-TW" / "index.html").read_text(encoding="utf-8")
        extended = html.split("延伸閱讀")[1]
        self.assertIn('data-track="cliuser"', extended)


class TestRootIndex(BuildFixture):
    def setUp(self):
        super().setUp()
        (self.src / "templates" / "root-index.html").write_text(
            "<html>{{languageLinks}}</html>", encoding="utf-8"
        )

    def test_emits_real_anchor_per_language(self):
        build.build_root_index(self.src, self.out, make_config())
        html = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/guide/zh-TW/"', html)
        self.assertIn("繁體中文", html)

    def test_works_without_javascript(self):
        build.build_root_index(self.src, self.out, make_config())
        html = (self.out / "index.html").read_text(encoding="utf-8")
        anchors = html.count("<a ")
        self.assertGreaterEqual(anchors, 1)


class TestSitemap(BuildFixture):
    def test_lists_only_existing_pages(self):
        config = make_config(content={"zh-TW": ["what-is-tmux"]})
        build.build_sitemap(self.tmp, config)
        xml = (self.tmp / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("https://example.test/guide/zh-TW/what-is-tmux/", xml)
        self.assertNotIn("/guide/zh-TW/setup/", xml)

    def test_includes_guide_root_and_track_index(self):
        build.build_sitemap(self.tmp, make_config())
        xml = (self.tmp / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("https://example.test/guide/", xml)
        self.assertIn("https://example.test/guide/zh-TW/", xml)

    def test_is_wellformed_xml(self):
        import xml.etree.ElementTree as ET

        build.build_sitemap(self.tmp, make_config())
        ET.parse(str(self.tmp / "sitemap.xml"))


class TestJsonLd(BuildFixture):
    def test_emits_article_type(self):
        meta = {"title": "T", "description": "D"}
        block = build.article_jsonld(make_config(), "zh-TW", "what-is-tmux", meta)
        self.assertIn('"@type": "Article"', block)
        self.assertIn("application/ld+json", block)

    def test_setup_page_also_emits_howto(self):
        meta = {"title": "T", "description": "D"}
        block = build.article_jsonld(make_config(), "zh-TW", "setup", meta)
        self.assertIn('"HowTo"', block)

    def test_non_setup_page_has_no_howto(self):
        meta = {"title": "T", "description": "D"}
        block = build.article_jsonld(make_config(), "zh-TW", "what-is-tmux", meta)
        self.assertNotIn('"HowTo"', block)

    def test_json_is_parseable(self):
        meta = {"title": "引號\"測試", "description": "D"}
        block = build.article_jsonld(make_config(), "zh-TW", "what-is-tmux", meta)
        payload = block.split(">", 1)[1].rsplit("<", 1)[0]
        json.loads(payload)


class TestArticleMeta(BuildFixture):
    def test_og_and_twitter_tags_present(self):
        (self.src / "templates" / "article.html").write_text(
            "{{ogTitle}}|{{ogDescription}}|{{ogUrl}}", encoding="utf-8"
        )
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        html = (self.out / "zh-TW" / "what-is-tmux" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("讓 agent 在你關掉手機後繼續跑", html)
        self.assertIn("https://example.test/guide/zh-TW/what-is-tmux/", html)


class TestEscaping(BuildFixture):
    def _set_meta(self, title, description="D"):
        strings = json.loads(
            (self.src / "strings" / "zh-TW.json").read_text(encoding="utf-8")
        )
        strings["articles"]["what-is-tmux"]["title"] = title
        strings["articles"]["what-is-tmux"]["description"] = description
        (self.src / "strings" / "zh-TW.json").write_text(
            json.dumps(strings, ensure_ascii=False), encoding="utf-8"
        )

    def test_quote_in_title_does_not_break_og_title_attribute(self):
        self._set_meta('讓 agent 在你關掉手機後繼續跑"引號測試')
        (self.src / "templates" / "article.html").write_text(
            "<title>{{title}}</title>"
            '<meta property="og:title" content="{{ogTitle}}">',
            encoding="utf-8",
        )
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        html_out = (self.out / "zh-TW" / "what-is-tmux" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'content="讓 agent 在你關掉手機後繼續跑&quot;引號測試"', html_out
        )
        self.assertNotIn(
            'content="讓 agent 在你關掉手機後繼續跑"引號測試"', html_out
        )

    def test_ampersand_and_lt_escaped_in_title_and_meta(self):
        self._set_meta("A & B < C")
        (self.src / "templates" / "article.html").write_text(
            "<title>{{title}}</title>"
            '<meta property="og:title" content="{{ogTitle}}">'
            '<meta name="description" content="{{description}}">',
            encoding="utf-8",
        )
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        html_out = (self.out / "zh-TW" / "what-is-tmux" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("<title>A &amp; B &lt; C</title>", html_out)
        self.assertIn('content="A &amp; B &lt; C"', html_out)

    def test_jsonld_still_parses_when_title_has_quote(self):
        self._set_meta('T"itle')
        (self.src / "templates" / "article.html").write_text(
            "{{jsonld}}", encoding="utf-8"
        )
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        html_out = (self.out / "zh-TW" / "what-is-tmux" / "index.html").read_text(
            encoding="utf-8"
        )
        payload = html_out.split(">", 1)[1].rsplit("<", 1)[0]
        json.loads(payload)

    def test_content_fragment_is_not_escaped(self):
        (self.src / "content" / "what-is-tmux" / "zh-TW.html").write_text(
            "<p><strong>粗體</strong></p>", encoding="utf-8"
        )
        (self.src / "templates" / "article.html").write_text(
            "{{content}}", encoding="utf-8"
        )
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        html_out = (self.out / "zh-TW" / "what-is-tmux" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("<p><strong>粗體</strong></p>", html_out)
        self.assertNotIn("&lt;p&gt;", html_out)


class TestWrapTables(unittest.TestCase):
    def test_bare_table_gets_wrapped(self):
        fragment = "<p>intro</p><table><tr><td>a</td></tr></table>"
        result = build.wrap_tables(fragment)
        self.assertIn(
            '<div class="table-wrap"><table><tr><td>a</td></tr></table></div>',
            result,
        )

    def test_already_wrapped_table_is_not_double_wrapped(self):
        fragment = '<div class="table-wrap"><table><tr><td>a</td></tr></table></div>'
        result = build.wrap_tables(fragment)
        self.assertEqual(result, fragment)
        self.assertEqual(result.count("table-wrap"), 1)

    def test_two_separate_tables_both_get_wrapped(self):
        fragment = "<table><tr><td>1</td></tr></table><p>between</p><table><tr><td>2</td></tr></table>"
        result = build.wrap_tables(fragment)
        self.assertEqual(result.count('<div class="table-wrap">'), 2)
        self.assertIn(
            '<div class="table-wrap"><table><tr><td>1</td></tr></table></div>', result
        )
        self.assertIn(
            '<div class="table-wrap"><table><tr><td>2</td></tr></table></div>', result
        )

    def test_fragment_with_no_table_is_unchanged(self):
        fragment = "<p>no tables here</p><pre><code>x = 1</code></pre>"
        self.assertEqual(build.wrap_tables(fragment), fragment)


class TestBuildArticleWrapsTables(BuildFixture):
    def test_bare_table_in_content_ends_up_inside_table_wrap(self):
        (self.src / "content" / "what-is-tmux" / "zh-TW.html").write_text(
            "<p>intro</p>"
            "<table><tr><th>指令</th><td>tmux new -s work</td></tr></table>",
            encoding="utf-8",
        )
        (self.src / "templates" / "article.html").write_text(
            "{{content}}", encoding="utf-8"
        )
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        html_out = (self.out / "zh-TW" / "what-is-tmux" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '<div class="table-wrap"><table><tr><th>指令</th>'
            "<td>tmux new -s work</td></tr></table></div>",
            html_out,
        )

    def test_table_inner_markup_survives_unescaped(self):
        (self.src / "content" / "what-is-tmux" / "zh-TW.html").write_text(
            "<table><tr><th>指令</th><td>tmux new -s work</td></tr></table>",
            encoding="utf-8",
        )
        (self.src / "templates" / "article.html").write_text(
            "{{content}}", encoding="utf-8"
        )
        build.build_article(self.src, self.out, make_config(), "zh-TW", "what-is-tmux")
        html_out = (self.out / "zh-TW" / "what-is-tmux" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("<th>指令</th>", html_out)
        self.assertIn("<td>tmux new -s work</td>", html_out)
        self.assertNotIn("&lt;th&gt;", html_out)
        self.assertNotIn("&lt;td&gt;", html_out)


if __name__ == "__main__":
    unittest.main()
