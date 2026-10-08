#!/usr/bin/env python3
"""
Build localized homepages for Agentmux.
Reads index.source.html and generates:
  - index.html (English / root)
  - zh-TW/index.html (Traditional Chinese)
  - zh-Hans/index.html (Simplified Chinese)
  - ja/index.html (Japanese)
  - en/index.html (redirect to root)
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent

LANG_CONFIG = {
    "en": {
        "html_lang": "en",
        "title": "Agentmux - Run SSH, tmux & Claude Code on iOS & Android",
        "description": "Mobile command center for remote projects: SSH, persistent tmux sessions, file editing, and AI coding agents like Claude Code, Codex, and OpenCode on iPhone, iPad, and Android.",
        "canonical": "https://agentmux.saxcave.cc/",
        "out_dir": "",
        "guide_href": "/guide/en/",
        "privacy_href": "/privacy.html?lang=en",
    },
    "zh-TW": {
        "html_lang": "zh-TW",
        "title": "Agentmux - 在 iPhone、iPad 上掌控 SSH、tmux 與 Claude Code",
        "description": "專為行動裝置打造的 SSH 與 tmux 工具：在 iPhone、iPad 上執行 Claude Code、Codex 等 AI Coding Agents，斷線自動重連，隨時推進遠端專案。",
        "canonical": "https://agentmux.saxcave.cc/zh-TW/",
        "out_dir": "zh-TW",
        "guide_href": "/guide/zh-TW/",
        "privacy_href": "/privacy.html?lang=zh-TW",
    },
    "zh-Hans": {
        "html_lang": "zh-Hans",
        "title": "Agentmux - 在 iPhone、iPad 与 Android 上掌控 SSH、tmux 与 Claude Code",
        "description": "专为移动端打造的 SSH 与 tmux 工具：在 iPhone、iPad 上运行 Claude Code、Codex 等 AI 编码智能体，断线自动重连，随时推进远程项目。",
        "canonical": "https://agentmux.saxcave.cc/zh-Hans/",
        "out_dir": "zh-Hans",
        "guide_href": "/guide/zh-TW/",
        "privacy_href": "/privacy.html?lang=zh-Hans",
    },
    "ja": {
        "html_lang": "ja",
        "title": "Agentmux - iPhone・iPad から SSH・tmux・Claude Code を操作",
        "description": "スマホやタブレットで快適に動く SSH & tmux クライアント。外出先でも iPhone・iPad から Claude Code やコーディングエージェントの作業をそのまま継続できます。",
        "canonical": "https://agentmux.saxcave.cc/ja/",
        "out_dir": "ja",
        "guide_href": "/guide/en/",
        "privacy_href": "/privacy.html?lang=ja",
    },
}


def extract_lang_spans(text: str):
    """Extract all span elements with data-lang attributes, handling nesting."""
    results = []
    idx = 0
    while True:
        m = re.search(r'<span([^>]*data-lang="([^"]+)"[^>]*)>', text[idx:])
        if not m:
            break
        start_pos = idx + m.start()
        attrs = m.group(1)
        lang = m.group(2)
        content_start = idx + m.end()

        depth = 1
        curr = content_start
        while depth > 0 and curr < len(text):
            next_open = text.find("<span", curr)
            next_close = text.find("</span>", curr)
            if next_close == -1:
                break
            if next_open != -1 and next_open < next_close:
                depth += 1
                curr = next_open + 5
            else:
                depth -= 1
                if depth == 0:
                    results.append((start_pos, next_close + 7, attrs, lang, text[content_start:next_close]))
                    idx = next_close + 7
                    break
                curr = next_close + 7
        if depth > 0:
            break
    return results


def make_lang_buttons(current_lang: str) -> str:
    langs = [
        ("en", "EN", "/"),
        ("zh-TW", "繁中", "/zh-TW/"),
        ("zh-Hans", "简中", "/zh-Hans/"),
        ("ja", "日本語", "/ja/"),
    ]
    lines = []
    for code, label, path in langs:
        active_cls = " active" if code == current_lang else ""
        lines.append(
            f'<a class="lang-btn{active_cls}" href="{path}" hreflang="{code}" onclick="localStorage.setItem(\'preferred-lang\', \'{code}\')">{label}</a>'
        )
    return "\n                ".join(lines)


def make_hreflangs() -> str:
    return (
        '    <link rel="alternate" hreflang="x-default" href="https://agentmux.saxcave.cc/">\n'
        '    <link rel="alternate" hreflang="en" href="https://agentmux.saxcave.cc/">\n'
        '    <link rel="alternate" hreflang="zh-TW" href="https://agentmux.saxcave.cc/zh-TW/">\n'
        '    <link rel="alternate" hreflang="zh-Hans" href="https://agentmux.saxcave.cc/zh-Hans/">\n'
        '    <link rel="alternate" hreflang="ja" href="https://agentmux.saxcave.cc/ja/">'
    )


def make_script(target_lang: str) -> str:
    if target_lang == "en":
        return """    <script>
        function setupNavCta() {
            const navCta = document.getElementById('nav-download-btn');
            if (!navCta) return;
            const ua = navigator.userAgent || '';
            if (/Android/i.test(ua)) {
                navCta.href = 'https://play.google.com/store/apps/details?id=cc.saxcave.agentmux';
                navCta.target = '_blank';
                navCta.rel = 'noopener noreferrer';
            } else if (/iPhone|iPad|iPod/i.test(ua)) {
                navCta.href = 'https://apps.apple.com/app/id6766158521';
                navCta.target = '_blank';
                navCta.rel = 'noopener noreferrer';
            } else {
                navCta.href = '#download';
            }
        }

        window.addEventListener('load', () => {
            setupNavCta();
            const params = new URLSearchParams(window.location.search);
            const qLang = params.get('lang');
            if (qLang === 'zh-TW') return location.replace('/zh-TW/');
            if (qLang === 'zh-Hans') return location.replace('/zh-Hans/');
            if (qLang === 'ja') return location.replace('/ja/');
            if (qLang === 'en') return location.replace('/');

            const saved = localStorage.getItem('preferred-lang');
            if (saved) {
                if (saved === 'zh-TW') return location.replace('/zh-TW/');
                if (saved === 'zh-Hans') return location.replace('/zh-Hans/');
                if (saved === 'ja') return location.replace('/ja/');
                if (saved === 'en') return;
            }
            const nav = (navigator.language || '').toLowerCase();
            if (nav.startsWith('zh-tw') || nav.startsWith('zh-hk') || nav.startsWith('zh-mo') || nav.startsWith('zh-hant')) {
                location.replace('/zh-TW/');
            } else if (nav.startsWith('zh')) {
                location.replace('/zh-Hans/');
            } else if (nav.startsWith('ja')) {
                location.replace('/ja/');
            }
        });
    </script>"""
    else:
        return f"""    <script>
        function setupNavCta() {{
            const navCta = document.getElementById('nav-download-btn');
            if (!navCta) return;
            const ua = navigator.userAgent || '';
            if (/Android/i.test(ua)) {{
                navCta.href = 'https://play.google.com/store/apps/details?id=cc.saxcave.agentmux';
                navCta.target = '_blank';
                navCta.rel = 'noopener noreferrer';
            }} else if (/iPhone|iPad|iPod/i.test(ua)) {{
                navCta.href = 'https://apps.apple.com/app/id6766158521';
                navCta.target = '_blank';
                navCta.rel = 'noopener noreferrer';
            }} else {{
                navCta.href = '#download';
            }}
        }}

        window.addEventListener('load', () => {{
            setupNavCta();
            localStorage.setItem('preferred-lang', '{target_lang}');
        }});
    </script>"""


def build_lang_page(source_html: str, lang: str, cfg: dict) -> str:
    # 1. Normalize resource paths to root-absolute
    html = re.sub(r'(src|href|poster)="resource/', r'\1="/resource/', source_html)

    # 2. Extract and replace spans
    spans = extract_lang_spans(html)
    buf = list(html)
    for start, end, attrs, span_lang, inner in reversed(spans):
        if span_lang == lang:
            if "cta-label-long" in attrs:
                replacement = f'<span class="cta-label-long active">{inner}</span>'
            elif "cta-label-short" in attrs:
                replacement = f'<span class="cta-label-short active">{inner}</span>'
            else:
                replacement = f'<span class="active">{inner}</span>'
        else:
            replacement = ""
        buf[start:end] = list(replacement)
    html = "".join(buf)

    # 3. Replace <html lang="...">
    html = re.sub(r'<html\s+lang="[^"]*">', f'<html lang="{cfg["html_lang"]}">', html, count=1)

    # 4. Replace Head metadata: title, description, canonical, hreflangs, og, twitter
    html = re.sub(r'<title>.*?</title>', f'<title>{cfg["title"]}</title>', html, count=1)
    html = re.sub(r'<meta id="meta-description" name="description" content="[^"]*">',
                  f'<meta id="meta-description" name="description" content="{cfg["description"]}">', html, count=1)
    html = re.sub(r'<link rel="canonical" href="[^"]*">',
                  f'<link rel="canonical" href="{cfg["canonical"]}">', html, count=1)

    hreflang_pattern = re.compile(r'<link rel="alternate" hreflang="[^"]*" href="[^"]*">\s*', re.DOTALL)
    html = hreflang_pattern.sub('', html)
    html = html.replace(f'<link rel="canonical" href="{cfg["canonical"]}">',
                        f'<link rel="canonical" href="{cfg["canonical"]}">\n' + make_hreflangs())

    html = re.sub(r'<meta id="og-title" property="og:title" content="[^"]*">',
                  f'<meta id="og-title" property="og:title" content="{cfg["title"]}">', html, count=1)
    html = re.sub(r'<meta id="og-description" property="og:description" content="[^"]*">',
                  f'<meta id="og-description" property="og:description" content="{cfg["description"]}">', html, count=1)
    html = re.sub(r'<meta property="og:url" content="[^"]*">',
                  f'<meta property="og:url" content="{cfg["canonical"]}">', html, count=1)
    html = re.sub(r'<meta id="twitter-title" name="twitter:title" content="[^"]*">',
                  f'<meta id="twitter-title" name="twitter:title" content="{cfg["title"]}">', html, count=1)
    html = re.sub(r'<meta id="twitter-description" name="twitter:description" content="[^"]*">',
                  f'<meta id="twitter-description" name="twitter:description" content="{cfg["description"]}">', html, count=1)

    # 5. Replace navigation links
    # Guide link
    html = re.sub(r'<a href="/guide/">', f'<a href="{cfg["guide_href"]}">', html, count=1)
    # Privacy links
    html = re.sub(r'<a href="privacy.html">', f'<a href="{cfg["privacy_href"]}">', html)

    # Lang buttons in nav
    button_block_pattern = re.compile(r'<button class="lang-btn[^"]*"[^>]*>.*?</button>\s*', re.DOTALL)
    # Find all button lang-btns and replace with links
    first_btn = html.find('<button class="lang-btn')
    if first_btn != -1:
        last_btn_end = 0
        for m in re.finditer(r'<button class="lang-btn[^"]*"[^>]*>.*?</button>', html):
            last_btn_end = m.end()
        html = html[:first_btn] + make_lang_buttons(lang) + html[last_btn_end:]

    # 6. Replace bottom script block
    script_pattern = re.compile(r'<script>.*?</script>', re.DOTALL)
    scripts = list(script_pattern.finditer(html))
    if scripts:
        last_script = scripts[-1]
        html = html[:last_script.start()] + make_script(lang) + html[last_script.end():]

    # 7. Clean up excessive blank lines from removed multilingual spans
    html = re.sub(r'\n[ \t]*\n([ \t]*\n)+', '\n\n', html)
    html = re.sub(r'([ \t]*\n){2,}([ \t]*</)', r'\n\2', html)

    return html


def build_en_redirect() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=/">
    <link rel="canonical" href="https://agentmux.saxcave.cc/">
    <title>Agentmux</title>
</head>
<body>
    <p>Redirecting to <a href="/">Agentmux</a>...</p>
    <script>location.replace('/');</script>
</body>
</html>
"""


def main():
    source_file = ROOT_DIR / "index.source.html"
    if not source_file.exists():
        raise FileNotFoundError(f"Source file {source_file} does not exist.")

    source_html = source_file.read_text(encoding="utf-8")

    for lang, cfg in LANG_CONFIG.items():
        page_html = build_lang_page(source_html, lang, cfg)
        out_dir = ROOT_DIR / cfg["out_dir"] if cfg["out_dir"] else ROOT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "index.html"
        out_file.write_text(page_html, encoding="utf-8")
        print(f"Generated {out_file.relative_to(ROOT_DIR)} ({lang}) - {len(page_html)} bytes")

    # Generate en/index.html redirect
    en_dir = ROOT_DIR / "en"
    en_dir.mkdir(parents=True, exist_ok=True)
    (en_dir / "index.html").write_text(build_en_redirect(), encoding="utf-8")
    print("Generated en/index.html (redirect to root)")


if __name__ == "__main__":
    main()
