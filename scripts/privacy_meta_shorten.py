"""One-shot copy fix: shorten privacy.html's English and Japanese search
descriptions so they fit a search-result snippet. The English string appears in
five places (title-adjacent meta, og, twitter, JSON-LD, LANG_META) and all five
must stay identical, so replace every occurrence."""

import pathlib

PATH = pathlib.Path("/Users/saxliao/Scripts/Agentmux/website/privacy.html")

OLD_EN = (
    "Agentmux privacy policy: no personal data collection, optional anonymous usage "
    "statistics, hardware-backed secure credentials, and encrypted SSH traffic that "
    "is never logged."
)
NEW_EN = (
    "Agentmux privacy policy: no personal data collection, anonymous statistics you "
    "can switch off, credentials protected in device hardware, SSH traffic not logged."
)
OLD_JA = (
    "Agentmux のプライバシーポリシー。個人データを収集せず、匿名の利用統計はいつでもオフにでき、"
    "認証情報はハードウェア暗号化（Keychain / Keystore）で保存され、SSH 通信は暗号化され、"
    "ターミナル通信は記録されません。"
)
NEW_JA = (
    "Agentmux は個人データを収集しません。匿名の利用統計はオフにでき、認証情報は端末内で暗号化して"
    "保存し、SSH 通信は記録されません。"
)

text = PATH.read_text(encoding="utf-8")
for old, new, label in ((OLD_EN, NEW_EN, "en"), (OLD_JA, NEW_JA, "ja")):
    hits = text.count(old)
    if hits == 0:
        raise SystemExit("no match for %s - the file changed under me" % label)
    text = text.replace(old, new)
    print("%s: replaced %d occurrence(s), %d -> %d chars" % (label, hits, len(old), len(new)))
PATH.write_text(text, encoding="utf-8")
