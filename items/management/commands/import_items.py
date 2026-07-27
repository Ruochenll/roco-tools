"""从 BWIKI(wiki.biligame.com/rocom)抓取道具图鉴数据。

数据链路(全部走 MediaWiki 官方 API):
  1. list=categorymembers 列出 [分类:道具] 下全部道具页面
  2. action=parse (prop=wikitext|images) 逐页获取:
     - {{物品信息|...}} 模板参数(名称/分类/稀有度/用途/来源...)
     - 页面实际引用的图片文件列表 ← 用真实文件名,不再猜测 {icon}.png
  3. prop=imageinfo 批量查询真实 URL 并下载到 static/images/items/
     文件按数据库 icon 字段记录的名字落盘,保证前端引用一致

用法:
  python manage.py import_items                # 全量抓取(含图标下载)
  python manage.py import_items --limit 20     # 只抓前 20 个(测试)
  python manage.py import_items --skip-images  # 不下载图标
  python manage.py import_items --no-proxy     # 绕过系统代理直连
  python manage.py import_items --delay 0.2    # 请求间隔(默认 0.3s,请保持礼貌)
"""

import re
import time
from collections import Counter
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


def norm(name: str) -> str:
    """文件名归一化:下划线=空格、去扩展名、小写,用于模糊匹配。"""
    name = name.rsplit('.', 1)[0] if '.' in name else name
    return name.replace('_', ' ').strip().lower()


_KNOWN_PREFIXES = ['img_', 'gs_', 'egg_', 'xuemai_', 'icon_', 'item_', 'medalicon_', 'bf_', 'bff_', 'skill_']



