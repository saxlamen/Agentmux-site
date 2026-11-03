#!/usr/bin/env python3
"""Agentmux guide site builder. Standard library only, targets Python 3.9."""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path

TOKEN = re.compile(r"\{\{(\w+)\}\}")
TABLE = re.compile(r"<table\b.*?</table>", re.DOTALL | re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
H2_SECTION = re.compile(r"<h2\b[^>]*>(.*?)</h2>(.*?)(?=<h2\b|\Z)", re.DOTALL | re.IGNORECASE)
H3_HEAD = re.compile(r"<h3\b[^>]*>(.*?)</h3>(.*?)(?=<h3\b|<h2\b|\Z)", re.DOTALL | re.IGNORECASE)
DATE_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}")

DEFAULT_OG_IMAGE = "/resource/ipad-raw-run-coding-agents-anywhere.webp"
IMAGES_FILE = Path(__file__).resolve().parent / "images.json"
FAQ_SLUGS = ("troubleshooting",)
FAQ_ANSWER_HEADINGS = ("fix", "解法")


class MissingContentError(Exception):
    """Raised when config declares content that does not exist on disk."""


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render(template: str, vars: dict) -> str:
    return TOKEN.sub(lambda m: str(vars.get(m.group(1), "")), template)


def esc(value: str) -> str:
    """Escape a value bound for an HTML attribute or element text."""
    return html.escape(str(value), quote=True)


def article_url(origin: str, lang: str, slug: str) -> str:
    return "{0}/guide/{1}/{2}/".format(origin.rstrip("/"), lang, slug)


def article_path(out_dir: Path, lang: str, slug: str) -> Path:
    return out_dir / lang / slug / "index.html"


def origin(config: dict) -> str:
    return config["site"]["origin"].rstrip("/")


def absolute_url(config: dict, path: str) -> str:
    """Turn a site-relative asset path into the absolute URL schema.org wants."""
    if str(path).startswith("http://") or str(path).startswith("https://"):
        return str(path)
    return origin(config) + "/" + str(path).lstrip("/")


def seo(config: dict) -> dict:
    """Search-specific settings. Every key has a working default, so a config
    without a `seo` block still builds valid pages."""
    return config.get("seo", {})


def og_image(config: dict, meta: dict = None) -> str:
    meta = meta or {}
    return absolute_url(config, meta.get("image") or seo(config).get("defaultOgImage") or DEFAULT_OG_IMAGE)


def image_tags(config: dict, meta: dict, lang: str) -> str:
    """og:image:width/height/alt for whatever image this page declares.

    Dimensions come from images.json; guide-src/refresh_images.py re-reads them
    from resource/ so a swapped screenshot cannot leave stale tags behind.
    """
    path = (meta or {}).get("image") or seo(config).get("defaultOgImage") or DEFAULT_OG_IMAGE
    entry = {}
    if IMAGES_FILE.exists():
        entry = json.loads(IMAGES_FILE.read_text(encoding="utf-8")).get(path, {})
    if not entry:
        return ""
    alt = (entry.get("alt") or {}).get(lang) or (entry.get("alt") or {}).get("en", "")
    tags = ['<meta property="og:image:width" content="%d">' % int(entry["width"]),
            '<meta property="og:image:height" content="%d">' % int(entry["height"])]
    if alt:
        tags.append('<meta property="og:image:alt" content="%s">' % esc(alt))
    return "\n    ".join(tags)


def organization_node(config: dict) -> dict:
    settings = seo(config)
    node = {
        "@type": "Organization",
        "@id": origin(config) + "/#organization",
        "name": settings.get("orgName") or "Agentmux",
        "url": origin(config) + "/",
    }
    logo = settings.get("logo")
    if logo:
        node["logo"] = {
            "@type": "ImageObject",
            "url": absolute_url(config, logo),
            "width": settings.get("logoWidth", 192),
            "height": settings.get("logoHeight", 192),
        }
    if settings.get("supportEmail"):
        node["email"] = settings["supportEmail"]
    same_as = settings.get("sameAs") or [
        config["site"].get("appStoreUrl"),
        config["site"].get("playStoreUrl"),
    ]
    same_as = [url for url in same_as if url]
    if same_as:
        node["sameAs"] = same_as
    return node


def website_node(config: dict) -> dict:
    return {
        "@type": "WebSite",
        "@id": origin(config) + "/#website",
        "url": origin(config) + "/",
        "name": seo(config).get("orgName") or "Agentmux",
        "publisher": {"@id": origin(config) + "/#organization"},
    }


