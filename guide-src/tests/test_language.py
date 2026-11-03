#!/usr/bin/env python3
"""Guard the zh-Hant copy against mainland terminology and simplified characters.

The Traditional Chinese guide copy is written by many hands (and by models), so
"鎖屏" and a stray simplified character slip back in easily. This test locks the
house style: zh-Hant files use Taiwanese technical vocabulary.

Scope is the zh-Hant sources only. index.source.html is deliberately excluded: it
carries zh-Hans and ja blocks, and those are meant to read mainland/Japanese.
"""

from __future__ import annotations

import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent

# mainland term -> what we write instead
MAINLAND_TERMS = {
    "鎖屏": "鎖定螢幕",
    "屏幕": "螢幕",
    "服务器": "伺服器",
    "服務器": "伺服器",
    "默认": "預設",
    "默認": "預設",
    "软件": "軟體",
    "軟件": "軟體",
    "硬件": "硬體",
    "网络": "網路",
    "網絡": "網路",
    "代码": "程式碼",
    "代碼": "程式碼",
    "用户": "使用者",
    "用戶": "使用者",
    "搜索": "搜尋",
    "菜单": "選單",
    "菜單": "選單",
    "内存": "記憶體",
    "內存": "記憶體",
    "缓存": "快取",
    "緩存": "快取",
    "进程": "程序",
    "進程": "程序",
    "界面": "介面",
    "图标": "圖示",
    "圖標": "圖示",
    "反馈": "回饋",
    "反饋": "回饋",
    "信息": "資訊",
    "运行": "運作",
    "覆盖": "涵蓋",
    "掉线": "斷線",
    "掉線": "斷線",
    "内网": "內部網路",
    "內網": "內部網路",
    "局域网": "區域網路",
    "云端": "雲端",
    "应用程序": "應用程式",
    "计算机": "電腦",
    "計算機": "電腦",
    "硬盘": "硬碟",
    "硬盤": "硬碟",
    "鼠标": "滑鼠",
    "视频": "影片",
    "視頻": "影片",
    "音频": "音訊",
    "音頻": "音訊",
    "设置": "設定",
    "設置": "設定",
    "加载": "載入",
    "加載": "載入",
    "卸载": "解除安裝",
    "卸載": "解除安裝",
    "上传": "上傳",
    "支持": "支援",
    "兜底": "保底",
    "落地": "上線/實作",
    "赋能": "賦能",
}

# characters that exist only in simplified orthography; any of them in a zh-Hant
# file is a leak. Deliberately excludes homograph pairs (面/台/后/里/干 …).
SIMPLIFIED_ONLY = set(
    "锁门网页载录际组级统总关边线运远连还进义乐习亚产亲从众无显暂术机权条来杰极"
    "柜标档检汉沟没泽洁测济润湿满灭灾热爱状现疗视觉览计认让论设证评词译误说谈败"
    "账购责资车轨轻辑迁违递遗邮释钟钥银链问闲队难顶顺预频题额风馆驶骑顾驻类紧纪"
    "纯约细织终绍结给络绝继绩维绿缓编缩联脑艰节药获营虑补规笔简电时东书写语读会"
    "见儿并于广盖"
)


def zh_hant_sources() -> list:
    paths = sorted((SRC / "content").glob("*/zh-TW.html"))
    paths += [SRC / "strings" / "zh-TW.json", SRC / "wizard" / "strings" / "zh-TW.json"]
    return [p for p in paths if p.exists()]


class ZhHantStyleTest(unittest.TestCase):
    def setUp(self):
        self.sources = zh_hant_sources()
        self.assertTrue(self.sources, "no zh-Hant sources found")

    def test_no_mainland_terminology(self):
        offenders = []
        for path in self.sources:
            text = path.read_text(encoding="utf-8")
            for term, preferred in MAINLAND_TERMS.items():
                if term in text:
                    line = text[: text.index(term)].count("\n") + 1
                    offenders.append("%s:%d %s (write %s)" % (path.name, line, term, preferred))
        self.assertEqual(offenders, [], "mainland terminology in zh-Hant copy:\n" + "\n".join(offenders))

    def test_no_simplified_characters(self):
        offenders = []
        for path in self.sources:
            text = path.read_text(encoding="utf-8")
            for char in sorted(set(text) & SIMPLIFIED_ONLY):
                line = text[: text.index(char)].count("\n") + 1
                offenders.append("%s:%d %s" % (path.name, line, char))
        self.assertEqual(offenders, [], "simplified characters in zh-Hant copy:\n" + "\n".join(offenders))

    def test_every_article_has_zh_hant(self):
        en = {p.parent.name for p in (SRC / "content").glob("*/en.html")}
        zh = {p.parent.name for p in (SRC / "content").glob("*/zh-TW.html")}
        self.assertEqual(en, zh, "articles missing a zh-TW draft")


if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
