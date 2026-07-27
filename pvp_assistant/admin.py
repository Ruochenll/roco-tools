from django.contrib import admin
from django import forms
from .models import TeamTemplate, TeamPet, TeamPetSkill


class TeamPetSkillInline(admin.TabularInline):
    model = TeamPetSkill
    extra = 0


class TeamPetInline(admin.TabularInline):
    model = TeamPet
    extra = 0


class TeamTemplateForm(forms.ModelForm):
    roster_code = forms.CharField(
        label='阵容码导入', required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'style': 'width:100%'}),
        help_text='粘贴阵容码(B~...~)，自动填充精灵和技能。留空则手动录入。',
    )

    class Meta:
        model = TeamTemplate
        fields = '__all__'


@admin.register(TeamTemplate)
class TeamTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_popular', 'created_at']
    list_filter = ['is_popular']
    search_fields = ['name']
    inlines = [TeamPetInline]
    form = TeamTemplateForm

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        code = form.cleaned_data.get('roster_code', '').strip()
        if code and not change:  # 仅新建时生效
            self._import_from_roster(obj, code)

    def _import_from_roster(self, template, raw_code):
        """从阵容码解析并创建 TeamPet + TeamPetSkill (含天分/性格)。"""
        from .roster_decoder import format_roster
        from .views_team import PERSONALITY_MAP
        from pets.models import Pet, Skill

        # 提取纯码
        filtered = ''.join(c for c in raw_code if c.isascii() and (c.isalnum() or c in '~_'))
        idx = filtered.find('B~') if 'B~' in filtered else filtered.find('b~')
        code = filtered[idx:] if idx != -1 else filtered

        try:
            roster = format_roster(code)
        except Exception:
            return

        IV_STAT_MAP = {1: 'talent_hp', 2: 'talent_pa', 3: 'talent_ma',
                       4: 'talent_pd', 5: 'talent_md', 6: 'talent_sp'}

        for pos, entry in enumerate(roster, 1):
            pet = Pet.objects.filter(name=entry.get('sprite')).first()
            if not pet:
                continue

            # 天分: 基础0, 三条IV各+10
            talents = {'talent_hp': 0, 'talent_pa': 0, 'talent_ma': 0,
                       'talent_pd': 0, 'talent_md': 0, 'talent_sp': 0}
            for v in entry.get('ivs', []):
                if v is not None:
                    key = IV_STAT_MAP.get(v - 78)
                    if key:
                        talents[key] = 10

            # 性格
            personality = entry.get('personality', '')
            nature_up = nature_down = ''
            if personality in PERSONALITY_MAP:
                nature_up, nature_down = PERSONALITY_MAP[personality]

            tp = TeamPet.objects.create(
                template=template, pet=pet, position=pos,
                talent_hp=talents['talent_hp'], talent_pa=talents['talent_pa'],
                talent_ma=talents['talent_ma'], talent_pd=talents['talent_pd'],
                talent_md=talents['talent_md'], talent_sp=talents['talent_sp'],
                nature_up=nature_up, nature_down=nature_down,
            )
            for slot, sname in enumerate(entry.get('skills', []), 1):
                if sname:
                    sk = Skill.objects.filter(name=sname).first()
                    if sk:
                        TeamPetSkill.objects.create(
                            team_pet=tp, skill=sk, slot=slot,
                        )
