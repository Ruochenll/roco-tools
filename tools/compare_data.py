"""
S1 vs S2 数据差异对比工具
比较网站S1数据库与Wiki S2数据，生成结构化差异报告
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from pets.models import Pet, Skill, PetSkill, Evolution, ElementType

S2_DIR = BASE_DIR / 'MD' / 's2_data'


def load_s2_data():
    """加载S2 JSON数据"""
    with open(S2_DIR / 'pets.json', 'r', encoding='utf-8') as f:
        pets = json.load(f)
    with open(S2_DIR / 'skills.json', 'r', encoding='utf-8') as f:
        skills = json.load(f)
    with open(S2_DIR / 'evolutions.json', 'r', encoding='utf-8') as f:
        evolutions = json.load(f)
    with open(S2_DIR / 'pet_skills.json', 'r', encoding='utf-8') as f:
        pet_skills = json.load(f)
    return pets, skills, evolutions, pet_skills


def parse_name_form(full_name: str, form_field: str = '') -> tuple:
    """
    解析精灵名称，提取(基础名称, 形态)
    S1: "丢丢（火山附近的样子）" → ("丢丢", "火山附近的样子")
    S1: "迪莫" → ("迪莫", "原始形态")
    S2: name="丢丢", form="火山附近的样子" → ("丢丢", "火山附近的样子")
    """
    # 尝试从全名中提取括号内的形态
    match = re.match(r'^(.+?)（(.+?)）$', full_name)
    if match:
        base = match.group(1)
        form = match.group(2)
    else:
        base = full_name
        form = form_field if form_field else '原始形态'
    return base.strip(), form.strip()


def is_valid_pet_s1(pet) -> bool:
    """判断S1精灵是否为有效数据（有实质种族值）"""
    return not (pet.hp == 0 and pet.physical_attack == 0 and pet.magical_attack == 0
                and pet.physical_defense == 0 and pet.magical_defense == 0 and pet.speed == 0)


def is_valid_pet_s2(pet_data: dict) -> bool:
    """判断S2精灵是否为有效数据"""
    return not (pet_data['hp'] == 0 and pet_data['physical_attack'] == 0
                and pet_data['magical_attack'] == 0 and pet_data['physical_defense'] == 0
                and pet_data['magical_defense'] == 0 and pet_data['speed'] == 0)


def compare_pets(s1_pets, s2_pets):
    """比较精灵数据 - 使用 (基础名称, 形态) 进行智能匹配"""
    
    # 构建 S2 索引: (base_name, form) → pet_data
    s2_index = {}
    s2_by_base = defaultdict(list)  # base_name → [(form, pet_data), ...]
    s2_stats = {'total': len(s2_pets), 'valid': 0, 'empty': 0}
    
    for p in s2_pets:
        base, form = parse_name_form(p['name'], p.get('form', ''))
        key = (base, form)
        s2_index[key] = p
        s2_by_base[base].append((form, p))
        if is_valid_pet_s2(p):
            s2_stats['valid'] += 1
        else:
            s2_stats['empty'] += 1
    
    # 构建 S1 索引
    s1_index = {}
    s1_stats = {'total': s1_pets.count(), 'valid': 0, 'empty': 0}
    
    for pet in s1_pets:
        base, form = parse_name_form(pet.name, pet.form)
        key = (base, form)
        # 避免重名覆蓋(S1可能有)
        if key not in s1_index:
            s1_index[key] = pet
        if is_valid_pet_s1(pet):
            s1_stats['valid'] += 1
        else:
            s1_stats['empty'] += 1
    
    s1_keys = set(s1_index.keys())
    s2_keys = set(s2_index.keys())
    
    # 新增: S2有但S1没有的(base, form)
    added_keys = s2_keys - s1_keys
    # 移除: S1有但S2没有的(base, form)
    removed_keys = s1_keys - s2_keys
    
    # 分离空壳和有效数据
    added = []
    added_empty = []
    for key in sorted(added_keys):
        p = s2_index[key]
        label = f'{key[0]}（{key[1]}）' if key[1] != '原始形态' else key[0]
        entry = {'name': label, 'base': key[0], 'form': key[1]}
        if is_valid_pet_s2(p):
            added.append(entry)
        else:
            added_empty.append(entry)
    
    removed = []
    removed_empty = []
    for key in sorted(removed_keys):
        pet = s1_index[key]
        label = f'{key[0]}（{key[1]}）' if key[1] != '原始形态' else key[0]
        entry = {'name': label, 'base': key[0], 'form': key[1]}
        if is_valid_pet_s1(pet):
            removed.append(entry)
        else:
            removed_empty.append(entry)
    
    # 数值比较字段
    NUMERIC_FIELDS = [
        ('hp', '生命'),
        ('physical_attack', '物攻'),
        ('magical_attack', '魔攻'),
        ('physical_defense', '物防'),
        ('magical_defense', '魔防'),
        ('speed', '速度'),
    ]
    
    STAT_FIELDS = [
        ('height_min', '身高最小值'),
        ('height_max', '身高最大值'),
        ('weight_min', '体重最小值'),
        ('weight_max', '体重最大值'),
    ]
    
    TEXT_FIELDS = [
        ('ability_name', '特性名称'),
        ('ability_effect', '特性效果'),
        ('description', '描述'),
    ]
    
    # 找到双方共有的(base, form)进行比较
    common_keys = s1_keys & s2_keys
    changed = []
    
    for key in sorted(common_keys):
        s1 = s1_index[key]
        s2 = s2_index[key]
        
        # 跳过双方都是空壳的
        if not is_valid_pet_s1(s1) and not is_valid_pet_s2(s2):
            continue
        
        changes = []
        
        # 属性变更
        s1_elems = set(s1.elements.values_list('name', flat=True))
        s2_elems = set(s2['elements'])
        if s1_elems != s2_elems:
            changes.append({
                'field': '属性',
                'label': '属性',
                'old': '、'.join(sorted(s1_elems)),
                'new': '、'.join(sorted(s2_elems)),
            })
        
        # 种族值变更
        for field, label in NUMERIC_FIELDS:
            old_val = getattr(s1, field, 0)
            new_val = s2.get(field, 0)
            if old_val != new_val:
                changes.append({
                    'field': field,
                    'label': label,
                    'old': old_val,
                    'new': new_val,
                    'delta': new_val - old_val,
                })
        
        # 身高体重变更
        for field, label in STAT_FIELDS:
            old_val = getattr(s1, field, 0)
            new_val = s2.get(field, 0)
            if abs(old_val - new_val) > 0.01:
                changes.append({
                    'field': field,
                    'label': label,
                    'old': round(old_val, 2),
                    'new': round(new_val, 2),
                    'delta': round(new_val - old_val, 2),
                })
        
        # 文本变更
        for field, label in TEXT_FIELDS:
            old_val = (getattr(s1, field, '') or '').strip()
            new_val = (s2.get(field, '') or '').strip()
            if old_val != new_val:
                changes.append({
                    'field': field,
                    'label': label,
                    'old': old_val[:200],
                    'new': new_val[:200],
                })
        
        # 是否为最终形态
        s1_final = s1.is_final
        s2_final = s2.get('is_final', False)
        if s1_final != s2_final:
            changes.append({
                'field': 'is_final',
                'label': '最终形态',
                'old': s1_final,
                'new': s2_final,
            })
        
        if changes:
            label = f'{key[0]}（{key[1]}）' if key[1] != '原始形态' else key[0]
            changed.append({
                'name': label,
                'changes': changes,
                's1_elements': list(s1_elems),
                's2_elements': list(s2_elems),
            })
    
    return {
        'added': added,
        'added_empty': added_empty,
        'removed': removed,
        'removed_empty': removed_empty,
        'changed': sorted(changed, key=lambda x: x['name']),
        'stats': {
            's1_total': s1_stats['total'],
            's1_valid': s1_stats['valid'],
            's1_empty': s1_stats['empty'],
            's2_total': s2_stats['total'],
            's2_valid': s2_stats['valid'],
            's2_empty': s2_stats['empty'],
        },
    }


def compare_skills(s1_skills, s2_skills):
    """比较技能数据"""
    s1_names = {s.name for s in s1_skills}
    s2_names = {s['name'] for s in s2_skills}
    
    s1_by_name = {s.name: s for s in s1_skills}
    s2_by_name = {s['name']: s for s in s2_skills}
    
    added = [n for n in s2_names - s1_names]
    removed = [n for n in s1_names - s2_names]
    
    NUMERIC_FIELDS = [
        ('power', '威力'),
        ('energy_cost', '能耗'),
    ]
    
    TEXT_FIELDS = [
        ('effect', '效果'),
    ]
    
    changed = []
    for name in s1_names & s2_names:
        s1 = s1_by_name[name]
        s2 = s2_by_name[name]
        
        changes = []
        
        # 属性变更
        s1_elem = s1.element.name
        s2_elem = s2['element']
        if s1_elem != s2_elem:
            changes.append({
                'field': 'element',
                'label': '属性',
                'old': s1_elem,
                'new': s2_elem,
            })
        
        # 分类变更
        s1_cat = s1.category
        s2_cat = s2['category']
        if s1_cat != s2_cat:
            changes.append({
                'field': 'category',
                'label': '分类',
                'old': s1_cat,
                'new': s2_cat,
            })
        
        # 数值变更
        for field, label in NUMERIC_FIELDS:
            old_val = getattr(s1, field, 0)
            new_val = s2.get(field, 0)
            if old_val != new_val:
                changes.append({
                    'field': field,
                    'label': label,
                    'old': old_val,
                    'new': new_val,
                    'delta': new_val - old_val,
                })
        
        # 效果描述 (field name in S2 is 'effect')
        old_desc = (s1.description or '').strip()
        new_desc = (s2.get('effect', '') or '').strip()
        if old_desc != new_desc:
            changes.append({
                'field': 'description',
                'label': '效果描述',
                'old': old_desc[:200],
                'new': new_desc[:200],
            })
        
        if changes:
            changed.append({
                'name': name,
                'changes': changes,
            })
    
    return {
        'added': sorted(added),
        'removed': sorted(removed),
        'changed': sorted(changed, key=lambda x: x['name']),
        'total_s1': len(s1_names),
        'total_s2': len(s2_names),
    }


def compare_pet_skills(s1_pet_skills, s2_pet_skills):
    """比较精灵技能关联"""
    # 构建 (pet_name, skill_name, learn_method) 的集合
    s1_set = set()
    for ps in s1_pet_skills:
        s1_set.add((ps.pet.name, ps.skill.name, ps.learn_method))
    
    s2_set = set()
    for ps in s2_pet_skills:
        s2_set.add((ps['pet_name'], ps['skill_name'], ps['learn_method']))
    
    added = sorted(s2_set - s1_set)
    removed = sorted(s1_set - s2_set)
    
    return {
        'added': added,
        'removed': removed,
        'total_s1': len(s1_set),
        'total_s2': len(s2_set),
    }


def compare_evolutions(s1_evos, s2_evos):
    """比较进化链"""
    s1_set = set()
    for evo in s1_evos:
        s1_set.add((evo.pet_from.name, evo.pet_to.name))
    
    s2_set = set()
    for evo in s2_evos:
        s2_set.add((evo['pet_from'], evo['pet_to']))
    
    added = sorted(s2_set - s1_set)
    removed = sorted(s1_set - s2_set)
    
    return {
        'added': added,
        'removed': removed,
        'total_s1': len(s1_set),
        'total_s2': len(s2_set),
    }


def main():
    print('=' * 60)
    print('S1 ↔ S2 数据差异对比 (智能名称匹配)')
    print('=' * 60)
    
    # 加载S2数据
    print('\n加载S2数据...')
    s2_pets, s2_skills, s2_evos, s2_pet_skills = load_s2_data()
    
    # 加载S1数据
    print('加载S1数据库...')
    s1_pets = Pet.objects.all().prefetch_related('elements')
    s1_skills = Skill.objects.all().select_related('element')
    s1_pet_skills = PetSkill.objects.all().select_related('pet', 'skill')
    s1_evos = Evolution.objects.all().select_related('pet_from', 'pet_to')
    
    print(f'  S1: {s1_pets.count()} 精灵, {s1_skills.count()} 技能, '
          f'{s1_pet_skills.count()} 关联, {s1_evos.count()} 进化')
    print(f'  S2: {len(s2_pets)} 精灵, {len(s2_skills)} 技能, '
          f'{len(s2_pet_skills)} 关联, {len(s2_evos)} 进化')
    
    # 比较
    print('\n[1/4] 比较精灵数据 (按 基础名称+形态 智能匹配)...')
    pet_diff = compare_pets(s1_pets, s2_pets)
    stats = pet_diff['stats']
    print(f'  S1: {stats["s1_total"]} 总数 ({stats["s1_valid"]} 有效 + {stats["s1_empty"]} 空壳)')
    print(f'  S2: {stats["s2_total"]} 总数 ({stats["s2_valid"]} 有效 + {stats["s2_empty"]} 空壳)')
    print(f'  有效新增: {len(pet_diff["added"])}, 空壳新增: {len(pet_diff["added_empty"])}')
    print(f'  有效移除: {len(pet_diff["removed"])}, 空壳移除: {len(pet_diff["removed_empty"])}')
    print(f'  数值变更: {len(pet_diff["changed"])}')
    
    print('[2/4] 比较技能数据...')
    skill_diff = compare_skills(s1_skills, s2_skills)
    print(f'  新增: {len(skill_diff["added"])}, 删除: {len(skill_diff["removed"])}, '
          f'变更: {len(skill_diff["changed"])}')
    
    print('[3/4] 比较进化数据...')
    evo_diff = compare_evolutions(s1_evos, s2_evos)
    print(f'  新增: {len(evo_diff["added"])}, 删除: {len(evo_diff["removed"])}')
    
    print('[4/4] 比较技能关联...')
    ps_diff = compare_pet_skills(s1_pet_skills, s2_pet_skills)
    print(f'  新增: {len(ps_diff["added"])}, 删除: {len(ps_diff["removed"])}')
    
    # 保存差异报告
    report = {
        'summary': {
            's1_total_pets': stats['s1_total'],
            's1_valid_pets': stats['s1_valid'],
            's1_empty_pets': stats['s1_empty'],
            's2_total_pets': stats['s2_total'],
            's2_valid_pets': stats['s2_valid'],
            's2_empty_pets': stats['s2_empty'],
            's1_skills': s1_skills.count(),
            's2_skills': len(s2_skills),
            'pet_added': len(pet_diff['added']),
            'pet_added_empty': len(pet_diff['added_empty']),
            'pet_removed': len(pet_diff['removed']),
            'pet_removed_empty': len(pet_diff['removed_empty']),
            'pet_changed': len(pet_diff['changed']),
            'skill_added': len(skill_diff['added']),
            'skill_removed': len(skill_diff['removed']),
            'skill_changed': len(skill_diff['changed']),
            'evo_added': len(evo_diff['added']),
            'evo_removed': len(evo_diff['removed']),
            'ps_added': len(ps_diff['added']),
            'ps_removed': len(ps_diff['removed']),
        },
        'pets': pet_diff,
        'skills': skill_diff,
        'evolutions': evo_diff,
        'pet_skills': ps_diff,
    }
    
    output_path = S2_DIR / 'diff_report.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f'\n差异报告已保存: {output_path}')
    print(f'文件大小: {output_path.stat().st_size / 1024:.1f} KB')
    
    # 打印摘要
    print('\n' + '=' * 60)
    print('差异摘要 (仅有效数据)')
    print('=' * 60)
    summary = report['summary']
    print(f'精灵: S1有效={summary["s1_valid_pets"]} → S2有效={summary["s2_valid_pets"]} '
          f'(+{summary["pet_added"]} 新增, {summary["pet_removed"]} 移除, '
          f'{summary["pet_changed"]} 变更)')
    print(f'  [空壳: S1={summary["s1_empty_pets"]}个, S2={summary["s2_empty_pets"]}个]')
    print(f'技能: S1={summary["s1_skills"]} → S2={summary["s2_skills"]} '
          f'(+{summary["skill_added"]} 新增, {summary["skill_removed"]} 移除, '
          f'{summary["skill_changed"]} 变更)')
    print(f'进化: +{summary["evo_added"]} 新增, {summary["evo_removed"]} 移除')
    print(f'技能关联: +{summary["ps_added"]} 新增, {summary["ps_removed"]} 移除')


if __name__ == '__main__':
    main()
