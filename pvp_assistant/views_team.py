"""PVP 战斗计算器 视图。"""

import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from pets.models import Pet, Skill
from .models import TeamTemplate
from .roster_decoder import format_roster

# 性格 → (加成stat, 削弱stat)
PERSONALITY_MAP = {
    '沉默': ('hp', 'physical_attack'), '平和': ('hp', 'magical_attack'),
    '忧郁': ('hp', 'physical_defense'), '粗心': ('hp', 'magical_defense'),
    '踏实': ('hp', 'speed'),
    '大胆': ('physical_attack', 'physical_defense'), '调皮': ('physical_attack', 'magical_defense'),
    '勇敢': ('physical_attack', 'speed'), '逞强': ('physical_attack', 'hp'),
    '固执': ('physical_attack', 'magical_attack'),
    '聪明': ('magical_attack', 'physical_attack'), '专注': ('magical_attack', 'physical_defense'),
    '偏执': ('magical_attack', 'magical_defense'), '冷静': ('magical_attack', 'speed'),
    '理性': ('magical_attack', 'hp'),
    '胆小': ('speed', 'physical_attack'), '开朗': ('speed', 'magical_attack'),
    '急躁': ('speed', 'physical_defense'), '莽撞': ('speed', 'magical_defense'),
    '热情': ('speed', 'hp'),
    '稳重': ('physical_defense', 'physical_attack'), '天真': ('physical_defense', 'magical_attack'),
    '悠闲': ('physical_defense', 'speed'), '懒散': ('physical_defense', 'magical_defense'),
    '坦率': ('physical_defense', 'hp'),
    '警惕': ('magical_defense', 'physical_attack'), '害羞': ('magical_defense', 'magical_attack'),
    '温顺': ('magical_defense', 'physical_defense'), '慎重': ('magical_defense', 'speed'),
    '焦虑': ('magical_defense', 'hp'),
}


def battle_calc(request):
    """新的阵容对战计算器页面。"""
    popular_teams = TeamTemplate.objects.filter(is_popular=True).order_by('name')
    return render(request, 'pvp/battle_calc.html', {
        'popular_teams': popular_teams,
    })


@require_POST
def api_import_roster(request):
    """阵容码解析 → 返回 JSON 精灵列表。"""
    code = request.POST.get('code', '').strip()
    if not code:
        return JsonResponse({'error': '请输入阵容码'}, status=400)
    try:
        roster = format_roster(code)
    except Exception as e:
        return JsonResponse({'error': f'解析失败: {e}'}, status=400)

    result = []
    for entry in roster:
        sprite_name = entry.get('sprite')
        pet = Pet.objects.filter(name=sprite_name).first() if sprite_name else None
        skills = []
        for sname in entry.get('skills', []):
            if sname:
                sk = Skill.objects.filter(name=sname).first()
                if sk:
                    skills.append({'id': sk.id, 'name': sk.name, 'power': sk.power,
                                   'element': sk.element.name, 'category': sk.category})

        # 天分: 基础0, 三条IV各+10
        IV_STAT_MAP = {1: 'talent_hp', 2: 'talent_pa', 3: 'talent_ma',
                       4: 'talent_pd', 5: 'talent_md', 6: 'talent_sp'}
        talents = {'talent_hp': 0, 'talent_pa': 0, 'talent_ma': 0,
                   'talent_pd': 0, 'talent_md': 0, 'talent_sp': 0}
        ivs = entry.get('ivs', [])
        for v in ivs:
            if v is None:
                continue
            talent_key = IV_STAT_MAP.get(v - 78)
            if talent_key:
                talents[talent_key] = 10

        # 性格 → nature_up / nature_down
        personality = entry.get('personality', '')
        nature_up = ''
        nature_down = ''
        if personality in PERSONALITY_MAP:
            nature_up, nature_down = PERSONALITY_MAP[personality]

        result.append({
            'sprite': sprite_name,
            'pet_id': pet.id if pet else None,
            'pet_name': pet.name if pet else (sprite_name or '未知'),
            'personality': personality,
            'image': pet.image if pet else '',
            'number': pet.number if pet else 0,
            'elements': [e.name for e in pet.elements.all()] if pet else [],
            'skills': skills,
            'hp': pet.hp if pet else 0,
            'physical_attack': pet.physical_attack if pet else 0,
            'magical_attack': pet.magical_attack if pet else 0,
            'physical_defense': pet.physical_defense if pet else 0,
            'magical_defense': pet.magical_defense if pet else 0,
            'speed': pet.speed if pet else 0,
            **talents,
            'nature_up': nature_up,
            'nature_down': nature_down,
        })
    return JsonResponse({'roster': result})


def api_popular_team(request, team_id):
    """加载热门阵容 → JSON。"""
    team = get_object_or_404(TeamTemplate, pk=team_id)
    return JsonResponse({'team': team.to_frontend()})


def api_pet_search(request):
    """精灵搜索 → 返回 JSON。"""
    q = request.GET.get('q', '').strip()
    pets = Pet.objects.all().order_by('number')
    if q:
        pets = pets.filter(name__icontains=q)
    results = []
    for pet in pets[:30]:
        results.append({
            'id': pet.id,
            'name': pet.name,
            'number': pet.number,
            'image': pet.image or '',
            'elements': [e.name for e in pet.elements.all()],
            'hp': pet.hp, 'physical_attack': pet.physical_attack,
            'magical_attack': pet.magical_attack,
            'physical_defense': pet.physical_defense,
            'magical_defense': pet.magical_defense, 'speed': pet.speed,
        })
    return JsonResponse({'pets': results})