def breadcrumb_node(config: dict, items: list) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": position, "name": name, "item": url}
            for position, (name, url) in enumerate(items, 1)
        ],
    }


def script_block(payload) -> str:
    """One <script> per page holding an @graph. One block rather than several
    keeps the head readable and keeps the build's own JSON extraction simple."""
    body = json.dumps(
        {"@context": "https://schema.org", "@graph": payload}
        if isinstance(payload, list)
        else payload,
        ensure_ascii=False,
    )
    # A literal `</script>` inside a JSON string would close the tag early.
    body = body.replace("</", "<\\/")
    return '<script type="application/ld+json">{0}</script>'.format(body)


def strip_tags(markup: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", str(markup))
    text = re.sub(r"(?i)<br\s*/?>", " ", text)
    text = TAG.sub("", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


_DATE_CACHE = {}


def _git_date(path: Path, extra_args: list) -> str:
    key = "|".join(extra_args) + "|" + str(path)
    if key in _DATE_CACHE:
        return _DATE_CACHE[key]
    date = ""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short"]
            + extra_args
            + ["--", str(path)],
            cwd=str(path.parent),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            lines = [line for line in result.stdout.splitlines() if DATE_TEXT.match(line)]
            # `--diff-filter=A` lists commits newest first, so the commit that
            # first added the file is the last one.
            if lines:
                date = lines[-1] if "A" in extra_args else lines[0]
    except (OSError, subprocess.SubprocessError):
        date = ""
    _DATE_CACHE[key] = date
    return date


def modified_date(path: Path) -> str:
    """Date of the last commit that touched `path`, '' when git is unavailable."""
    if not path or not Path(path).exists():
        return ""
    return _git_date(Path(path), [])


def added_date(path: Path) -> str:
    """Date of the commit that first added `path`."""
    if not path or not Path(path).exists():
        return ""
    return _git_date(Path(path), ["--diff-filter=A"])


def latest_date(*paths: Path) -> str:
    dates = [date for date in (modified_date(path) for path in paths) if date]
    return max(dates) if dates else ""


def fallback_date(config: dict) -> str:
    """Used when git is unavailable (tarball build, no history) so the sitemap
    still carries a lastmod rather than silently dropping the field."""
    return seo(config).get("fallbackUpdated", "")


def article_dates(config: dict, src: Path, lang: str, slug: str) -> tuple:
    """(datePublished, dateModified) for one article. The copy under strings/
    counts as an update too — a reworded headline is a real change."""
    content = src / "content" / slug / "{0}.html".format(lang) if src else None
    strings = src / "strings" / "{0}.json".format(lang) if src else None
    if not content or not content.exists():
        return ("", "")
    published = added_date(content) or latest_date(content)
    modified = latest_date(content, strings) or modified_date(content)
    if not published and not modified:
        # No git history (tarball build, fresh shallow clone). Fall back to the
        # date in config so the field is present rather than missing.
        stamp = fallback_date(config)
        return (stamp, stamp)
    if not published:
        published = modified
    if not modified:
        modified = published
    return (published, modified)


def faq_nodes(config: dict, slug: str, content: str) -> list:
    """FAQPage entries read straight out of the article body.

    Google only accepts FAQ markup that mirrors visible text, so the question is
    the article's own <h2> and the answer is the paragraph under its "Fix" (or
    first) sub-heading — nothing is invented here.
    """
    wanted = [heading.lower() for heading in seo(config).get("faqAnswerHeadings", FAQ_ANSWER_HEADINGS)]
    questions = []
    for heading, body in H2_SECTION.findall(content):
        question = strip_tags(heading)
        if not question:
            continue
        blocks = H3_HEAD.findall(body)
        answer = ""
        for sub_heading, text in blocks:
            if strip_tags(sub_heading).lower() in wanted:
                answer = strip_tags(text)
                break
        if not answer:
            paragraph = re.search(r"<p\b[^>]*>(.*?)</p>", body, re.DOTALL | re.IGNORECASE)
            answer = strip_tags(paragraph.group(1)) if paragraph else ""
        # A CJK answer of twenty characters already says something; the same
        # bar measured in English letters would need forty.
        if len(answer) < int(seo(config).get("faqAnswerMinChars", 20)):
            continue
        # Keep the answer a verbatim prefix of what the reader actually sees —
        # long enough to answer the question, short enough that the JSON-LD does
        # not double the size of the page it sits on.
        limit = int(seo(config).get("faqAnswerMaxChars", 520))
        if len(answer) > limit:
            cut = answer[:limit]
            boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("。"), cut.rfind("；"), cut.rfind("，"))
            answer = cut[: boundary + 1].strip() if boundary > limit // 2 else cut.rstrip() + "…"
        questions.append({"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": answer}})
    return questions


