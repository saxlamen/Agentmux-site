#!/usr/bin/env python3
"""Check an announce.json candidate against the client contract.

Usage: python3 check_announce.py <file.json> [link_base_url]

Only stdlib: json, re, urllib (for the live-link HEAD check).
"""
import json
import re
import sys
import urllib.request

ALLOWED_TOP = {
    "schemaVersion", "id", "timestamp", "publishAt", "expiresAt",
    "minAppVersion", "minAppVersions", "hideForPro", "platforms",
    "title", "message", "localized", "action",
}
REQUIRED_TOP = {"id", "timestamp", "title", "message"}
ALLOWED_LOCALIZED = {"title", "message", "actionLabel"}
ALLOWED_PLATFORMS = {"ios", "android", "macos"}
ALLOWED_ACTION_TYPES = {"none", "url", "paywall"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$")
VER_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")

problems = []


def check(cond, msg):
    if not cond:
        problems.append(msg)


def main():
    path = sys.argv[1]
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    data = json.loads(raw)

    check(not problems, "json parses")

    keys = set(data)
    check(not (keys - ALLOWED_TOP),
          f"unknown top-level keys (schema is additionalProperties:false): {sorted(keys - ALLOWED_TOP)}")
    check(REQUIRED_TOP <= keys, f"missing required keys: {sorted(REQUIRED_TOP - keys)}")

    sv = data.get("schemaVersion")
    check(sv is None or (isinstance(sv, int) and sv >= 1 and sv <= 2),
          f"schemaVersion {sv!r} must be an int <= 2 (clients ignore anything higher)")

    check(bool(data.get("id", "").strip()), "id must not be empty")
    for field in ("timestamp", "publishAt", "expiresAt"):
        val = data.get(field)
        if val is not None:
            check(bool(DATE_RE.match(val)), f"{field} is not ISO8601 date-time: {val!r}")

    for field in ("minAppVersion",):
        val = data.get(field)
        if val is not None:
            check(bool(VER_RE.match(val)), f"{field} is not semver: {val!r}")

    mins = data.get("minAppVersions")
    if mins is not None:
        check(isinstance(mins, dict), "minAppVersions must be an object")
        for platform, val in mins.items():
            check(platform in ALLOWED_PLATFORMS, f"minAppVersions key {platform!r} not in {sorted(ALLOWED_PLATFORMS)}")
            check(bool(VER_RE.match(val)), f"minAppVersions.{platform} is not semver: {val!r}")

    plats = data.get("platforms")
    if plats is not None:
        check(isinstance(plats, list) and set(plats) <= ALLOWED_PLATFORMS,
              f"platforms must be a subset of {sorted(ALLOWED_PLATFORMS)}: {plats!r}")

    action = data.get("action")
    action_url = None
    if action is not None:
        check("type" in action, "action needs a type")
        check(set(action) <= {"label", "type", "url"}, f"action has unknown keys: {sorted(set(action) - {'label', 'type', 'url'})}")
        check(action.get("type") in ALLOWED_ACTION_TYPES, f"action.type {action.get('type')!r} invalid")
        check(action.get("type") != "url" or action.get("url"), "action.type 'url' needs a url")
        action_url = action.get("url")

    localized = data.get("localized")
    locales = []
    if localized is not None:
        check(isinstance(localized, dict), "localized must be an object")
        for locale, copy in localized.items():
            locales.append(locale)
            check({"title", "message"} <= set(copy), f"localized.{locale} missing title/message")
            check(set(copy) <= ALLOWED_LOCALIZED, f"localized.{locale} has unknown keys: {sorted(set(copy) - ALLOWED_LOCALIZED)}")
            for field, val in copy.items():
                check(isinstance(val, str) and val.strip(), f"localized.{locale}.{field} must be a non-empty string")

    print(f"file        : {path}")
    print(f"id          : {data.get('id')}")
    print(f"publishAt   : {data.get('publishAt')}    expiresAt: {data.get('expiresAt')}")
    print(f"minVersions : per-platform {mins or '-'} / fallback {data.get('minAppVersion') or '-'}")
    print(f"platforms   : {plats}")
    print(f"hideForPro  : {data.get('hideForPro')}")
    print(f"action      : {action.get('type') if action else '(none)'} {action_url or ''}")
    print(f"locales     : en (default) + {len(locales)} -> {', '.join(sorted(locales))}")
    print(f"message len : en {len(data.get('message', ''))} chars")

    if action_url:
        try:
            request = urllib.request.Request(action_url, method="HEAD", headers={"User-Agent": "announce-check"})
            with urllib.request.urlopen(request, timeout=20) as response:
                print(f"CTA live    : HTTP {response.status} {action_url}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"CTA url is not reachable: {action_url} ({exc})")

    if problems:
        print("\nPROBLEMS:")
        for problem in problems:
            if problem != "json parses":
                print(f"  - {problem}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
