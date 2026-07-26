"""从 BWIKI(wiki.biligame.com/rocom)抓取道具图鉴数据。

数据链路(全部走 MediaWiki 官方 API,与 tools/wiki_fetcher.py 同源):
  1. list=categorymembers 列出 [分类:道具] 下全部道具页面
  2. action=parse 逐页获取 wikitext,解析 {{物品信息|...}} 模板参数
  3. prop=imageinfo 批量查询 File:{icon}.png 的真实 URL 并下载到 static/images/items/

用法:
  python manage.py import_items                # 全量抓取(含图标下载)
  python manage.py import_items --limit 20     # 只抓前 20 个(测试)
  python manage.py import_items --skip-images  # 不下载图标
  python manage.py import_items --delay 0.5    # 每次请求间隔(默认 0.3s,请保持礼貌)
"""

import re
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from items.models import GameItem

API_URL = 'https://wiki.biligame.com/rocom/api.php'
CATEGORY = '分类:道具'
ITEM_IMG_DIR = Path(settings.STATICFILES_DIRS[0]) / 'images' / 'items'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://wiki.biligame.com/rocom/',
}

TEMPLATE_RE = re.compile(r'\{\{\s*物品信息(.*?)\n\}\}', re.DOTALL)
PARAM_RE = re.compile(r'^\|\s*([^=|]+?)\s*=\s*(.*?)\s*$', re.MULTILINE)


def clean_wikitext(value: str) -> str:
    """去掉常见 wiki 标记,保留纯文本。"""
    value = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', value)  # [[a|b]] → b
    value = re.sub(r"'''?", '', value)
    value = value.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    value = re.sub(r'<[^>]+>', '', value)
    return value.strip()