def article_jsonld(
    config: dict,
    lang: str,
    slug: str,
    meta: dict,
    strings: dict = None,
    content: str = "",
    dates: tuple = ("", ""),
) -> str:
    url = article_url(config["site"]["origin"], lang, slug)
    ui = (strings or {}).get("ui", {})
    node = {
        "@context": "https://schema.org",
        "@type": "HowTo" if slug == "setup" else "Article",
        "headline": meta["title"],
        "description": meta["description"],
        "inLanguage": lang,
        "mainEntityOfPage": url,
        "url": url,
        "image": [og_image(config, meta)],
        "author": organization_node(config),
        "publisher": organization_node(config),
        "isPartOf": {"@id": origin(config) + "/#website"},
    }
    published, modified = dates
    if published:
        node["datePublished"] = published
    if modified:
        node["dateModified"] = modified

    graph = [node, breadcrumb_node(config, guide_trail(config, strings, lang, slug))]
    if slug in seo(config).get("faqSlugs", FAQ_SLUGS) and content:
        questions = faq_nodes(config, slug, content)
        if questions:
            graph.append(
                {
                    "@type": "FAQPage",
                    "inLanguage": lang,
                    "mainEntity": questions,
                }
            )
    return script_block(graph)


def guide_trail(config: dict, strings: dict, lang: str, slug: str = None) -> list:
    """(name, url) pairs for the breadcrumb of one article or one guide index."""
    ui = (strings or {}).get("ui", {})
    trail = [
        (ui.get("home") or "Home", origin(config) + "/"),
        (ui.get("guideRoot") or "Agentmux Guide", origin(config) + "/guide/"),
        (ui.get("guideHome") or "Guide", "{0}/guide/{1}/".format(origin(config), lang)),
    ]
    if slug:
        title = ((strings or {}).get("articles", {}).get(slug) or {}).get("title")
        trail.append((title or slug, article_url(config["site"]["origin"], lang, slug)))
    return trail


def collection_jsonld(
    config: dict,
    lang: str,
    title: str,
    description: str,
    slugs: list,
    strings: dict,
    date_modified: str = "",
) -> str:
    url = "{0}/guide/{1}/".format(origin(config), lang)
    items = [
        {
            "@type": "ListItem",
            "position": position,
            "url": article_url(config["site"]["origin"], lang, slug),
            "name": strings["articles"][slug]["title"],
        }
        for position, slug in enumerate(slugs, 1)
    ]
    return script_block(
        [
            {
                "@type": "CollectionPage",
                "name": title,
                "description": description,
                "url": url,
                "inLanguage": lang,
                "dateModified": date_modified or fallback_date(config),
                "isPartOf": {"@id": origin(config) + "/#website"},
                "publisher": organization_node(config),
                "hasPart": {"@type": "ItemList", "itemListElement": items},
            },
            breadcrumb_node(config, guide_trail(config, strings, lang)),
        ]
    )


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


def wrap_tables(fragment: str) -> str:
    """Put every table inside a scroll container.

    site.css sets `body { overflow-x: hidden }`, so a table wider than the
    viewport is clipped and its far columns become unreachable rather than
    scrollable. The scroll container has to be a separate element whose width
    the parent constrains — putting overflow on the table itself does nothing,
    because `min-width` widens that same box. Doing this at build time keeps it
    off the content author's checklist.
    """

    def wrap(match):
        table = match.group(0)
        if 'class="table-wrap"' in fragment[max(0, match.start() - 120):match.start()]:
            return table
        return '<div class="table-wrap">' + table + "</div>"

    return TABLE.sub(wrap, fragment)


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


def index_hreflang_block(config: dict, lang: str = None) -> str:
    """hreflang for the two guide index pages, which have language siblings
    rather than article siblings."""
    base = "{0}/guide/".format(origin(config))
    lines = [
        '<link rel="alternate" hreflang="{0}" href="{1}{2}/">'.format(code, base, code)
        for code in [entry["code"] for entry in config["languages"]]
        if config.get("content", {}).get(code)
    ]
    lines.append('<link rel="alternate" hreflang="x-default" href="{0}">'.format(base))
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


