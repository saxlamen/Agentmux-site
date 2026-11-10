# Guide copy: house rules

This file governs the guide only. The home page, the privacy policy, and the
four-language picture live in [`../COPY.md`](../COPY.md).

Everything under `content/<slug>/{en,zh-TW}.html` is a **fragment** — no `<html>`,
`<head>`, `<style>`, `<script>`. The title, `<h1>`, meta description, and og tags
come from `strings/<lang>.json`; the fragment supplies the body only.

## Voice

The guide is an argument, not a feature list. Each section states one claim and
then proves it concretely — with a command, a mechanism, or a physical
consequence. Concrete nouns beat adjectives.

Banned: seamless, powerful, robust, effortless, intuitive, game-changer,
supercharge, streamline, "in today's fast-moving world", "whether you're a
beginner or a pro", exclamation marks, emoji, rhetorical "Let's".

Allowed and used throughout: second person, em-dashes, short declarative
sentences next to longer ones, honest trade-offs ("Termius is the better tool
when…"), and the mechanism behind a claim (`SIGHUP`, not "dies for unknown
reasons").

## HTML allowed

`<p>`, `<section id="kebab-case">` with `<h2>`, `<h3>`, `<ul>/<ol>/<li>`,
`<pre><code>`, inline `<code>`, `<strong>`, `<em>`, `<a href="/guide/<lang>/slug/">`,
`<table>` (`<thead>/<tbody>/<tr>/<th>/<td>`), `<details><summary><h2>…</h2></summary>`,
and `<figure>` + `<img src="/resource/x.webp" alt="…">` + `<figcaption>` for files
that already exist in `resource/` (add `class="figure-phone"` on the `<figure>` of
a tall phone shot so it does not stretch to two screens; wide iPad shots take no
class).

Never add `class` or `style` — the stylesheet has no hooks for them. The one
exception is `figure class="figure-phone"` above. Tables get
wrapped in a scroll container at build time; don't add one yourself.

**Do not change an existing `id`.** Other pages and the troubleshooting index link
to those anchors. New sections need a kebab-case id.

Never edit `strings/`, `config.json`, `build.py`, or the templates — copy only.

## Answer-first opening

The first `<p>` must be a self-contained answer to the query the title implies:
35–60 English words, or 60–100 Traditional Chinese characters. Someone quoting it
in an answer engine should need no surrounding context.

That means no anaphora in paragraph one: no "as the last article argued", no
"this article explains". Those belong in paragraph two, which is where the hook
lives.

## Headings

A heading is either the question a reader typed or a claim specific enough to
argue. Bare labels ("Setup", "Overview", "Why it matters") are the failure mode.
Roughly half may be literal questions; do not force every heading into one.
Keep headings under about 10 words.

## Facts about the product — use only these

- Agentmux is a client for iOS, iPadOS and Android. It is not a host: the code
  and the agent always run on a machine the user owns (Mac, Linux box, server).
- Connection is plain SSH, with keys or passwords. Tailscale is the recommended
  way in, because it needs no port open to the public internet; MagicDNS names or
  100.x addresses are the addresses to use, not LAN IPs.
- tmux sessions persist: a dropped phone connection detaches, it does not stop
  the agent. The app can install tmux when missing, and probes for PATH problems.
- Windows 10 and 11 work as an SSH host. The app detects the host itself, no
  switch: its own commands go through PowerShell, and psmux is the multiplexer.
  It looks for `psmux`, then `pmux`, then `tmux.exe`, and installs with winget,
  then Scoop, then cargo when none is found. Browsing, editing and transferring
  files need the SFTP subsystem; running a script and Git operations from the
  file browser are refused on Windows. psmux has no `pane_current_path`, so the
  status strip cannot name a pane's folder. Windows is only ever the host: there
  is no Agentmux that runs on Windows. Article: `windows-server`.
- Agents it drives: Claude Code, Codex, Gemini, OpenCode, or any custom CLI
  command. From the phone you can launch, watch, reply to prompts, and answer
  permission requests.
- Files: browse and edit remote files over SSH; file history and branch tools;
  multiple servers, custom agents, and batch actions.
- Plans: 14-day full-feature trial, then a free single-server tier (single
  server, persistent sessions, core terminal). Pro adds multiple servers, custom
  agents, remote editing, file history, branch tools, batch actions. Say
  "single-server tier" — never quote a price in a currency.
- AI Permission Review (zh-TW: AI 自動權限審查): a blacklist blocks dangerous
  commands, an allowlist passes ones the user already trusts, the rest go to an
  AI judgement, and a mode decides whether it only suggests the key or presses
  it.
- Privacy: no personal data collection, optional anonymous usage statistics,
  hardware-backed credential storage, SSH traffic encrypted and never logged.
- The setup page is an interactive wizard: three questions, then a checklist.
  "A Windows PC" gets the explainer at `#windows` on that page and the
  `windows-server` article instead of a checklist.
- App Store `id6766158521`; Google Play `cc.saxcave.agentmux`. The guide exists in
  en and zh-TW; only the homepages exist in zh-Hans and ja.
- `troubleshooting` already covers: SSH timeouts, `Permission denied (publickey)`,
  correct password rejected, tmux missing, `claude: command not found`, Tailscale
  connected but unreachable, macOS Remote Login on but refusing, `sudo: a
  terminal is required`. Link to it instead of duplicating it.

Off limits: benchmarks, currency prices, iOS/Android version numbers, security
audit claims, "unlimited" anything, and any claim about a competitor's product
that is not already stated in the file you are editing. If a fact is not above,
either write it conditionally ("if your distribution…") or leave it out.

## English and Traditional Chinese are separate drafts

`zh-TW.html` is not a translation of `en.html`; it is the same argument written
for a Traditional Chinese reader. Keep technical terms untranslated (tmux, SSH,
session, agent, commit, port), keep commands in English, and never translate an
English idiom literally.

It also has to read as written in Taiwan: preferred term first, never the
mainland one — 鎖定螢幕 not 鎖屏, 網路 not 網絡, 使用者 not 用戶, 儲存 not
保存, 程式碼 not 代碼, 介面 not 界面, 圖示 not 圖標, 支援 not 支持, 快取 not
緩存, 記憶體 not 內存, 程序 not 進程, 設定 not 設置, 載入 not 加載, 影片 not
視頻, 硬碟 not 硬盤, 滑鼠 not 鼠標, 電腦 not 計算機. And no simplified
characters anywhere in a zh-TW file — the site has a separate zh-Hans page for
that orthography.

`guide-src/tests/test_language.py` checks both rules. Run it after writing any
zh-TW copy: `python3 guide-src/tests/test_language.py`.

## Links and the closing hook

Two to four internal links per article, using the current language's path
(`/guide/en/…` in `en.html`, `/guide/zh-TW/…` in `zh-TW.html`).

Most articles end with one sentence that opens the next problem ("Then you put
your phone away, the tunnel drops, and the agent dies with it. Unless…"). Keep
that habit and adapt it when the body changes.
