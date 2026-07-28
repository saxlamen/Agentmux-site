from __future__ import annotations

import json
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
                        "prev": "上一篇",
                        "next": "下一篇",
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


if __name__ == "__main__":
    unittest.main()
