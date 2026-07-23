import json
import os
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from pets.models import ElementType, TypeMatchup, EggGroup, Pet, Skill, PetSkill, Evolution


from django.conf import settings as django_settings

MD_DIR = str(django_settings.BASE_DIR.parent / 'MD' / 's2_data')
MD_ROOT = str(django_settings.BASE_DIR.parent / 'MD')

# Hardcoded egg group names (no JSON data available)
EGG_GROUPS = [
    '动物组', '拟人组', '巨灵组', '魔力组', '天空组', '两栖组', '植物组',
    '大地组', '妖精组', '昆虫组', '软体组', '机械组', '海洋组', '龙组',
]

# 3 pets referenced in evolutions.json but missing from pets.json
# (BWIKI anti-scraping blocked these pages)
KNOWN_MISSING_PETS = {
    '樱桃饰品香草甜甜', '杨桃饰品香草甜甜', '蓝莓饰品香草甜甜',
}


class Command(BaseCommand):
    help = 'Import all game data from MD/*.json files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing data before importing',
        )

    def handle(self, *args, **options):
        from eggs.models import EggData, EggImage

        if options['clear']:
            self.stdout.write(self.style.WARNING('Deleting all existing data...'))
            from eggs.models import EggData, EggImage, EggTradeItem, EggTrade
            EggTradeItem.objects.all().delete()
            EggTrade.objects.all().delete()
            EggImage.objects.all().delete()
            EggData.objects.all().delete()
            PetSkill.objects.all().delete()
            Skill.objects.all().delete()
            Evolution.objects.all().delete()
            Pet.objects.all().delete()
            EggGroup.objects.all().delete()
            TypeMatchup.objects.all().delete()
            ElementType.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('All data cleared.'))

        # ---- Phase A: ElementType (18 records) ----
        self.stdout.write('Phase A: Importing ElementTypes...')
        with open(os.path.join(MD_DIR, 'elements.json'), 'r', encoding='utf-8') as f:
            elements_data = json.load(f)

        element_map = {}
        for item in elements_data:
            elem, _ = ElementType.objects.get_or_create(
                name=item['name'],
                defaults={'icon': item.get('icon', '')},
            )
            element_map[item['name']] = elem
        self.stdout.write(self.style.SUCCESS(f'  {len(element_map)} elements imported.'))

        # ---- Phase B: TypeMatchup (115 records) ----
        self.stdout.write('Phase B: Importing TypeMatchups...')
        with open(os.path.join(MD_DIR, 'type_matchups.json'), 'r', encoding='utf-8') as f:
            matchups_data = json.load(f)

        matchup_count = 0
        for item in matchups_data:
            atk = element_map.get(item['attacking_type'])
            defe = element_map.get(item['defending_type'])
            if atk and defe:
                TypeMatchup.objects.get_or_create(
                    attacking_type=atk,
                    defending_type=defe,
                    defaults={'multiplier': item['multiplier']},
                )
                matchup_count += 1
        self.stdout.write(self.style.SUCCESS(f'  {matchup_count} matchups imported.'))

        # ---- Phase C: Pet (456 records) ----
        self.stdout.write('Phase C: Importing Pets...')
        with open(os.path.join(MD_DIR, 'pets.json'), 'r', encoding='utf-8') as f:
            pets_data = json.load(f)

        pet_map = {}
        for idx, item in enumerate(pets_data, start=1):
            pet = Pet.objects.create(
                number=idx,
                name=item['name'],
                ability_name=item.get('ability_name', ''),
                ability_effect=item.get('ability_effect', ''),
                description=item.get('description', ''),
                height_min=item.get('height_min', 0),
                height_max=item.get('height_max', 0),
                weight_min=item.get('weight_min', 0),
                weight_max=item.get('weight_max', 0),
                hp=item.get('hp', 0),
                physical_attack=item.get('physical_attack', 0),
                magical_attack=item.get('magical_attack', 0),
                physical_defense=item.get('physical_defense', 0),
                magical_defense=item.get('magical_defense', 0),
                speed=item.get('speed', 0),
                image=item.get('image', ''),
                ability_icon=item.get('ability_icon', ''),
                distribution=item.get('distribution', ''),
                form=item.get('form', ''),
                is_final=item.get('is_final', False),
            )

            # Set M2M: elements
            elem_names = item.get('elements', [])
            for ename in elem_names:
                if ename in element_map:
                    pet.elements.add(element_map[ename])

            pet_map[item['name']] = pet
        self.stdout.write(self.style.SUCCESS(f'  {len(pet_map)} pets imported.'))

        # ---- Phase D: Skill (490 records) ----
        self.stdout.write('Phase D: Importing Skills...')
        with open(os.path.join(MD_DIR, 'skills.json'), 'r', encoding='utf-8') as f:
            skills_data = json.load(f)

        skill_map = {}
        for item in skills_data:
            elem = element_map.get(item['element'])
            if not elem:
                self.stdout.write(self.style.WARNING(
                    f'  Unknown element "{item["element"]}" for skill "{item["name"]}", skipping.'
                ))
                continue

            # Map JSON 'effect' -> model 'description'
            # Note: some JSON entries use 'effect' others 'description'
            desc = item.get('effect') or item.get('description', '')

            # Normalize category to valid choices
            category = item.get('category', '物攻')
            if category not in ('物攻', '魔攻', '防御', '状态'):
                if '魔' in category:
                    category = '魔攻'
                elif '物' in category:
                    category = '物攻'
                elif '防' in category:
                    category = '防御'
                else:
                    category = '状态'

            skill, _ = Skill.objects.get_or_create(
                name=item['name'],
                element=elem,
                defaults={
                    'category': category,
                    'power': item.get('power', 0),
                    'energy_cost': item.get('energy_cost', 0),
                    'icon': item.get('icon', ''),
                    'description': desc,
                },
            )
            skill_map[item['name']] = skill
        self.stdout.write(self.style.SUCCESS(f'  {len(skill_map)} skills imported.'))

        # ---- Phase E: PetSkill (20,115 records) ----
        self.stdout.write('Phase E: Importing PetSkills...')
        with open(os.path.join(MD_DIR, 'pet_skills.json'), 'r', encoding='utf-8') as f:
            pet_skills_data = json.load(f)

        to_create = []
        skipped = 0
        for item in pet_skills_data:
            pet = pet_map.get(item['pet_name'])
            skill = skill_map.get(item['skill_name'])
            if not pet or not skill:
                skipped += 1
                continue

            learn_method = item.get('learn_method', '升级')
            learn_level = item.get('learn_level')
            # Only 升级 has learn_level
            if learn_method != '升级':
                learn_level = None

            to_create.append(PetSkill(
                pet=pet,
                skill=skill,
                learn_method=learn_method,
                learn_level=learn_level,
            ))

        # Bulk create in batches
        batch_size = 500
        for i in range(0, len(to_create), batch_size):
            PetSkill.objects.bulk_create(to_create[i:i + batch_size], ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f'  {len(to_create)} pet-skills imported, {skipped} skipped.'))

        # ---- Phase F: Evolution (276 records) ----
        self.stdout.write('Phase F: Importing Evolutions...')
        with open(os.path.join(MD_DIR, 'evolutions.json'), 'r', encoding='utf-8') as f:
            evolutions_data = json.load(f)

        evo_count = 0
        evo_skipped = 0
        for item in evolutions_data:
            pet_from_name = item.get('pet_from', '')
            pet_to_name = item.get('pet_to', '')

            if not pet_from_name or not pet_to_name:
                evo_skipped += 1
                continue

            pet_from = pet_map.get(pet_from_name)
            pet_to = pet_map.get(pet_to_name)

            if pet_from_name in KNOWN_MISSING_PETS:
                self.stdout.write(self.style.WARNING(
                    f'  WARNING: "{pet_from_name}" missing from pets.json (BWIKI anti-scrape), skipping evolution.'
                ))
                evo_skipped += 1
                continue
            if pet_to_name in KNOWN_MISSING_PETS:
                self.stdout.write(self.style.WARNING(
                    f'  WARNING: "{pet_to_name}" missing from pets.json (BWIKI anti-scrape), skipping evolution.'
                ))
                evo_skipped += 1
                continue

            if not pet_from or not pet_to:
                if pet_from_name not in KNOWN_MISSING_PETS and pet_to_name not in KNOWN_MISSING_PETS:
                    self.stdout.write(self.style.WARNING(
                        f'  WARNING: Cannot find pet(s) for evolution: {pet_from_name} → {pet_to_name}'
                    ))
                evo_skipped += 1
                continue

            Evolution.objects.get_or_create(
                pet_from=pet_from,
                pet_to=pet_to,
                defaults={'condition': item.get('condition', '')},
            )
            evo_count += 1

        self.stdout.write(self.style.SUCCESS(f'  {evo_count} evolutions imported, {evo_skipped} skipped.'))

        # ---- Phase G: EggGroup (14 records) ----
        self.stdout.write('Phase G: Importing EggGroups...')
        for name in EGG_GROUPS:
            EggGroup.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS(f'  {len(EGG_GROUPS)} egg groups imported.'))

        # ---- Phase H: EggData (from egg_data.json) ----
        self.stdout.write('Phase H: Importing EggData...')
        egg_data_path = os.path.join(MD_ROOT, 'egg_data.json')
        if os.path.exists(egg_data_path):
            with open(egg_data_path, 'r', encoding='utf-8') as f:
                egg_data_list = json.load(f)

            egg_count = 0
            egg_skipped = 0
            for item in egg_data_list:
                pet = pet_map.get(item['pet_name'])
                if not pet:
                    self.stdout.write(self.style.WARNING(
                        f'  WARNING: Pet "{item["pet_name"]}" not found for EggData, skipping.'
                    ))
                    egg_skipped += 1
                    continue

                EggData.objects.get_or_create(
                    pet=pet,
                    defaults={
                        'height_min': item['height_min'],
                        'height_max': item['height_max'],
                        'weight_min': item['weight_min'],
                        'weight_max': item['weight_max'],
                    },
                )
                egg_count += 1

            self.stdout.write(self.style.SUCCESS(f'  {egg_count} egg data imported, {egg_skipped} skipped.'))
        else:
            self.stdout.write(self.style.WARNING('  egg_data.json not found, skipping.'))

        # ---- Phase I: Egg Images (from egg_images.json) ----
        self.stdout.write('Phase I: Importing Egg Images...')
        egg_images_path = os.path.join(MD_ROOT, 'egg_images.json')
        if os.path.exists(egg_images_path):
            with open(egg_images_path, 'r', encoding='utf-8') as f:
                egg_images_data = json.load(f)

            egg_img_count = 0
            for item in egg_images_data:
                pet = pet_map.get(item['name'])
                if pet:
                    EggImage.objects.get_or_create(
                        pet=pet,
                        defaults={'image': item.get('image', '')},
                    )
                    egg_img_count += 1

            self.stdout.write(self.style.SUCCESS(f'  {egg_img_count} egg images assigned.'))
        else:
            self.stdout.write(self.style.WARNING('  egg_images.json not found, skipping.'))

        self.stdout.write(self.style.SUCCESS('\n=== Data import complete! ==='))
