"""
伤害计算器页面视图。
"""

from django.shortcuts import render


def _round(x: float) -> int:
    """四舍五入 (与Excel ROUND一致)"""
    return int(x + 0.5) if x >= 0 else int(x - 0.5)
from pets.models import Pet, PetSkill, Skill, ElementType, TypeMatchup
from .damage_calculator import (
    PetStats, SkillConfig, BattleContext, calc_pet_stats, quick_damage
)


def pet_search(request):
    """宠物搜索联想接口。"""
    query = request.GET.get('search', '').strip()
    element = request.GET.get('element', '').strip()

    pets = Pet.objects.prefetch_related('elements')
    if element:
        pets = pets.filter(elements__name=element)
    if query:
        pets = pets.filter(name__icontains=query)
    pets = pets.order_by('number')[:30]

    return render(request, 'pvp/pet_suggestions.html', {
        'pets': pets,
        'query': query,
        'active_element': element,
        'all_elements': ElementType.objects.all(),
    })


def damage_calc(request):
    """伤害计算器主页面。"""
    return render(request, 'pvp/damage_calc.html')


def _parse_pet_config(request, field):
    """从请求中解析精灵配置。"""
    talents = {}
    stat_keys = ['hp', 'physical_attack', 'magical_attack',
                 'physical_defense', 'magical_defense', 'speed']
    for key in stat_keys:
        t = request.GET.get(f'{field}_{key}_talent', '0').strip()
        talents[key] = int(t) if t.isdigit() else 0

    nature_up = request.GET.get(f'{field}_nature_up', '-')
    nature_down = request.GET.get(f'{field}_nature_down', '-')

    nature_map = {
        'hp': 'nature_hp', 'physical_attack': 'nature_pa',
        'magical_attack': 'nature_ma', 'physical_defense': 'nature_pd',
        'magical_defense': 'nature_md', 'speed': 'nature_sp',
    }
    nature_kwargs = {}
    for key in stat_keys:
        nature_kwargs[nature_map[key]] = (
            '↑' if key == nature_up else ('↓' if key == nature_down else '-')
        )

    return talents, nature_up, nature_down, nature_kwargs


def pet_stat_card(request):
    """HTMX：精灵面板值 + 天分/性格配置。"""
    pet_id = request.GET.get('pet_id')
    field = request.GET.get('field', 'att')

    if not pet_id:
        return render(request, 'pvp/pet_stat_card.html', {'pet': None, 'field': field})

    pet = Pet.objects.prefetch_related('elements').get(pk=pet_id)
    talents, nature_up, nature_down, nature_kwargs = _parse_pet_config(request, field)

    p = PetStats(
        hp=pet.hp, talent_hp=talents['hp'],
        physical_attack=pet.physical_attack, talent_pa=talents['physical_attack'],
        magical_attack=pet.magical_attack, talent_ma=talents['magical_attack'],
        physical_defense=pet.physical_defense, talent_pd=talents['physical_defense'],
        magical_defense=pet.magical_defense, talent_md=talents['magical_defense'],
        speed=pet.speed, talent_sp=talents['speed'],
        level=60, star=5, growth=0, **nature_kwargs,
    )
    final = calc_pet_stats(p)

    stats = [
        ('hp', '生命', final['hp'], talents['hp']),
        ('physical_attack', '物攻', final['physical_attack'], talents['physical_attack']),
        ('magical_attack', '魔攻', final['magical_attack'], talents['magical_attack']),
        ('physical_defense', '物防', final['physical_defense'], talents['physical_defense']),
        ('magical_defense', '魔防', final['magical_defense'], talents['magical_defense']),
        ('speed', '速度', final['speed'], talents['speed']),
    ]

    return render(request, 'pvp/pet_stat_card.html', {
        'pet': pet, 'stats': stats, 'field': field,
        'nature_up': nature_up, 'nature_down': nature_down,
    })


def pet_skills(request):
    """HTMX：返回精灵的所有可用技能（4个下拉选择栏）。"""
    pet_id = request.GET.get('pet_id')
    field = request.GET.get('field', 'att')

    skills = []
    if pet_id:
        pskills = (PetSkill.objects.filter(pet_id=pet_id)
                   .select_related('skill', 'skill__element')
                   .order_by('-skill__power', 'skill__name'))
        for ps in pskills:
            skills.append({
                'id': ps.skill.id,
                'name': ps.skill.name,
                'power': ps.skill.power,
                'category': ps.skill.category,
                'element': ps.skill.element.name,
                'energy_cost': ps.skill.energy_cost,
            })

    return render(request, 'pvp/pet_skills_panel.html', {
        'skills': skills, 'field': field,
    })


