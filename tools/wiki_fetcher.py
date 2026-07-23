"""
Wiki数据抓取与解析脚本
从 https://wiki.biligame.com/rocom/ 获取S2版本的精灵、技能、进化数据
解析Lua模块为结构化JSON，输出到 MD/s2_data/ 目录
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
import lupa

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
MD_DIR = BASE_DIR / 'MD'
OUTPUT_DIR = MD_DIR / 's2_data'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Wiki API 基础URL
WIKI_API = 'https://wiki.biligame.com/rocom/index.php'

# Lua模块列表
LUA_MODULES = {
    'Core': 'Module:PetData/Core',
    'Evolution': 'Module:PetData/Evolution',
    'SkillCatalog': 'Module:PetData/SkillCatalog',
    'LearnsetCatalog': 'Module:PetData/LearnsetCatalog',
    'LearnsetMapping': 'Module:PetData/Learnsets',
    'Index': 'Module:PetData/Index',
}

# 属性名称映射（Wiki格式 → 网站格式）
ELEMENT_MAP = {
    '光系': '光', '草系': '草', '火系': '火', '水系': '水',
    '地系': '地', '冰系': '冰', '龙系': '龙', '电系': '电',
    '毒系': '毒', '虫系': '虫', '武系': '武', '翼系': '翼',
    '萌系': '萌', '幽系': '幽', '恶系': '恶', '机械系': '机械',
    '幻系': '幻', '普通系': '普通',
    # 也支持直接匹配
    '光': '光', '草': '草', '火': '火', '水': '水',
    '地': '地', '冰': '冰', '龙': '龙', '电': '电',
    '毒': '毒', '虫': '虫', '武': '武', '翼': '翼',
    '萌': '萌', '幽': '幽', '恶': '恶', '机械': '机械',
    '幻': '幻', '普通': '普通',
}

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://wiki.biligame.com/rocom/',
})

API_URL = 'https://wiki.biligame.com/rocom/api.php'


def fetch_raw_module(module_name: str) -> str:
    """通过 MediaWiki API parse 获取Lua模块的原始wikitext"""
    print(f'  正在获取: {module_name} ...', end=' ', flush=True)
    params = {
        'action': 'parse',
        'page': module_name,
        'prop': 'wikitext',
        'format': 'json',
    }
    resp = SESSION.get(API_URL, params=params, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    
    if 'error' in data:
        raise RuntimeError(f"API Error: {data['error']}")
    
    text = data['parse']['wikitext']['*']
    print(f'({len(text)} 字符)')
    return text


def parse_lua_table(lua_text: str) -> dict:
    """
    使用 lupa 解析 Lua table
    去除 require 语句避免依赖问题
    """
    # 移除 require 语句 (Module:PetData/Skills 中有引用)
    cleaned = re.sub(r'local\s+\w+\s*=\s*require\s*\(.+\).*', '', lua_text)
    cleaned = re.sub(r'require\s*\(.+\).*', '', cleaned)
    
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    
    # 将 text 包装成函数以获取 return 值
    try:
        func = lua.eval(f'function() {cleaned} end')
        result = func()
    except Exception as e:
        print(f'  [错误] Lua 解析失败: {e}')
        # 尝试提取 return 后面的内容
        match = re.search(r'return\s*(\{.+\})', cleaned, re.DOTALL)
        if match:
            try:
                func = lua.eval(f'function() return {match.group(1)} end')
                result = func()
            except Exception as e2:
                print(f'  [错误] 二次解析也失败: {e2}')
                raise
        else:
            raise
    
    # 转换为纯 Python dict（去除 Lua 类型的代理）
    return lua_to_python(result)


def lua_to_python(obj) -> any:
    """递归将 lupa 的 Lua 对象转换为原生 Python 对象"""
    import lupa.lua54 as lua_mod
    
    if obj is None:
        return None
    if isinstance(obj, lua_mod.LuaRuntime):
        return None
    if isinstance(obj, bool):
        return bool(obj)
    if isinstance(obj, (int, float)):
        return obj
    if isinstance(obj, str):
        return obj
    
    # 检查是否是 lupa table
    if hasattr(obj, 'items') and hasattr(obj, 'keys'):
        try:
            # 先收集所有键值对
            raw_items = {}
            all_keys_are_ints = True
            max_key = 0
            
            for k in obj.keys():
                python_key = lua_to_python(k)
                python_val = lua_to_python(obj[k])
                if python_val is not None and not callable(python_val):
                    raw_items[python_key] = python_val
                    if isinstance(python_key, int) and python_key > 0:
                        max_key = max(max_key, python_key)
                    else:
                        all_keys_are_ints = False
            
            # 判断是否为 Lua 数组（键从1开始连续）
            if all_keys_are_ints and len(raw_items) > 0:
                # 检查是否是连续的 1..N
                expected_keys = set(range(1, max_key + 1))
                actual_keys = set(raw_items.keys())
                if actual_keys == expected_keys:
                    # 是数组
                    result = []
                    for i in range(1, max_key + 1):
                        result.append(raw_items[i])
                    return result
            
            return raw_items
        except Exception:
            pass
    
    # 基本类型
    if isinstance(obj, bool):
        return bool(obj)
    if isinstance(obj, (int, float)):
        return obj
    if isinstance(obj, str):
        return obj
    
    # 降级：转字符串
    try:
        return str(obj)
    except Exception:
        return None


def parse_height(height_str: str) -> tuple:
    """解析身高字符串 '0.53~0.75M' → (0.53, 0.75)"""
    if not height_str:
        return (0, 0)
    # 去除单位
    cleaned = height_str.upper().replace('M', '').replace('CM', '').strip()
    parts = cleaned.split('~')
    if len(parts) == 2:
        try:
            return (float(parts[0]), float(parts[1]))
        except ValueError:
            return (0, 0)
    try:
        val = float(cleaned)
        return (val, val)
    except ValueError:
        return (0, 0)


def parse_weight(weight_str: str) -> tuple:
    """解析体重字符串 '3.62~4.6KG' → (3.62, 4.6)"""
    if not weight_str:
        return (0, 0)
    cleaned = weight_str.upper().replace('KG', '').replace('G', '').strip()
    parts = cleaned.split('~')
    if len(parts) == 2:
        try:
            return (float(parts[0]), float(parts[1]))
        except ValueError:
            return (0, 0)
    try:
        val = float(cleaned)
        return (val, val)
    except ValueError:
        return (0, 0)


def map_elements(wiki_elements: list) -> list:
    """将 Wiki 属性格式映射为网站格式"""
    result = []
    for elem in wiki_elements:
        mapped = ELEMENT_MAP.get(elem, elem)
        if mapped not in result:
            result.append(mapped)
    return result


def convert_pets(core_data: dict, skill_catalog: dict, evo_data: dict, index_data: dict) -> list:
    """
    将 Core 模块数据转换为我们网站 pets.json 格式
    """
    pets = []
    
    # 构建进化链查找（找到每个精灵的进化关系）
    # evo_data: {evo_000001: {name, chain: [{id, name, stage, level, cond}, ...]}}
    
    # 构建 title 到 name 的映射（用于进化from/to查找）
    title_to_name = {}
    if 'titles' in index_data:
        for pet_id, title in index_data['titles'].items():
            title_to_name[str(title)] = str(pet_id)
    
    # 构建 pet_id → evolution info
    pet_evo_map = {}  # pet_id → {evolves_to: [pet_ids], evolves_from: pet_id, condition, level}
    for evo_key, evo in evo_data.items():
        if not isinstance(evo, dict) or 'chain' not in evo:
            continue
        chain = evo['chain']
        if not isinstance(chain, (list, tuple)):
            continue
        chain = list(chain)
        for i, stage in enumerate(chain):
            if not isinstance(stage, dict):
                continue
            pid = str(stage.get('id', ''))
            if not pid:
                continue
            if pid not in pet_evo_map:
                pet_evo_map[pid] = {
                    'evolves_to': [],
                    'evolves_from': None,
                    'condition': '',
                    'level': None,
                    'evo_chain': str(evo_key),
                    'evo_chain_name': str(evo.get('name', '')),
                }
            # 下一阶段
            if i + 1 < len(chain):
                next_stage = chain[i + 1]
                if isinstance(next_stage, dict):
                    pet_evo_map[pid]['evolves_to'].append(str(next_stage.get('id', '')))
            # 上一阶段
            if i > 0:
                prev_stage = chain[i - 1]
                if isinstance(prev_stage, dict):
                    pet_evo_map[pid]['evolves_from'] = str(prev_stage.get('id', ''))
                    pet_evo_map[pid]['condition'] = str(stage.get('cond', ''))
                    pet_evo_map[pid]['level'] = stage.get('level')
    
    # 分类收集所有pet_id
    valid_ids = set(core_data.keys()) & set(index_data.get('titles', {}).keys())
    
    for pet_id in sorted(valid_ids):
        pet = core_data[pet_id]
        if not isinstance(pet, dict):
            continue
        
        # 基础字段
        name = str(pet.get('n', ''))
        if not name:
            continue
        
        # 属性
        elements = map_elements(pet.get('tp', []))
        
        # 种族值
        stats = pet.get('st', {})
        if isinstance(stats, dict):
            hp = int(stats.get('hp', 0))
            physical_attack = int(stats.get('at', 0))
            magical_attack = int(stats.get('sa', 0))
            physical_defense = int(stats.get('df', 0))
            magical_defense = int(stats.get('sd', 0))
            speed = int(stats.get('se', 0))
        else:
            hp = physical_attack = magical_attack = physical_defense = magical_defense = speed = 0
        
        # 身高体重
        h_min, h_max = parse_height(str(pet.get('ht', '')))
        w_min, w_max = parse_weight(str(pet.get('wt', '')))
        
        # 特性（通过 SkillCatalog 查找 fs skill ID）
        ability_name = ''
        ability_effect = ''
        fs_skill_id = str(pet.get('fs', ''))
        if fs_skill_id and fs_skill_id in skill_catalog:
            skill_info = skill_catalog[fs_skill_id]
            if isinstance(skill_info, dict):
                ability_name = str(skill_info.get('name', ''))
                ability_effect = str(skill_info.get('desc', ''))
        
        # 描述
        description = str(pet.get('d', ''))
        
        # 分布地区
        distribution = str(pet.get('hb', {}).get('i', '')) if isinstance(pet.get('hb'), dict) else ''
        
        # 形态
        stage = int(pet.get('sg', 1))
        form = str(pet.get('f', ''))
        title = index_data.get('titles', {}).get(pet_id, name)
        
        # 是否为最终形态
        evo_info = pet_evo_map.get(pet_id, {})
        is_final = len(evo_info.get('evolves_to', [])) == 0
        
        # 图片
        img_info = pet.get('img', {})
        if isinstance(img_info, dict):
            image = str(img_info.get('il', ''))  # 立绘
            if image:
                image = image + '.png'
        else:
            image = ''
        
        # 特性图标
        ability_icon = ''
        if ability_name:
            ability_icon = ability_name + '.png'
        
        pets.append({
            'name': name,
            'elements': elements,
            'ability_name': ability_name,
            'ability_effect': ability_effect,
            'description': description,
            'distribution': distribution,
            'height_min': h_min,
            'height_max': h_max,
            'weight_min': w_min,
            'weight_max': w_max,
            'hp': hp,
            'physical_attack': physical_attack,
            'magical_attack': magical_attack,
            'physical_defense': physical_defense,
            'magical_defense': magical_defense,
            'speed': speed,
            'image': image,
            'ability_icon': ability_icon,
            'form': form,
            'is_final': is_final,
            # S2 附加信息（用于diff）
            '_wiki_id': pet_id,
            '_wiki_title': title,
            '_stage': stage,
            '_evo_chain': evo_info.get('evo_chain', ''),
        })
    
    return pets


def convert_skills(skill_catalog: dict) -> list:
    """
    将 SkillCatalog 数据转换为我们网站 skills.json 格式
    只提取非特性类技能（category != '特性'）
    """
    skills = []
    
    for skill_id, skill in skill_catalog.items():
        if not isinstance(skill, dict):
            continue
        
        name = str(skill.get('name', ''))
        if not name:
            continue
        
        # 分类映射
        category = str(skill.get('category', '攻击'))
        # Wiki: 攻击→物攻/魔攻需看 damage_class
        damage_class = str(skill.get('damage_class', '物理'))
        wiki_category = str(skill.get('category', ''))
        
        if wiki_category == '特性':
            continue  # 特性在精灵数据中处理
        
        if wiki_category == '状态':
            cat = '状态'
        elif wiki_category == '防御':
            cat = '防御'
        elif '魔' in damage_class:
            cat = '魔攻'
        else:
            cat = '物攻'
        
        # 元素映射
        element_raw = str(skill.get('element', '无系别'))
        element = ELEMENT_MAP.get(element_raw, '普通')
        
        power = int(skill.get('power', 0))
        energy_cost = int(skill.get('energy', 0))
        desc = str(skill.get('desc', ''))
        icon_id = int(skill.get('icon_id', 0))
        
        skills.append({
            'name': name,
            'element': element,
            'category': cat,
            'power': power,
            'energy_cost': energy_cost,
            'effect': desc,
            'icon': f'skill_{icon_id}.png' if icon_id else '',
            '_wiki_id': skill_id,
            '_wiki_skill_id': int(skill.get('id', 0)),
        })
    
    return skills


def convert_evolutions(pet_data: dict, evo_data: dict) -> list:
    """
    将 Evolution 模块数据转换为我们网站 evolutions.json 格式
    """
    evolutions = []
    
    # 构建 pet_id → pet_name 映射
    id_to_name = {}
    for pet_id, pet in pet_data.items():
        if isinstance(pet, dict):
            id_to_name[str(pet_id)] = str(pet.get('n', ''))
    
    for evo_key, evo in evo_data.items():
        if not isinstance(evo, dict) or 'chain' not in evo:
            continue
        chain = evo['chain']
        if not isinstance(chain, (list, tuple)):
            continue
        chain = list(chain)
        
        for i in range(len(chain) - 1):
            stage = chain[i]
            next_stage = chain[i + 1]
            if not isinstance(stage, dict) or not isinstance(next_stage, dict):
                continue
            
            pet_from_id = str(stage.get('id', ''))
            pet_to_id = str(next_stage.get('id', ''))
            
            pet_from_name = id_to_name.get(pet_from_id, pet_from_id)
            pet_to_name = id_to_name.get(pet_to_id, pet_to_id)
            
            condition = str(next_stage.get('cond', ''))
            level = next_stage.get('level')
            
            if level is not None:
                if condition:
                    condition = f'等级{int(level)}且{condition}'
                else:
                    condition = f'等级{int(level)}'
            
            evolutions.append({
                'pet_from': pet_from_name,
                'pet_to': pet_to_name,
                'condition': condition,
                '_from_id': pet_from_id,
                '_to_id': pet_to_id,
                '_evo_key': str(evo_key),
            })
    
    return evolutions


def convert_pet_skills(learnset_catalog: dict, learnset_mapping: dict,
                       pet_data: dict, skill_catalog: dict) -> list:
    """
    将 LearnsetCatalog + LearnsetMapping 转换为我们网站 pet_skills.json 格式
    """
    pet_skills = []
    
    # 构建 skill_id → skill_name 映射
    skill_id_to_name = {}
    for sid, skill in skill_catalog.items():
        if isinstance(skill, dict):
            skill_id_to_name[str(sid)] = str(skill.get('name', ''))
    
    # 构建 pet_id → pet_name 映射
    id_to_name = {}
    for pet_id, pet in pet_data.items():
        if isinstance(pet, dict):
            id_to_name[str(pet_id)] = str(pet.get('n', ''))
    
    # 遍历 learnset_mapping (pet_id → learnset_id)
    for pet_id, learnset_id in learnset_mapping.items():
        pet_id_str = str(pet_id)
        learnset_id_str = str(learnset_id)
        
        pet_name = id_to_name.get(pet_id_str, '')
        if not pet_name:
            continue
        
        learnset = learnset_catalog.get(learnset_id_str, {})
        if not isinstance(learnset, dict):
            continue
        
        # 1. 自然习得技能 (ns) → 升级
        ns_skills = learnset.get('ns', {})
        if isinstance(ns_skills, (list, tuple)):
            for entry in ns_skills:
                if not isinstance(entry, dict):
                    continue
                skill_id = str(entry.get('sk', ''))
                skill_name = skill_id_to_name.get(skill_id, skill_id)
                level = entry.get('lv')
                
                pet_skills.append({
                    'pet_name': pet_name,
                    'skill_name': skill_name,
                    'learn_method': '升级',
                    'learn_level': int(level) if level is not None else None,
                    '_pet_id': pet_id_str,
                    '_skill_id': skill_id,
                })
        
        # 2. 血脉技能 (bs) → 血脉技能
        bs_skills = learnset.get('bs', {})
        if isinstance(bs_skills, (list, tuple)):
            for entry in bs_skills:
                if not isinstance(entry, dict):
                    continue
                skill_id = str(entry.get('sk', ''))
                skill_name = skill_id_to_name.get(skill_id, skill_id)
                
                pet_skills.append({
                    'pet_name': pet_name,
                    'skill_name': skill_name,
                    'learn_method': '血脉技能',
                    'learn_level': None,
                    '_pet_id': pet_id_str,
                    '_skill_id': skill_id,
                })
        
        # 3. 技能石技能 (ss) → 技能石
        ss_skills = learnset.get('ss', {})
        if isinstance(ss_skills, (list, tuple)):
            for skill_id in ss_skills:
                skill_id_str = str(skill_id)
                skill_name = skill_id_to_name.get(skill_id_str, skill_id_str)
                
                pet_skills.append({
                    'pet_name': pet_name,
                    'skill_name': skill_name,
                    'learn_method': '技能石',
                    'learn_level': None,
                    '_pet_id': pet_id_str,
                    '_skill_id': skill_id_str,
                })
    
    return pet_skills


def main():
    print('=' * 60)
    print('洛克王国世界 Wiki 数据抓取工具 (S2版本)')
    print('=' * 60)
    
    # ========== Step 1: 抓取所有Lua模块 ==========
    print('\n[1/6] 抓取所有Lua数据模块...')
    raw_modules = {}
    for key, module_name in LUA_MODULES.items():
        raw_modules[key] = fetch_raw_module(module_name)
    
    # ========== Step 2: 解析Lua模块 ==========
    print('\n[2/6] 解析Lua数据...')
    parsed = {}
    for key in ['Core', 'Evolution', 'SkillCatalog', 'LearnsetCatalog', 'LearnsetMapping', 'Index']:
        print(f'  解析 {key} ...', end=' ')
        try:
            parsed[key] = parse_lua_table(raw_modules[key])
            if isinstance(parsed[key], dict):
                print(f'({len(parsed[key])} 条记录)')
            else:
                print(f'(类型: {type(parsed[key]).__name__})')
        except Exception as e:
            print(f'失败: {e}')
            parsed[key] = {}
    
    # ========== Step 3: 保存原始解析数据 ==========
    print('\n[3/6] 保存原始解析数据...')
    for key, data in parsed.items():
        fname = OUTPUT_DIR / f'_raw_{key}.json'
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'  已保存: {fname.name}')
    
    # ========== Step 4: 转换为网站格式 ==========
    print('\n[4/6] 转换为网站数据格式...')
    
    # 精灵数据
    print('  转换精灵数据...')
    pets = convert_pets(
        parsed.get('Core', {}),
        parsed.get('SkillCatalog', {}),
        parsed.get('Evolution', {}),
        parsed.get('Index', {}),
    )
    with open(OUTPUT_DIR / 'pets.json', 'w', encoding='utf-8') as f:
        json.dump(pets, f, ensure_ascii=False, indent=2)
    print(f'  → 精灵: {len(pets)} 条')
    
    # 技能数据
    print('  转换技能数据...')
    skills = convert_skills(parsed.get('SkillCatalog', {}))
    with open(OUTPUT_DIR / 'skills.json', 'w', encoding='utf-8') as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)
    print(f'  → 技能: {len(skills)} 条')
    
    # 进化数据
    print('  转换进化数据...')
    evolutions = convert_evolutions(
        parsed.get('Core', {}),
        parsed.get('Evolution', {}),
    )
    with open(OUTPUT_DIR / 'evolutions.json', 'w', encoding='utf-8') as f:
        json.dump(evolutions, f, ensure_ascii=False, indent=2)
    print(f'  → 进化: {len(evolutions)} 条')
    
    # 精灵技能关联
    print('  转换精灵技能关联...')
    pet_skills = convert_pet_skills(
        parsed.get('LearnsetCatalog', {}),
        parsed.get('LearnsetMapping', {}),
        parsed.get('Core', {}),
        parsed.get('SkillCatalog', {}),
    )
    with open(OUTPUT_DIR / 'pet_skills.json', 'w', encoding='utf-8') as f:
        json.dump(pet_skills, f, ensure_ascii=False, indent=2)
    print(f'  → 精灵技能关联: {len(pet_skills)} 条')
    
    # ========== Step 5: 保存元素类型 ==========
    print('\n[5/6] 提取元素类型...')
    all_elements = set()
    for pet in pets:
        for elem in pet['elements']:
            all_elements.add(elem)
    for skill in skills:
        all_elements.add(skill['element'])
    
    elements = [{'name': e, 'icon': f'{e}.png'} for e in sorted(all_elements)]
    with open(OUTPUT_DIR / 'elements.json', 'w', encoding='utf-8') as f:
        json.dump(elements, f, ensure_ascii=False, indent=2)
    print(f'  → 元素: {len(elements)} 种 ({sorted(all_elements)})')
    
    # ========== 总结 ==========
    print('\n' + '=' * 60)
    print('数据抓取完成！')
    print(f'  精灵:     {len(pets)} 条')
    print(f'  技能:     {len(skills)} 条')
    print(f'  进化:     {len(evolutions)} 条')
    print(f'  技能关联: {len(pet_skills)} 条')
    print(f'  元素:     {len(elements)} 种')
    print(f'  输出目录: {OUTPUT_DIR}')
    print('=' * 60)


if __name__ == '__main__':
    main()
