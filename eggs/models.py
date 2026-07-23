from django.conf import settings
from django.db import models
from pets.models import Pet


class EggData(models.Model):
    """孵蛋匹配表 — 蛋的身高体重范围对应可孵化的精灵"""
    pet = models.ForeignKey(
        Pet, on_delete=models.CASCADE,
        related_name='egg_data', verbose_name='精灵'
    )
    height_min = models.FloatField(verbose_name='蛋身高最小值(m)')
    height_max = models.FloatField(verbose_name='蛋身高最大值(m)')
    weight_min = models.FloatField(verbose_name='蛋体重最小值(kg)')
    weight_max = models.FloatField(verbose_name='蛋体重最大值(kg)')

    class Meta:
        verbose_name = '孵蛋数据'
        verbose_name_plural = '孵蛋数据'

    def __str__(self):
        return f'{self.pet.name} 蛋: {self.height_min}-{self.height_max}m / {self.weight_min}-{self.weight_max}kg'


class EggImage(models.Model):
    """精灵蛋图片表 — 精灵对应的蛋图片"""
    pet = models.OneToOneField(
        Pet, on_delete=models.CASCADE,
        related_name='egg_image', verbose_name='精灵'
    )
    image = models.CharField(max_length=100, verbose_name='蛋图片文件名')

    class Meta:
        verbose_name = '蛋图片'
        verbose_name_plural = '蛋图片'

    def __str__(self):
        return f'{self.pet.name} 的蛋图片'


class EggTrade(models.Model):
    """交换信息表"""
    STATUS_CHOICES = [
        ('active', '活跃'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    publisher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='egg_trades', verbose_name='发布者'
    )
    game_uid = models.CharField(max_length=50, verbose_name='游戏UID')
    notes = models.TextField(blank=True, verbose_name='备注')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='active', verbose_name='状态'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='发布时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '交换信息'
        verbose_name_plural = '交换信息'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.publisher.username} 的交换 (#{self.id})'


class EggTradeItem(models.Model):
    """交换条目表"""
    ITEM_TYPE_CHOICES = [
        ('offer', '我拥有'),
        ('want', '我想要'),
    ]

    trade = models.ForeignKey(
        EggTrade, on_delete=models.CASCADE,
        related_name='items', verbose_name='所属交换'
    )
    pet = models.ForeignKey(
        Pet, on_delete=models.CASCADE,
        related_name='trade_items', verbose_name='精灵蛋'
    )
    item_type = models.CharField(
        max_length=10, choices=ITEM_TYPE_CHOICES, verbose_name='类型'
    )

    class Meta:
        verbose_name = '交换条目'
        verbose_name_plural = '交换条目'

    def __str__(self):
        return f'{self.get_item_type_display()}: {self.pet.name}'