def calc_damages(request):
    """HTMX：计算 8 个技能的伤害结果（攻方4个 + 防方4个）。"""
    # 解析双方配置
    atk_talents, _, _, atk_nature = _parse_pet_config(request, 'att')
    def_talents, _, _, def_nature = _parse_pet_config(request, 'def')

    atk_id = request.GET.get('att_pet_id', '')
    def_id = request.GET.get('def_pet_id', '')
    if not atk_id or not def_id:
        return render(request, 'pvp/damage_results.html', {'error': '请选择双方精灵'})

    attacker = Pet.objects.prefetch_related('elements').get(pk=atk_id)
    defender = Pet.objects.prefetch_related('elements').get(pk=def_id)

    # 计算双方最终面板
    atk_p = PetStats(
        hp=attacker.hp, talent_hp=atk_talents['hp'],
        physical_attack=attacker.physical_attack, talent_pa=atk_talents['physical_attack'],
        magical_attack=attacker.magical_attack, talent_ma=atk_talents['magical_attack'],
        physical_defense=attacker.physical_defense, talent_pd=atk_talents['physical_defense'],
        magical_defense=attacker.magical_defense, talent_md=atk_talents['magical_defense'],
        speed=attacker.speed, talent_sp=atk_talents['speed'],
        level=60, star=5, growth=0, **atk_nature,
    )
    def_p = PetStats(
        hp=defender.hp, talent_hp=def_talents['hp'],
        physical_attack=defender.physical_attack, talent_pa=def_talents['physical_attack'],
        magical_attack=defender.magical_attack, talent_ma=def_talents['magical_attack'],
        physical_defense=defender.physical_defense, talent_pd=def_talents['physical_defense'],
        magical_defense=defender.magical_defense, talent_md=def_talents['magical_defense'],
        speed=defender.speed, talent_sp=def_talents['speed'],
        level=60, star=5, growth=0, **def_nature,
    )
    atk_final = calc_pet_stats(atk_p)
    def_final = calc_pet_stats(def_p)
    def_hp = def_final['hp']
    att_hp = atk_final['hp']

    # 收集 8 个技能
    results = []
    for side, pet, final_stats, other_elements in [
        ('att', attacker, atk_final, list(defender.elements.all())),
        ('def', defender, def_final, list(attacker.elements.all())),
    ]:
        for i in range(1, 5):
            sid = request.GET.get(f'{side}_skill_{i}', '')
            result = {'side': side, 'slot': i, 'name': '—', 'damage': None, 'percent': 0, 'pct_class': ''}
            if sid:
                try:
                    skill = Skill.objects.select_related('element').get(pk=sid)
                except Skill.DoesNotExist:
                    results.append(result)
                    continue

                if skill.power == 0 or skill.category not in ('物攻', '魔攻'):
                    result['name'] = f'{skill.name}'
                    result['damage'] = 0
                    result['label'] = skill.category
                    results.append(result)
                    continue

                is_physical = skill.category == '物攻'
                atk_val = final_stats['physical_attack'] if is_physical else final_stats['magical_attack']
                def_val = (def_final['physical_defense'] if is_physical
                           else def_final['magical_defense']) if side == 'att' else (
                           atk_final['physical_defense'] if is_physical
                           else atk_final['magical_defense'])

                # 类型倍率
                my_elements = list(pet.elements.all())
                is_stab = any(e == skill.element for e in my_elements)
                multiplier = 1.0
                type_details = []
                for de in other_elements:
                    m = TypeMatchup.objects.filter(
                        attacking_type=skill.element, defending_type=de
                    ).first()
                    if m:
                        multiplier += m.multiplier - 1  # 加法模型: 1+Σ(m-1)
                        type_details.append(f'{skill.element.name}→{de.name}: ×{m.multiplier}')
                multiplier = max(0.25, multiplier)  # 最低 0.25x

                # 强化层数：每个面板有独立 name，不会冲突
                if side == 'att':
                    pa_boost = int(request.GET.get('att_pa_boost', '0') or '0')
                    ma_boost = int(request.GET.get('att_ma_boost', '0') or '0')
                    pd_boost = int(request.GET.get('def_pd_boost', '0') or '0')
                    md_boost = int(request.GET.get('def_md_boost', '0') or '0')
                else:
                    pa_boost = int(request.GET.get('def_pa_boost', '0') or '0')
                    ma_boost = int(request.GET.get('def_ma_boost', '0') or '0')
                    pd_boost = int(request.GET.get('att_pd_boost', '0') or '0')
                    md_boost = int(request.GET.get('att_md_boost', '0') or '0')

                atk_boost = pa_boost if is_physical else ma_boost
                def_boost = pd_boost if is_physical else md_boost

                # 威力增加/威力加成/连击数（全局 + 单技能叠加）
                prefix = f'{side}_skill_{i}'
                global_pbonus = int(request.GET.get(f'{side}_power_bonus', '0') or '0')
                global_pmul = float(request.GET.get(f'{side}_power_mul', '1') or '1')
                global_combo = int(request.GET.get(f'{side}_combo', '1') or '1')
                skill_pbonus = int(request.GET.get(f'{prefix}_pbonus', '0') or '0')
                skill_pmul = float(request.GET.get(f'{prefix}_pmul', '1') or '1')
                skill_combo = int(request.GET.get(f'{prefix}_combo', '1') or '1')

                total_pbonus = global_pbonus + skill_pbonus
                total_pmul = global_pmul * skill_pmul
                total_combo = global_combo + skill_combo - 1  # 基准都是1，相加后减1

                atk_eff = atk_val * (1 + 0.1 * atk_boost)
                def_eff = def_val * (1 + 0.1 * def_boost)
                power = skill.power + total_pbonus
                stab = 1.25 if is_stab else 1.0
                effective_power = power * stab * total_pmul * multiplier

                dmg = int(_round(atk_eff * effective_power * 37 / 41) / def_eff) if def_eff > 0 else 0
                dmg = dmg * total_combo
                target_hp = def_hp if side == 'att' else att_hp
                pct = int(dmg / target_hp * 100) if target_hp > 0 else 0

                pct_class = 'hp-green' if pct < 30 else ('hp-yellow' if pct < 60 else 'hp-red')
                if dmg >= target_hp:
                    pct_class = 'hp-red'

                result['name'] = f'{skill.name} [{skill.power}]'
                result['damage'] = dmg
                result['percent'] = min(pct, 100)
                result['pct_class'] = pct_class
                result['element'] = skill.element.name
                result['category'] = skill.category
                result['is_stab'] = is_stab
                result['multiplier'] = multiplier
                result['type_details'] = type_details

            results.append(result)

    return render(request, 'pvp/damage_results.html', {
        'attacker': attacker, 'defender': defender,
        'att_hp': atk_final['hp'], 'def_hp': def_hp,
        'results': results,
    })
