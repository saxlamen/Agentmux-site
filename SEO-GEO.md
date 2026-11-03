# SEO / GEO — status, runbook, open items

Last audited: 2026-11-04 against `agentmux.saxcave.cc` (site repo, `main`).
Everything marked *verified* was checked against generated files or the live
host in that audit, not assumed.

## 1. Done and verified

### Crawl and index
| What | Where | Verified |
|---|---|---|
| 30 URLs, every one with `lastmod` from git history | `sitemap.xml` | yes |
| 10 AI/search crawlers allowed by name (Googlebot, Bingbot, GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-SearchBot, PerplexityBot, Applebot, DuckBot) + `Sitemap:` line | `robots.txt` | yes |
| IndexNow key + ping (Bing/Copilot/ChatGPT freshness) | `7a9460…c3b5.txt`, `guide-src/indexnow.py` | accepted, 30 URLs |
| Branded 404 that routes back into the guide | `404.html` | 200 |
| Canonical on every page; hreflang `en`/`zh-TW`/`x-default` on guide, four locales on home | templates, `build_home.py` | yes |
| Language picker uses real `<a>` links (crawlable without JS) | `guide/index.html` | yes |

### Structured data (one `@graph` per page, all blocks parse as JSON)
Article / HowTo with `author`, `publisher`, `image`, `datePublished`,
`dateModified`; `BreadcrumbList` (25); `CollectionPage` + `ItemList` for the
indexes; `FAQPage` derived from the troubleshooting `<h2>` questions and their
visible `Fix` / `解法` paragraphs only; `Organization`, `WebSite`,
`SoftwareApplication` (with `offers`, `featureList`, `sameAs` → App Store and
Google Play) on home. Counts from the last build: Article 20, HowTo 2,
FAQPage 2, BreadcrumbList 25, CollectionPage 3.

### Preview cards and SERP text
- `og:image:width/height/alt` on every guide page; dimensions read from
  `resource/` by `guide-src/refresh_images.py` into `guide-src/images.json`.
- Meta descriptions inside the pixel budget: en ≤ 153, zh-TW ≤ 79. Four were
  being cut mid-sentence (permission-review was 276 characters).
- `twitter:card/title/description/image` on guide pages; `og:locale`,
  `og:site_name` too.

### Content (the part that actually ranks and gets quoted)
- Every article opens with a self-contained answer (en 35–60 words, zh-TW
  60–100 characters) so a quote can stand alone.
- Headings are questions or claims, not table-of-contents labels.
- `what-is-cli` / `-ssh` / `-tmux` / `-tailscale` deepened from ~350 words to
  1100–1200 (zh-TW 1730–2015 characters). `why-agentmux` is a buyer's guide
  with a capability table. New: `claude-code-on-iphone`.
- Traditional Chinese follows Taiwanese vocabulary; `guide-src/WRITING.md`
  lists the terms and `guide-src/tests/test_language.py` enforces them.

### Answer engines
`llms.txt` (index) and `llms-full.txt` (full text, ~185 KB / 134k characters)
are generated from the same config/strings/content matrix as the HTML, and
every page head advertises both as `rel=alternate type=text/plain`.

### Guards (110 tests)
`guide-src/tests/`: `test_build.py` 82 (includes meta length caps, og:image
tags, llms links, images.json coverage, 404 routes, IndexNow key), `test_build`
plus `test_language.py` 3, `test_wizard_data.py` 20, `test_site_map.py` 5.

## 2. Runbook

```bash
cd website
python3 guide-src/build.py                 # guide, sitemap, llms.txt, llms-full.txt
python3 build_home.py                      # four home locales
python3 guide-src/refresh_images.py        # only if resource/ images changed
python3 guide-src/site_map.py              # only if config.json slugs changed
for t in test_build test_language test_wizard_data test_site_map; do
  python3 guide-src/tests/$t.py || exit 1
done
git add -A && git commit && git push origin main
# wait ~60s for Pages, then:
python3 guide-src/indexnow.py              # or --dry-run to inspect first
```

