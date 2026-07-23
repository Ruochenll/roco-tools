"""洛克王国世界 阵容分享码 编解码（Web端，兼容桌面版）。"""

import json
from pathlib import Path
from urllib.request import urlopen

BASE64_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
MAPS_FILE = Path(__file__).resolve().parent / 'data' / 'roster_id_maps.json'

_maps_cache = None


def _load_maps() -> dict:
    """从缓存文件加载 ID→名称映射。"""
    global _maps_cache
    if _maps_cache is not None:
        return _maps_cache
    if MAPS_FILE and MAPS_FILE.exists():
        _maps_cache = json.loads(MAPS_FILE.read_text(encoding='utf-8'))
        return _maps_cache
    # 兜底：从远端拉取
    base = 'https://rocom.qq.com/cp/rocom_game_manager_json/prod'
    maps = {}
    try:
        spr = json.loads(urlopen(f'{base}/sprite/base_info/list.json').read())
        maps['sprite'] = {s['id']: s['name'] for s in spr}
    except Exception:
        maps['sprite'] = {}
    try:
        skl = json.loads(urlopen(f'{base}/skill/list.json').read())
        maps['skill'] = {s['id']: s['name'] for s in skl}
    except Exception:
        maps['skill'] = {}
    try:
        char = json.loads(urlopen(f'{base}/sprite/character/list.json').read())
        maps['character'] = {c['id']: c['name'] for c in char}
    except Exception:
        maps['character'] = {}
    try:
        bl = json.loads(urlopen(f'{base}/basic/bloodline/list.json').read())
        maps['bloodline'] = {b['id']: b['name'] for b in bl}
    except Exception:
        maps['bloodline'] = {}
    try:
        iv = json.loads(urlopen(f'{base}/sprite/individual/list.json').read())
        maps['individual'] = {item['id']: item['name'] for item in iv}
    except Exception:
        maps['individual'] = {}
    _maps_cache = maps
    return maps


def parse_base64(s: str) -> int:
    s = s.replace('~', '').replace('-', '+').replace('_', '/')
    result = 0
    n = len(s)
    for i, ch in enumerate(s):
        result += BASE64_CHARS.index(ch) * (64 ** (n - i - 1))
    return result


def _null_if_zero(s: str) -> int | None:
    s = s.replace('~', '')
    if not s or all(c == '0' for c in s):
        return None
    return parse_base64(s)


def decode_roster(sharedata: str) -> dict:
    """解码分享码为结构化数据。"""
    version = parse_base64(sharedata[0:2])
    count = parse_base64(sharedata[2:3])
    pos = 3
    teams = []
    for _ in range(count):
        block = sharedata[pos:pos + 35]
        pos += 35
        ivs = []
        for k in range(3):
            iv = block[9 + k * 2: 9 + (k + 1) * 2]
            ivs.append(_null_if_zero(iv))
        skills = []
        for j in range(4):
            sk = block[15 + j * 5:15 + (j + 1) * 5]
            skills.append(_null_if_zero(sk))
        teams.append({
            'sprite_id': _null_if_zero(block[0:5]),
            'bloodline_id': _null_if_zero(block[5:7]),
            'personality_id': _null_if_zero(block[7:9]),
            'ivs': ivs,
            'skills': skills,
        })
    return {'version': version, 'count': count, 'teams': teams}


def format_roster(sharedata: str, maps: dict | None = None) -> list[dict]:
    """解码并翻译为可读名称。"""
    if maps is None:
        maps = _load_maps()
    data = decode_roster(sharedata)
    sm = maps.get('sprite', {})
    skm = maps.get('skill', {})
    cm = maps.get('character', {})
    bm = maps.get('bloodline', {})
    im = maps.get('individual', {})
    result = []
    for t in data['teams']:
        sid = str(t['sprite_id']) if t['sprite_id'] else None
        iv_labels = []
        for v in t['ivs']:
            if v is None:
                iv_labels.append(None)
            else:
                iv_labels.append(im.get(str(v - 78), str(v)))
        result.append({
            'sprite': sm.get(sid, f'ID:{sid}') if sid else None,
            'bloodline': bm.get(str(t['bloodline_id']), ''),
            'personality': cm.get(str(t['personality_id']), ''),
            'ivs': t['ivs'],
            'iv_labels': iv_labels,
            'skills': [skm.get(str(s), f'ID:{s}') if s else None for s in t['skills']],
        })
    return result
