"""One-shot copy fix: the privacy policy said credentials are protected "in
device hardware". The code stores them in the OS credential store (iOS Keychain
with kSecAttrAccessibleAfterFirstUnlock, Android Keystore) and never asks for
biometry, so "hardware" promised a guarantee the app does not implement. This
updates the search description in all five places it appears (description,
og:description, twitter:description, JSON-LD, LANG_META) so they stay identical.

    python3 scripts/privacy_credentials_wording.py
"""

import pathlib

PATH = pathlib.Path(__file__).resolve().parent.parent / "privacy.html"

OLD = "credentials protected in device hardware"
NEW = "credentials kept in the system keychain"

text = PATH.read_text(encoding="utf-8")
hits = text.count(OLD)
if hits == 0:
    raise SystemExit("already applied - nothing matched")
PATH.write_text(text.replace(OLD, NEW), encoding="utf-8")
print("replaced %d occurrence(s)" % hits)
