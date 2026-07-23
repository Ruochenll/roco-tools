"""
从 BWIKI "阵容一览" 页面批量下载所有精灵圆形头像。

工作原理：
1. 调用 MediaWiki API 获取页面渲染后的 HTML
2. 解析 class="rocom_lineup_line_pet_img" 的 img 标签
3. 从 img 后的 div.rocom_lineup_line_pet_name 提取精灵名称
4. 去重后批量下载到目标目录
"""

import re
import time
import urllib.request
import json
from pathlib import Path
from html.parser import HTMLParser


API_URL = "https://wiki.biligame.com/rocom/api.php"
TARGET_DIR = Path(r"D:\Project\LuoKeWangGuo\static\images\pets_head")


class AvatarParser(HTMLParser):
    """解析 HTML，提取 img URL 和精灵名称的配对。"""

    def __init__(self):
        super().__init__()
        self.pairs = []           # [(name, url), ...]
        self._current_url = None
        self._in_pet_img = False
        self._in_pet_name = False
        self._name_div_depth = 0
        self._skip = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        # 匹配精灵头像 img
        cls = attrs.get("class", "")
        if tag == "img" and "rocom_lineup_line_pet_img" in cls:
            src = attrs.get("src", "")
            if src and "patchwiki.biligame.com" in src:
                self._current_url = src
                self._in_pet_img = True
            return

        # 匹配精灵名称 div（紧跟 img 之后）
        if tag == "div" and "rocom_lineup_line_pet_name" in attrs.get("class", ""):
            if self._current_url:
                self._in_pet_name = True
                self._name_div_depth = 0
            return

        if self._in_pet_name:
            self._name_div_depth += 1

    def handle_data(self, data):
        if self._in_pet_name:
            name = data.strip()
            if name and not self._skip:
                self.pairs.append((name, self._current_url))
                self._current_url = None  # 用完即清，避免误配对
            self._in_pet_name = False
            self._in_pet_img = False

    def handle_endtag(self, tag):
        if self._in_pet_name:
            if tag == "div":
                if self._name_div_depth == 0:
                    self._in_pet_name = False
                    self._in_pet_img = False
                    self._current_url = None
                else:
                    self._name_div_depth -= 1


def fetch_page_html():
    """调用 MediaWiki API 获取阵容一览页面的渲染 HTML。"""
    params = urllib.parse.urlencode({
        "action": "parse",
        "page": "阵容一览",
        "prop": "text",
        "format": "json",
        "disablelimitreport": "1",
    })
    url = f"{API_URL}?{params}"
    print(f"Fetching page data from API...")
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    html = data["parse"]["text"]["*"]
    print(f"  Got {len(html):,} chars of HTML")
    return html


def parse_avatars(html):
    """解析 HTML，返回去重后的 (name, url) 列表。"""
    parser = AvatarParser()
    parser.feed(html)
    pairs = parser.pairs

    # 过滤掉血脉魔法名称（进化之力、愿力冲击等不是精灵名）
    rare_names = {"进化之力", "愿力冲击", "强化术", "光合治愈"}
    pairs = [(n, u) for n, u in pairs if n not in rare_names]

    # 去重（同一精灵可能出现在多个阵容中）
    seen = set()
    unique = []
    for name, url in pairs:
        if name not in seen:
            seen.add(name)
            unique.append((name, url))
    return unique


def download_all(pairs):
    """批量下载头像图片。"""
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    success = 0
    fail = 0
    skipped = 0

    for i, (name, url) in enumerate(pairs, 1):
        out_path = TARGET_DIR / f"{name}.png"

        # 跳过已存在的
        if out_path.exists():
            skipped += 1
            continue

        try:
            print(f"  [{i}/{len(pairs)}] {name} ... ", end="", flush=True)
            urllib.request.urlretrieve(url, str(out_path))
            print("OK")
            success += 1
        except Exception as e:
            print(f"FAIL ({e})")
            fail += 1
            continue

        # 礼貌限速，避免被 ban
        time.sleep(0.3)

    print(f"\nDone! {success} downloaded, {skipped} skipped, {fail} failed.")


def main():
    print("=== BWIKI 精灵头像批量下载 ===\n")

    html = fetch_page_html()
    pairs = parse_avatars(html)

    print(f"\nFound {len(pairs)} unique pet avatars")
    print(f"Target directory: {TARGET_DIR}\n")

    if not pairs:
        print("No avatars found! Check HTML parsing.")
        return

    # 展示前 10 个
    for name, url in pairs[:10]:
        print(f"  {name}: {url}")
    if len(pairs) > 10:
        print(f"  ... and {len(pairs) - 10} more")

    print()
    download_all(pairs)


if __name__ == "__main__":
    main()