def _pager(config: dict, strings: dict, lang: str, slug: str) -> str:
    tracks = track_of(config, slug)
    if not tracks:
        return ""
    available = set(config.get("content", {}).get(lang, []))

    # 一篇文章可以同時屬於多條 track，每條 track 的鄰居未必相同。先收集所有
    # 鄰居（同一個目標只留一張卡，但記住是哪幾條 track 指向它）。
    entries = []
    by_target = {}
    for track in tracks:
        prev_slug, next_slug = neighbors(config, track, slug)
        for label_key, target in (("prev", prev_slug), ("next", next_slug)):
            if not target or target not in available:
                continue
            if target in by_target:
                entry = by_target[target]
                if track not in entry["tracks"]:
                    entry["tracks"].append(track)
                continue
            entry = {"key": label_key, "target": target, "tracks": [track]}
            by_target[target] = entry
            entries.append(entry)
    if not entries:
        return ""

    # 上面是按 track 逐條收集的，攤平後會變成「上一篇→下一篇→上一篇」。
    # 重排成所有 prev 在前、所有 next 在後，各組內維持 track 的宣告順序。
    entries = [e for e in entries if e["key"] == "prev"] + [
        e for e in entries if e["key"] == "next"
    ]

    # 兩張卡都叫「上一篇」時，光看標籤無從分辨走的是哪條 track，所以只在這種
    # 情況補上路線名稱；不重複的標籤維持乾淨。
    counts = {}
    for entry in entries:
        counts[entry["key"]] = counts.get(entry["key"], 0) + 1

    parts = []
    for entry in entries:
        plain = strings["ui"][entry["key"]]
        label = plain
        if counts[entry["key"]] > 1:
            names = strings["ui"]["listJoin"].join(
                strings["ui"]["tracks"][track]["title"] for track in entry["tracks"]
            )
            label = strings["ui"]["pagerTrackFormat"].format(label, names)
        # data-tracks / data-label 讓 track.js 在讀者選過路線後收掉另一條的卡，
        # 並把標籤還原成不帶路線名的版本。沒有 JS 時看到的就是上面的完整標籤。
        parts.append(
            '<a class="pager-{0}" data-tracks="{1}" data-label="{2}"'
            ' href="/guide/{3}/{4}/">{5}<span>{6}</span></a>'.format(
                entry["key"],
                esc(" ".join(entry["tracks"])),
                esc(plain),
                lang,
                entry["target"],
                esc(label),
                esc(strings["articles"][entry["target"]]["title"]),
            )
        )
    return '<nav class="guide-pager">' + "".join(parts) + "</nav>"


def build_article(src: Path, out: Path, config: dict, lang: str, slug: str) -> None:
    template = (src / "templates" / "article.html").read_text(encoding="utf-8")
    strings = _load_strings(src, lang)
    meta = strings["articles"][slug]
    fragment = _content_fragment(src, lang, slug)
    published, modified = article_dates(config, src, lang, slug)
    image = og_image(config, meta)
    other_code = "en" if lang == "zh-TW" else "zh-TW"
    other_label = "English" if lang == "zh-TW" else "繁體中文"
    matrix = config.get("content", {})
    if slug in matrix.get(other_code, []):
        other_url = "/guide/{0}/{1}/".format(other_code, slug)
    else:
        other_url = "/guide/{0}/".format(other_code)

    page_vars = {
        "htmlLang": esc(_language(config, lang)["htmlLang"]),
        "lang": esc(lang),
        "title": esc(meta["title"]),
        "description": esc(meta["description"]),
        "canonical": esc(article_url(config["site"]["origin"], lang, slug)),
        "content": wrap_tables(fragment),
        "hreflang": hreflang_block(config, slug),
        "jsonld": article_jsonld(config, lang, slug, meta, strings, fragment, (published, modified)),
        "ogTitle": esc(meta["title"]),
        "ogDescription": esc(meta["description"]),
        "ogUrl": esc(article_url(config["site"]["origin"], lang, slug)),
        "ogImage": esc(image),
        "ogImageExtras": image_tags(config, meta, lang),
        "ogLocale": esc(seo(config).get("ogLocale", {}).get(lang, "en_US")),
        "ogSiteName": esc(seo(config).get("orgName") or "Agentmux"),
        "publishedDate": esc(published),
        "modifiedDate": esc(modified or published),
        "guideHomeLabel": esc(strings["ui"]["guideHome"]),
        "troubleshootingLabel": esc(strings["ui"]["troubleshooting"]),
        "homeLabel": esc(strings["ui"].get("home", "首頁" if lang == "zh-TW" else "Home")),
        "privacyLabel": esc(strings["ui"].get("privacy", "隱私政策" if lang == "zh-TW" else "Privacy")),
        "supportLabel": esc(strings["ui"].get("support", "技術支援" if lang == "zh-TW" else "Support")),
        "otherLangUrl": esc(other_url),
        "otherLangLabel": esc(other_label),
        "appStoreUrl": esc(config["site"]["appStoreUrl"]),
        "playStoreUrl": esc(config["site"].get("playStoreUrl", "https://play.google.com/store/apps/details?id=cc.saxcave.agentmux")),
        "ctaLine": esc(strings["ui"]["ctaLine"]),
        "ctaButton": esc(strings["ui"]["ctaButton"]),
        "ctaAppStore": esc(strings["ui"].get("ctaAppStore", strings["ui"]["ctaButton"])),
        "ctaPlayStore": esc(strings["ui"].get("ctaPlayStore", "Google Play")),
        "pager": _pager(config, strings, lang, slug),
    }
    target = article_path(out, lang, slug)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(template, page_vars), encoding="utf-8")


