from django.contrib import admin
from .models import TeamTemplate, TeamPet, TeamPetSkill


class TeamPetSkillInline(admin.TabularInline):
    model = TeamPetSkill
    extra = 0


class TeamPetInline(admin.TabularInline):
    model = TeamPet
    extra = 0


@admin.register(TeamTemplate)
class TeamTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_popular', 'created_at']
    list_filter = ['is_popular']
    search_fields = ['name']
    inlines = [TeamPetInline]