class Command(BaseCommand):
    help = '从 BWIKI 抓取道具图鉴(名称/分类/稀有度/用途/图标,图标用页面真实文件名)'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='只处理前 N 个道具(0=全部)')
        parser.add_argument('--skip-images', action='store_true', help='跳过图标下载')
        parser.add_argument('--delay', type=float, default=0.3, help='请求间隔秒数')
        parser.add_argument('--no-proxy', action='store_true',
                            help='绕过系统代理直连(代理不稳定导致下载失败时使用)')
        parser.add_argument('--retry-missing', action='store_true',
                            help='只重试数据库中已有 icon 记录但文件缺失的道具,不重新解析页面')

    def handle(self, *args, **opts):
        import requests
        session = requests.Session()
        session.headers.update(HEADERS)
        if opts['no_proxy']:
            session.trust_env = False

        # --retry-missing 快捷模式: 直接补下载缺失图片
        if opts['retry_missing']:
            self.retry_missing_icons(session, opts['delay'])
            return

        titles = self.list_category_members(session, opts['delay'])
        if opts['limit']:
            titles = titles[:opts['limit']]
        self.stdout.write(f'共 {len(titles)} 个道具页面待处理')

        # ---------- 第一阶段:抓取模板参数 + 页面真实图片列表 ----------
        results = []   # (title, params, page_images)
        failed = 0
        for i, title in enumerate(titles, 1):
            try:
                params, images = self.fetch_item_page(session, title)
                if params is None:
                    self.stdout.write(self.style.WARNING(f'  [{i}/{len(titles)}] {title}: 未找到物品信息模板,跳过'))
                    failed += 1
                else:
                    results.append((title, params, images))
                if i % 50 == 0:
                    self.stdout.write(f'  已抓取 {i}/{len(titles)} ...')
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.stdout.write(self.style.WARNING(f'  [{i}/{len(titles)}] {title}: {exc}'))
            time.sleep(opts['delay'])

        # ---------- 识别公共装饰图(背景/边框等,出现在大量页面上的文件) ----------
        freq = Counter()
        for _, _, images in results:
            freq.update(set(images))
        threshold = max(20, int(len(results) * 0.25))
        common_files = {f for f, c in freq.items() if c >= threshold}
        if common_files:
            self.stdout.write(f'已识别 {len(common_files)} 个公共装饰图(背景/边框),不作为道具图标: '
                              f'{sorted(common_files)[:5]}...')

        # ---------- 第二阶段:确定每个道具的真实图标文件名并入库 ----------
        created = updated = 0
        icon_files = {}    # 真实文件名 → GameItem
        no_icon_items = []
        for title, params, images in results:
            icon_param = params.get('icon', '').strip()
            candidates = [f for f in images if f not in common_files]

            icon_file = ''
            if icon_param:
                n_param = norm(icon_param)
                # 1) 精确归一化匹配
                for f in candidates:
                    if norm(f) == n_param:
                        icon_file = f
                        break
                # 2) 剥离已知前缀后匹配 (如 icon="1012" 匹配 "Img_1012.png")
                if not icon_file:
                    for f in candidates:
                        nf = norm(f)
                        for pfx in _KNOWN_PREFIXES:
                            if nf.startswith(pfx) and nf[len(pfx):] == n_param:
                                icon_file = f
                                break
                        if icon_file:
                            break
                # 3) icon 参数是纯数字 → 候选文件名中包含该数字
                if not icon_file and icon_param.isdigit():
                    for f in candidates:
                        if icon_param in norm(f):
                            icon_file = f
                            break
            if not icon_file and len(candidates) == 1:
                # 页面上只剩一张非公共图,就是它
                icon_file = candidates[0]
            if not icon_file and icon_param:
                # 兜底:退回旧的猜测方式
                icon_file = f'{icon_param}.png'

            number = 0
            num_param = params.get('物品序号', '').strip()
            if num_param.isdigit():
                number = int(num_param)
            elif icon_param.isdigit():
                number = int(icon_param)

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
            if icon_file:
                icon_files[icon_file] = obj
            else:
                no_icon_items.append(obj.name)

        self.stdout.write(self.style.SUCCESS(
            f'道具数据完成: 新增 {created}, 更新 {updated}, 页面失败 {failed}, '
            f'wiki 无图标 {len(no_icon_items)} 个'))
        if no_icon_items:
            self.stdout.write(f'  无图标示例: {no_icon_items[:8]}')

        # ---------- 第三阶段:下载图标 ----------
        if not opts['skip_images'] and icon_files:
            self.download_icons(session, icon_files, opts['delay'])

        # ---------- 收尾:统计仍缺图的道具 ----------
        missing = [name for f, obj in icon_files.items()
                   if not (ITEM_IMG_DIR / f).exists()
                   for name in [obj.name]]
        if missing:
            self.stdout.write(self.style.WARNING(
                f'仍有 {len(missing)} 个道具的图标文件在 wiki 上不存在或下载失败: {missing[:8]}...'))
        else:
            self.stdout.write(self.style.SUCCESS('所有有图标记录的道具均已配齐图片 ✔'))

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

    def fetch_item_page(self, session, title):
        """返回 (模板参数 dict | None, 页面图片文件名列表)。"""
        resp = session.get(API_URL, params={
            'action': 'parse', 'page': title, 'prop': 'wikitext|images',
            'format': 'json', 'formatversion': 2,
        }, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if 'error' in data:
            raise RuntimeError(data['error'].get('info', 'API error'))
        wikitext = data['parse']['wikitext']
        images = data['parse'].get('images', [])  # 真实文件名(规范形式,含空格)
        m = TEMPLATE_RE.search(wikitext)
        if not m:
            return None, images
        params = {}
        for key, value in PARAM_RE.findall(m.group(1)):
            params[key.strip()] = clean_wikitext(value)
        return params, images

    def download_icons(self, session, icon_files, delay):
        ITEM_IMG_DIR.mkdir(parents=True, exist_ok=True)
        pending = [f for f in icon_files if not (ITEM_IMG_DIR / f).exists()]
        self.stdout.write(f'需下载图标 {len(pending)} 个(已存在 {len(icon_files) - len(pending)} 个,跳过)')

        def _fetch_batch(batch):
            """带重试的批量 imageinfo 查询。"""
            for attempt in range(5):
                try:
                    resp = session.get(API_URL, params={
                        'action': 'query',
                        'titles': '|'.join(f'File:{f}' for f in batch),
                        'prop': 'imageinfo', 'iiprop': 'url',
                        'format': 'json', 'formatversion': 2,
                    }, timeout=60)
                    resp.raise_for_status()
                    return resp.json().get('query', {})
                except Exception as exc:
                    if attempt == 4:
                        raise
                    self.stdout.write(f'  批量查询重试 {attempt + 1}/5: {exc}')
                    time.sleep(2 * (attempt + 1))

        downloaded = failed = missing_on_wiki = 0
        for batch_start in range(0, len(pending), 50):
            batch = pending[batch_start:batch_start + 50]
            try:
                data = _fetch_batch(batch)
            except Exception as exc:  # noqa: BLE001
                self.stdout.write(self.style.ERROR(f'  批量查询失败,整批 {len(batch)} 张跳过: {exc}'))
                failed += len(batch)
                time.sleep(delay)
                continue

            norm_map = {n['to']: n['from'] for n in data.get('normalized', [])}
            for page in data.get('pages', []):
                req_title = norm_map.get(page['title'], page['title'])
                fname = req_title.split(':', 1)[-1].strip()
                info = page.get('imageinfo')
                if not info:
                    missing_on_wiki += 1
                    continue
                url = info[0]['url']
                ok = False
                for attempt in range(3):
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
            if (batch_start // 50) % 4 == 3:
                self.stdout.write(f'  图标进度 {min(batch_start + 50, len(pending))}/{len(pending)} ...')

        msg = f'图标下载完成: 成功 {downloaded}, 下载失败 {failed}, wiki 上不存在 {missing_on_wiki}'
        if failed:
            msg += '(下载失败的可加 --retry-missing 重跑补齐)'
        self.stdout.write(self.style.SUCCESS(msg))

    def retry_missing_icons(self, session, delay):
        """只补下载数据库中 icon 字段有值但磁盘上文件缺失的图片。"""
        items = GameItem.objects.exclude(icon='')
        ITEM_IMG_DIR.mkdir(parents=True, exist_ok=True)
        icon_files = {}
        for obj in items:
            if not (ITEM_IMG_DIR / obj.icon).exists():
                icon_files[obj.icon] = obj
        if not icon_files:
            self.stdout.write(self.style.SUCCESS('所有图标均已存在,无需下载'))
            return
        self.stdout.write(f'发现 {len(icon_files)} 个缺失图标,开始补下载...')
        self.download_icons(session, icon_files, delay)