def build_root_index(src: Path, out: Path, config: dict) -> None:
    template = (src / "templates" / "root-index.html").read_text(encoding="utf-8")
    settings = seo(config)
    title = settings.get("guideRootTitle") or "Agentmux Guide"
    description = settings.get("guideRootDescription") or (
        "Learn SSH, Tailscale, and CLI coding agents — then run them from your phone."
    )
    links = "\n        ".join(
        '<a class="lang-card" href="/guide/{0}/" hreflang="{0}">{1}</a>'.format(
            lang["code"], esc(lang["label"])
        )
        for lang in config["languages"]
        if config.get("content", {}).get(lang["code"])
    )
    items = [
        {
            "@type": "ListItem",
            "position": position,
            "url": "{0}/guide/{1}/".format(origin(config), lang["code"]),
            "name": "{0} — {1}".format(title, lang["label"]),
            "inLanguage": lang["code"],
        }
        for position, lang in enumerate(
            [entry for entry in config["languages"] if config.get("content", {}).get(entry["code"])],
            1,
        )
    ]
    jsonld = script_block(
        [
            organization_node(config),
            website_node(config),
            {
                "@type": "CollectionPage",
                "name": title,
                "description": description,
                "url": "{0}/guide/".format(origin(config)),
                "inLanguage": [entry["code"] for entry in config["languages"]],
                "dateModified": (
                    latest_date(src / "templates" / "root-index.html", Path(__file__))
                    or fallback_date(config)
                ),
                "isPartOf": {"@id": origin(config) + "/#website"},
                "publisher": organization_node(config),
                "hasPart": {"@type": "ItemList", "itemListElement": items},
            },
        ]
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        render(
            template,
            {
                "languageLinks": links,
                "origin": config["site"]["origin"],
                "title": esc(title),
                "description": esc(description),
                "hreflang": index_hreflang_block(config),
                "jsonld": jsonld,
                "ogTitle": esc(title),
                "ogDescription": esc(description),
                "ogUrl": esc("{0}/guide/".format(origin(config))),
                "ogImage": esc(og_image(config)),
                "ogImageExtras": image_tags(config, {}, "en"),
                "ogLocale": esc(settings.get("ogLocale", {}).get("en", "en_US")),
                "ogSiteName": esc(settings.get("orgName") or "Agentmux"),
            },
        ),
        encoding="utf-8",
    )


