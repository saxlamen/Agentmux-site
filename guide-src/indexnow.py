#!/usr/bin/env python3
"""Tell Bing (and the engines that share its index) that the site changed.

IndexNow is the only freshness signal available for the Bing side of the web,
and Bing's index is what Copilot and ChatGPT search answer from. GitHub Pages
gives no ping hook, so this runs after a push.

    python3 guide-src/indexnow.py            # ping every URL in sitemap.xml
    python3 guide-src/indexnow.py --dry-run  # show the payload, send nothing
    python3 guide-src/indexnow.py --limit 8  # ping the first N URLs

Run it once GitHub Pages has served the new build (about a minute after push),
otherwise the engines fetch the old pages. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SRC = Path(__file__).resolve().parent
WEB_ROOT = SRC.parent
ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_FILE = re.compile(r"^[0-9a-f]{32}\.txt$")
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def find_key() -> str:
    for file in WEB_ROOT.iterdir():
        if KEY_FILE.match(file.name):
            return file.name[:-4]
    raise SystemExit("no IndexNow key: create an empty <32 hex chars>.txt in the site root")


def sitemap_urls(limit: int) -> list:
    root = ET.parse(str(WEB_ROOT / "sitemap.xml")).getroot()
    urls = [node.findtext(NS + "loc") for node in root.findall(NS + "url")]
    return [u for u in urls if u][:limit]


def main(argv: list) -> int:
    dry_run = "--dry-run" in argv
    limit = 10000
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])

    config = json.loads((SRC / "config.json").read_text(encoding="utf-8"))
    origin = config["site"]["origin"]
    host = re.sub(r"^https?://", "", origin).split("/")[0]
    key = find_key()
    urls = sitemap_urls(limit)
    payload = {"host": host, "key": key, "keyLocation": "%s/%s.txt" % (origin, key), "urlList": urls}

    print("host %s | %d urls | key %s…%s" % (host, len(urls), key[:6], key[-4:]))
    if dry_run:
        for url in urls[:10]:
            print("  ", url)
        print("   …" if len(urls) > 10 else "")
        print("dry run: nothing sent")
        return 0

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8",
                                              "User-Agent": "agentmux-site-indexnow/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        print("rejected: HTTP %d %s" % (error.code, error.read().decode("utf-8", "replace")[:200]))
        return 1
    except urllib.error.URLError as error:
        print("could not reach %s: %s" % (ENDPOINT, error.reason))
        return 1
    print("accepted" if status in (200, 202) else "HTTP %d" % status)
    return 0 if status in (200, 202) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
