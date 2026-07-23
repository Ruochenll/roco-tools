from django.db import models


class ElementType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='属性名称')
    icon = models.CharField(max_length=100, blank=True, verbose_name='图标文件名')

    class Meta:
        verbose_name = '属性'
        verbose_name_plural = '属性'
        ordering = ['name']

    def __str__(self):
        return self.name


class TypeMatchup(models.Model):
    attacking_type = models.ForeignKey(
        ElementType, on_delete=models.CASCADE,
        related_name='attacking_matchups', verbose_name='攻击方属性'
    )
    defending_type = models.ForeignKey(
        ElementType, on_delete=models.CASCADE,
        related_name='defending_matchups', verbose_name='防御方属性'
    )
    multiplier = models.FloatField(verbose_name='倍率')

    class Meta:
        verbose_name = '属性克制'
        verbose_name_plural = '属性克制'
        unique_together = ['attacking_type', 'defending_type']

    def __str__(self):
        return f'{self.attacking_type.name} → {self.defending_type.name}: {self.multiplier}x'


class EggGroup(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='蛋组名称')

    class Meta:
        verbose_name = '蛋组'
        verbose_name_plural = '蛋组'
        ordering = ['name']

    def __str__(self):
        return self.name


class Pet(models.Model):
    number = models.IntegerField(default=0, verbose_name='编号')
    name = models.CharField(max_length=50, unique=True, verbose_name='名称')
    elements = models.ManyToManyField(ElementType, related_name='pets', verbose_name='属性')
    egg_groups = models.ManyToManyField(EggGroup, blank=True, related_name='pets', verbose_name='蛋组')
    ability_name = models.CharField(max_length=100, blank=True, verbose_name='特性名称')
    ability_effect = models.TextField(blank=True, verbose_name='特性效果')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    height_min = models.FloatField(verbose_name='身高最小值(m)')
    height_max = models.FloatField(verbose_name='身高最大值(m)')
    weight_min = models.FloatField(verbose_name='体重最小值(kg)')
    weight_max = models.FloatField(verbose_name='体重最大值(kg)')
    hp = models.IntegerField(verbose_name='生命')
    physical_attack = models.IntegerField(verbose_name='物攻')
    magical_attack = models.IntegerField(verbose_name='魔攻')
    physical_defense = models.IntegerField(verbose_name='物防')
    magical_defense = models.IntegerField(verbose_name='魔防')
    speed = models.IntegerField(verbose_name='速度')
    image = models.CharField(max_length=100, blank=True, verbose_name='图片文件名')
    ability_icon = models.CharField(max_length=100, blank=True, verbose_name='特性图标文件名')
    distribution = models.CharField(max_length=200, blank=True, verbose_name='分布地区')
    form = models.CharField(max_length=50, blank=True, verbose_name='形态')
    is_final = models.BooleanField(default=False, verbose_name='是否为最终形态')

    class Meta:
        verbose_name = '精灵'
        verbose_name_plural = '精灵'
        ordering = ['number', 'name']

    def __str__(self):
        return f'#{self.number} {self.name}'

    @property
    def stat_total(self):
        return self.hp + self.physical_attack + self.magical_attack + \
               self.physical_defense + self.magical_defense + self.speed


class Skill(models.Model):
    CATEGORY_CHOICES = [
        ('物攻', '物攻'),
        ('魔攻', '魔攻'),
        ('防御', '防御'),
        ('状态', '状态'),
    ]

    name = models.CharField(max_length=100, verbose_name='名称')
    element = models.ForeignKey(
        ElementType, on_delete=models.CASCADE,
        related_name='skills', verbose_name='属性'
    )
    category = models.CharField(
        max_length=10, choices=CATEGORY_CHOICES, verbose_name='类别'
    )
    power = models.IntegerField(default=0, verbose_name='威力')
    energy_cost = models.IntegerField(default=0, verbose_name='能耗')
    icon = models.CharField(max_length=100, blank=True, verbose_name='图标文件名')
    description = models.TextField(blank=True, verbose_name='效果描述')

    class Meta:
        verbose_name = '技能'
        verbose_name_plural = '技能'
        ordering = ['name']

    def __str__(self):
        return self.name


class PetSkill(models.Model):
    LEARN_METHOD_CHOICES = [
        ('升级', '升级'),
        ('血脉技能', '血脉技能'),
        ('技能石', '技能石'),
    ]

    pet = models.ForeignKey(
        Pet, on_delete=models.CASCADE,
        related_name='pet_skills', verbose_name='精灵'
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.CASCADE,
        related_name='pet_skills', verbose_name='技能'
    )
    learn_level = models.IntegerField(null=True, blank=True, verbose_name='学习等级')
    learn_method = models.CharField(
        max_length=20, choices=LEARN_METHOD_CHOICES, verbose_name='学习方式'
    )

    class Meta:
        verbose_name = '精灵技能'
        verbose_name_plural = '精灵技能'
        ordering = ['learn_method', 'learn_level']

    def __str__(self):
        level_str = f' Lv.{self.learn_level}' if self.learn_level else ''
        return f'{self.pet.name} - {self.skill.name} ({self.learn_method}{level_str})'


class Evolution(models.Model):
    pet_from = models.ForeignKey(
        Pet, on_delete=models.CASCADE,
        related_name='evolves_to', verbose_name='进化前'
    )
    pet_to = models.ForeignKey(
        Pet, on_delete=models.CASCADE,
        related_name='evolves_from', verbose_name='进化后'
    )
    condition = models.CharField(max_length=100, blank=True, verbose_name='进化条件')
    level = models.IntegerField(null=True, blank=True, verbose_name='所需等级')

    class Meta:
        verbose_name = '进化链'
        verbose_name_plural = '进化链'
        unique_together = ['pet_from', 'pet_to']

    def __str__(self):
        return f'{self.pet_from.name} → {self.pet_to.name}'