def build_track_index(src: Path, out: Path, config: dict, lang: str) -> None:
    template = (src / "templates" / "track-index.html").read_text(encoding="utf-8")
    strings = _load_strings(src, lang)
    available = set(config.get("content", {}).get(lang, []))
    extended_matrix = config.get("trackExtended", {})
    other_code = "en" if lang == "zh-TW" else "zh-TW"
    other_label = "English" if lang == "zh-TW" else "繁體中文"
    other_url = "/guide/{0}/".format(other_code)
    blocks = []
    for track_name, slugs in config["tracks"].items():
        track_strings = strings["ui"]["tracks"][track_name]
        items = "\n            ".join(
            '<li><a data-track="{0}" href="/guide/{1}/{2}/">{3}</a></li>'.format(
                esc(track_name), lang, slug, esc(strings["articles"][slug]["title"])
            )
            for slug in slugs
            if slug in available
        )
        extended_slugs = [s for s in extended_matrix.get(track_name, []) if s in available]
        extended_html = ""
        if extended_slugs:
            extended_links = strings["ui"]["listJoin"].join(
                '<a data-track="{0}" href="/guide/{1}/{2}/">{3}</a>'.format(
                    esc(track_name), lang, slug, esc(strings["articles"][slug]["title"])
                )
                for slug in extended_slugs
            )
            extended_html = '\n          <p class="track-extended"><strong>{0}{1}</strong>{2}</p>'.format(
                esc(strings["ui"]["extendedReading"]),
                esc(strings["ui"]["labelColon"]),
                extended_links,
            )
        blocks.append(
            '<section class="track" id="{0}">\n'
            "          <h2>{1}</h2>\n"
            "          <p>{2}</p>\n"
            "          <ol>\n            {3}\n          </ol>{4}\n"
            "        </section>".format(
                track_name,
                esc(track_strings["title"]),
                esc(track_strings["blurb"]),
                items,
                extended_html,
            )
        )
    target = out / lang / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    reading_order = [slug for slug in config["slugs"] if slug in available]
    target.write_text(
        render(
            template,
            {
                "htmlLang": esc(_language(config, lang)["htmlLang"]),
                "lang": esc(lang),
                "title": esc(strings["ui"]["trackIndexTitle"]),
                "description": esc(strings["ui"]["trackIndexDescription"]),
                "canonical": esc(
                    "{0}/guide/{1}/".format(config["site"]["origin"].rstrip("/"), lang)
                ),
                "hreflang": index_hreflang_block(config),
                "jsonld": collection_jsonld(
                    config,
                    lang,
                    strings["ui"]["trackIndexTitle"],
                    strings["ui"]["trackIndexDescription"],
                    reading_order,
                    strings,
                    latest_date(
                        src / "templates" / "track-index.html",
                        src / "strings" / "{0}.json".format(lang),
                    )
                    or fallback_date(config),
                ),
                "ogTitle": esc(strings["ui"]["trackIndexTitle"]),
                "ogDescription": esc(strings["ui"]["trackIndexDescription"]),
                "ogUrl": esc("{0}/guide/{1}/".format(origin(config), lang)),
                "ogImage": esc(og_image(config)),
                "ogImageExtras": image_tags(config, {}, lang),
                "ogLocale": esc(seo(config).get("ogLocale", {}).get(lang, "en_US")),
                "ogSiteName": esc(seo(config).get("orgName") or "Agentmux"),
                "tracks": "\n        ".join(blocks),
                "guideHomeLabel": esc(strings["ui"]["guideHome"]),
                "troubleshootingLabel": esc(strings["ui"]["troubleshooting"]),
                "homeLabel": esc(strings["ui"].get("home", "首頁" if lang == "zh-TW" else "Home")),
                "privacyLabel": esc(strings["ui"].get("privacy", "隱私政策" if lang == "zh-TW" else "Privacy")),
                "supportLabel": esc(strings["ui"].get("support", "技術支援" if lang == "zh-TW" else "Support")),
                "otherLangUrl": esc(other_url),
                "otherLangLabel": esc(other_label),
            },
        ),
        encoding="utf-8",
    )


def build_sitemap(out_root: Path, config: dict, src: Path = None) -> None:
    origin = config["site"]["origin"].rstrip("/")
    fallback = fallback_date(config)
    web_root = out_root if src is None else src.parent

    def stamp(*paths: Path) -> str:
        return latest_date(*paths) or fallback

    urls = [("{0}/".format(origin), stamp(web_root / "index.source.html", web_root / "build_home.py"))]
    for code in ("zh-TW", "zh-Hans", "ja"):
        urls.append(
            (
                "{0}/{1}/".format(origin, code),
                stamp(web_root / "index.source.html", web_root / "build_home.py"),
            )
        )
    urls.append(("{0}/privacy.html".format(origin), stamp(web_root / "privacy.html")))
    guide_src = src if src is not None else web_root / "guide-src"
    root_template = guide_src / "templates" / "root-index.html"
    track_template = guide_src / "templates" / "track-index.html"
    urls.append(("{0}/guide/".format(origin), stamp(root_template, guide_src / "build.py")))
    matrix = config.get("content", {})
    for lang in config["languages"]:
        code = lang["code"]
        if not matrix.get(code):
            continue
        strings_file = guide_src / "strings" / "{0}.json".format(code)
        urls.append(("{0}/guide/{1}/".format(origin, code), stamp(track_template, strings_file)))
        for slug in config["slugs"]:
            if slug in matrix[code]:
                published, modified = article_dates(config, guide_src, code, slug)
                urls.append((article_url(origin, code, slug), modified or published or fallback))
    body = "\n".join(
        "  <url><loc>{0}</loc>{1}</url>".format(
            url, "<lastmod>{0}</lastmod>".format(stamp_value) if stamp_value else ""
        )
        for url, stamp_value in urls
    )
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body
        + "\n</urlset>\n",
        encoding="utf-8",
    )


