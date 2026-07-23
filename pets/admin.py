from django.contrib import admin
from .models import ElementType, TypeMatchup, EggGroup, Pet, Skill, PetSkill, Evolution


@admin.register(ElementType)
class ElementTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon']
    search_fields = ['name']


@admin.register(TypeMatchup)
class TypeMatchupAdmin(admin.ModelAdmin):
    list_display = ['attacking_type', 'defending_type', 'multiplier']
    list_filter = ['attacking_type', 'defending_type', 'multiplier']
    search_fields = ['attacking_type__name', 'defending_type__name']


@admin.register(EggGroup)
class EggGroupAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


class PetSkillInline(admin.TabularInline):
    model = PetSkill
    extra = 0
    raw_id_fields = ['skill']


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'form', 'is_final', 'stat_total_display']
    list_filter = ['elements', 'is_final', 'form']
    search_fields = ['name', 'number']
    filter_horizontal = ['elements', 'egg_groups']

    @admin.display(description='种族值和')
    def stat_total_display(self, obj):
        return obj.stat_total


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'element', 'category', 'power', 'energy_cost']
    list_filter = ['element', 'category']
    search_fields = ['name']


@admin.register(PetSkill)
class PetSkillAdmin(admin.ModelAdmin):
    list_display = ['pet', 'skill', 'learn_method', 'learn_level']
    list_filter = ['learn_method']
    search_fields = ['pet__name', 'skill__name']
    raw_id_fields = ['pet', 'skill']


@admin.register(Evolution)
class EvolutionAdmin(admin.ModelAdmin):
    list_display = ['pet_from', 'pet_to', 'condition']
    search_fields = ['pet_from__name', 'pet_to__name']
    raw_id_fields = ['pet_from', 'pet_to']
