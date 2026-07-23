from django.shortcuts import get_object_or_404, render
from .models import Pet, Skill, PetSkill, ElementType
from .utils import compute_type_matchups, build_evolution_tree


def pet_list(request):
    pets = Pet.objects.all().prefetch_related('elements')

    search = request.GET.get('search', '').strip()
    # Use getlist to correctly handle multiple checkbox values
    element_list = request.GET.getlist('elements', [])
    element_list = [e.strip() for e in element_list if e.strip()]

    if search:
        pets = pets.filter(name__icontains=search)

    if element_list:
        # AND logic: pet must have ALL selected elements
        for elem_name in element_list:
            pets = pets.filter(elements__name=elem_name)
        pets = pets.distinct()

    pets = pets.order_by('number', 'name')
    all_elements = ElementType.objects.all()

    # Pagination: 40 per page, infinite scroll
    page = int(request.GET.get('page', 1))
    per_page = 40
    total = pets.count()
    offset = (page - 1) * per_page
    has_more = (offset + per_page) < total
    next_page = page + 1
    pets = pets[offset:offset + per_page]

    # Build list of selected element objects for badge display
    selected_element_objs = []
    if element_list:
        selected_element_objs = [
            e for e in all_elements if e.name in element_list
        ]

    context = {
        'pets': pets,
        'all_elements': all_elements,
        'search': search,
        'selected_elements': element_list,
        'selected_element_objs': selected_element_objs,
        'page': page,
        'has_more': has_more,
        'next_page': next_page,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'pets/pet_list_partial.html', context)
    return render(request, 'pets/pet_list.html', context)


def pet_detail(request, pet_id):
    pet = get_object_or_404(
        Pet.objects.prefetch_related('elements', 'egg_groups'), pk=pet_id
    )

    # Skills grouped by learn_method
    pet_skills = pet.pet_skills.select_related('skill', 'skill__element').all()

    level_up_skills = [ps for ps in pet_skills if ps.learn_method == '升级']
    level_up_skills.sort(key=lambda x: x.learn_level or 0)

    bloodline_skills = [ps for ps in pet_skills if ps.learn_method == '血脉技能']
    stone_skills = [ps for ps in pet_skills if ps.learn_method == '技能石']

    # Evolution tree
    evolution_tree = build_evolution_tree(pet)

    # Type matchups
    elements = list(pet.elements.all())
    type_matchups = compute_type_matchups(elements) if elements else {}

    stat_max = 200
    stats = [
        ('生命', pet.hp, 'hp'),
        ('物攻', pet.physical_attack, 'pa'),
        ('魔攻', pet.magical_attack, 'ma'),
        ('物防', pet.physical_defense, 'pd'),
        ('魔防', pet.magical_defense, 'md'),
        ('速度', pet.speed, 'sp'),
    ]

    context = {
        'pet': pet,
        'stats': stats,
        'stat_max': stat_max,
        'level_up_skills': level_up_skills,
        'bloodline_skills': bloodline_skills,
        'stone_skills': stone_skills,
        'evolution_tree': evolution_tree,
        'type_matchups': type_matchups,
    }
    return render(request, 'pets/pet_detail.html', context)


def skill_list(request):
    skills = Skill.objects.select_related('element').all()

    search = request.GET.get('search', '').strip()
    element_names = request.GET.get('elements', '')
    categories = request.GET.get('categories', '')

    if search:
        skills = skills.filter(name__icontains=search)

    if element_names:
        element_list = [e.strip() for e in element_names.split(',') if e.strip()]
        for elem_name in element_list:
            skills = skills.filter(element__name=elem_name)
        skills = skills.distinct()

    if categories:
        cat_list = [c.strip() for c in categories.split(',') if c.strip()]
        skills = skills.filter(category__in=cat_list)

    skills = skills.order_by('name')
    all_elements = ElementType.objects.all()
    all_categories = Skill.CATEGORY_CHOICES

    # Pagination: 40 per page
    page = int(request.GET.get('page', 1))
    per_page = 40
    total = skills.count()
    offset = (page - 1) * per_page
    has_more = (offset + per_page) < total
    next_page = page + 1
    skills = skills[offset:offset + per_page]

    context = {
        'skills': skills,
        'all_elements': all_elements,
        'all_categories': all_categories,
        'search': search,
        'selected_elements': element_names,
        'selected_categories': categories,
        'page': page,
        'has_more': has_more,
        'next_page': next_page,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'pets/skill_list_partial.html', context)
    return render(request, 'pets/skill_list.html', context)


def skill_detail(request, skill_id):
    skill = get_object_or_404(Skill.objects.select_related('element'), pk=skill_id)

    pet_skills = PetSkill.objects.filter(
        skill=skill
    ).select_related('pet').order_by('learn_method', 'learn_level')

    level_up = [ps for ps in pet_skills if ps.learn_method == '升级']
    bloodline = [ps for ps in pet_skills if ps.learn_method == '血脉技能']
    stone = [ps for ps in pet_skills if ps.learn_method == '技能石']

    context = {
        'skill': skill,
        'level_up_pets': level_up,
        'bloodline_pets': bloodline,
        'stone_pets': stone,
    }
    return render(request, 'pets/skill_detail.html', context)


def type_calc(request):
    all_elements = ElementType.objects.all()

    primary = request.GET.get('primary', '')
    secondary = request.GET.get('secondary', '')

    defending = []
    primary_obj = None
    secondary_obj = None

    if primary:
        primary_obj = ElementType.objects.filter(name=primary).first()
        if primary_obj:
            defending.append(primary_obj)
    if secondary:
        secondary_obj = ElementType.objects.filter(name=secondary).first()
        if secondary_obj:
            defending.append(secondary_obj)

    tiers = {3.0: [], 2.0: [], 0.5: [], 0.25: []}
    if defending:
        tiers = compute_type_matchups(defending)

    context = {
        'all_elements': all_elements,
        'primary': primary,
        'secondary': secondary,
        'primary_obj': primary_obj,
        'secondary_obj': secondary_obj,
        'tiers': tiers,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'pets/type_calc_partial.html', context)
    return render(request, 'pets/type_calc.html', context)