def pre_text(markup: str) -> str:
    """Text of a <pre> block with its line structure intact — strip_tags would
    fold a six-line install recipe onto one line."""
    text = html.unescape(TAG.sub("", markup))
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip("\n")


def table_to_markdown(table_html: str) -> str:
    """A real markdown table. Cell text is flattened to one line, which is what
    makes a comparison table answerable from plain text."""
    rows = re.findall(r"(?is)<tr\b[^>]*>(.*?)</tr>", table_html)
    lines = []
    for index, row in enumerate(rows):
        cells = [strip_tags(cell) for cell in re.findall(r"(?is)<t[hd]\b[^>]*>(.*?)</t[hd]>", row)]
        cells = [cell for cell in cells if cell]
        if not cells:
            continue
        lines.append("| " + " | ".join(cells) + " |")
        if index == 0:
            lines.append("|" + "|".join([" --- "] * len(cells)) + "|")
    return "\n" + "\n".join(lines) + "\n" if lines else table_html


def html_to_markdown(fragment: str) -> str:
    """Markdown for llms-full.txt.

    Answer engines summarise a page far more faithfully from plain prose than
    from markup, so the guide is published as text as well as HTML. This stays
    deliberately small — the content files use headings, paragraphs, lists,
    tables, and code blocks, and nothing else."""
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", fragment)
    text = TABLE.sub(lambda match: table_to_markdown(match.group(0)), text)
    text = re.sub(
        r"(?is)<pre[^>]*>(.*?)</pre>",
        lambda match: "\n```\n{0}\n```\n".format(pre_text(match.group(1))),
        text,
    )
    for level in ("h1", "h2", "h3", "h4"):
        text = re.sub(
            r"(?i)<{0}[^>]*>(.*?)</{0}>".format(level),
            lambda match, marks="#" * int(level[1]): "\n\n{0} {1}\n\n".format(
                marks, strip_tags(match.group(1))
            ),
            text,
        )
    text = re.sub(r"(?i)<li\b[^>]*>", "\n- ", text)
    text = re.sub(r"(?i)<(strong|b)\b[^>]*>", "**", text)
    text = re.sub(r"(?i)</(strong|b)>", "**", text)
    text = re.sub(r"(?i)<(em|i)\b[^>]*>", "*", text)
    text = re.sub(r"(?i)</(em|i)>", "*", text)
    text = re.sub(r"(?i)<code\b[^>]*>", "`", text)
    text = re.sub(r"(?i)</code>", "`", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|ul|ol|table|section|blockquote|article)>", "\n\n", text)
    text = TAG.sub("", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # The source HTML is indented for readability; that indentation is not part
    # of the prose. Fenced code keeps its own leading whitespace.
    parts = text.split("```")
    parts = [
        part if index % 2 else re.sub(r"(?m)^[ \t]+", "", part) for index, part in enumerate(parts)
    ]
    return "```".join(parts).strip()


def _language_order(config: dict) -> list:
    """English first: it is the x-default locale, so it is the one an answer
    engine is most likely to read. The rest keep config order."""
    codes = [entry["code"] for entry in config["languages"]]
    ordered = [code for code in codes if code == "en"] + [code for code in codes if code != "en"]
    by_code = {entry["code"]: entry for entry in config["languages"]}
    return [by_code[code] for code in ordered]


def _guide_llms_section(config: dict, strings: dict, code: str, slugs: list, label: str) -> list:
    lines = ["## Guide ({0})".format(label), ""]
    for slug in slugs:
        meta = strings["articles"][slug]
        lines.append(
            "- [{0}]({1}): {2}".format(
                meta["title"],
                article_url(config["site"]["origin"], code, slug),
                meta["description"],
            )
        )
    lines.append("")
    return lines


def build_llms_txt(web_root: Path, src: Path, config: dict) -> None:
    """llms.txt: a plain-text table of contents for answer engines.

    Generated from the same strings and content matrix the site is built from,
    so it cannot drift out of step with the guide."""
    settings = seo(config)
    facts = settings.get("llms", {})
    origin_base = origin(config)
    lines = ["# " + (facts.get("title") or "Agentmux"), ""]
    if facts.get("summary"):
        lines += ["> " + facts["summary"], ""]
    for note in facts.get("notes", []):
        lines.append(note)
    if facts.get("notes"):
        lines.append("")
    lines += [
        "App Store: {0}".format(config["site"].get("appStoreUrl", "")),
        "Google Play: {0}".format(
            config["site"].get(
                "playStoreUrl", "https://play.google.com/store/apps/details?id=cc.saxcave.agentmux"
            )
        ),
        "Support: mailto:{0}".format(settings.get("supportEmail", "")),
        "Full guide text (all languages, one file): {0}/llms-full.txt".format(origin_base),
        "",
    ]

    homes = facts.get("home", [])
    if homes:
        lines += ["## Home", ""]
        for entry in homes:
            lines.append(
                "- [{0}]({1}): {2}".format(
                    entry["name"], origin_base + entry["path"], entry["description"]
                )
            )
        lines.append("")

    matrix = config.get("content", {})
    for lang_entry in _language_order(config):
        code = lang_entry["code"]
        slugs = [slug for slug in config["slugs"] if slug in matrix.get(code, [])]
        if not slugs:
            continue
        strings = _load_strings(src, code)
        lines += _guide_llms_section(config, strings, code, slugs, lang_entry["label"])

    default_code = (
        "en"
        if any(entry["code"] == "en" for entry in config["languages"])
        else config["languages"][0]["code"]
    )
    lines += [
        "## Support and legal",
        "",
        "- [Privacy Policy]({0}/privacy.html): what Agentmux does and does not collect.".format(
            origin_base
        ),
        "- [Setup guide]({0}/guide/{1}/setup/): install steps for the agent runtime.".format(
            origin_base, default_code
        ),
        "",
    ]
    (web_root / "llms.txt").write_text("\n".join(lines), encoding="utf-8")


def build_llms_full(web_root: Path, src: Path, config: dict) -> None:
    """llms-full.txt: the whole guide as text, so a model can answer from the
    source instead of a search snippet."""
    settings = seo(config)
    facts = settings.get("llms", {})
    matrix = config.get("content", {})
    origin_base = origin(config)
    blocks = [
        "# " + (facts.get("title") or "Agentmux"),
        "",
        facts.get("summary", ""),
        "",
        "Source: {0}/  |  App Store: {1}  |  Google Play: {2}".format(
            origin_base,
            config["site"].get("appStoreUrl", ""),
            config["site"].get(
                "playStoreUrl", "https://play.google.com/store/apps/details?id=cc.saxcave.agentmux"
            ),
        ),
        "",
    ]
    for lang_entry in _language_order(config):
        code = lang_entry["code"]
        slugs = [slug for slug in config["slugs"] if slug in matrix.get(code, [])]
        if not slugs:
            continue
        strings = _load_strings(src, code)
        blocks += ["", "---", "", "# Guide — {0}".format(lang_entry["label"]), ""]
        for slug in slugs:
            meta = strings["articles"][slug]
            url = article_url(origin_base, code, slug)
            blocks += [
                "## {0}".format(meta["title"]),
                "",
                "URL: {0}".format(url),
                "Language: {0}".format(code),
                "Updated: {0}".format(article_dates(config, src, code, slug)[1]),
                "",
                meta["description"],
                "",
                html_to_markdown(_content_fragment(src, code, slug)),
                "",
            ]
    (web_root / "llms-full.txt").write_text("\n".join(blocks).rstrip() + "\n", encoding="utf-8")


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

    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "wizard.js", assets / "wizard.js")
    shutil.copy(src / "wizard" / "steps.json", assets / "steps.json")
    for lang in config["languages"]:
        wstrings = src / "wizard" / "strings" / "{0}.json".format(lang["code"])
        if wstrings.exists():
            shutil.copy(wstrings, assets / "wizard-{0}.json".format(lang["code"]))

    build_root_index(src, out, config)
    build_sitemap(web_root, config, src)
    build_llms_txt(web_root, src, config)
    build_llms_full(web_root, src, config)
    print("built {0} language(s)".format(len([l for l in config["languages"] if matrix.get(l["code"])])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