class Command(BaseCommand):
    help = '从 BWIKI 抓取道具图鉴(名称/分类/稀有度/用途/图标)'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='只处理前 N 个道具(0=全部)')
        parser.add_argument('--skip-images', action='store_true', help='跳过图标下载')
        parser.add_argument('--delay', type=float, default=0.3, help='请求间隔秒数')
        parser.add_argument('--no-proxy', action='store_true',
                            help='绕过系统代理直连(代理不稳定导致下载失败时使用)')

    def handle(self, *args, **opts):
        import requests
        session = requests.Session()
        session.headers.update(HEADERS)
        if opts['no_proxy']:
            session.trust_env = False  # 忽略系统/环境变量代理设置

        titles = self.list_category_members(session, opts['delay'])
        if opts['limit']:
            titles = titles[:opts['limit']]
        self.stdout.write(f'共 {len(titles)} 个道具页面待处理')

        created = updated = failed = 0
        icons_needed = {}  # icon文件名 → GameItem

        for i, title in enumerate(titles, 1):
            try:
                params = self.fetch_item_params(session, title)
                if params is None:
                    self.stdout.write(self.style.WARNING(f'  [{i}/{len(titles)}] {title}: 未找到物品信息模板,跳过'))
                    failed += 1
                    continue
                icon_id = params.get('icon', '').strip()
                icon_file = f'{icon_id}.png' if icon_id else ''
                number = int(params.get('物品序号', 0) or (icon_id if icon_id.isdigit() else 0) or 0)
                obj, was_created = GameItem.objects.update_or_create(
                    name=params.get('物品名称') or title,
                    defaults={
                        'number': number,
                        'icon': icon_file,
                        'main_category': params.get('主分类', ''),
                        'sub_category': params.get('次分类', ''),
                        'rarity': params.get('稀有度', ''),
                        'usage': params.get('用途', ''),
                        'description': params.get('描述', ''),
                        'source': params.get('来源', ''),
                        'version': params.get('道具版本', ''),
                    },
                )
                created += was_created
                updated += (not was_created)
                if icon_id:
                    icons_needed[icon_id] = obj
                if i % 20 == 0:
                    self.stdout.write(f'  已处理 {i}/{len(titles)} ...')
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.stdout.write(self.style.WARNING(f'  [{i}/{len(titles)}] {title}: {exc}'))
            time.sleep(opts['delay'])

        self.stdout.write(self.style.SUCCESS(
            f'道具数据完成: 新增 {created}, 更新 {updated}, 失败 {failed}'))

        if not opts['skip_images'] and icons_needed:
            self.download_icons(session, icons_needed, opts['delay'])

    # ---------- API helpers ----------

    def list_category_members(self, session, delay):
        titles = []
        cont = {}
        while True:
            params = {
                'action': 'query', 'list': 'categorymembers',
                'cmtitle': CATEGORY, 'cmlimit': 500, 'cmnamespace': 0,
                'format': 'json', 'formatversion': 2, **cont,
            }
            resp = session.get(API_URL, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            titles += [m['title'] for m in data['query']['categorymembers']]
            if 'continue' not in data:
                break
            cont = data['continue']
            time.sleep(delay)
        return titles

    def fetch_item_params(self, session, title):
        resp = session.get(API_URL, params={
            'action': 'parse', 'page': title, 'prop': 'wikitext',
            'format': 'json', 'formatversion': 2,
        }, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if 'error' in data:
            raise RuntimeError(data['error'].get('info', 'API error'))
        wikitext = data['parse']['wikitext']
        m = TEMPLATE_RE.search(wikitext)
        if not m:
            return None
        params = {}
        for key, value in PARAM_RE.findall(m.group(1)):
            params[key.strip()] = clean_wikitext(value)
        return params

    def download_icons(self, session, icons_needed, delay):
        ITEM_IMG_DIR.mkdir(parents=True, exist_ok=True)
        pending = {k: v for k, v in icons_needed.items()
                   if not (ITEM_IMG_DIR / f'{k}.png').exists()}
        self.stdout.write(f'需下载图标 {len(pending)} 个(已存在 {len(icons_needed) - len(pending)} 个,跳过)')

        icon_ids = list(pending.keys())
        downloaded = failed = 0
        for batch_start in range(0, len(icon_ids), 50):
            batch = icon_ids[batch_start:batch_start + 50]
            resp = session.get(API_URL, params={
                'action': 'query',
                'titles': '|'.join(f'File:{i}.png' for i in batch),
                'prop': 'imageinfo', 'iiprop': 'url',
                'format': 'json', 'formatversion': 2,
            }, timeout=60)
            resp.raise_for_status()
            data = resp.json().get('query', {})
            # MediaWiki 会把下划线规范化成空格、首字母大写等,导致返回的
            # 标题和我们请求的不一致。这里建立「规范化标题 → 请求名」映射,
            # 保证文件按数据库里记录的原始名字落盘,前端引用才能对上。
            norm_map = {}
            for n in data.get('normalized', []):
                norm_map[n['to']] = n['from']
            for page in data.get('pages', []):
                info = page.get('imageinfo')
                if not info:
                    continue
                req_title = norm_map.get(page['title'], page['title'])
                fname = req_title.split(':', 1)[-1].strip()  # 'File:xxx.png' → 'xxx.png'
                url = info[0]['url']
                ok = False
                for attempt in range(3):  # 代理/网络抖动时重试
                    try:
                        img = session.get(url, timeout=60)
                        img.raise_for_status()
                        (ITEM_IMG_DIR / fname).write_bytes(img.content)
                        ok = True
                        break
                    except Exception as exc:  # noqa: BLE001
                        if attempt == 2:
                            self.stdout.write(self.style.WARNING(f'  图标下载失败 {fname}: {exc}'))
                        else:
                            time.sleep(1.5 * (attempt + 1))
                downloaded += ok
                failed += (not ok)
                time.sleep(delay)
        msg = f'图标下载完成: {downloaded} 个 → static/images/items/'
        if failed:
            msg += f'(失败 {failed} 个,可加 --no-proxy 重跑补齐)'
        self.stdout.write(self.style.SUCCESS(msg))
