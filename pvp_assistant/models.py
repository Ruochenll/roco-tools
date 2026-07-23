"""PVP 阵容模板模型（Admin 管理热门阵容，用户端只读）。"""

from django.db import models
from pets.models import Pet, Skill


class TeamTemplate(models.Model):
    """精灵阵容模板（仅 Admin 可管理）。"""
    name = models.CharField(max_length=100, verbose_name='阵容名称')
    description = models.TextField(blank=True, verbose_name='备注')
    is_popular = models.BooleanField(
        default=False, verbose_name='热门阵容',
        help_text='勾选后在敌方热门阵容下拉中可选',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '阵容模板'
        verbose_name_plural = '阵容模板'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def to_frontend(self):
        """序列化为前端可用的 JSON。"""
        return {
            'id': self.id,
            'name': self.name,
            'pets': [tp.to_frontend() for tp in
                     self.pets.all().select_related('pet')
                     .prefetch_related('skills__skill', 'skills__skill__element')],
        }


class TeamPet(models.Model):
    """模板中的一只精灵（含完整培养配置）。"""
    NATURE_CHOICES = [
        ('', '无'),
        ('hp', '生命'), ('physical_attack', '物攻'), ('magical_attack', '魔攻'),
        ('physical_defense', '物防'), ('magical_defense', '魔防'), ('speed', '速度'),
    ]

    template = models.ForeignKey(TeamTemplate, on_delete=models.CASCADE, related_name='pets')
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField(verbose_name='位置 (1-6)')

    level = models.PositiveSmallIntegerField(default=60, verbose_name='等级')
    star = models.PositiveSmallIntegerField(default=5, verbose_name='星级')
    growth = models.PositiveSmallIntegerField(default=0, verbose_name='成长')

    talent_hp = models.PositiveSmallIntegerField(default=5)
    talent_pa = models.PositiveSmallIntegerField(default=5)
    talent_ma = models.PositiveSmallIntegerField(default=5)
    talent_pd = models.PositiveSmallIntegerField(default=5)
    talent_md = models.PositiveSmallIntegerField(default=5)
    talent_sp = models.PositiveSmallIntegerField(default=5)

    nature_up = models.CharField(max_length=20, blank=True, choices=NATURE_CHOICES, default='')
    nature_down = models.CharField(max_length=20, blank=True, choices=NATURE_CHOICES, default='')

    class Meta:
        verbose_name = '阵容精灵'
        verbose_name_plural = '阵容精灵'
        ordering = ['position']

    def __str__(self):
        return f'{self.template.name} - {self.pet.name} (#{self.position})'

    def to_frontend(self):
        return {
            'pet_id': self.pet_id,
            'pet_name': self.pet.name,
            'image': self.pet.image or '',
            'number': self.pet.number,
            'elements': [e.name for e in self.pet.elements.all()],
            'hp': self.pet.hp, 'physical_attack': self.pet.physical_attack,
            'magical_attack': self.pet.magical_attack,
            'physical_defense': self.pet.physical_defense,
            'magical_defense': self.pet.magical_defense, 'speed': self.pet.speed,
            'level': self.level, 'star': self.star, 'growth': self.growth,
            'talent_hp': self.talent_hp, 'talent_pa': self.talent_pa,
            'talent_ma': self.talent_ma, 'talent_pd': self.talent_pd,
            'talent_md': self.talent_md, 'talent_sp': self.talent_sp,
            'nature_up': self.nature_up, 'nature_down': self.nature_down,
            'skills': [
                {'id': ts.skill_id, 'name': ts.skill.name,
                 'power': ts.skill.power, 'element': ts.skill.element.name,
                 'category': ts.skill.category, 'energy': ts.skill.energy_cost}
                for ts in self.skills.all().select_related('skill', 'skill__element')
            ],
        }


class TeamPetSkill(models.Model):
    """模板精灵携带的技能（4个槽位）。"""
    team_pet = models.ForeignKey(TeamPet, on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    slot = models.PositiveSmallIntegerField(verbose_name='技能槽 (1-4)')

    class Meta:
        verbose_name = '精灵技能'
        verbose_name_plural = '精灵技能'
        ordering = ['slot']
        unique_together = [('team_pet', 'slot')]
