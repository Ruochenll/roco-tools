"""
PVP截图上传 + 本地数据查询视图。
精灵基础信息和技能数据全部从本地 s2_data JSON 读取，零网络请求。
"""

import time
import json
from pathlib import Path

from django.conf import settings
from django.shortcuts import render

from .capture_pipeline import recognize_pets

WIKI_BASE = 'https://wiki.biligame.com/rocom/'

STAT_DISPLAY = ['hp', 'physical_attack', 'magical_attack',
                'physical_defense', 'magical_defense', 'speed']
STAT_LABELS_CN = {'hp': '生命', 'physical_attack': '物攻', 'magical_attack': '魔攻',
                  'physical_defense': '物防', 'magical_defense': '魔防', 'speed': '速度'}

# 本地数据（模块级懒加载，一次读、常驻内存）
_local_pets = None
_local_skills = None
_local_skill_idx = None  # pet_name → [ps_entry, ...]


def _load_local_data():
    """加载 s2_data 到内存并建索引。"""
    global _local_pets, _local_skills, _local_skill_idx
    if _local_pets is not None:
        return

    data_dir = settings.BASE_DIR / 'MD' / 's2_data'

    with open(data_dir / 'pets.json', encoding='utf-8') as f:
        _local_pets = {p['name']: p for p in json.load(f)}

    with open(data_dir / 'skills.json', encoding='utf-8') as f:
        _local_skills = {s['name']: s for s in json.load(f)}

    with open(data_dir / 'pet_skills.json', encoding='utf-8') as f:
        ps_list = json.load(f)
        _local_skill_idx = {}
        for ps in ps_list:
            _local_skill_idx.setdefault(ps['pet_name'], []).append(ps)


def _get_pet_skills(pet_name: str) -> list[dict]:
    """O(1) 索引查精灵技能。"""
    _load_local_data()
    results = []
    for ps in _local_skill_idx.get(pet_name, []):
        skill = _local_skills.get(ps['skill_name'])
        if skill:
            results.append({
                'name': skill['name'],
                'element': skill['element'],
                'category': skill['category'],
                'power': skill['power'],
                'energy_cost': skill.get('energy_cost', 0),
                'effect': skill.get('effect', ''),
                'icon': skill.get('icon', ''),
                'learn_method': ps['learn_method'],
                'learn_level': ps['learn_level'],
            })
        else:
            results.append({
                'name': ps['skill_name'],
                'learn_method': ps['learn_method'],
                'learn_level': ps['learn_level'],
            })
    results.sort(key=lambda x: (-(x.get('power') or 0), x.get('learn_level') or 99))
    return results


def _query_pet(name: str) -> dict | None:
    """从本地 pvent.json 查精灵基础数据。"""
    _load_local_data()
    pet = _local_pets.get(name)
    if not pet:
        return {'name': name, 'error': '本地数据中未找到'}

    stats = {k: pet.get(k, 0) for k in STAT_DISPLAY}
    max_stat = max(stats.values()) if stats else 170

    return {
        'name': name,
        'wiki_title': name,
        'elements': pet.get('elements', []),
        'stats': stats,
        'stat_order': [(STAT_LABELS_CN[k], k, stats[k]) for k in STAT_DISPLAY],
        'max_stat': max_stat,
        'wiki_url': WIKI_BASE + name,
        'image': None,  # 后续可从 static/images/pets/ 补
    }


def capture_page(request):
    """截图上传页面。"""
    return render(request, 'pvp/capture.html')


def capture_analyze(request):
    """处理上传截图 → 识别 → 查本地数据。"""
    if request.method != 'POST':
        return render(request, 'pvp/capture.html', {'error': '请上传截图'})

    file = request.FILES.get('screenshot')
    if not file:
        return render(request, 'pvp/capture.html', {'error': '请选择截图文件'})

    tmp_path = Path(settings.MEDIA_ROOT) / 'captures' / file.name
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp_path, 'wb+') as f:
        for chunk in file.chunks():
            f.write(chunk)

    t0 = time.time()

    # 识别精灵
    results = recognize_pets(str(tmp_path))
    t1 = time.time()

    # 本地查询（毫秒级，无延迟）
    for r in results:
        if r.get('name'):
            wiki = _query_pet(r['name'])
            r['wiki'] = wiki
            if wiki and 'error' not in wiki:
                r['skills'] = _get_pet_skills(r['name'])
        else:
            r['wiki'] = None
            r['skills'] = []
    t2 = time.time()

    errors = [r for r in results if 'error' in r]
    if errors and len(errors) >= len(results):
        return render(request, 'pvp/capture_result.html', {
            'error': errors[0]['error'],
            'results': results,
        })

    return render(request, 'pvp/capture_result.html', {
        'results': results,
        'errors': errors,
        'detect_time': round(t1 - t0, 2),
        'wiki_time': round(t2 - t1, 2),
    })