Cloudflare caches `/robots.txt` and `/sitemap.xml` for up to 4 hours. Purge
those two paths in the dashboard after changing them, or accept the delay.

## 3. Open items — mine, in value order

1. **Guide does not exist in zh-Hans or ja** while home does. hreflang
   correctly tells Google those languages have no guide, so Simplified Chinese
   and Japanese searches for "what is tmux" / "tailscale 是什麼" land on the
   home page instead of the answer. This is the largest remaining lever:
   11 articles × 2 languages. zh-Hans must use mainland vocabulary (服务器,
   锁屏, 默认…) — the rule set is the mirror image of `test_language.py`, so
   that file needs a zh-Hans half before the first draft.
2. **OG cards at 1200×630.** Five articles point at iPhone screenshots
   (1320×2868); link previews crop those to a narrow band. Four more share the
   site default image. `screenshots-generator` can render landscape cards;
   this needs a decision about the card design, not engineering.
3. **Two more high-intent pages**: a "best SSH client for iPad/iPhone" list
   (comparison queries are where Termius traffic is won) and a tmux command
   cheat sheet that can be quoted verbatim by answer engines.
4. **Organization entity is thin** — name, url, logo, sameAs only. `slogan`,
   `foundingDate` and social `sameAs` need real values from you.
   `aggregateRating` stays out until a real rating appears on the page.
5. **Home page alt text is English on every locale.** Guide alt is localized;
   the home page strings in `index.source.html` are not.
6. **No analytics at all.** We can see Google and Bing behaviour in their
   consoles, but not ChatGPT/Perplexity referrals. A privacy-friendly counter
   (or server-side referrer log) is the cheapest way to learn whether the GEO
   work moves traffic. Decide whether you want it before the traffic exists.

## 4. Open items — yours

| Item | Why it matters | Where |
|---|---|---|
| Verify `agentmux.saxcave.cc` in Bing Webmaster Tools and submit the sitemap | ChatGPT search and Copilot answer from the Bing index; without verification we get no feedback loop | bing.com/webmaster |
| Verify in Search Console and submit the sitemap | Coverage, query data, and the only signal for the English pages | search.google.com/search-console |
| Purge Cloudflare cache for `/robots.txt` and `/sitemap.xml` | New crawler rules and lastmod dates are live at origin but may be cached up to 4 h | Cloudflare → Caching → Purge Custom |
| Domain decision (e.g. `agentmux.com` + 301) | An entity-stable domain helps both ranking and citation; a subdomain on a free zone is fine but weaker | your decision |
| Optional: `slogan`, founding year, social profiles | Fills the Organization entity | item 4 above |

## 5. What to measure, and when

Six weeks after Bing and Search Console are verified:
- Search Console → Pages report filtered to `/guide/`: impressions and average
  position for `what is tmux`, `what is tailscale`, `ssh from phone`,
  `claude code on iphone`. A page that gets impressions at position 20+ needs
  its opening and headings revised, not more words.
- Bing Webmaster → Indexed Pages count and Queries. If Bing indexes stay flat
  while Google grows, the GEO work is not reaching ChatGPT.
- Referral traffic from `chatgpt.com`, `perplexity.org`, `copilot` — zero
  today because there is no analytics (item 6 above).

## 6. Deliberately not done

- **`aggregateRating`** — no rating is shown on the page, so publishing one
  would violate the structured-data guidelines.
- **`SearchAction`** — the site has no search.
- **RSS / blog cadence** — a feed with three posts is a negative signal.
- **hreflang for a zh-Hans/ja guide** — would be a lie until the pages exist.
- **A JS framework for the guide** — static HTML is why answer engines can read
  it in one fetch.
- **`noindex` on the llms files** — they are plain text and are meant to be
  fetched, not indexed as pages.
- **More structured data types** — the page has what it describes; adding
  irrelevant types (Product, Event) is noise.
