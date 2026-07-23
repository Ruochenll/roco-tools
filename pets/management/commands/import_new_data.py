import json
import os

from django.core.management.base import BaseCommand
from django.db.models import Max

from pets.models import ElementType, Pet, Skill, PetSkill, Evolution

from django.conf import settings

NEW_DATA_DIR = str(settings.BASE_DIR / 'MD' / '新精灵图鉴数据整理')


class Command(BaseCommand):
    help = 'Import new game data from MD/新精灵图鉴数据整理/'

    def handle(self, *args, **options):
        # Load existing lookup data
        element_map = {e.name: e for e in ElementType.objects.all()}
        pet_map = {p.name: p for p in Pet.objects.all()}
        skill_map = {s.name: s for s in Skill.objects.all()}

        # ---- Phase A: New Skills ----
        self.stdout.write('Phase A: Importing new skills...')
        skills_path = os.path.join(NEW_DATA_DIR, 'new_skills.json')
        with open(skills_path, 'r', encoding='utf-8') as f:
            skills_data = json.load(f)

        new_skill_count = 0
        for item in skills_data:
            elem = element_map.get(item['element'])
            if not elem:
                self.stdout.write(self.style.WARNING(
                    f'  Unknown element "{item["element"]}" for "{item["name"]}", skipping.'
                ))
                continue
            _, created = Skill.objects.get_or_create(
                name=item['name'],
                element=elem,
                defaults={
                    'category': item.get('category', '物攻'),
                    'power': item.get('power', 0),
                    'energy_cost': item.get('energy_cost', 0),
                    'icon': item.get('icon', ''),
                    'description': item.get('effect', ''),
                },
            )
            if created:
                new_skill_count += 1
                skill_map[item['name']] = _
            else:
                skill_map[item['name']] = _

        self.stdout.write(self.style.SUCCESS(f'  {new_skill_count} new skills imported '
                                              f'({len(skills_data) - new_skill_count} already existed).'))

        # ---- Phase B: New Pets ----
        self.stdout.write('Phase B: Importing new pets...')
        pets_path = os.path.join(NEW_DATA_DIR, 'new_pets.json')
        with open(pets_path, 'r', encoding='utf-8') as f:
            pets_data = json.load(f)

        max_num = Pet.objects.aggregate(Max('number'))['number__max'] or 0
        new_pet_count = 0

        for idx, item in enumerate(pets_data, start=max_num + 1):
            pet, created = Pet.objects.get_or_create(
                name=item['name'],
                defaults={
                    'number': idx,
                    'ability_name': item.get('ability_name') or '',
                    'ability_effect': item.get('ability_effect') or '',
                    'description': item.get('description') or '',
                    'height_min': item.get('height_min') or 0,
                    'height_max': item.get('height_max') or 0,
                    'weight_min': item.get('weight_min') or 0,
                    'weight_max': item.get('weight_max') or 0,
                    'hp': item.get('hp') or 0,
                    'physical_attack': item.get('physical_attack') or 0,
                    'magical_attack': item.get('magical_attack') or 0,
                    'physical_defense': item.get('physical_defense') or 0,
                    'magical_defense': item.get('magical_defense') or 0,
                    'speed': item.get('speed') or 0,
                    'image': item.get('image') or '',
                    'ability_icon': item.get('ability_icon') or '',
                    'distribution': item.get('distribution') or '',
                    'form': item.get('form') or '',
                    'is_final': item.get('is_final') or False,
                },
            )
            if created:
                new_pet_count += 1

            # Set M2M elements
            for ename in item.get('elements', []):
                if ename in element_map:
                    pet.elements.add(element_map[ename])

            pet_map[item['name']] = pet

        self.stdout.write(self.style.SUCCESS(f'  {new_pet_count} new pets imported '
                                              f'(numbers {max_num + 1}–{max_num + len(pets_data)}).'))

        # ---- Phase C: New Pet-Skill Associations ----
        self.stdout.write('Phase C: Importing new pet-skill associations...')
        ps_path = os.path.join(NEW_DATA_DIR, 'new_pet_skills.json')
        with open(ps_path, 'r', encoding='utf-8') as f:
            ps_data = json.load(f)

        to_create = []
        skipped = 0
        for item in ps_data:
            pet = pet_map.get(item['pet_name'])
            skill = skill_map.get(item['skill_name'])
            if not pet:
                self.stdout.write(self.style.WARNING(
                    f'  WARNING: Pet "{item["pet_name"]}" not found, skipping skill "{item["skill_name"]}".'
                ))
                skipped += 1
                continue
            if not skill:
                self.stdout.write(self.style.WARNING(
                    f'  WARNING: Skill "{item["skill_name"]}" not found, skipping for "{item["pet_name"]}".'
                ))
                skipped += 1
                continue

            learn_method = item.get('learn_method', '升级')
            learn_level = item.get('learn_level')
            if learn_method != '升级':
                learn_level = None

            to_create.append(PetSkill(
                pet=pet,
                skill=skill,
                learn_method=learn_method,
                learn_level=learn_level,
            ))

        batch_size = 500
        for i in range(0, len(to_create), batch_size):
            PetSkill.objects.bulk_create(
                to_create[i:i + batch_size], ignore_conflicts=True
            )

        self.stdout.write(self.style.SUCCESS(
            f'  {len(to_create)} pet-skills imported, {skipped} skipped.'
        ))

        # ---- Phase D: New Evolutions ----
        self.stdout.write('Phase D: Importing new evolutions...')
        evo_path = os.path.join(NEW_DATA_DIR, 'new_evolutions.json')
        with open(evo_path, 'r', encoding='utf-8') as f:
            evo_data = json.load(f)

        evo_count = 0
        evo_skipped = 0
        for item in evo_data:
            pet_from = pet_map.get(item['pet_from'])
            pet_to = pet_map.get(item['pet_to'])
            if not pet_from or not pet_to:
                self.stdout.write(self.style.WARNING(
                    f'  WARNING: Cannot resolve {item["pet_from"]} → {item["pet_to"]}, skipping.'
                ))
                evo_skipped += 1
                continue

            _, created = Evolution.objects.get_or_create(
                pet_from=pet_from,
                pet_to=pet_to,
                defaults={'condition': item.get('condition', '')},
            )
            if created:
                evo_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'  {evo_count} new evolutions imported, {evo_skipped} skipped.'
        ))

        self.stdout.write(self.style.SUCCESS('\n=== New data import complete! ==='))
        self.stdout.write(f'  Total pets: {Pet.objects.count()}')
        self.stdout.write(f'  Total skills: {Skill.objects.count()}')
        self.stdout.write(f'  Total evolutions: {Evolution.objects.count()}')
