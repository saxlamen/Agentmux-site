#!/usr/bin/env python3
"""Agentmux guide site builder. Standard library only, targets Python 3.9."""

from __future__ import annotations

import json
import re
from pathlib import Path

TOKEN = re.compile(r"\{\{(\w+)\}\}")


class MissingContentError(Exception):
    """Raised when config declares content that does not exist on disk."""


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render(template: str, vars: dict) -> str:
    return TOKEN.sub(lambda m: str(vars.get(m.group(1), "")), template)


def article_url(origin: str, lang: str, slug: str) -> str:
    return "{0}/guide/{1}/{2}/".format(origin.rstrip("/"), lang, slug)


def article_path(out_dir: Path, lang: str, slug: str) -> Path:
    return out_dir / lang / slug / "index.html"


def _language(config: dict, code: str) -> dict:
    for lang in config["languages"]:
        if lang["code"] == code:
            return lang
    raise KeyError("language not declared in config: {0}".format(code))


def _load_strings(src: Path, lang: str) -> dict:
    return json.loads((src / "strings" / "{0}.json".format(lang)).read_text(encoding="utf-8"))


def _content_fragment(src: Path, lang: str, slug: str) -> str:
    path = src / "content" / slug / "{0}.html".format(lang)
    if not path.exists():
        raise MissingContentError(str(path))
    return path.read_text(encoding="utf-8")


def langs_with(config: dict, slug: str) -> list:
    matrix = config.get("content", {})
    return [
        lang["code"]
        for lang in config["languages"]
        if slug in matrix.get(lang["code"], [])
    ]


def hreflang_block(config: dict, slug: str) -> str:
    origin = config["site"]["origin"].rstrip("/")
    lines = [
        '<link rel="alternate" hreflang="{0}" href="{1}">'.format(
            code, article_url(origin, code, slug)
        )
        for code in langs_with(config, slug)
    ]
    lines.append(
        '<link rel="alternate" hreflang="x-default" href="{0}/guide/">'.format(origin)
    )
    return "\n    ".join(lines)


def verify_content(src: Path, config: dict) -> None:
    missing = []
    for lang_code, slugs in config.get("content", {}).items():
        for slug in slugs:
            path = src / "content" / slug / "{0}.html".format(lang_code)
            if not path.exists():
                missing.append(str(path))
    if missing:
        raise MissingContentError(
            "config.json declares content that does not exist:\n  "
            + "\n  ".join(sorted(missing))
        )


def track_of(config: dict, slug: str) -> list:
    return [name for name, slugs in config["tracks"].items() if slug in slugs]


def neighbors(config: dict, track: str, slug: str) -> tuple:
    slugs = config["tracks"].get(track, [])
    if slug not in slugs:
        return (None, None)
    i = slugs.index(slug)
    prev_slug = slugs[i - 1] if i > 0 else None
    next_slug = slugs[i + 1] if i < len(slugs) - 1 else None
    return (prev_slug, next_slug)


def build_article(src: Path, out: Path, config: dict, lang: str, slug: str) -> None:
    template = (src / "templates" / "article.html").read_text(encoding="utf-8")
    strings = _load_strings(src, lang)
    meta = strings["articles"][slug]
    page_vars = {
        "htmlLang": _language(config, lang)["htmlLang"],
        "lang": lang,
        "title": meta["title"],
        "description": meta["description"],
        "canonical": article_url(config["site"]["origin"], lang, slug),
        "content": _content_fragment(src, lang, slug),
        "hreflang": hreflang_block(config, slug),
    }
    target = article_path(out, lang, slug)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(template, page_vars), encoding="utf-8")


def build_root_index(src: Path, out: Path, config: dict) -> None:
    template = (src / "templates" / "root-index.html").read_text(encoding="utf-8")
    links = "\n        ".join(
        '<a class="lang-card" href="/guide/{0}/" hreflang="{0}">{1}</a>'.format(
            lang["code"], lang["label"]
        )
        for lang in config["languages"]
        if config.get("content", {}).get(lang["code"])
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        render(template, {"languageLinks": links, "origin": config["site"]["origin"]}),
        encoding="utf-8",
    )


def build_track_index(src: Path, out: Path, config: dict, lang: str) -> None:
    template = (src / "templates" / "track-index.html").read_text(encoding="utf-8")
    strings = _load_strings(src, lang)
    available = set(config.get("content", {}).get(lang, []))
    blocks = []
    for track_name, slugs in config["tracks"].items():
        track_strings = strings["ui"]["tracks"][track_name]
        items = "\n            ".join(
            '<li><a href="/guide/{0}/{1}/">{2}</a></li>'.format(
                lang, slug, strings["articles"][slug]["title"]
            )
            for slug in slugs
            if slug in available
        )
        blocks.append(
            '<section class="track" id="{0}">\n'
            "          <h2>{1}</h2>\n"
            "          <p>{2}</p>\n"
            "          <ol>\n            {3}\n          </ol>\n"
            "        </section>".format(
                track_name, track_strings["title"], track_strings["blurb"], items
            )
        )
    target = out / lang / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render(
            template,
            {
                "htmlLang": _language(config, lang)["htmlLang"],
                "lang": lang,
                "title": strings["ui"]["trackIndexTitle"],
                "description": strings["ui"]["trackIndexDescription"],
                "canonical": "{0}/guide/{1}/".format(
                    config["site"]["origin"].rstrip("/"), lang
                ),
                "tracks": "\n        ".join(blocks),
            },
        ),
        encoding="utf-8",
    )


def build_sitemap(out_root: Path, config: dict) -> None:
    origin = config["site"]["origin"].rstrip("/")
    urls = ["{0}/guide/".format(origin)]
    matrix = config.get("content", {})
    for lang in config["languages"]:
        code = lang["code"]
        if not matrix.get(code):
            continue
        urls.append("{0}/guide/{1}/".format(origin, code))
        for slug in config["slugs"]:
            if slug in matrix[code]:
                urls.append(article_url(origin, code, slug))
    body = "\n".join("  <url><loc>{0}</loc></url>".format(u) for u in urls)
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body
        + "\n</urlset>\n",
        encoding="utf-8",
    )


def main() -> int:
    src = Path(__file__).resolve().parent
    web_root = src.parent
    out = web_root / "guide"
    config = load_config(src / "config.json")

    verify_content(src, config)

    matrix = config.get("content", {})
    for lang in config["languages"]:
        code = lang["code"]
        if not matrix.get(code):
            continue
        for slug in config["slugs"]:
            if slug in matrix[code]:
                build_article(src, out, config, code, slug)
        build_track_index(src, out, config, code)
    build_root_index(src, out, config)
    build_sitemap(web_root, config)
    print("built {0} language(s)".format(len([l for l in config["languages"] if matrix.get(l["code"])])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
